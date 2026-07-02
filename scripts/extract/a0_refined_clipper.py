#!/usr/bin/env python3
import argparse
import json
import re
import statistics
import subprocess
from pathlib import Path


WHISPER_BIN = "/Users/jaewon/Library/Python/3.9/bin/whisper"
FACE_DETECT_SOURCE = Path(__file__).with_name("FaceDetect.swift")

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
    "싫어요",
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
    "오랫만",
]

A0_KOREAN_TERMS += [
    "뭐라고요",
    "부탁",
    "미쳤어",
    "마음에들어",
    "힘내",
    "화이팅",
    "맛있어",
    "어떡해",
    "됐어",
    "깜짝이야",
    "있잖아",
    "다시",
    "나중에",
    "멋있어",
    "궁금해",
    "피곤해",
    "누가",
    "잠시만",
    "잘자",
    "방금",
    "근데",
    "얼른",
    "상관없어",
    "그런가",
    "설마",
    "뭐야",
    "근데요",
    "모르겠어요",
    "여보세요",
    "벌써",
    "그치",
    "잘했어",
    "시끄러워",
    "왜요",
    "가요",
    "그래요",
    "그냥",
    "오빠",
    "귀여워",
    "솔직히",
    "한번만",
    "당연하지",
    "제가요",
    "아니거든",
    "알겠어",
    "아파",
    "무서워",
    "해봐",
    "그럴래",
    "필요없어",
    "힘들어",
    "여기요",
    "주세요",
    "갈게요",
    "그렇구나",
    "알았어요",
    "안녕하세요",
    "그랬어",
    "갑자기",
    "왜이래",
    "뭐해",
    "왔어",
    "어머",
    "싫은데",
    "봐봐",
    "나한테",
    "그게",
    "앉아",
]

CASUAL_NEGATIVE_TERMS = {"아니", "아니야", "아니다", "아니라", "아니고"}
POLITE_NEGATIVE_TERMS = {"아니요", "아니에요", "아닙니다"}


def normalize_korean(text):
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text)


def normalized_tokens(text):
    return [normalize_korean(token) for token in re.findall(r"[0-9A-Za-z가-힣]+", text)]


def term_family(term):
    normalized = normalize_korean(term)
    if normalized == "아니":
        return CASUAL_NEGATIVE_TERMS
    if normalized == "아니에요":
        return POLITE_NEGATIVE_TERMS
    if normalized in {"오랜만", "오랫만"}:
        return {"오랜만", "오랫만"}
    return {normalized}


def category_for_term(term):
    normalized = normalize_korean(term)
    if normalized in CASUAL_NEGATIVE_TERMS:
        return "아니"
    if normalized in POLITE_NEGATIVE_TERMS:
        return "아니에요"
    if normalized in {"오랜만", "오랫만"}:
        return "오랜만"
    return normalized or "term"


def surface_for_normalized(normalized_word, expected_term):
    normalized_expected = normalize_korean(expected_term)
    if normalized_word == normalized_expected:
        return expected_term
    return normalized_word


def parse_timecode(value):
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000.0


def parse_srt(path):
    content = path.read_text(encoding="utf-8-sig", errors="replace")
    blocks = re.split(r"\n\s*\n", content.strip())
    entries = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        time_line_index = 0 if "-->" in lines[0] else 1
        if time_line_index >= len(lines) or "-->" not in lines[time_line_index]:
            continue
        start_raw, end_raw = [part.strip() for part in lines[time_line_index].split("-->")]
        text = re.sub(r"<[^>]+>", "", " ".join(lines[time_line_index + 1 :]))
        entries.append({"start": parse_timecode(start_raw), "end": parse_timecode(end_raw), "text": text})
    return entries


def best_term(text, terms):
    tokens = set(normalized_tokens(text))
    matches = []
    for term in terms:
        normalized_term = normalize_korean(term)
        if not normalized_term:
            continue
        if tokens.intersection(term_family(term)):
            matches.append((term, normalized_term))
    if not matches:
        return None
    return max(matches, key=lambda item: len(item[1]))


def run(cmd):
    subprocess.run(cmd, check=True)


def run_capture(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def ffprobe_duration(video_path):
    result = run_capture(
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
    )
    return float(result.stdout.strip())


def ffprobe_video_size(video_path):
    result = run_capture(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0:s=x",
            str(video_path),
        ],
    )
    width, height = result.stdout.strip().split("x")
    return int(width), int(height)


def even_int(value):
    return int(value) - (int(value) % 2)


def clamp(value, low, high):
    return max(low, min(high, value))


def ensure_face_detector(work_dir):
    detector = work_dir / "FaceDetect"
    if detector.exists() and detector.stat().st_mtime >= FACE_DETECT_SOURCE.stat().st_mtime:
        return detector
    module_cache = work_dir / "swift_module_cache"
    module_cache.mkdir(parents=True, exist_ok=True)
    run(["xcrun", "swiftc", "-module-cache-path", str(module_cache), str(FACE_DETECT_SOURCE), "-o", str(detector)])
    return detector


def extract_frame(video_path, time_sec, output_path):
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{max(0.0, time_sec):.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(output_path),
        ]
    )


def detect_faces(detector_path, image_path):
    result = run_capture([str(detector_path), str(image_path)])
    return json.loads(result.stdout or "[]")


def motion_score_for_crop(video_path, start, end, crop):
    duration = max(0.18, end - start)
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-ss",
            f"{max(0.0, start):.3f}",
            "-i",
            str(video_path),
            "-t",
            f"{duration:.3f}",
            "-vf",
            (
                f"crop={crop['width']}:{crop['height']}:{crop['x']}:{crop['y']},"
                "crop=iw:floor(ih*0.68):0:0,"
                "fps=12,format=gray,tblend=all_mode=difference,signalstats,metadata=print"
            ),
            "-an",
            "-f",
            "null",
            "-",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    values = [float(match.group(1)) for match in re.finditer(r"lavfi\.signalstats\.YAVG=([0-9.]+)", result.stderr)]
    return statistics.mean(values) if values else 0.0


def choose_motion_crop(region_path, match, target_width, target_height):
    width, height = ffprobe_video_size(region_path)
    crop_aspect = target_width / target_height
    if width / height > crop_aspect:
        crop_h = even_int(height)
        crop_w = even_int(crop_h * crop_aspect)
    else:
        crop_w = even_int(width)
        crop_h = even_int(crop_w / crop_aspect)

    max_x = max(0, width - crop_w)
    centers = [0.18, 0.32, 0.50, 0.68, 0.82]
    crops = []
    for center in centers:
        x = even_int(clamp(width * center - crop_w / 2, 0, max_x))
        y = even_int(clamp(height * 0.50 - crop_h / 2, 0, max(0, height - crop_h)))
        crop = {"x": x, "y": y, "width": crop_w, "height": crop_h}
        if crop not in crops:
            crops.append(crop)

    start = max(0.0, match["word_start"] - 0.12)
    end = match["word_end"] + 0.12
    scored = []
    for crop in crops:
        score = motion_score_for_crop(region_path, start, end, crop)
        # Prefer real motion but avoid tiny differences from compression noise.
        scored.append((score, crop))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored or scored[0][0] < 0.35:
        return None
    best_score, best_crop = scored[0]
    center_x = width / 2
    edge_margin = max(48, crop_w * 0.12)
    original_best_score = best_score
    if best_crop["x"] <= edge_margin or best_crop["x"] >= max_x - edge_margin:
        viable = [item for item in scored if item[0] >= best_score * 0.40]
        if viable:
            best_score, best_crop = min(
                viable,
                key=lambda item: abs((item[1]["x"] + item[1]["width"] / 2) - center_x),
            )
    if best_score < original_best_score * 0.65:
        return None
    return {
        "time": (match["word_start"] + match["word_end"]) / 2,
        "x": best_crop["x"],
        "y": best_crop["y"],
        "width": best_crop["width"],
        "height": best_crop["height"],
        "center_x": best_crop["x"] + best_crop["width"] / 2,
        "center_y": best_crop["y"] + best_crop["height"] * 0.42,
        "image_width": width,
        "image_height": height,
        "area_ratio": (best_crop["width"] * best_crop["height"]) / (width * height),
        "confidence": 0.0,
        "kind": "motion_crop",
        "score": best_score,
        "crop_override": best_crop,
        "motion_candidates": [{"score": score, "crop": crop} for score, crop in scored],
    }


def choose_speaker_face(region_path, match, detector_path, face_dir, min_face_ratio):
    duration = ffprobe_duration(region_path)
    sample_times = [
        (match["word_start"] + match["word_end"]) / 2,
        (match["utterance_start"] + match["utterance_end"]) / 2,
        max(match["utterance_start"], match["word_start"] - 0.10),
        min(duration - 0.04, match["word_end"] + 0.10),
    ]

    best = None
    for index, time_sec in enumerate(sample_times):
        if time_sec < 0 or time_sec >= duration:
            continue
        frame_path = face_dir / f"{region_path.stem}_{index:02d}.jpg"
        extract_frame(region_path, time_sec, frame_path)
        for face in detect_faces(detector_path, frame_path):
            area_ratio = (face["width"] * face["height"]) / (face["imageWidth"] * face["imageHeight"])
            if area_ratio < min_face_ratio:
                continue
            center_bias = abs((face["x"] + face["width"] / 2) / face["imageWidth"] - 0.5)
            score = area_ratio * float(face.get("confidence", 1.0)) - center_bias * 0.01
            candidate = {
                "time": time_sec,
                "x": face["x"],
                "y": face["y"],
                "width": face["width"],
                "height": face["height"],
                "center_x": face["x"] + face["width"] / 2,
                "center_y": face["y"] + face["height"] / 2,
                "image_width": face["imageWidth"],
                "image_height": face["imageHeight"],
                "area_ratio": area_ratio,
                "confidence": face.get("confidence"),
                "score": score,
            }
            if best is None or candidate["score"] > best["score"]:
                best = candidate
    if best is not None:
        return best
    return choose_motion_crop(region_path, match, 1080, 1920)


def detect_scene_cuts(video_path, threshold=0.12):
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(video_path),
            "-vf",
            f"select='gt(scene,{threshold})',showinfo",
            "-an",
            "-f",
            "null",
            "-",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    cuts = []
    for match in re.finditer(r"pts_time:([0-9.]+)", result.stderr):
        cuts.append(float(match.group(1)))
    return cuts


def detect_black_ranges(video_path):
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(video_path),
            "-vf",
            "blackdetect=d=0.05:pix_th=0.08",
            "-an",
            "-f",
            "null",
            "-",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    ranges = []
    for match in re.finditer(
        r"black_start:([0-9.]+)\s+black_end:([0-9.]+)\s+black_duration:([0-9.]+)",
        result.stderr,
    ):
        ranges.append((float(match.group(1)), float(match.group(2)), float(match.group(3))))
    return ranges


def sample_luma_values(video_path):
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(video_path),
            "-vf",
            "fps=2,signalstats,metadata=print",
            "-an",
            "-f",
            "null",
            "-",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    values = []
    for match in re.finditer(r"lavfi\.signalstats\.YAVG=([0-9.]+)", result.stderr):
        values.append(float(match.group(1)))
    return values


def render_region(video_path, output_path, start, end):
    if output_path.exists():
        try:
            if ffprobe_duration(output_path) > 0:
                return
        except Exception:
            output_path.unlink(missing_ok=True)
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


def render_face_crop_region(
    video_path,
    output_path,
    start,
    end,
    face_info,
    target_width=1080,
    target_height=1920,
    output_preset="slow",
    video_bitrate="9M",
    maxrate="11M",
    bufsize="18M",
    profile="main",
    scale_flags="lanczos",
    sharpen_filter="unsharp=5:5:0.30:3:3:0",
):
    if output_path.exists():
        try:
            if ffprobe_duration(output_path) > 0:
                return
        except Exception:
            output_path.unlink(missing_ok=True)
    source_width, source_height = ffprobe_video_size(video_path)
    if face_info.get("crop_override"):
        override = face_info["crop_override"]
        scale_x = source_width / face_info["image_width"]
        scale_y = source_height / face_info["image_height"]
        x = even_int(clamp(override["x"] * scale_x, 0, source_width - 2))
        y = even_int(clamp(override["y"] * scale_y, 0, source_height - 2))
        crop_w = even_int(min(source_width - x, override["width"] * scale_x))
        crop_h = even_int(min(source_height - y, override["height"] * scale_y))
    else:
        crop_aspect = target_width / target_height
        if source_width / source_height > crop_aspect:
            crop_h = even_int(source_height)
            crop_w = even_int(crop_h * crop_aspect)
        else:
            crop_w = even_int(source_width)
            crop_h = even_int(crop_w / crop_aspect)

        scale_x = source_width / face_info["image_width"]
        scale_y = source_height / face_info["image_height"]
        face_center_x = face_info["center_x"] * scale_x
        face_center_y = face_info["center_y"] * scale_y

        x = even_int(clamp(face_center_x - crop_w / 2, 0, source_width - crop_w))
        # Keep the face slightly above center, matching dialogue close-ups.
        y = even_int(clamp(face_center_y - crop_h * 0.42, 0, source_height - crop_h))
    filters = [
        f"crop={crop_w}:{crop_h}:{x}:{y}",
        f"scale={target_width}:{target_height}:flags={scale_flags}",
    ]
    if sharpen_filter:
        filters.append(sharpen_filter)
    vf = ",".join(filters)

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
            "-vf",
            vf,
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-profile:v",
            profile,
            "-preset",
            output_preset,
            "-b:v",
            video_bitrate,
            "-maxrate",
            maxrate,
            "-bufsize",
            bufsize,
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    face_info["crop"] = {
        "x": x,
        "y": y,
        "width": crop_w,
        "height": crop_h,
        "target_width": target_width,
        "target_height": target_height,
    }


def transcribe_region(region_path, transcript_dir, model):
    transcript_path = transcript_dir / f"{region_path.stem}.json"
    if transcript_path.exists():
        return transcript_path
    run(
        [
            WHISPER_BIN,
            str(region_path),
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


def find_spoken_match(transcript_path, expected_term):
    data = json.loads(transcript_path.read_text())
    expected_family = term_family(expected_term)
    candidates = []

    for segment in data.get("segments", []):
        words = segment.get("words") or []
        for word in words:
            normalized_word = normalize_korean(word.get("word", ""))
            if normalized_word in expected_family:
                surface_term = surface_for_normalized(normalized_word, expected_term)
                candidates.append(
                    {
                        "term": surface_term,
                        "category": category_for_term(surface_term),
                        "text": word.get("word", "").strip(),
                        "word_start": float(word["start"]),
                        "word_end": float(word["end"]),
                        "utterance_start": float(segment.get("start", word["start"])),
                        "utterance_end": float(segment.get("end", word["end"])),
                        "utterance_text": segment.get("text", "").strip(),
                        "probability": word.get("probability"),
                    }
                )
    if candidates:
        return max(candidates, key=lambda item: item.get("probability") or 0)

    if set(normalized_tokens(data.get("text", ""))).intersection(expected_family):
        segment = (data.get("segments") or [{}])[0]
        surface_term = expected_term
        return {
            "term": surface_term,
            "category": category_for_term(surface_term),
            "text": data.get("text", "").strip(),
            "word_start": float(segment.get("start", 0.0)),
            "word_end": float(segment.get("end", 0.0)),
            "utterance_start": float(segment.get("start", 0.0)),
            "utterance_end": float(segment.get("end", 0.0)),
            "utterance_text": data.get("text", "").strip(),
            "probability": None,
        }
    return None


def keyword_focus_ok(match, max_focus_tokens):
    tokens = [token for token in normalized_tokens(match.get("utterance_text") or match.get("text") or "") if token]
    term = normalize_korean(match.get("term") or "")
    if not tokens or not term:
        return False, {"tokens": tokens, "term": term}
    if len(tokens) <= max_focus_tokens:
        return True, {"tokens": tokens, "term": term}
    if len(tokens) == 2 and tokens[0] in {"아", "어", "음", "저", "그"}:
        return True, {"tokens": tokens, "term": term}
    return False, {"tokens": tokens, "term": term}


def natural_window(
    region_start,
    region_end,
    match,
    pre_roll,
    post_roll,
    min_pre_roll,
    min_post_roll,
    min_duration,
    max_duration,
):
    word_start = region_start + match["word_start"]
    word_end = region_start + match["word_end"]

    start = max(region_start, word_start - pre_roll)
    end = min(region_end, word_end + post_roll)

    if end - start > max_duration:
        compact_start = max(region_start, word_start - min_pre_roll)
        compact_end = min(region_end, word_end + min_post_roll)
        if compact_end - compact_start <= max_duration:
            start, end = compact_start, compact_end
        else:
            return None

    if end - start < min_duration:
        needed = min_duration - (end - start)
        grow_left = min(needed / 2, start - region_start)
        grow_right = needed - grow_left
        start = max(region_start, start - grow_left)
        end = min(region_end, end + grow_right)

    if start > word_start - min_pre_roll:
        return None
    if end < word_end + min_post_roll:
        return None
    if end - start > max_duration:
        return None
    return start, end


def validate_clip(
    clip_path,
    match,
    clip_start,
    reject_scene_during_utterance=True,
    min_yavg=45.0,
    min_keyword_start=0.22,
):
    clip_duration = ffprobe_duration(clip_path)
    scene_cuts = detect_scene_cuts(clip_path)
    black_ranges = detect_black_ranges(clip_path)
    luma_values = sample_luma_values(clip_path)

    relative_word_start = match["word_start"] + clip_start["region_start"] - clip_start["clip_start"]
    relative_word_end = match["word_end"] + clip_start["region_start"] - clip_start["clip_start"]

    reasons = []
    if relative_word_start < min_keyword_start:
        reasons.append("keyword_too_close_to_start")

    if reject_scene_during_utterance:
        for cut in scene_cuts:
            if relative_word_start - 0.08 <= cut <= relative_word_end + 0.08:
                reasons.append("scene_cut_during_keyword")
                break
    for cut in scene_cuts:
        if cut <= 0.15 or cut >= clip_duration - 0.15:
            reasons.append("scene_cut_too_close_to_edge")
            break

    for start, end, _duration in black_ranges:
        if start <= 0.08 or end >= clip_duration - 0.08:
            reasons.append("black_at_edge")
            break

    median_yavg = statistics.median(luma_values) if luma_values else None
    if median_yavg is not None and median_yavg < min_yavg:
        reasons.append("too_dark_for_speaker_visibility")

    return {
        "ok": not reasons,
        "reasons": reasons,
        "scene_cuts": scene_cuts,
        "black_ranges": black_ranges,
        "luma_median": median_yavg,
    }


def main():
    parser = argparse.ArgumentParser(description="Refine subtitle A0 candidates with local STT word timestamps.")
    parser.add_argument("video", type=Path)
    parser.add_argument("--srt", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=Path("outputs/crash_a0_refined_test"))
    parser.add_argument("--work", type=Path, default=Path("work/a0_refined"))
    parser.add_argument("--max-clips", type=int, default=20)
    parser.add_argument("--model", default="tiny")
    parser.add_argument("--candidate-pad", type=float, default=2.0)
    parser.add_argument("--pre-roll", type=float, default=0.25)
    parser.add_argument("--post-roll", type=float, default=0.35)
    parser.add_argument("--min-pre-roll", type=float, default=0.22)
    parser.add_argument("--min-post-roll", type=float, default=0.25)
    parser.add_argument("--min-keyword-start", type=float, default=0.22)
    parser.add_argument("--min-duration", type=float, default=1.00)
    parser.add_argument("--max-duration", type=float, default=1.80)
    parser.add_argument("--max-focus-tokens", type=int, default=1)
    parser.add_argument("--min-probability", type=float, default=0.35)
    parser.add_argument("--min-yavg", type=float, default=45.0)
    parser.add_argument("--min-face-ratio", type=float, default=0.003)
    parser.add_argument("--target-width", type=int, default=1080)
    parser.add_argument("--target-height", type=int, default=1920)
    parser.add_argument("--output-preset", default="veryslow")
    parser.add_argument("--video-bitrate", default="12M")
    parser.add_argument("--maxrate", default="16M")
    parser.add_argument("--bufsize", default="24M")
    parser.add_argument("--profile", default="main")
    parser.add_argument("--scale-flags", default="lanczos")
    parser.add_argument("--sharpen-filter", default="unsharp=5:5:0.30:3:3:0")
    parser.add_argument("--allow-scene-cut-during-utterance", action="store_true")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    region_dir = args.work / "regions"
    transcript_dir = args.work / "transcripts"
    face_dir = args.work / "faces"
    region_dir.mkdir(parents=True, exist_ok=True)
    transcript_dir.mkdir(parents=True, exist_ok=True)
    face_dir.mkdir(parents=True, exist_ok=True)
    detector_path = ensure_face_detector(args.work)

    duration = ffprobe_duration(args.video)
    manifest = []
    rejected = []
    term_counts = {}
    candidate_index = 0

    for entry in parse_srt(args.srt):
        matched = best_term(entry["text"], A0_KOREAN_TERMS)
        if not matched:
            continue

        term = matched[0]
        region_start = max(0.0, entry["start"] - args.candidate_pad)
        region_end = min(duration, entry["end"] + args.candidate_pad)
        candidate_index += 1
        region_path = region_dir / f"candidate_{candidate_index:03d}.mp4"
        render_region(args.video, region_path, region_start, region_end)
        transcript_path = transcribe_region(region_path, transcript_dir, args.model)
        spoken_match = find_spoken_match(transcript_path, term)
        if not spoken_match:
            rejected.append({"candidate": candidate_index, "reason": "no_spoken_match", "subtitle_text": entry["text"]})
            continue
        if spoken_match.get("probability") is not None and spoken_match["probability"] < args.min_probability:
            rejected.append(
                {
                    "candidate": candidate_index,
                    "reason": "low_probability",
                    "probability": spoken_match.get("probability"),
                    "subtitle_text": entry["text"],
                    "utterance_text": spoken_match.get("utterance_text"),
                }
            )
            continue
        focus_ok, focus_detail = keyword_focus_ok(spoken_match, args.max_focus_tokens)
        if not focus_ok:
            rejected.append(
                {
                    "candidate": candidate_index,
                    "reason": "keyword_not_isolated",
                    "focus": focus_detail,
                    "subtitle_text": entry["text"],
                    "utterance_text": spoken_match.get("utterance_text"),
                    "spoken_text": spoken_match.get("text"),
                }
            )
            continue

        clip_window = natural_window(
            region_start,
            region_end,
            spoken_match,
            args.pre_roll,
            args.post_roll,
            args.min_pre_roll,
            args.min_post_roll,
            args.min_duration,
            args.max_duration,
        )
        if clip_window is None:
            rejected.append(
                {
                    "candidate": candidate_index,
                    "reason": "unnatural_duration_or_edge",
                    "subtitle_text": entry["text"],
                    "utterance_text": spoken_match.get("utterance_text"),
                    "word_start": region_start + spoken_match["word_start"],
                    "word_end": region_start + spoken_match["word_end"],
                    "utterance_start": region_start + spoken_match["utterance_start"],
                    "utterance_end": region_start + spoken_match["utterance_end"],
                }
            )
            continue
        clip_start, clip_end = clip_window

        speaker_face = choose_speaker_face(
            region_path,
            spoken_match,
            detector_path,
            face_dir,
            args.min_face_ratio,
        )
        if not speaker_face:
            rejected.append(
                {
                    "candidate": candidate_index,
                    "reason": "no_visible_speaker_face",
                    "subtitle_text": entry["text"],
                    "utterance_text": spoken_match.get("utterance_text"),
                    "word_start": region_start + spoken_match["word_start"],
                    "word_end": region_start + spoken_match["word_end"],
                    "utterance_start": region_start + spoken_match["utterance_start"],
                    "utterance_end": region_start + spoken_match["utterance_end"],
                }
            )
            continue

        surface_term = normalize_korean(spoken_match.get("term") or term) or "term"
        category = spoken_match.get("category") or category_for_term(surface_term)
        term_counts[category] = term_counts.get(category, 0) + 1
        output_path = args.out / f"{category}_{surface_term}_{term_counts[category]:03d}.mp4"
        render_face_crop_region(
            args.video,
            output_path,
            clip_start,
            clip_end,
            speaker_face,
            target_width=args.target_width,
            target_height=args.target_height,
            output_preset=args.output_preset,
            video_bitrate=args.video_bitrate,
            maxrate=args.maxrate,
            bufsize=args.bufsize,
            profile=args.profile,
            scale_flags=args.scale_flags,
            sharpen_filter=args.sharpen_filter,
        )
        validation = validate_clip(
            output_path,
            spoken_match,
            {
                "region_start": region_start,
                "clip_start": clip_start,
            },
            reject_scene_during_utterance=not args.allow_scene_cut_during_utterance,
            min_yavg=args.min_yavg,
            min_keyword_start=args.min_keyword_start,
        )
        if not validation["ok"]:
            output_path.unlink(missing_ok=True)
            term_counts[category] -= 1
            rejected.append(
                {
                    "candidate": candidate_index,
                    "reason": "visual_or_timing_validation",
                    "reasons": validation["reasons"],
                    "scene_cuts": validation["scene_cuts"],
                    "black_ranges": validation["black_ranges"],
                    "luma_median": validation["luma_median"],
                    "subtitle_text": entry["text"],
                    "utterance_text": spoken_match.get("utterance_text"),
                    "category": category,
                    "term": surface_term,
                    "speaker_face": speaker_face,
                }
            )
            continue
        manifest.append(
            {
                "clip": str(output_path),
                "level": "A0",
                "category": category,
                "term": surface_term,
                "subtitle_text": entry["text"],
                "spoken_text": spoken_match["text"],
                "utterance_text": spoken_match.get("utterance_text"),
                "word_start": region_start + spoken_match["word_start"],
                "word_end": region_start + spoken_match["word_end"],
                "utterance_start": region_start + spoken_match["utterance_start"],
                "utterance_end": region_start + spoken_match["utterance_end"],
                "clip_start": clip_start,
                "clip_end": clip_end,
                "clip_duration": clip_end - clip_start,
                "probability": spoken_match.get("probability"),
                "scene_cuts": validation["scene_cuts"],
                "black_ranges": validation["black_ranges"],
                "luma_median": validation["luma_median"],
                "speaker_face": speaker_face,
            }
        )
        if len(manifest) >= args.max_clips:
            break

    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    rejected_path = args.out / "rejected.json"
    rejected_path.write_text(json.dumps(rejected, ensure_ascii=False, indent=2))
    print(f"created {len(manifest)} clips")
    print(manifest_path)
    print(f"rejected {len(rejected)} candidates")
    print(rejected_path)


if __name__ == "__main__":
    main()
