#!/usr/bin/env python3
import argparse
import csv
import json
import math
import os
import re
import statistics
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".m4v"}


def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def normalize_name(value):
    return unicodedata.normalize("NFC", value)


def split_folder_name(path):
    name = normalize_name(path.name)
    m = re.match(r"^(\d+)\s*(.*)$", name)
    if not m:
        return None, name
    return int(m.group(1)), m.group(2).strip()


def ratio_to_float(value):
    if not value or value == "0/0":
        return None
    if "/" in value:
        num, den = value.split("/", 1)
        try:
            den_f = float(den)
            return float(num) / den_f if den_f else None
        except ValueError:
            return None
    try:
        return float(value)
    except ValueError:
        return None


def ffprobe(path):
    proc = run([
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ])
    if proc.returncode != 0:
        return None, proc.stderr.strip()
    try:
        return json.loads(proc.stdout), None
    except json.JSONDecodeError as exc:
        return None, str(exc)


def stream_info(meta):
    streams = meta.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    duration = None
    for source in (video, meta.get("format", {})):
        try:
            duration = float(source.get("duration"))
            break
        except (TypeError, ValueError):
            pass
    fps = ratio_to_float(video.get("avg_frame_rate")) or ratio_to_float(video.get("r_frame_rate"))
    frames = None
    if video.get("nb_frames"):
        try:
            frames = int(video["nb_frames"])
        except ValueError:
            frames = None
    if frames is None and duration and fps:
        frames = int(round(duration * fps))
    return {
        "duration": duration,
        "fps": fps,
        "frames": frames,
        "width": video.get("width"),
        "height": video.get("height"),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
    }


def silence_analysis(path, duration, noise="-35dB", silence_duration="0.06"):
    proc = run([
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        f"silencedetect=n={noise}:d={silence_duration}",
        "-f",
        "null",
        "-",
    ])
    text = proc.stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", text)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", text)]
    starts_at_silence = bool(starts and starts[0] <= 0.03)
    ends_at_silence = bool(starts and duration and starts[-1] < duration and len(starts) > len(ends))

    lead_silence = 0.0
    if starts_at_silence and ends:
        lead_silence = max(0.0, min(duration or ends[0], ends[0]))

    tail_silence = 0.0
    if duration:
        if ends_at_silence:
            tail_silence = max(0.0, duration - starts[-1])
        elif ends and ends[-1] >= duration - 0.08:
            paired_start = starts[-1] if starts else duration
            tail_silence = max(0.0, duration - paired_start)

    return {
        "lead_silence": lead_silence,
        "tail_silence": tail_silence,
        "silence_events": len(starts),
        "starts_with_audio": lead_silence < 0.12,
        "ends_with_audio": tail_silence < 0.12,
    }


def scene_analysis(path):
    proc = run([
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-vf",
        "select='gt(scene,0.30)',showinfo",
        "-an",
        "-f",
        "null",
        "-",
    ])
    pts = []
    for match in re.finditer(r"pts_time:([0-9.]+)", proc.stderr):
        try:
            pts.append(float(match.group(1)))
        except ValueError:
            pass
    return {
        "scene_cut_count": len(pts),
        "scene_cut_times": pts[:12],
    }


def black_analysis(path):
    proc = run([
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-vf",
        "blackdetect=d=0.05:pix_th=0.08",
        "-an",
        "-f",
        "null",
        "-",
    ])
    starts = []
    for match in re.finditer(r"black_start:([0-9.]+)\s+black_end:([0-9.]+)\s+black_duration:([0-9.]+)", proc.stderr):
        starts.append((float(match.group(1)), float(match.group(2)), float(match.group(3))))
    return {
        "black_count": len(starts),
        "black_ranges": starts[:8],
        "starts_black": bool(starts and starts[0][0] <= 0.04),
        "ends_black": bool(starts and starts[-1][1] >= 0),
    }


def classify_clip(row):
    duration = row.get("duration") or 0
    scene_cuts = row.get("scene_cut_count") or 0
    lead = row.get("lead_silence") or 0
    tail = row.get("tail_silence") or 0
    starts_audio = row.get("starts_with_audio")
    ends_audio = row.get("ends_with_audio")

    flags = []
    if duration < 0.8:
        flags.append("too_short")
    if duration > 4.5:
        flags.append("long_phrase_or_context")
    if starts_audio and lead < 0.08:
        flags.append("keyword_may_start_immediately")
    if ends_audio and tail < 0.08:
        flags.append("may_end_on_speech")
    if scene_cuts > 0:
        flags.append("contains_scene_cut")
    return "|".join(flags)


def percentile(values, q):
    if not values:
        return None
    values = sorted(values)
    idx = (len(values) - 1) * q
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return values[int(idx)]
    return values[lo] * (hi - idx) + values[hi] * (idx - lo)


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fields})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", type=Path, default=Path("outputs/reference_clip_analysis"))
    parser.add_argument("--max-clips", type=int, default=0)
    parser.add_argument("--folder-number", type=int, action="append", default=[])
    parser.add_argument("--scene", action="store_true")
    parser.add_argument("--black", action="store_true")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    folders = [p for p in args.root.iterdir() if p.is_dir()]
    folders.sort(key=lambda p: split_folder_name(p)[0] if split_folder_name(p)[0] is not None else 10**9)
    if args.folder_number:
        wanted = set(args.folder_number)
        folders = [p for p in folders if split_folder_name(p)[0] in wanted]

    rows = []
    folder_rows = []
    clips_seen = 0
    for folder in folders:
        number, keyword = split_folder_name(folder)
        clips = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
        clips.sort(key=lambda p: p.name)
        if not clips:
            continue
        folder_durations = []
        folder_frames = []
        folder_flags = Counter()
        for clip in clips:
            if args.max_clips and clips_seen >= args.max_clips:
                break
            clips_seen += 1
            meta, error = ffprobe(clip)
            row = {
                "folder_number": number,
                "keyword": keyword,
                "folder": str(folder),
                "file": str(clip),
                "filename": normalize_name(clip.name),
                "error": error,
            }
            if meta:
                row.update(stream_info(meta))
                if row.get("duration") is not None:
                    row.update(silence_analysis(clip, row["duration"]))
                if args.scene:
                    row.update(scene_analysis(clip))
                else:
                    row.update({"scene_cut_count": None, "scene_cut_times": []})
                if args.black:
                    row.update(black_analysis(clip))
                else:
                    row.update({"black_count": None, "black_ranges": []})
                row["flags"] = classify_clip(row)
                folder_durations.append(row.get("duration"))
                folder_frames.append(row.get("frames"))
                for flag in filter(None, row["flags"].split("|")):
                    folder_flags[flag] += 1
            rows.append(row)
        durations = [d for d in folder_durations if d is not None]
        frames = [f for f in folder_frames if f is not None]
        folder_rows.append({
            "folder_number": number,
            "keyword": keyword,
            "folder": str(folder),
            "clip_count": len(clips),
            "duration_min": min(durations) if durations else None,
            "duration_p25": percentile(durations, 0.25),
            "duration_median": percentile(durations, 0.5),
            "duration_p75": percentile(durations, 0.75),
            "duration_max": max(durations) if durations else None,
            "duration_mean": statistics.mean(durations) if durations else None,
            "frames_median": percentile(frames, 0.5),
            "common_flags": ", ".join(f"{k}:{v}" for k, v in folder_flags.most_common(6)),
        })
        if args.max_clips and clips_seen >= args.max_clips:
            break

    clip_fields = [
        "folder_number",
        "keyword",
        "filename",
        "duration",
        "fps",
        "frames",
        "width",
        "height",
        "lead_silence",
        "tail_silence",
        "starts_with_audio",
        "ends_with_audio",
        "silence_events",
        "scene_cut_count",
        "scene_cut_times",
        "black_count",
        "black_ranges",
        "flags",
        "file",
        "error",
    ]
    folder_fields = [
        "folder_number",
        "keyword",
        "clip_count",
        "duration_min",
        "duration_p25",
        "duration_median",
        "duration_p75",
        "duration_max",
        "duration_mean",
        "frames_median",
        "common_flags",
        "folder",
    ]
    write_csv(args.out / "clips.csv", rows, clip_fields)
    write_csv(args.out / "folders.csv", folder_rows, folder_fields)

    durations = [r["duration"] for r in rows if r.get("duration") is not None]
    frames = [r["frames"] for r in rows if r.get("frames") is not None]
    summary = {
        "root": str(args.root),
        "folder_count": len(folder_rows),
        "clip_count": len(rows),
        "duration": {
            "min": min(durations) if durations else None,
            "p10": percentile(durations, 0.10),
            "p25": percentile(durations, 0.25),
            "median": percentile(durations, 0.50),
            "p75": percentile(durations, 0.75),
            "p90": percentile(durations, 0.90),
            "max": max(durations) if durations else None,
            "mean": statistics.mean(durations) if durations else None,
        },
        "frames": {
            "median": percentile(frames, 0.50),
            "p90": percentile(frames, 0.90),
        },
        "resolution_counts": Counter(f"{r.get('width')}x{r.get('height')}" for r in rows if r.get("width")).most_common(12),
        "fps_counts": Counter(round(r.get("fps"), 3) for r in rows if r.get("fps")).most_common(12),
        "flags": Counter(flag for r in rows for flag in (r.get("flags") or "").split("|") if flag).most_common(20),
    }
    with open(args.out / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
