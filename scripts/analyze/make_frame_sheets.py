#!/usr/bin/env python3
import argparse
import math
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path


VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".m4v"}


def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def normalize(value):
    return unicodedata.normalize("NFC", value)


def split_folder_name(path):
    name = normalize(path.name)
    m = re.match(r"^(\d+)\s*(.*)$", name)
    if not m:
        return None, name
    return int(m.group(1)), m.group(2).strip()


def duration(path):
    proc = run([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ])
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return 0.0


def safe_name(number, keyword):
    base = f"{number:03d}_{keyword}" if number is not None else keyword
    return re.sub(r"[^0-9A-Za-z가-힣_. -]+", "_", base).strip()


def extract_frame(video, time_sec, out):
    proc = run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{max(0.0, time_sec):.3f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-vf",
        "scale=180:-1",
        "-q:v",
        "5",
        str(out),
    ])
    return proc.returncode == 0


def make_sheet(folder, out_root, work_root):
    number, keyword = split_folder_name(folder)
    clips = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
    clips.sort(key=lambda p: p.name)
    if not clips:
        return None

    base = safe_name(number, keyword)
    frame_dir = work_root / base
    if frame_dir.exists():
        shutil.rmtree(frame_dir)
    frame_dir.mkdir(parents=True)

    for clip_index, clip in enumerate(clips):
        dur = duration(clip)
        points = [0.0, dur * 0.25, dur * 0.5, dur * 0.75, max(0.0, dur - 0.04)]
        for point_index, point in enumerate(points):
            extract_frame(clip, point, frame_dir / f"{clip_index:03d}_{point_index:02d}.jpg")

    rows = len(clips)
    out_root.mkdir(parents=True, exist_ok=True)
    sheet = out_root / f"{base}.jpg"
    proc = run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-framerate",
        "1",
        "-pattern_type",
        "glob",
        "-i",
        str(frame_dir / "*.jpg"),
        "-vf",
        f"tile=5x{rows}:padding=2:margin=2:color=white",
        "-frames:v",
        "1",
        "-q:v",
        "4",
        str(sheet),
    ])
    if proc.returncode != 0:
        print(proc.stderr)
        return None
    return sheet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", type=Path, default=Path("outputs/reference_clip_analysis/frame_sheets"))
    parser.add_argument("--work", type=Path, default=Path("work/reference_clip_analysis/frame_sheets"))
    parser.add_argument("--folder-number", type=int, action="append", default=[])
    parser.add_argument("--single-folder", action="store_true")
    args = parser.parse_args()

    folders = [args.root] if args.single_folder else [p for p in args.root.iterdir() if p.is_dir()]
    folders.sort(key=lambda p: split_folder_name(p)[0] if split_folder_name(p)[0] is not None else 10**9)
    if args.folder_number:
        wanted = set(args.folder_number)
        folders = [p for p in folders if split_folder_name(p)[0] in wanted]

    for folder in folders:
        sheet = make_sheet(folder, args.out, args.work)
        if sheet:
            print(sheet)


if __name__ == "__main__":
    main()
