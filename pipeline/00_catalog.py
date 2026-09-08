# -*- coding: utf-8 -*-
"""0.1 全量编目：扫描源视频目录，产出 docs/course_inventory.json + .md

用法：python pipeline/00_catalog.py <源视频根目录>
时长/编码信息由 ffprobe 采集；若某文件 ffprobe 失败则跳过并记录。
"""
import json
import os
import subprocess
import sys
from datetime import date

FFPROBE = os.environ.get("FFPROBE", r"E:\pytools\ffmpeg\ffprobe.exe")
DOC_FIX = {  # 官方文档/视频文件名导出时丢失字母 s，编目中修正为正确标题
    "witch": "switch", "lice": "slice", "truct": "struct",
    "ync 包": "sync 包", "unafe": "unsafe",
}


def fix_title(t: str) -> str:
    for bad, good in DOC_FIX.items():
        t = t.replace(bad, good)
    return t


def probe(path: str):
    try:
        out = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries",
             "format=duration:stream=codec_type,codec_name,width,height",
             "-of", "json", path],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout
        info = json.loads(out)
        streams = info.get("streams", [])
        v = next((s for s in streams if s.get("codec_type") == "video"), {})
        a = next((s for s in streams if s.get("codec_type") == "audio"), {})
        return {
            "seconds": round(float(info["format"]["duration"]), 1),
            "width": v.get("width"), "height": v.get("height"),
            "video_codec": v.get("codec_name"), "audio_codec": a.get("codec_name"),
        }
    except Exception as e:
        return {"error": str(e)}


def hms(s: float) -> str:
    s = int(round(s))
    return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def main(src_root: str):
    entries = []
    for dirpath, dirnames, filenames in os.walk(src_root):
        dirnames.sort()
        for fn in sorted(filenames):
            if not fn.lower().endswith(".mp4") or "_2026-" in fn:
                continue  # 排除重复下载的时间戳副本
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, src_root)
            ep = {
                "file": rel.replace("\\", "/"),
                "size_mb": round(os.path.getsize(full) / 1e6, 1),
                **probe(full),
            }
            entries.append(ep)
            print(("OK " if "seconds" in ep else "ERR ") + rel)

    inv = {
        "generated": str(date.today()),
        "source_root": src_root,
        "episodes": entries,
        "total_seconds": round(sum(e["seconds"] for e in entries if "seconds" in e), 1),
    }
    os.makedirs("docs", exist_ok=True)
    with open("docs/course_inventory.json", "w", encoding="utf-8") as f:
        json.dump(inv, f, ensure_ascii=False, indent=2)

    lines = [
        "# 课程资产清单（0.1 编目产出）",
        "",
        f"> 生成：{inv['generated']} ｜ 源根目录：`{src_root}` ｜ 共 {len(entries)} 个视频，"
        f"总时长 {hms(inv['total_seconds'])}",
        "",
        "| # | 文件 | 时长 | 分辨率 | 大小(MB) | 编码 |",
        "|---|------|------|--------|----------|------|",
    ]
    for i, e in enumerate(entries, 1):
        if "seconds" in e:
            lines.append(
                f"| {i} | {e['file']} | {hms(e['seconds'])} | "
                f"{e['width']}x{e['height']} | {e['size_mb']} | "
                f"{e['video_codec']}/{e['audio_codec']} |"
            )
        else:
            lines.append(f"| {i} | {e['file']} | ❌ ffprobe 失败 | - | {e['size_mb']} | - |")
    lines += [
        "",
        "## 备注",
        "",
        "- 官方文稿随视频附带（拉勾课程 24 篇 .md），文件名导出时丢失部分字母 s（如 witch→switch），"
        "内容本身完好；编目与后续理解阶段一律使用修正后的标题。",
        "- 文件名含全角冒号「：」，Git Bash 直传原生子进程会乱码；所有涉及源目录的操作须走 PowerShell 或 python os API。",
        "- [5226] 开篇词另有两个带时间戳后缀的重复下载副本，已排除。",
    ]
    with open("docs/course_inventory.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"-> docs/course_inventory.json / .md  共 {len(entries)} 集，总时长 {hms(inv['total_seconds'])}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else r"E:\培训视频重生项目-原视频")
