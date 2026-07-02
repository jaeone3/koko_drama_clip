#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from pathlib import Path


WHISPER_BIN = "/Users/jaewon/Library/Python/3.9/bin/whisper"

A0_KOREAN_TERMS = [
    "안녕",
    "네",
    "아니",
    "아니야",
    "아니요",
    "아니에요",
    "아닙니다",
    "아니다",
    "아니라",
    "아니고",
    "고마워",
    "고마워요",
    "감사",
    "감사합니다",
    "미안",
    "미안해",
    "미안해요",
    "죄송",
    "죄송합니다",
    "괜찮아",
    "괜찮아요",
    "좋아",
    "좋아요",
    "싫어",
    "맞아",
    "맞아요",
    "몰라",
    "몰라요",
    "알아",
    "알아요",
    "있어",
    "있어요",
    "없어",
    "없어요",
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
    "오늘은",
    "오늘도",
    "내일",
    "어제",
    "여기",
    "저기",
    "어디",
    "누구",
    "누구세요",
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

CASUAL_NEGATIVE_TERMS = {"아니", "아니야", "아니다", "아니라", "아니고"}
POLITE_NEGATIVE_TERMS = {"아니요", "아니에요", "아닙니다"}


def normalize_korean(text):
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text)


def term_family(term):
    normalized = normalize_korean(term)
    if normalized == "아니":
        return CASUAL_NEGATIVE_TERMS
    if normalized == "아니에요":
        return POLITE_NEGATIVE_TERMS
    if normalized.startswith("오랫만") or normalized.startswith("오랜만"):
        return {"오랜만", "오랫만", "오랜만이야", "오랫만이네"}
    return {normalized}


def category_for_term(term):
    normalized = normalize_korean(term)
    if normalized in CASUAL_NEGATIVE_TERMS:
        return "아니"
    if normalized in POLITE_NEGATIVE_TERMS:
        return "아니에요"
    if normalized.startswith("오랫만") or normalized.startswith("오랜만"):
        return "오랜만"
    return normalized or "term"


def surface_for_match(normalized_word, matched_term):
    normalized_term = normalize_korean(matched_term)
    if normalized_word == normalized_term:
        return matched_term
    return normalized_word


def run(cmd):
    subprocess.run(cmd, check=True)


def ffprobe_duration(video_path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def transcribe(video_path, transcript_dir, model):
    transcript_path = transcript_dir / f"{video_path.stem}.json"
    if transcript_path.exists():
        return transcript_path

    run(
        [
            WHISPER_BIN,
            str(video_path),
            "--language",
            "ko",
            "--model",
            model,
            "--word_timestamps",
            "True",
            "--output_format",
            "json",
            "--output_dir",
            str(transcript_dir),
            "--fp16",
            "False",
        ]
    )
    return transcript_path


def match_term(normalized_text, candidates):
    matches = []
    for original_term, normalized_term in candidates:
        if not normalized_term:
            continue
        if normalized_text in term_family(original_term):
            matches.append((original_term, normalized_term))

    if not matches:
        return None
    return max(matches, key=lambda item: len(item[1]))


def iter_matches(transcript_path, terms):
    data = json.loads(transcript_path.read_text())
    normalized_terms = [(term, normalize_korean(term)) for term in terms]

    for segment in data.get("segments", []):
        words = segment.get("words") or []
        if words:
            for word in words:
                normalized_word = normalize_korean(word.get("word", ""))
                matched_term = match_term(normalized_word, normalized_terms)
                if matched_term:
                    surface_term = surface_for_match(normalized_word, matched_term[0])
                    yield {
                        "category": category_for_term(surface_term),
                        "term": surface_term,
                        "text": word.get("word", "").strip(),
                        "start": float(word["start"]),
                        "end": float(word["end"]),
                        "probability": word.get("probability"),
                    }
        else:
            normalized_text = normalize_korean(segment.get("text", ""))
            matched_term = match_term(normalized_text, normalized_terms)
            if matched_term:
                surface_term = surface_for_match(normalized_text, matched_term[0])
                yield {
                    "category": category_for_term(surface_term),
                    "term": surface_term,
                    "text": segment.get("text", "").strip(),
                    "start": float(segment["start"]),
                    "end": float(segment["end"]),
                    "probability": None,
                }


def clip_window(match, duration, pre_roll, post_roll, min_duration, max_duration, keep_short_source_under):
    if duration <= keep_short_source_under:
        return 0.0, duration

    start = max(0.0, match["start"] - pre_roll)
    end = min(duration, match["end"] + post_roll)

    current = end - start
    if min_duration > 0 and current < min_duration:
        extra = (min_duration - current) / 2.0
        start = max(0.0, start - extra)
        end = min(duration, end + extra)
    if min_duration > 0 and end - start < min_duration:
        if start == 0.0:
            end = min(duration, min_duration)
        elif end == duration:
            start = max(0.0, duration - min_duration)

    if end - start > max_duration:
        center = (match["start"] + match["end"]) / 2.0
        start = max(0.0, center - max_duration / 2.0)
        end = min(duration, start + max_duration)
        start = max(0.0, end - max_duration)

    return start, end


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
            "-to",
            f"{end:.3f}",
            "-i",
            str(video_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
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
    parser = argparse.ArgumentParser(description="Extract short Korean beginner-expression clips in timeline order.")
    parser.add_argument("videos", nargs="+", type=Path)
    parser.add_argument("--keywords", nargs="+", help="Optional override terms. If omitted, the built-in A0 term list is used.")
    parser.add_argument("--out", type=Path, default=Path("outputs/a0_clips"))
    parser.add_argument("--model", default="tiny")
    parser.add_argument("--pre-roll", type=float, default=0.28)
    parser.add_argument("--post-roll", type=float, default=0.75)
    parser.add_argument("--min-duration", type=float, default=0.0)
    parser.add_argument("--max-duration", type=float, default=3.0)
    parser.add_argument("--keep-short-source-under", type=float, default=3.0)
    parser.add_argument("--min-probability", type=float, default=0.35)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    transcript_dir = args.out / "_transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    terms = args.keywords if args.keywords else A0_KOREAN_TERMS

    manifest = []
    term_counts = {}
    for video_path in args.videos:
        duration = ffprobe_duration(video_path)
        transcript_path = transcribe(video_path, transcript_dir, args.model)
        filtered_matches = [
            match
            for match in iter_matches(transcript_path, terms)
            if match["probability"] is None or match["probability"] >= args.min_probability
        ]
        for index, match in enumerate(filtered_matches, start=1):
            start, end = clip_window(
                match,
                duration,
                args.pre_roll,
                args.post_roll,
                args.min_duration,
                args.max_duration,
                args.keep_short_source_under,
            )
            safe_term = normalize_korean(match["term"]) or "term"
            category = match.get("category") or category_for_term(safe_term)
            term_counts[category] = term_counts.get(category, 0) + 1
            output_path = args.out / f"{category}_{safe_term}_{term_counts[category]:03d}.mp4"
            render_clip(video_path, output_path, start, end)
            manifest.append(
                {
                    "source": str(video_path),
                    "clip": str(output_path),
                    "level": "A0",
                    "category": category,
                    "term": match["term"],
                    "recognized_text": match["text"],
                    "match_start": match["start"],
                    "match_end": match["end"],
                    "clip_start": start,
                    "clip_end": end,
                    "clip_duration": end - start,
                    "probability": match["probability"],
                }
            )

    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"created {len(manifest)} clips")
    print(manifest_path)


if __name__ == "__main__":
    main()
