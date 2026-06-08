#!/usr/bin/env python3
"""Download candidate videos selected for the 2B deep dive."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from collect_creator_assets import MOBILE_USER_AGENT, CollectError, item_from_mobile_share


OUTPUT_COLUMNS = [
    "作品ID",
    "作品标题",
    "抽样锚点",
    "下载状态",
    "视频文件",
    "视频URL文件",
    "错误信息",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download 2B candidate videos from video_sample_candidates.csv."
    )
    parser.add_argument("run_dir", help="A outputs/douyin_creator_assets/<timestamp> directory.")
    parser.add_argument(
        "--source",
        default="video_sample_candidates.csv",
        help="Candidate CSV filename inside run_dir.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing downloaded mp4 files.",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def get_nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def candidate_urls(item: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    video = item.get("video") or {}

    address_candidates = [
        video.get("play_addr"),
        video.get("play_addr_h264"),
        video.get("download_addr"),
        video.get("play_addr_bytevc1"),
    ]
    for addr in address_candidates:
        if isinstance(addr, dict):
            for url in addr.get("url_list") or []:
                if isinstance(url, str) and url not in urls:
                    urls.append(url)

    for bit_rate in video.get("bit_rate") or []:
        if isinstance(bit_rate, dict):
            play_addr = bit_rate.get("play_addr") or {}
            for url in play_addr.get("url_list") or []:
                if isinstance(url, str) and url not in urls:
                    urls.append(url)

    # Some mobile-share payloads use nested detail fields.
    fallback = get_nested(item, "video_info", "download_addr", "url_list")
    if isinstance(fallback, list):
        for url in fallback:
            if isinstance(url, str) and url not in urls:
                urls.append(url)
    return urls


def download_url(url: str, target_path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": MOBILE_USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    if not data:
        raise CollectError("empty_video_response")
    target_path.write_bytes(data)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir)
    source_path = run_dir / args.source
    rows = read_csv(source_path)

    result_rows: list[dict[str, str]] = []
    for row in rows:
        if row.get("建议下载", "是") not in {"是", "yes", "Y", "y", "1", "true", "True"}:
            continue
        aweme_id = str(row.get("作品ID") or "").strip()
        title = str(row.get("作品标题") or "").strip()
        anchors = str(row.get("抽样锚点") or "").strip()
        if not aweme_id:
            result_rows.append(
                {
                    "作品ID": "",
                    "作品标题": title,
                    "抽样锚点": anchors,
                    "下载状态": "失败",
                    "视频文件": "",
                    "视频URL文件": "",
                    "错误信息": "missing_aweme_id",
                }
            )
            continue

        filename = f"2b_{aweme_id}.mp4"
        video_path = run_dir / filename
        url_path = run_dir / f"2b_{aweme_id}.url.txt"
        raw_path = run_dir / f"2b_{aweme_id}.raw.json"
        if video_path.exists() and not args.overwrite:
            result_rows.append(
                {
                    "作品ID": aweme_id,
                    "作品标题": title,
                    "抽样锚点": anchors,
                    "下载状态": "已存在",
                    "视频文件": str(video_path),
                    "视频URL文件": str(url_path) if url_path.exists() else "",
                    "错误信息": "",
                }
            )
            continue

        try:
            item = item_from_mobile_share(aweme_id)
            urls = candidate_urls(item)
            if not urls:
                raise CollectError("video_url_not_found")
            last_error = ""
            for url in urls:
                try:
                    download_url(url, video_path)
                    url_path.write_text(url + "\n", encoding="utf-8")
                    raw_path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
                    last_error = ""
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = str(exc)
            if last_error:
                raise CollectError(last_error)
            status = "成功"
            error = ""
        except (CollectError, urllib.error.URLError, TimeoutError, OSError) as exc:
            status = "失败"
            error = str(exc)

        result_rows.append(
            {
                "作品ID": aweme_id,
                "作品标题": title,
                "抽样锚点": anchors,
                "下载状态": status,
                "视频文件": str(video_path) if video_path.exists() else "",
                "视频URL文件": str(url_path) if url_path.exists() else "",
                "错误信息": error,
            }
        )

    output_path = run_dir / "downloaded_videos.csv"
    write_csv(output_path, result_rows)
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
