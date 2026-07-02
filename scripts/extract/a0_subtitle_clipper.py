#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from pathlib import Path


A0_KOREAN_TERMS = [
    "안녕",
    "네",
    "아니",
    "아니야",
    "고마워",
    "감사",
    "미안",
    "죄송",
    "괜찮아",
    "좋아",
    "싫어",
    "맞아",
    "몰라",
    "알아",
    "있어",
    "없어",
    "가자",
    "와",
    "봐",
    "먹어",
    "자",
    "제발",
    "잠깐",
    "빨리",
    "천천히",
    "지금",
    "오늘",
    "내일",
    "어제",
    "여기",
    "저기",
    "어디",
    "누구",
    "뭐",
    "왜",
    "언제",
    "어떻게",
    "이거",
    "저거",
    "그거",
    "나도",
    "너도",
    "우리",
    "엄마",
    "아빠",
    "친구",
    "집",
    "학교",
    "사랑",
    "진짜",
    "너무",
    "많이",
    "조금",
    "아마",
    "아마도",
    "오랜만",
    "오랜만이야",
    "오랫만",
    "오랫만이네",
]


def normalize_korean(text):
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text)


def parse_timecode(value):
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(millis) / 1000.0
    )


def format_time(value):
    minutes, seconds = divmod(value, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{seconds:06.3f}"


def parse_srt(path):
    content = path.read_text(encoding="utf-8-sig", errors="replace")
    blocks = re.split(r"\n\s*\n", content.strip())
    entries = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        time_line_index = 0
        if "-->" not in lines[0] and len(lines) > 1:
            time_line_index = 1
        if "-->" not in lines[time_line_index]:
            continue
        start_raw, end_raw = [part.strip() for part in lines[time_line_index].split("-->")]
        text = " ".join(lines[time_line_index + 1 :])
        text = re.sub(r"<[^>]+>", "", text)
        entries.append(
            {
                "start": parse_timecode(start_raw),
                "end": parse_timecode(end_raw),
                "text": text,
            }
        )
    return entries


def find_a0_term(text, terms):
    normalized_text = normalize_korean(text)
    matches = []
    for term in terms:
        normalized_term = normalize_korean(term)
        if not normalized_term:
            continue
        index = normalized_text.find(normalized_term)
        if index < 0:
            continue
        if len(normalized_term) <= 1 and normalized_text != normalized_term:
            continue
        matches.append((term, normalized_term, index))

    if not matches:
        return None
    return max(matches, key=lambda item: len(item[1]))


def clip_window(entry, normalized_term, index, min_duration, max_duration, pre_roll, post_roll):
    start = entry["start"]
    end = entry["end"]
    duration = max(0.1, end - start)
    normalized_text = normalize_korean(entry["text"])

    if normalized_text:
        center_fraction = (index + len(normalized_term) / 2.0) / len(normalized_text)
    else:
        center_fraction = 0.5

    center = start + duration * max(0.0, min(1.0, center_fraction))
    estimated_keyword_duration = max(0.5, min(1.15, len(normalized_term) * 0.22))
    target_duration = min(max_duration, estimated_keyword_duration + pre_roll + post_roll)
    if min_duration > 0:
        target_duration = max(min_duration, target_duration)
    clip_start = max(0.0, center - target_duration / 2.0)
    clip_end = clip_start + target_duration

    if clip_start < start - pre_roll:
        clip_start = max(0.0, start - pre_roll)
        clip_end = clip_start + target_duration
    if clip_end > end + post_roll:
        clip_end = end + post_roll
        clip_start = max(0.0, clip_end - target_duration)

    return clip_start, clip_end


def run(cmd):
    subprocess.run(cmd, check=True)


def render_clip(video_path, output_path, start, end):
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(video_path),
            "-t",
            f"{end - start:.3f}",
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )


def main():
    parser = argparse.ArgumentParser(description="Create timeline-ordered A0 Korean clips from an SRT file.")
    parser.add_argument("video", type=Path)
    parser.add_argument("--srt", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=Path("outputs/crash_a0_test"))
    parser.add_argument("--max-clips", type=int, default=20)
    parser.add_argument("--min-duration", type=float, default=0.0)
    parser.add_argument("--max-duration", type=float, default=3.0)
    parser.add_argument("--pre-roll", type=float, default=0.18)
    parser.add_argument("--post-roll", type=float, default=0.32)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    entries = parse_srt(args.srt)
    manifest = []
    term_counts = {}

    for entry in entries:
        matched = find_a0_term(entry["text"], A0_KOREAN_TERMS)
        if not matched:
            continue

        term, normalized_term, index = matched
        clip_start, clip_end = clip_window(
            entry,
            normalized_term,
            index,
            args.min_duration,
            args.max_duration,
            args.pre_roll,
            args.post_roll,
        )
        number = len(manifest) + 1
        safe_term = normalize_korean(term) or "term"
        term_counts[safe_term] = term_counts.get(safe_term, 0) + 1
        output_path = args.out / f"{safe_term}_{term_counts[safe_term]:03d}.mp4"
        render_clip(args.video, output_path, clip_start, clip_end)
        manifest.append(
            {
                "clip": str(output_path),
                "level": "A0",
                "term": term,
                "subtitle_text": entry["text"],
                "subtitle_start": entry["start"],
                "subtitle_end": entry["end"],
                "clip_start": clip_start,
                "clip_end": clip_end,
                "clip_duration": clip_end - clip_start,
                "timecode": f"{format_time(clip_start)} - {format_time(clip_end)}",
            }
        )
        if len(manifest) >= args.max_clips:
            break

    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"created {len(manifest)} clips")
    print(manifest_path)


if __name__ == "__main__":
    main()
