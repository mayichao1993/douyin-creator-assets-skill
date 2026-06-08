#!/usr/bin/env python3
"""Render 2B video deep-dive outputs from agent-neutral JSONL results."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


COLUMNS = [
    "作品ID",
    "作品标题",
    "四项互动锚点",
    "视频文件",
    "抽帧图",
    "S层命中人群",
    "前三秒",
    "不划走理由",
    "前三秒文案类型",
    "三秒停留技巧",
    "后文是否接住前三秒",
    "中段停留机制",
    "视频核心内容",
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

METRIC_COLUMNS = ["点赞数", "评论数", "收藏数", "分享数", "总互动"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render video_content_deep_dive.csv/md from JSONL produced by WorkBuddy or another video agent."
    )
    parser.add_argument("run_dir", help="A outputs/douyin_creator_assets/<timestamp> directory.")
    parser.add_argument(
        "--results",
        default="video_understanding_results.jsonl",
        help="JSONL/JSON filename inside run_dir, or an absolute path.",
    )
    return parser.parse_args()


def read_csv_if_exists(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_results(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"missing results file: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        data = json.loads(text)
        return [normalize_record(item) for item in data if isinstance(item, dict)]
    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        if isinstance(data, dict):
            records.append(normalize_record(data))
    return records


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    if isinstance(record.get("result"), dict):
        merged = dict(record)
        nested = record["result"]
        merged.update(nested)
        return merged
    return record


def text(row: dict[str, Any], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        value = str(value or "").strip()
        if value:
            return value
    return ""


def index_by_id(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        aweme_id = text(row, "作品ID", "aweme_id", "aweme_id_str")
        if aweme_id:
            indexed[aweme_id] = row
    return indexed


def id_from_path(path_text: str) -> str:
    stem = Path(path_text).stem
    if stem.endswith("_grid"):
        stem = stem[:-5]
    if stem.startswith("2b_"):
        return stem[3:]
    return stem


def index_grids(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        aweme_id = id_from_path(text(row, "抽帧图") or text(row, "视频文件"))
        if aweme_id:
            indexed[aweme_id] = row
    return indexed


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


def fallback(value: str) -> str:
    return value if value else "待补充"


def build_rows(run_dir: Path, results: list[dict[str, Any]]) -> list[dict[str, str]]:
    candidates = index_by_id(read_csv_if_exists(run_dir / "video_sample_candidates.csv"))
    downloads = index_by_id(read_csv_if_exists(run_dir / "downloaded_videos.csv"))
    grids = index_grids(read_csv_if_exists(run_dir / "video_frame_grids.csv"))
    rows: list[dict[str, str]] = []

    for result in results:
        aweme_id = text(result, "作品ID", "aweme_id", "id")
        if not aweme_id:
            continue
        candidate = candidates.get(aweme_id, {})
        download = downloads.get(aweme_id, {})
        grid = grids.get(aweme_id, {})
        video_path = text(result, "视频文件") or text(download, "视频文件") or str(run_dir / f"2b_{aweme_id}.mp4")
        grid_path = text(result, "抽帧图") or text(grid, "抽帧图") or str(run_dir / f"2b_{aweme_id}_grid.jpg")
        row: dict[str, str] = {
            "作品ID": aweme_id,
            "作品标题": text(result, "作品标题", "title") or text(candidate, "作品标题"),
            "四项互动锚点": text(result, "四项互动锚点") or text(candidate, "抽样锚点"),
            "视频文件": normalize_path(run_dir, video_path),
            "抽帧图": normalize_path(run_dir, grid_path),
        }
        for column in COLUMNS:
            if column in row:
                continue
            row[column] = fallback(text(result, column))
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def metric_table(run_dir: Path, rows: list[dict[str, str]]) -> list[str]:
    candidate_map = index_by_id(read_csv_if_exists(run_dir / "video_sample_candidates.csv"))
    lines = [
        "| 作品ID | 抽样锚点 | 点赞 | 评论 | 收藏 | 分享 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        candidate = candidate_map.get(row["作品ID"], {})
        metrics = {field: text(candidate, field) for field in METRIC_COLUMNS}
        lines.append(
            f"| `{row['作品ID']}` | {row['四项互动锚点']} | {metrics['点赞数']} | "
            f"{metrics['评论数']} | {metrics['收藏数']} | {metrics['分享数']} |"
        )
    return lines


def build_md(run_dir: Path, rows: list[dict[str, str]]) -> str:
    lines = [
        "# 视频内容细看报告（2B）",
        "",
        f"- 来源目录：`{run_dir}`",
        f"- 样本数：{len(rows)}",
        "- 查看方式：由外部视频理解 Agent 查看 mp4/抽帧图/字幕后回填 JSON，本脚本只负责渲染成 2B 报告。",
        "",
        "## 1. 抽样锚点",
        "",
    ]
    lines.extend(metric_table(run_dir, rows))
    lines.extend(["", "## 2. 单条视频细看", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row['作品ID']}：{row['作品标题']}",
                "",
                f"打的是：{row['S层命中人群']}",
                "",
                f"前三秒：{row['前三秒']}",
                "",
                f"不划走理由：{row['不划走理由']}",
                "",
                f"前三秒文案类型：{row['前三秒文案类型']}；三秒停留技巧：{row['三秒停留技巧']}；后文承接：{row['后文是否接住前三秒']}",
                "",
                f"中段停留机制：{row['中段停留机制']}",
                "",
                f"视频核心内容：{row['视频核心内容']}",
                "",
                f"口播/字幕依据：{row['口播/字幕依据']}",
                "",
                f"画面重点：{row['画面重点']}",
                "",
                f"商品出现方式：{row['商品出现方式']}；达人说服方式：{row['达人说服方式']}；内容真实感：{row['内容真实感']}",
                "",
                "| 互动 | 判断 |",
                "|---|---|",
                f"| 点赞 | {row['点赞为什么高/低']} |",
                f"| 评论 | {row['评论为什么高/低']} |",
                f"| 收藏 | {row['收藏为什么高/低']} |",
                f"| 分享 | {row['分享为什么高/低']} |",
                "",
                f"品类连接来源：{row['品类连接来源']}",
                "",
                f"下一步评论验证点：{row['下一步评论验证点']}",
                "",
            ]
        )
    lines.extend(
        [
            "## 3. 文件",
            "",
            f"- 2B 明细表：`{run_dir / 'video_content_deep_dive.csv'}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir)
    results_path = Path(args.results)
    if not results_path.is_absolute():
        results_path = run_dir / results_path
    results = read_results(results_path)
    rows = build_rows(run_dir, results)
    csv_path = run_dir / "video_content_deep_dive.csv"
    md_path = run_dir / "video_content_deep_dive.md"
    write_csv(csv_path, rows)
    md_path.write_text(build_md(run_dir, rows), encoding="utf-8")
    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
