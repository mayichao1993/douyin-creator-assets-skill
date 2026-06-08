#!/usr/bin/env python3
"""Build an agent-neutral handoff package for 2B media understanding."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from output_names import existing_output_path, mirror_legacy, output_path


SCHEMA_FIELDS = [
    "作品ID",
    "作品标题",
    "四项互动锚点",
    "媒体类型",
    "视频文件",
    "图片文件",
    "图片清单文件",
    "抽帧图",
    "S层命中人群",
    "前三秒",
    "不划走理由",
    "前三秒文案类型",
    "三秒停留技巧",
    "后文是否接住前三秒",
    "中段停留机制",
    "媒体核心内容",
    "口播/字幕依据",
    "画面重点",
    "商品出现方式",
    "达人说服方式",
    "内容真实感",
    "点赞为什么高/低",
    "评论为什么高/低",
    "收藏为什么高/低",
    "分享为什么高/低",
    "品类连接来源",
    "下一步评论验证点",
]

METRIC_FIELDS = ["点赞数", "评论数", "收藏数", "分享数", "总互动"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a provider-neutral 2B media understanding handoff from downloaded media and frame grids."
    )
    parser.add_argument("run_dir", help="A outputs/douyin_creator_assets/<timestamp> directory.")
    parser.add_argument("--candidates", default="video_sample_candidates.csv")
    parser.add_argument("--downloads", default="downloaded_videos.csv")
    parser.add_argument("--grids", default="video_frame_grids.csv")
    parser.add_argument(
        "--transcript-dir",
        default="",
        help="Optional directory containing transcript files. Defaults to run_dir.",
    )
    return parser.parse_args()


def read_csv_if_exists(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def text(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = str(row.get(name) or "").strip()
        if value:
            return value
    return ""


def id_from_path(path_text: str) -> str:
    stem = Path(path_text).stem
    if stem.endswith("_grid"):
        stem = stem[:-5]
    if stem.endswith("_images"):
        stem = stem[:-7]
    if stem.startswith("2b_"):
        return stem[3:]
    return stem


def normalize_path(run_dir: Path, path_text: str) -> str:
    if not path_text:
        return ""
    path = Path(path_text)
    if path.is_absolute():
        return str(path)
    if path.exists():
        return str(path.resolve())
    candidate = run_dir / path
    if candidate.exists():
        return str(candidate.resolve())
    return str(path)


def index_downloads(run_dir: Path, rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        aweme_id = text(row, "作品ID", "aweme_id")
        if aweme_id:
            indexed[aweme_id] = row
    for video_path in sorted(run_dir.glob("2b_*.mp4")):
        aweme_id = id_from_path(str(video_path))
        indexed.setdefault(aweme_id, {})
        indexed[aweme_id].setdefault("视频文件", str(video_path))
        indexed[aweme_id].setdefault("媒体类型", "video")
        indexed[aweme_id].setdefault("下载状态", "已存在")
    for manifest_path in sorted(run_dir.glob("2b_*_images.json")):
        aweme_id = id_from_path(str(manifest_path))
        indexed.setdefault(aweme_id, {})
        indexed[aweme_id].setdefault("图片清单文件", str(manifest_path))
        indexed[aweme_id].setdefault("媒体类型", "image")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            image_files = manifest.get("image_files") or []
            if isinstance(image_files, list):
                indexed[aweme_id].setdefault("图片文件", "；".join(str(path) for path in image_files))
        except Exception:
            pass
    return indexed


def index_grids(run_dir: Path, rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        grid = text(row, "抽帧图")
        video = text(row, "视频文件")
        aweme_id = id_from_path(grid or video)
        if aweme_id:
            indexed[aweme_id] = row
    for grid_path in sorted(run_dir.glob("2b_*_grid.jpg")):
        aweme_id = id_from_path(str(grid_path))
        indexed.setdefault(aweme_id, {})
        indexed[aweme_id].setdefault("抽帧图", str(grid_path))
        indexed[aweme_id].setdefault("抽帧状态", "已存在")
    return indexed


def find_transcript(transcript_dir: Path, aweme_id: str) -> str:
    patterns = [
        f"2b_{aweme_id}.transcript.txt",
        f"2b_{aweme_id}.transcript.md",
        f"2b_{aweme_id}.transcript.json",
        f"{aweme_id}.transcript.txt",
        f"{aweme_id}.transcript.md",
        f"transcript_{aweme_id}.txt",
        f"transcript_{aweme_id}.md",
    ]
    for pattern in patterns:
        path = transcript_dir / pattern
        if path.exists():
            return str(path)
    return ""


def split_paths(value: str) -> list[str]:
    paths: list[str] = []
    for part in value.replace("\n", "；").split("；"):
        stripped = part.strip()
        if stripped:
            paths.append(stripped)
    return paths


def image_paths_from_manifest(path_text: str) -> list[str]:
    if not path_text:
        return []
    path = Path(path_text)
    if not path.exists():
        return []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    image_files = manifest.get("image_files") or []
    if not isinstance(image_files, list):
        return []
    return [str(item) for item in image_files if item]


def expected_schema() -> dict[str, str]:
    return {
        field: "必填。看真实媒体素材后用人话填写，不要写空泛词。"
        for field in SCHEMA_FIELDS
    }


def build_prompt(record: dict[str, Any]) -> str:
    media = record["media"]
    media_lines = [
        f"媒体类型：{media['media_type'] or '未知'}",
        f"视频文件：{media['video_path'] or '无'}",
        f"图片文件：{media['image_paths'] or '无'}",
        f"抽帧图：{media['frame_grid_path'] or '无'}",
        f"字幕/转写：{media['transcript_path'] or '无'}",
    ]
    return (
        "请查看这个抖音样本的媒体文件：如果 media_type=video，就看视频文件和抽帧图；如果 media_type=image，就看图片文件/图片清单。按 output_schema 输出一个 JSON 对象。\n"
        "不要只复述画面。每条判断都按“媒体证据 -> 打中的家长问题 -> 互动数据是否验证 -> 对点赞/评论/收藏/分享的影响”来写。\n"
        "S层命中人群不要写成宝妈/家长这种身份词，要写清她现在卡在哪一步。\n"
        "视频作品要判断前三秒为什么用户愿意先停一下、属于哪类文案入口、用了什么停留技巧、后文有没有接住。\n"
        "图片/图文作品没有前三秒时，不要硬编前三秒；改写首图/前两张图如何留人、标题和图片顺序如何制造继续看的理由。\n"
        "中段停留机制不能写成多画面/真实感/信息密度高，必须写中段或后续图片回答了家长什么问题。\n"
        "如果内容和母婴/儿童/营养/健康/育儿焦虑相关但四项互动低，要写：方向相关，但该账号粉丝里对应人群响应不强或人群可能不多。\n"
        "只输出 JSON，不要输出 Markdown。\n\n"
        f"作品ID：{record['aweme_id']}\n"
        f"标题：{record['title']}\n"
        f"抽样锚点：{record['sampling']['anchors']}\n"
        f"互动数据：{record['metrics']}\n"
        + "\n".join(media_lines)
    )


def build_records(
    run_dir: Path,
    transcript_dir: Path,
    *,
    candidates_name: str,
    downloads_name: str,
    grids_name: str,
) -> list[dict[str, Any]]:
    candidates = read_csv_if_exists(existing_output_path(run_dir, candidates_name))
    downloads = index_downloads(run_dir, read_csv_if_exists(existing_output_path(run_dir, downloads_name)))
    grids = index_grids(run_dir, read_csv_if_exists(existing_output_path(run_dir, grids_name)))
    schema = expected_schema()
    records: list[dict[str, Any]] = []

    for row in candidates:
        if text(row, "建议下载") not in {"", "是", "yes", "Y", "y", "1", "true", "True"}:
            continue
        aweme_id = text(row, "作品ID", "aweme_id")
        if not aweme_id:
            continue
        download_row = downloads.get(aweme_id, {})
        grid_row = grids.get(aweme_id, {})
        media_type = text(download_row, "媒体类型") or ("image" if text(download_row, "图片文件", "图片清单文件") else "video")
        video_path = normalize_path(run_dir, text(download_row, "视频文件") or str(run_dir / f"2b_{aweme_id}.mp4"))
        image_manifest_path = normalize_path(run_dir, text(download_row, "图片清单文件") or str(run_dir / f"2b_{aweme_id}_images.json"))
        image_paths = [
            normalize_path(run_dir, path)
            for path in split_paths(text(download_row, "图片文件"))
        ]
        if not image_paths:
            image_paths = [normalize_path(run_dir, path) for path in image_paths_from_manifest(image_manifest_path)]
        grid_path = normalize_path(run_dir, text(grid_row, "抽帧图") or str(run_dir / f"2b_{aweme_id}_grid.jpg"))
        transcript_path = find_transcript(transcript_dir, aweme_id)
        record: dict[str, Any] = {
            "task_type": "douyin_creator_assets_2B_media_understanding",
            "aweme_id": aweme_id,
            "title": text(row, "作品标题", "标题"),
            "sampling": {
                "anchors": text(row, "抽样锚点"),
                "reason": text(row, "抽样理由"),
            },
            "metrics": {field: text(row, field) for field in METRIC_FIELDS},
            "content_coarse": {
                "内容主题": text(row, "内容主题"),
                "品类连接母类": text(row, "品类连接母类"),
                "连接强度": text(row, "连接强度"),
                "商品内容信号": text(row, "商品内容信号"),
            },
            "media": {
                "media_type": media_type,
                "video_path": video_path if Path(video_path).exists() else "",
                "image_paths": [path for path in image_paths if Path(path).exists()],
                "image_manifest_path": image_manifest_path if Path(image_manifest_path).exists() else "",
                "frame_grid_path": grid_path if Path(grid_path).exists() else "",
                "transcript_path": transcript_path,
                "video_url_file": normalize_path(run_dir, str(run_dir / f"2b_{aweme_id}.url.txt")),
            },
            "output_schema": schema,
            "prompt": "",
        }
        record["prompt"] = build_prompt(record)
        records.append(record)
    return records


def build_md(run_dir: Path, records: list[dict[str, Any]]) -> str:
    lines = [
        "# 2B 媒体理解 Agent 交接包",
        "",
        f"- 来源目录：`{run_dir}`",
        f"- 样本数：{len(records)}",
        "- 用途：交给 WorkBuddy 或其他能查看视频/图片/字幕的 Agent，按统一 JSON 字段回填 2B 细看结果。",
        "",
        "## 回填要求",
        "",
        "每个媒体样本回填一个 JSON 对象，字段必须和 `output_schema` 一致。不要输出 Markdown，不要合并多条样本。",
        "",
        "关键判断链条：媒体证据 -> 打中的家长问题 -> 互动数据是否验证 -> 点赞/评论/收藏/分享哪个动作被激发或没被激发。",
        "",
        "## 样本",
        "",
        "| 作品ID | 标题 | 抽样锚点 | 媒体类型 | 视频 | 图片 | 抽帧图 | 字幕/转写 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for record in records:
        media = record["media"]
        title = record["title"].replace("|", "｜")
        image_text = "；".join(media.get("image_paths") or [])
        lines.append(
            f"| `{record['aweme_id']}` | {title} | {record['sampling']['anchors']} | "
            f"{media.get('media_type', '')} | `{media['video_path']}` | `{image_text}` | "
            f"`{media['frame_grid_path']}` | `{media['transcript_path']}` |"
        )
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "1. 把 `02B_媒体理解交接包.jsonl` 交给媒体理解 Agent。",
            "2. 让 Agent 逐条输出 JSONL，建议文件名：`video_understanding_results.jsonl`。",
            "3. 运行 `render_video_deep_dive.py` 渲染 `02B_媒体内容细看明细.csv` 和 `02B_媒体内容细看.md`。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir)
    transcript_dir = Path(args.transcript_dir) if args.transcript_dir else run_dir
    records = build_records(
        run_dir,
        transcript_dir,
        candidates_name=args.candidates,
        downloads_name=args.downloads,
        grids_name=args.grids,
    )
    jsonl_path = output_path(run_dir, "video_understanding_handoff.jsonl")
    md_path = output_path(run_dir, "video_understanding_handoff.md")
    write_jsonl(jsonl_path, records)
    mirror_legacy(jsonl_path, run_dir, "video_understanding_handoff.jsonl")
    md_path.write_text(build_md(run_dir, records), encoding="utf-8")
    mirror_legacy(md_path, run_dir, "video_understanding_handoff.md")
    print(f"wrote {jsonl_path}")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
