#!/usr/bin/env python3
import argparse
import array
import hashlib
import importlib.util
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLIPPER_PATH = ROOT / "scripts/extract/a0_refined_clipper.py"
SUBTITLE_RENDERER_SOURCE = ROOT / "scripts/render/RenderSubtitleOverlay.swift"
CTA_VIDEO = ROOT / "assets/cta/cta_video.mp4"
OUTPUT_ROOT = ROOT / "outputs/drama_folder_ad_only_batch"
WORK_ROOT = ROOT / "work/drama_folder_ad_only_batch"
ACCELERATED_PYTHON = Path("/Applications/Xcode.app/Contents/Developer/usr/bin/python3")
RUNTIME_CACHE_ROOT = WORK_ROOT / "_runtime_cache"
COLOR_FILTER = "eq=brightness=0.045:contrast=0.96:saturation=0.95:gamma=1.10"
CLIP_PRE_ROLL = 0.32
CLIP_POST_ROLL = 0.36
MIN_CLIP_DURATION = 1.00
TARGET_SHORT_CLIP_DURATION = 1.35
MAX_CLIP_DURATION = 2.10
MAX_SCENE_AWARE_CLIP_DURATION = 2.20
END_SCENE_CUT_LOOKBACK = 0.55
MIN_POST_SCENE_CUT_HOLD = 0.50
TARGET_POST_SCENE_CUT_HOLD = 0.75
SCENE_CUT_HARD_MARGIN = 0.055
MIN_SCENE_SEGMENT_HOLD = 0.55
EDGE_SCENE_CUT_GUARD = 0.35
KEYWORD_SCENE_CUT_GUARD = 0.08
MIN_HARD_CUT_CLIP_DURATION = 0.90
MIN_FINAL_DURATION = 15.0
MIN_FINAL_CLIP_PACING_DURATION = 0.95
MAX_FINAL_CLIPS_PER_VIDEO = 0
ALLOW_FINAL_INTERNAL_SCENE_CUTS = True
MAX_FOCUS_TOKENS = 20
KEYWORD_FILLER_TOKENS = {"아", "어", "음", "저", "그"}
WHISPER_MODEL = "tiny"
CANDIDATE_PAD = 1.40
MAX_SUBTITLE_CANDIDATE_DURATION = None
MIN_EXACT_WORD_PROBABILITY = 0.35
MIN_RENDERED_EXACT_WORD_PROBABILITY = 0.35
MIN_RENDERED_KEYWORD_SECONDS_PER_SYLLABLE = 0.09
MIN_RENDERED_KEYWORD_DURATION_FLOOR = 0.18
MAX_RENDERED_KEYWORD_DURATION_REQUIREMENT = 0.72
FAST_KEYWORD_FRAME_ONLY = True
FAST_VISUAL_FILL_SAMPLES = True
VERIFY_AUDIO_BEFORE_RENDER = False
SOURCE_ASR_AUDIO_ONLY = True
VERIFY_RENDERED_SPOKEN_BEFORE_POOL = True
VERIFY_SOURCE_AUTO_AUDIO_BEFORE_RENDER = False
VERIFY_KEYWORD_SPEAKER_BEFORE_POOL = True
VERIFY_OVERALL_FACE_BEFORE_POOL = True
REQUIRE_SOURCE_MOUTH_BEFORE_POOL = False
STRICT_POOL_VALIDATION = True
DELETE_FAILED_FINAL_CLIPS = False
VERIFY_FINAL_AUTO_KOREAN_AUDIO = True
REQUIRE_FINAL_AUTO_KEYWORD = True
REQUIRE_FINAL_RENDERED_FACE = True
REQUIRE_RENDERED_SPOKEN_KEYWORD = True
REQUIRE_CUT_AWARE_CROP = True
REQUIRE_FINAL_CUT_AWARE_SUBJECTS = True
REQUIRE_FINAL_START_FACE = True
REQUIRE_CLEAN_SOURCE_FRAME = True
REQUIRE_SINGLE_SHOT_CLIP = False
MIN_KEYWORD_RMS_DBFS = -34.0
MIN_KEYWORD_PEAK_DBFS = -22.0
KEYWORD_AUDIO_PAD = 0.10
MIN_SOURCE_SPEAKER_MOUTH_MOTION = 0.006
MIN_RENDERED_SPEAKER_MOUTH_MOTION = 0.016
MIN_RENDERED_KEYWORD_TAIL = 0.08
MAX_STILL_FACE_MOTION = 0.020
MIN_RENDERED_KEYWORD_FACE_AREA = 0.018
MIN_RENDERED_START_FACE_AREA = 0.006
MIN_RENDERED_FACE_CONFIDENCE = 0.50
STRONG_RENDERED_FACE_CONFIDENCE = 0.62
RENDERED_FACE_CENTER_X_RANGE = (0.28, 0.72)
RENDERED_FACE_CENTER_Y_RANGE = (0.20, 0.72)
LOW_CONF_RENDERED_FACE_CENTER_X_RANGE = (0.36, 0.64)
LOW_CONF_RENDERED_FACE_CENTER_Y_RANGE = (0.24, 0.66)
MIN_KEYWORD_VALIDATION_WINDOW = 0.65
KEYWORD_VALIDATION_EXTRA_PAD = 0.12
FRAME_TIGHTEN_CLIP_WINDOW = True
FRAME_TIGHT_START_SCAN_SECONDS = 1.15
FRAME_TIGHT_END_SCAN_SECONDS = 0.55
FRAME_TIGHT_KEYWORD_AUDIO_LEAD = 0.08
FRAME_TIGHT_KEYWORD_AUDIO_TAIL = 0.10
FRAME_TIGHT_MIN_START_SHIFT = 0.012
FRAME_TIGHT_MIN_END_SHIFT = 0.012
FRAME_TIGHT_MIN_SOURCE_FACE_RATIO = 0.0022
FRAME_TIGHT_MAX_SPEAKER_BIAS = 0.20
FINAL_START_FACE_SAMPLE_TIMES = (0.0, 0.08, 0.20)
REQUIRE_FINAL_FIRST_FRAME_FACE = True

DRAMA_FOLDERS = [
    Path("/Volumes/EXTERNAL_USB/Crash.Landing.on.You.S01.2019.1080p.NF.WEBRip.DDP2.0.x265-RL"),
    Path("/Volumes/EXTERNAL_USB/Its.Okay.to.Not.Be.Okay.S01.2020.1080p.NF.WEBRip.DDP2.0.x265-RL"),
    Path("/Volumes/EXTERNAL_USB/Mr.Sunshine.S01.2018.1080p.NF.WEBRip.DDP2.0.x265-RL"),
    Path("/Volumes/EXTERNAL_USB/Reply.1988.S01.KOREAN.1080p.NF.WEBRip.DDP2.0.x264-ExREN[rartv]"),
    Path("/Volumes/EXTERNAL_USB/Strong.Woman.Do.Bong.Soon.S01.1080p.VIKI.WEB-DL.AAC.x264-BlackLuster"),
    Path("/Volumes/EXTERNAL_USB/Vincenzo.S01.1080p.NF.WEBRip.DDP2.0.x265"),
]

LEXICON = {
    "안녕": ("[an-nyeong]", "Hi.", "Casual"),
    "네": ("[ne]", "Yes.", "Polite"),
    "아니": ("[a-ni]", "No.", "Casual"),
    "아니야": ("[a-ni-ya]", "No.", "Casual"),
    "아니요": ("[a-ni-yo]", "No.", "Polite"),
    "아니에요": ("[a-ni-e-yo]", "No.", "Polite"),
    "고마워": ("[go-ma-wo]", "Thanks.", "Casual"),
    "고마워요": ("[go-ma-wo-yo]", "Thank you.", "Polite"),
    "감사": ("[gam-sa]", "Thanks.", "Polite"),
    "감사합니다": ("[gam-sa-ham-ni-da]", "Thank you.", "Polite"),
    "미안": ("[mi-an]", "Sorry.", "Casual"),
    "미안해": ("[mi-an-hae]", "Sorry.", "Casual"),
    "미안해요": ("[mi-an-hae-yo]", "Sorry.", "Polite"),
    "죄송": ("[joe-song]", "Sorry.", "Polite"),
    "죄송합니다": ("[joe-song-ham-ni-da]", "I'm sorry.", "Polite"),
    "괜찮아": ("[gwaen-chan-a]", "It's okay.", "Casual"),
    "괜찮아요": ("[gwaen-chan-a-yo]", "It's okay.", "Polite"),
    "좋아": ("[jo-a]", "Good.", "Casual"),
    "좋아요": ("[jo-a-yo]", "Good.", "Polite"),
    "싫어": ("[sil-eo]", "No way.", "Casual"),
    "싫어요": ("[sil-eo-yo]", "No, thanks.", "Polite"),
    "맞아": ("[ma-ja]", "Right.", "Casual"),
    "맞아요": ("[ma-ja-yo]", "That's right.", "Polite"),
    "몰라": ("[mol-la]", "I don't know.", "Casual"),
    "몰라요": ("[mol-la-yo]", "I don't know.", "Polite"),
    "알아": ("[a-ra]", "I know.", "Casual"),
    "알아요": ("[a-ra-yo]", "I know.", "Polite"),
    "알았어요": ("[a-ra-sseo-yo]", "Okay.", "Polite"),
    "알겠어": ("[al-ge-sseo]", "Got it.", "Casual"),
    "있어": ("[i-sseo]", "There is.", "Casual"),
    "있어요": ("[i-sseo-yo]", "There is.", "Polite"),
    "없어": ("[eop-seo]", "There isn't.", "Casual"),
    "없어요": ("[eop-seo-yo]", "There isn't.", "Polite"),
    "가자": ("[ga-ja]", "Let's go.", "Casual"),
    "제발": ("[je-bal]", "Please.", "Casual"),
    "잠깐": ("[jam-kkan]", "Wait.", "Casual"),
    "잠시만": ("[jam-si-man]", "One moment.", "Casual"),
    "빨리": ("[ppal-li]", "Hurry.", "Casual"),
    "지금": ("[ji-geum]", "Now.", "Casual"),
    "오늘": ("[o-neul]", "Today.", "Casual"),
    "내일": ("[nae-il]", "Tomorrow.", "Casual"),
    "어제": ("[eo-je]", "Yesterday.", "Casual"),
    "여기": ("[yeo-gi]", "Here.", "Casual"),
    "여기요": ("[yeo-gi-yo]", "Excuse me.", "Polite"),
    "저기": ("[jeo-gi]", "There.", "Casual"),
    "어디": ("[eo-di]", "Where?", "Casual"),
    "누구": ("[nu-gu]", "Who?", "Casual"),
    "뭐": ("[mwo]", "What?", "Casual"),
    "뭐야": ("[mwo-ya]", "What?", "Casual"),
    "뭐라고요": ("[mwo-ra-go-yo]", "What did you say?", "Polite"),
    "왜": ("[wae]", "Why?", "Casual"),
    "왜요": ("[wae-yo]", "Why?", "Polite"),
    "언제": ("[eon-je]", "When?", "Casual"),
    "어떻게": ("[eo-tteo-ke]", "How?", "Casual"),
    "이거": ("[i-geo]", "This.", "Casual"),
    "저거": ("[jeo-geo]", "That.", "Casual"),
    "그거": ("[geu-geo]", "That.", "Casual"),
    "나도": ("[na-do]", "Me too.", "Casual"),
    "우리": ("[u-ri]", "We.", "Casual"),
    "엄마": ("[eom-ma]", "Mom.", "Casual"),
    "아빠": ("[a-ppa]", "Dad.", "Casual"),
    "친구": ("[chin-gu]", "Friend.", "Casual"),
    "사랑": ("[sa-rang]", "Love.", "Casual"),
    "진짜": ("[jin-jja]", "Really?", "Casual"),
    "너무": ("[neo-mu]", "Too much.", "Casual"),
    "조금": ("[jo-geum]", "A little.", "Casual"),
    "아마": ("[a-ma]", "Maybe.", "Casual"),
    "오랜만": ("[o-raen-man]", "Long time no see.", "Casual"),
    "부탁": ("[bu-tak]", "Favor.", "Casual"),
    "미쳤어": ("[mi-cheo-sseo]", "That's crazy.", "Casual"),
    "힘내": ("[him-nae]", "Cheer up.", "Casual"),
    "화이팅": ("[hwa-i-ting]", "Fighting.", "Casual"),
    "맛있어": ("[ma-si-sseo]", "It's delicious.", "Casual"),
    "어떡해": ("[eo-tteok-hae]", "What do I do?", "Casual"),
    "됐어": ("[dwae-sseo]", "Forget it.", "Casual"),
    "깜짝이야": ("[kkam-jja-gi-ya]", "You scared me.", "Casual"),
    "있잖아": ("[it-ja-na]", "You know.", "Casual"),
    "다시": ("[da-si]", "Again.", "Casual"),
    "나중에": ("[na-jung-e]", "Later.", "Casual"),
    "멋있어": ("[meo-si-sseo]", "Cool.", "Casual"),
    "궁금해": ("[gung-geum-hae]", "I'm curious.", "Casual"),
    "피곤해": ("[pi-gon-hae]", "I'm tired.", "Casual"),
    "잘자": ("[jal-ja]", "Good night.", "Casual"),
    "방금": ("[bang-geum]", "Just now.", "Casual"),
    "근데": ("[geun-de]", "But.", "Casual"),
    "얼른": ("[eol-leun]", "Quickly.", "Casual"),
    "상관없어": ("[sang-gwan-eop-seo]", "It doesn't matter.", "Casual"),
    "설마": ("[seol-ma]", "No way.", "Casual"),
    "여보세요": ("[yeo-bo-se-yo]", "Hello?", "Polite"),
    "벌써": ("[beol-sseo]", "Already.", "Casual"),
    "그치": ("[geu-chi]", "Right?", "Casual"),
    "잘했어": ("[jal-hae-sseo]", "Good job.", "Casual"),
    "시끄러워": ("[si-kkeu-reo-wo]", "Be quiet.", "Casual"),
    "그래요": ("[geu-rae-yo]", "Sure.", "Polite"),
    "그냥": ("[geu-nyang]", "Just.", "Casual"),
    "오빠": ("[o-ppa]", "Oppa.", "Casual"),
    "귀여워": ("[gwi-yeo-wo]", "Cute.", "Casual"),
    "솔직히": ("[sol-jik-hi]", "Honestly.", "Casual"),
    "한번만": ("[han-beon-man]", "Just once.", "Casual"),
    "당연하지": ("[dang-yeon-ha-ji]", "Of course.", "Casual"),
    "제가요": ("[je-ga-yo]", "Me?", "Polite"),
    "아파": ("[a-pa]", "It hurts.", "Casual"),
    "무서워": ("[mu-seo-wo]", "I'm scared.", "Casual"),
    "해봐": ("[hae-bwa]", "Try it.", "Casual"),
    "주세요": ("[ju-se-yo]", "Please give me.", "Polite"),
    "갈게요": ("[gal-ge-yo]", "I'll go.", "Polite"),
    "안녕하세요": ("[an-nyeong-ha-se-yo]", "Hello.", "Polite"),
    "왜이래": ("[wae-i-rae]", "What's wrong?", "Casual"),
    "뭐해": ("[mwo-hae]", "What are you doing?", "Casual"),
    "왔어": ("[wa-sseo]", "I'm here.", "Casual"),
    "어머": ("[eo-meo]", "Oh my.", "Casual"),
    "봐봐": ("[bwa-bwa]", "Look.", "Casual"),
    "앉아": ("[an-ja]", "Sit.", "Casual"),
}

REFERENCE_STYLE_EXTRA_TERMS = (
    "가요",
    "갑자기",
    "거짓말",
    "걱정 마",
    "그게",
    "그래",
    "그랬어",
    "그런가",
    "그런거아니야",
    "그럴래",
    "그럴리가",
    "그럴줄알았어",
    "그렇구나",
    "그렇습니다",
    "그만해",
    "근데요",
    "글쎄",
    "끊어",
    "끝",
    "나한테",
    "내가잘못했어",
    "누가",
    "누구세요",
    "니가",
    "다녀오겠습니다",
    "다행이다",
    "답답해",
    "당장",
    "대박",
    "들어가세요",
    "들어와",
    "따라와",
    "때문에",
    "마음에들어",
    "말도안돼",
    "말해",
    "맛있게드세요",
    "먼저갈게",
    "모르겠어요",
    "무슨뜻이야",
    "무슨일이에요",
    "무슨 일 있어",
    "뭐라는거야",
    "바보",
    "배고파",
    "보고 싶었어",
    "비밀",
    "빨리빨리",
    "사랑해",
    "사실은",
    "세상에",
    "싫은데",
    "아니거든",
    "아마도",
    "아무것도",
    "아싸",
    "아이씨",
    "안됩니다",
    "어떻게알았어",
    "어쩌라고",
    "얼마나",
    "역시",
    "오랜만이야",
    "이게뭐야",
    "이리 와",
    "잘먹겠습니다",
    "잘어울려",
    "잘 지냈어",
    "잠깐만요",
    "절대",
    "정신차려",
    "좋아해",
    "죽을래",
    "진심이야",
    "짜증나",
    "최고",
    "축하해",
    "틀렸어",
    "필요없어",
    "혹시",
    "힘들어",
)

CANDIDATE_TERMS = tuple(dict.fromkeys([*LEXICON.keys(), *REFERENCE_STYLE_EXTRA_TERMS]))


def import_clipper():
    spec = importlib.util.spec_from_file_location("a0_refined_clipper", CLIPPER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure_runtime_cache_env():
    RUNTIME_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    for name, relative in {
        "MPLCONFIGDIR": "matplotlib",
        "TORCH_HOME": "torch",
        "PYTHONPYCACHEPREFIX": "pycache",
    }.items():
        path = RUNTIME_CACHE_ROOT / relative
        path.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault(name, str(path))
    user_cache = Path.home() / ".cache"
    if (user_cache / "whisper").exists():
        os.environ.setdefault("XDG_CACHE_HOME", str(user_cache))
    else:
        xdg_cache = RUNTIME_CACHE_ROOT / "xdg"
        xdg_cache.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("XDG_CACHE_HOME", str(xdg_cache))


def ensure_accelerated_python():
    configure_runtime_cache_env()
    if os.environ.get("KOKO_SKIP_ACCELERATED_PYTHON") == "1":
        return
    if os.environ.get("KOKO_ACCELERATED_PYTHON") == "1":
        return
    if not ACCELERATED_PYTHON.exists():
        return
    try:
        if Path(sys.executable).resolve() == ACCELERATED_PYTHON.resolve():
            return
    except OSError:
        pass
    env = os.environ.copy()
    env["KOKO_ACCELERATED_PYTHON"] = "1"
    print(f"runtime: switching to accelerated Python: {ACCELERATED_PYTHON}", flush=True)
    os.execve(str(ACCELERATED_PYTHON), [str(ACCELERATED_PYTHON), *sys.argv], env)


clipper = import_clipper()


def run(cmd):
    subprocess.run([str(part) for part in cmd], check=True)


def capture(cmd):
    return subprocess.check_output([str(part) for part in cmd], text=True).strip()


def duration(path):
    return float(capture(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path]))


def source_video_fps(video):
    key = str(video)
    cached = _SOURCE_FPS_CACHE.get(key)
    if cached:
        return cached
    fps = None
    cv2 = lazy_cv2()
    if cv2 is not None:
        cap = cv2.VideoCapture(str(video))
        if cap.isOpened():
            value = cap.get(cv2.CAP_PROP_FPS) or 0.0
            if value > 1.0:
                fps = float(value)
        cap.release()
    if fps is None:
        try:
            raw = capture(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=avg_frame_rate",
                    "-of",
                    "default=nw=1:nk=1",
                    video,
                ]
            )
            if "/" in raw:
                numerator, denominator = raw.split("/", 1)
                fps = float(numerator) / max(1.0, float(denominator))
            else:
                fps = float(raw)
        except Exception:
            fps = 30.0
    fps = clamp(float(fps or 30.0), 12.0, 60.0)
    _SOURCE_FPS_CACHE[key] = fps
    return fps


def snap_time_to_frame(video, time_sec, video_duration=None, mode="nearest"):
    fps = source_video_fps(video)
    frame = float(time_sec) * fps
    if mode == "ceil":
        snapped = math.ceil(frame - 1e-6) / fps
    elif mode == "floor":
        snapped = math.floor(frame + 1e-6) / fps
    else:
        snapped = round(frame) / fps
    high = video_duration if video_duration is not None else max(0.0, float(time_sec))
    return clamp(snapped, 0.0, max(0.0, float(high)))


def safe_slug(path):
    name = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", path.name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name[:96] or "drama"


def safe_file_component(value, fallback="clip", limit=64):
    name = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", str(value or fallback))
    name = re.sub(r"_+", "_", name).strip("_")
    return (name or fallback)[:limit]


def clamp(value, low, high):
    return max(low, min(high, value))


def episode_number(path):
    match = re.search(r"S\d+E(\d+)|E(\d+)", path.name, re.IGNORECASE)
    if not match:
        return 9999
    return int(match.group(1) or match.group(2))


def list_episode_videos(folder):
    videos = []
    for path in folder.iterdir():
        if path.suffix.lower() not in {".mkv", ".mp4", ".mov"}:
            continue
        if re.search(r"S\d+E\d+|E\d+", path.name, re.IGNORECASE):
            videos.append(path)
    return sorted(videos, key=lambda p: (episode_number(p), p.name))


def ffprobe_streams(video):
    return json.loads(
        capture(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=index,codec_type,codec_name:stream_tags=language,title",
                "-of",
                "json",
                video,
            ]
        )
    ).get("streams", [])


def choose_korean_subtitle_stream(video):
    candidates = []
    subtitle_position = -1
    for stream in ffprobe_streams(video):
        if stream.get("codec_type") != "subtitle":
            continue
        subtitle_position += 1
        tags = stream.get("tags") or {}
        language = (tags.get("language") or "").lower()
        title = (tags.get("title") or "").lower()
        if language not in {"kor", "ko", "korean"}:
            continue
        score = 0
        if stream.get("codec_name") == "subrip":
            score += 4
        if "sdh" in title:
            score -= 3
        if "forced" in title:
            score -= 5
        if not title:
            score += 1
        candidates.append((score, subtitle_position, stream.get("index"), tags))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return {"subtitle_position": candidates[0][1], "stream_index": candidates[0][2], "tags": candidates[0][3]}


def extract_korean_srt(video, output_path):
    if output_path.exists() and output_path.stat().st_size > 64:
        return output_path
    selected = choose_korean_subtitle_stream(video)
    if selected is None:
        return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video, "-map", f"0:{selected['stream_index']}", output_path])
    if output_path.exists() and output_path.stat().st_size > 64:
        return output_path
    return None


def best_lexicon_term(text):
    matched = clipper.best_term(text, CANDIDATE_TERMS)
    return matched[0] if matched else None


def spoken_focus_text(text):
    text = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\[[^]]*\]", " ", text)
    text = re.sub(r"^[\s\\-–—:：]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def exact_lexicon_term(text):
    focused = spoken_focus_text(text)
    term = best_lexicon_term(focused)
    if not term:
        return None
    term_norm = clipper.normalize_korean(term)
    if not clipper.normalized_text_term_match(term_norm, focused):
        return None
    return term


def keyword_focus_ok(text, term, max_focus_tokens=MAX_FOCUS_TOKENS):
    focused = spoken_focus_text(text)
    tokens = [token for token in clipper.normalized_tokens(focused) if token]
    term_norm = clipper.normalize_korean(term)
    detail = {"focused_text": focused, "tokens": tokens, "term": term_norm}
    if not tokens or not term_norm or not clipper.normalized_text_term_match(term_norm, focused):
        return False, detail
    if len(tokens) <= max_focus_tokens:
        return True, detail
    if len(tokens) == max_focus_tokens + 1:
        others = [token for token in tokens if token != term_norm]
        if others and all(token in KEYWORD_FILLER_TOKENS for token in others):
            return True, detail
    return False, detail


def candidate_priority(entry, term, focus_detail):
    tokens = focus_detail.get("tokens") or []
    focused = focus_detail.get("focused_text") or ""
    term_norm = clipper.normalize_korean(term)
    duration_score = abs((float(entry["end"]) - float(entry["start"])) - TARGET_SHORT_CLIP_DURATION)
    exact_bonus = 0 if len(tokens) == 1 and tokens[0] == term_norm else 1
    token_penalty = max(0, len(tokens) - 1)
    position = clipper.normalize_korean(focused).find(term_norm)
    position_penalty = 0.0 if position < 0 else abs((position / max(1, len(clipper.normalize_korean(focused)))) - 0.5)
    return (exact_bonus, token_penalty, duration_score, position_penalty)


ACCEPTED_FACE_KINDS = {"opencv_dnn_face", "face", "coreimage_face", "human", "person_segmentation", "skin", "skin_subject"}
FRONTAL_FACE_KINDS = {"opencv_dnn_face", "face", "coreimage_face"}
KEYWORD_MIN_FACE_RATIO = 0.003
KEYWORD_MAX_CENTER_BIAS = 0.34
CUT_CROP_MIN_FACE_RATIO = 0.0022
CUT_CROP_MIN_BODY_RATIO = 0.006
CUT_SAMPLE_EDGE_PAD = 0.10
CUT_MIN_SEGMENT_DURATION = MIN_SCENE_SEGMENT_HOLD
CROP_SCENE_CUT_THRESHOLD = 0.45
KEYWORD_FACE_SEARCH_PAD = 0.24
KEYWORD_FACE_SAMPLE_STEP = 0.08
SEGMENT_SUBJECT_SAMPLE_LIMIT = 5
RENDERED_SEGMENT_SAMPLE_STEP = 0.24
SOURCE_SCENE_MAX_SUBTITLE_GAP = 8.0
SOURCE_SCENE_NEAR_DUPLICATE_SECONDS = 2.0
_MEDIAPIPE_FACE_DETECTORS = None
MEDIAPIPE_FACE_MODEL = ROOT / "assets/models/blaze_face_short_range.tflite"
_OPENCV_DNN_FACE_NET = None
_OPENCV_DNN_FACE_SIZE = None
_SCENE_CUT_CACHE = {}
_FRAME_DETECTIONS = {}
_RENDERED_FACE_CACHE = {}
_SOURCE_FPS_CACHE = {}
OPENCV_FACE_PROTO = ROOT / "assets/models/deploy.prototxt"
OPENCV_FACE_MODEL = ROOT / "assets/models/res10_300x300_ssd_iter_140000.caffemodel"
OPENCV_YUNET_MODEL = ROOT / "assets/models/face_detection_yunet_2023mar.onnx"


def opencv_dnn_faces(frame_path):
    global _OPENCV_DNN_FACE_NET, _OPENCV_DNN_FACE_SIZE
    try:
        import cv2
    except ImportError:
        return []
    if not OPENCV_YUNET_MODEL.exists():
        return []
    image = cv2.imread(str(frame_path))
    if image is None:
        return []
    height, width = image.shape[:2]
    if _OPENCV_DNN_FACE_NET is None:
        _OPENCV_DNN_FACE_NET = cv2.FaceDetectorYN_create(
            str(OPENCV_YUNET_MODEL),
            "",
            (width, height),
            0.5,
            0.3,
            5000,
        )
        _OPENCV_DNN_FACE_SIZE = (width, height)
    elif _OPENCV_DNN_FACE_SIZE != (width, height):
        _OPENCV_DNN_FACE_NET.setInputSize((width, height))
        _OPENCV_DNN_FACE_SIZE = (width, height)
    _, detections = _OPENCV_DNN_FACE_NET.detect(image)
    faces = []
    if detections is None:
        return faces
    for detection in detections:
        confidence = float(detection[14]) if len(detection) > 14 else 0.5
        if confidence < 0.5:
            continue
        x1 = max(0.0, float(detection[0]))
        y1 = max(0.0, float(detection[1]))
        w = min(float(width) - x1, float(detection[2]))
        h = min(float(height) - y1, float(detection[3]))
        if w <= 1 or h <= 1:
            continue
        faces.append(
            {
                "x": x1,
                "y": y1,
                "width": w,
                "height": h,
                "confidence": confidence,
                "kind": "opencv_dnn_face",
                "imageWidth": width,
                "imageHeight": height,
            }
        )
    return faces


def mediapipe_faces(frame_path):
    global _MEDIAPIPE_FACE_DETECTORS
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
    except ImportError:
        return []

    if not MEDIAPIPE_FACE_MODEL.exists():
        return []
    image = mp.Image.create_from_file(str(frame_path))
    height = image.height
    width = image.width
    if _MEDIAPIPE_FACE_DETECTORS is None:
        options = mp_vision.FaceDetectorOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(MEDIAPIPE_FACE_MODEL)),
            min_detection_confidence=0.35,
        )
        _MEDIAPIPE_FACE_DETECTORS = [mp_vision.FaceDetector.create_from_options(options)]

    faces = []
    for detector in _MEDIAPIPE_FACE_DETECTORS:
        result = detector.detect(image)
        for detection in result.detections or []:
            box = detection.bounding_box
            x = max(0.0, float(box.origin_x))
            y = max(0.0, float(box.origin_y))
            w = min(width - x, float(box.width))
            h = min(height - y, float(box.height))
            if w <= 1 or h <= 1:
                continue
            confidence = detection.categories[0].score if detection.categories else 0.5
            faces.append(
                {
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "confidence": float(confidence),
                    "kind": "mediapipe_face",
                    "imageWidth": width,
                    "imageHeight": height,
                }
            )
    return faces


def cached_frame_detections(detector, frame_path):
    key = str(frame_path)
    detections = _FRAME_DETECTIONS.get(key)
    if detections is None:
        detections = []
        detections.extend(opencv_dnn_faces(frame_path))
        if not detections:
            detections.extend(clipper.detect_faces(detector, frame_path))
        _FRAME_DETECTIONS[key] = detections
    return [dict(face) for face in detections]


def large_faces_at(
    video,
    detector,
    face_dir,
    time_sec,
    min_face_ratio=0.0022,
    allowed_kinds=ACCEPTED_FACE_KINDS,
    max_center_bias=KEYWORD_MAX_CENTER_BIAS,
    speaker_anchor=None,
):
    frame_path = face_dir / f"{video.stem}_{int(time_sec * 1000):08d}.png"
    if not frame_path.exists():
        extract_frame_fast(video, time_sec, frame_path)
    faces = cached_frame_detections(detector, frame_path)
    candidates = []
    for face in faces:
        if face.get("kind") not in allowed_kinds:
            continue
        area_ratio = (face["width"] * face["height"]) / (face["imageWidth"] * face["imageHeight"])
        if area_ratio < min_face_ratio:
            continue
        center_bias = abs((face["x"] + face["width"] / 2) / face["imageWidth"] - 0.5)
        if center_bias > max_center_bias:
            continue
        center_x = face["x"] + face["width"] / 2
        center_y = face["y"] + face["height"] / 2
        speaker_bias = 0.0
        if speaker_anchor:
            anchor_x = float(speaker_anchor["center_x"]) / float(speaker_anchor["image_width"])
            anchor_y = float(speaker_anchor["center_y"]) / float(speaker_anchor["image_height"])
            candidate_x = center_x / face["imageWidth"]
            candidate_y = center_y / face["imageHeight"]
            speaker_bias = abs(candidate_x - anchor_x) + abs(candidate_y - anchor_y) * 0.60
        score = area_ratio * float(face.get("confidence", 1.0)) - center_bias * 0.008 - speaker_bias * 0.018
        candidate = {
            "time": time_sec,
            "x": face["x"],
            "y": face["y"],
            "width": face["width"],
            "height": face["height"],
            "center_x": center_x,
            "center_y": center_y,
            "image_width": face["imageWidth"],
            "image_height": face["imageHeight"],
            "area_ratio": area_ratio,
            "confidence": face.get("confidence"),
            "kind": face.get("kind"),
            "speaker_bias": speaker_bias,
            "score": score,
        }
        candidates.append(candidate)
    candidates.sort(key=lambda candidate: candidate["score"], reverse=True)
    return candidates


def first_large_face(
    video,
    detector,
    face_dir,
    time_sec,
    min_face_ratio=0.0022,
    allowed_kinds=ACCEPTED_FACE_KINDS,
    max_center_bias=KEYWORD_MAX_CENTER_BIAS,
    speaker_anchor=None,
):
    faces = large_faces_at(
        video,
        detector,
        face_dir,
        time_sec,
        min_face_ratio=min_face_ratio,
        allowed_kinds=allowed_kinds,
        max_center_bias=max_center_bias,
        speaker_anchor=speaker_anchor,
    )
    return faces[0] if faces else None


def speaker_anchor_bias(face, speaker_anchor):
    if not face or not speaker_anchor:
        return 0.0
    anchor_x = float(speaker_anchor["center_x"]) / max(1.0, float(speaker_anchor["image_width"]))
    anchor_y = float(speaker_anchor["center_y"]) / max(1.0, float(speaker_anchor["image_height"]))
    candidate_x = float(face["center_x"]) / max(1.0, float(face["image_width"]))
    candidate_y = float(face["center_y"]) / max(1.0, float(face["image_height"]))
    return abs(candidate_x - anchor_x) + abs(candidate_y - anchor_y) * 0.60


def source_frame_speaker_face(
    video,
    detector,
    face_dir,
    time_sec,
    speaker_anchor=None,
    min_face_ratio=FRAME_TIGHT_MIN_SOURCE_FACE_RATIO,
):
    faces = large_faces_at(
        video,
        detector,
        face_dir,
        time_sec,
        min_face_ratio=min_face_ratio,
        allowed_kinds=FRONTAL_FACE_KINDS,
        max_center_bias=0.50,
        speaker_anchor=speaker_anchor,
    )
    if not faces:
        return None
    if not speaker_anchor:
        return faces[0]
    same_speaker_faces = [
        face
        for face in faces
        if speaker_anchor_bias(face, speaker_anchor) <= FRAME_TIGHT_MAX_SPEAKER_BIAS
    ]
    return same_speaker_faces[0] if same_speaker_faces else None


def confirmed_source_start_face(video, detector, face_dir, time_sec, speaker_anchor, frame_step):
    face = source_frame_speaker_face(video, detector, face_dir, time_sec, speaker_anchor)
    if not face:
        return None
    next_face = source_frame_speaker_face(
        video,
        detector,
        face_dir,
        time_sec + frame_step,
        speaker_anchor,
    )
    if not next_face:
        return None
    face = dict(face)
    face["confirmed_next_frame_time"] = time_sec + frame_step
    return face


def unique_sample_times(times, start, end):
    if end <= start:
        return []
    low = max(0.0, start)
    high = max(low, end)
    seen = set()
    result = []
    for time_sec in times:
        clamped = clamp(float(time_sec), low, high)
        key = round(clamped, 3)
        if key in seen:
            continue
        seen.add(key)
        result.append(clamped)
    return sorted(result)


def keyword_face_sample_times(keyword_start, keyword_end, search_start=None, search_end=None):
    center = (keyword_start + keyword_end) / 2
    search_start = keyword_start - KEYWORD_FACE_SEARCH_PAD if search_start is None else search_start
    search_end = keyword_end + KEYWORD_FACE_SEARCH_PAD if search_end is None else search_end
    if FAST_KEYWORD_FRAME_ONLY:
        return unique_sample_times([center], search_start, search_end)
    times = [center, keyword_start, keyword_end]
    for step in (KEYWORD_FACE_SAMPLE_STEP, KEYWORD_FACE_SAMPLE_STEP * 2, KEYWORD_FACE_SAMPLE_STEP * 3):
        times.extend([center - step, center + step])
    times.extend([search_start, search_end])
    return unique_sample_times(times, search_start, search_end)


def speaker_motion_sample_times(keyword_start, keyword_end, search_start=None, search_end=None):
    center = (keyword_start + keyword_end) / 2
    search_start = keyword_start - 0.16 if search_start is None else search_start
    search_end = keyword_end + 0.16 if search_end is None else search_end
    times = [keyword_start, center, keyword_end]
    for step in (0.08, 0.16, 0.24):
        times.extend([center - step, center + step])
    return unique_sample_times(times, search_start, search_end)


def lazy_cv2():
    try:
        import cv2
    except ImportError:
        return None
    return cv2


def extract_frame_fast(video, time_sec, frame_path):
    if frame_path.exists():
        return
    frame_path.parent.mkdir(parents=True, exist_ok=True)
    cv2 = lazy_cv2()
    if cv2 is not None:
        cap = cv2.VideoCapture(str(video))
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, float(time_sec)) * 1000.0)
            ok, frame = cap.read()
            cap.release()
            if ok and frame is not None and cv2.imwrite(str(frame_path), frame):
                return
        else:
            cap.release()
    clipper.extract_frame(video, time_sec, frame_path)


def clamp_face_box(face, width, height):
    x = int(max(0, round(float(face.get("x", 0)))))
    y = int(max(0, round(float(face.get("y", 0)))))
    w = int(max(1, round(float(face.get("width", 0)))))
    h = int(max(1, round(float(face.get("height", 0)))))
    x2 = min(width, x + w)
    y2 = min(height, y + h)
    x = min(max(0, x), max(0, x2 - 1))
    y = min(max(0, y), max(0, y2 - 1))
    return x, y, max(1, x2 - x), max(1, y2 - y)


def mouth_motion_from_frames(frames, face):
    cv2 = lazy_cv2()
    if cv2 is None:
        return {"ok": False, "reason": "opencv_unavailable"}
    usable = [frame for frame in frames if frame is not None]
    if len(usable) < 2:
        return {"ok": False, "reason": "not_enough_frames", "frames": len(usable)}
    height, width = usable[0].shape[:2]
    x, y, w, h = clamp_face_box(face, width, height)
    mouth_x1 = x + int(w * 0.18)
    mouth_x2 = x + int(w * 0.82)
    mouth_y1 = y + int(h * 0.58)
    mouth_y2 = y + int(h * 0.90)
    face_x1 = x + int(w * 0.10)
    face_x2 = x + int(w * 0.90)
    face_y1 = y + int(h * 0.20)
    face_y2 = y + int(h * 0.92)

    prev_mouth = None
    prev_face = None
    mouth_diffs = []
    face_diffs = []
    frames_used = 0
    for frame in usable:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        mouth = gray[max(0, mouth_y1):min(height, mouth_y2), max(0, mouth_x1):min(width, mouth_x2)]
        face_crop = gray[max(0, face_y1):min(height, face_y2), max(0, face_x1):min(width, face_x2)]
        if mouth.size == 0 or face_crop.size == 0:
            continue
        mouth = cv2.resize(mouth, (64, 32), interpolation=cv2.INTER_AREA)
        face_crop = cv2.resize(face_crop, (64, 64), interpolation=cv2.INTER_AREA)
        if prev_mouth is not None:
            mouth_diffs.append(float(cv2.mean(cv2.absdiff(prev_mouth, mouth))[0]) / 255.0)
            face_diffs.append(float(cv2.mean(cv2.absdiff(prev_face, face_crop))[0]) / 255.0)
        prev_mouth = mouth
        prev_face = face_crop
        frames_used += 1
    if not mouth_diffs:
        return {"ok": False, "reason": "not_enough_frame_diffs", "frames": frames_used}
    mouth_motion = sum(mouth_diffs) / len(mouth_diffs)
    face_motion = sum(face_diffs) / len(face_diffs) if face_diffs else 0.0
    return {
        "ok": True,
        "frames": frames_used,
        "mouth_motion": mouth_motion,
        "face_motion": face_motion,
        "mouth_to_face_ratio": mouth_motion / max(face_motion, 1e-6),
    }


def source_face_mouth_motion(video, face_dir, face, sample_times):
    cv2 = lazy_cv2()
    if cv2 is None:
        return {"ok": False, "reason": "opencv_unavailable"}
    frames = []
    for time_sec in sample_times:
        frame_path = face_dir / f"{video.stem}_{int(time_sec * 1000):08d}.png"
        if not frame_path.exists():
            extract_frame_fast(video, time_sec, frame_path)
        frames.append(cv2.imread(str(frame_path)))
    return mouth_motion_from_frames(frames, face)


def segment_subject_sample_times(segment, preferred_time=None):
    start = float(segment["start"])
    end = float(segment["end"])
    duration_sec = max(0.0, end - start)
    pad = min(CUT_SAMPLE_EDGE_PAD, duration_sec * 0.25)
    low = start + pad
    high = end - pad if end - pad >= low else end
    center = (start + end) / 2
    times = []
    if preferred_time is not None and start <= preferred_time <= end:
        times.append(preferred_time)
    times.append(low)
    if FAST_KEYWORD_FRAME_ONLY:
        return unique_sample_times(times, low, high)[:1]
    times.extend([center, start + duration_sec * 0.25, start + duration_sec * 0.75, low, high])
    return unique_sample_times(times, low, high)[:SEGMENT_SUBJECT_SAMPLE_LIMIT]


def rendered_segment_sample_times(segment):
    start = float(segment["start"])
    end = float(segment["end"])
    duration_sec = max(0.0, end - start)
    pad = min(0.08, duration_sec * 0.25)
    low = start + pad
    high = end - pad if end - pad >= low else end
    if FAST_VISUAL_FILL_SAMPLES:
        return unique_sample_times([(start + end) / 2], low, high)
    times = [low, (start + end) / 2, high]
    if duration_sec > RENDERED_SEGMENT_SAMPLE_STEP * 2:
        cursor = low + RENDERED_SEGMENT_SAMPLE_STEP
        while cursor < high:
            times.append(cursor)
            cursor += RENDERED_SEGMENT_SAMPLE_STEP
    return unique_sample_times(times, low, high)


def estimate_keyword_window(entry, term):
    text = clipper.normalize_korean(entry["text"])
    surface = clipper.normalize_korean(term)
    entry_duration = max(0.0, entry["end"] - entry["start"])
    keyword_center_ratio = 0.5
    if text and surface:
        position = text.find(surface)
        if position >= 0:
            keyword_center_ratio = (position + len(surface) / 2) / max(1, len(text))
            keyword_center_ratio = clamp(keyword_center_ratio, 0.18, 0.82)
    keyword_center = entry["start"] + entry_duration * keyword_center_ratio
    half_window = min(0.18, max(0.08, entry_duration * 0.28))
    return max(entry["start"], keyword_center - half_window), min(entry["end"], keyword_center + half_window)


def choose_keyword_speaker_face(
    video,
    detector,
    face_dir,
    keyword_start,
    keyword_end,
    min_face_ratio=KEYWORD_MIN_FACE_RATIO,
    search_start=None,
    search_end=None,
    source_content_crop=None,
):
    sample_times = keyword_face_sample_times(keyword_start, keyword_end, search_start, search_end)
    motion_times = speaker_motion_sample_times(keyword_start, keyword_end, search_start, search_end)
    faces = []
    seen_faces = set()
    for time_sec in sample_times:
        for face in large_faces_at(
            video,
            detector,
            face_dir,
            time_sec,
            min_face_ratio,
            allowed_kinds=FRONTAL_FACE_KINDS,
            max_center_bias=0.98,
        )[:6]:
            key = (
                round(float(face["center_x"]) / max(1.0, float(face["image_width"])), 2),
                round(float(face["center_y"]) / max(1.0, float(face["image_height"])), 2),
                round(float(face["area_ratio"]), 3),
            )
            if key in seen_faces:
                continue
            seen_faces.add(key)
            face = dict(face)
            if REQUIRE_SOURCE_MOUTH_BEFORE_POOL:
                motion = source_face_mouth_motion(video, face_dir, face, motion_times)
            else:
                motion = {"ok": False, "reason": "skipped_before_pool"}
            face["source_mouth_motion"] = motion
            if REQUIRE_SOURCE_MOUTH_BEFORE_POOL and motion.get("ok"):
                mouth_motion = float(motion.get("mouth_motion") or 0.0)
                face_motion = float(motion.get("face_motion") or 0.0)
                face["active_speaker_score"] = face["score"] + mouth_motion * 0.85 - face_motion * 0.12
            elif REQUIRE_SOURCE_MOUTH_BEFORE_POOL:
                face["active_speaker_score"] = face["score"] - 0.20
            else:
                face["active_speaker_score"] = face["score"]
            faces.append(face)
    if faces:
        faces.sort(key=lambda face: face["active_speaker_score"], reverse=True)
        best = faces[0]
        motion = best.get("source_mouth_motion") or {}
        best["keyword_window"] = {"start": keyword_start, "end": keyword_end}
        best["keyword_sample_times"] = sample_times
        best["speaker_motion_sample_times"] = motion_times
        best["speaker_candidates_checked"] = len(faces)
        best["speaker_detection_mode"] = "face"
        if source_content_crop:
            best["source_content_crop"] = source_content_crop
        if (
            REQUIRE_SOURCE_MOUTH_BEFORE_POOL
            and (
                not motion.get("ok")
                or float(motion.get("mouth_motion") or 0.0) < MIN_SOURCE_SPEAKER_MOUTH_MOTION
            )
        ):
            return None
        return best

    return None


def choose_keyword_person_subject(video, detector, face_dir, keyword_start, keyword_end):
    center = (keyword_start + keyword_end) / 2
    sample_times = [center] if FAST_KEYWORD_FRAME_ONLY else [center, max(keyword_start, center - 0.10), min(keyword_end, center + 0.10)]
    subjects = [
        first_large_face(
            video,
            detector,
            face_dir,
            time_sec,
            min_face_ratio=0.01,
            allowed_kinds={"person_segmentation"},
            max_center_bias=0.48,
        )
        for time_sec in sample_times
    ]
    subjects = [subject for subject in subjects if subject]
    if not subjects:
        return None
    subjects.sort(key=lambda subject: subject["score"], reverse=True)
    best = subjects[0]
    best["keyword_window"] = {"start": keyword_start, "end": keyword_end}
    return best


def choose_keyword_skin_subject(video, detector, face_dir, keyword_start, keyword_end, source_content_crop=None):
    center = (keyword_start + keyword_end) / 2
    sample_times = [center] if FAST_KEYWORD_FRAME_ONLY else [center, max(keyword_start, center - 0.10), min(keyword_end, center + 0.10)]
    subjects = [
        first_large_face(
            video,
            detector,
            face_dir,
            time_sec,
            min_face_ratio=0.006,
            allowed_kinds={"skin"},
            max_center_bias=0.50,
        )
        for time_sec in sample_times
    ]
    subjects = [subject for subject in subjects if subject]
    if not subjects:
        subjects = [
            detect_skin_subject(video, time_sec, source_content_crop=source_content_crop)
            for time_sec in sample_times
        ]
        subjects = [subject for subject in subjects if subject]
    if not subjects:
        return None
    subjects.sort(key=lambda subject: subject["score"], reverse=True)
    best = subjects[0]
    best["keyword_window"] = {"start": keyword_start, "end": keyword_end}
    return best


def detect_skin_subject(video, time_sec, source_content_crop=None, sample_width=320):
    source_width, source_height = clipper.ffprobe_video_size(video)
    crop = source_content_crop or {"x": 0, "y": 0, "width": source_width, "height": source_height}
    crop_width = int(crop["width"])
    crop_height = int(crop["height"])
    sample_height = max(2, int(round(crop_height * sample_width / crop_width)))
    if sample_height % 2:
        sample_height += 1
    vf = (
        f"crop={crop_width}:{crop_height}:{int(crop['x'])}:{int(crop['y'])},"
        f"scale={sample_width}:{sample_height}:flags=bilinear"
    )
    result = subprocess.run(
        [
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
            vf,
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        check=False,
        capture_output=True,
    )
    expected = sample_width * sample_height * 3
    if len(result.stdout) < expected:
        return None
    data = result.stdout[:expected]
    mask = bytearray(sample_width * sample_height)
    for y in range(sample_height):
        row = y * sample_width
        for x in range(sample_width):
            i = (row + x) * 3
            r, g, b = data[i], data[i + 1], data[i + 2]
            if r > 58 and g > 34 and b > 22 and r > b * 1.12 and r >= g * 0.95 and max(r, g, b) - min(r, g, b) > 10:
                mask[row + x] = 1

    visited = bytearray(sample_width * sample_height)
    best = None
    for index, value in enumerate(mask):
        if not value or visited[index]:
            continue
        stack = [index]
        visited[index] = 1
        count = 0
        min_x = sample_width
        min_y = sample_height
        max_x = 0
        max_y = 0
        while stack:
            current = stack.pop()
            count += 1
            x = current % sample_width
            y = current // sample_width
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            for neighbor in (current - 1, current + 1, current - sample_width, current + sample_width):
                if neighbor < 0 or neighbor >= len(mask) or visited[neighbor] or not mask[neighbor]:
                    continue
                if abs((neighbor % sample_width) - x) > 1:
                    continue
                visited[neighbor] = 1
                stack.append(neighbor)
        box_w = max_x - min_x + 1
        box_h = max_y - min_y + 1
        if count < 18 or box_w < 4 or box_h < 4:
            continue
        if box_w > sample_width * 0.55 or box_h > sample_height * 0.72 or count > sample_width * sample_height * 0.18:
            continue
        center_y_ratio = ((min_y + max_y) / 2) / sample_height
        score = count * (1.20 - abs(center_y_ratio - 0.38))
        if best is None or score > best["score"]:
            best = {"count": count, "min_x": min_x, "min_y": min_y, "max_x": max_x, "max_y": max_y, "score": score}
    if not best:
        return None

    scale_x = crop_width / sample_width
    scale_y = crop_height / sample_height
    center_x = crop["x"] + ((best["min_x"] + best["max_x"] + 1) / 2) * scale_x
    center_y = crop["y"] + ((best["min_y"] + best["max_y"] + 1) / 2) * scale_y
    box_w = max(80.0, (best["max_x"] - best["min_x"] + 1) * scale_x)
    box_h = max(80.0, (best["max_y"] - best["min_y"] + 1) * scale_y)
    return {
        "time": time_sec,
        "x": center_x - box_w / 2,
        "y": center_y - box_h / 2,
        "width": box_w,
        "height": box_h,
        "center_x": center_x,
        "center_y": center_y,
        "image_width": source_width,
        "image_height": source_height,
        "area_ratio": (box_w * box_h) / (source_width * source_height),
        "confidence": min(1.0, best["count"] / 900.0),
        "kind": "skin_subject",
        "score": best["score"],
        "source_content_crop": source_content_crop,
    }


def detect_scene_cuts_cv2(video, start, end, threshold=0.32):
    cv2 = lazy_cv2()
    if cv2 is None or end <= start:
        return None
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return None
    diff_threshold = max(0.09, min(0.22, float(threshold) * 0.35))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frame_step = max(1, int(round(fps / 12.0)))
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, float(start)) * 1000.0)
    cuts = []
    prev_gray = None
    prev_time = None
    last_cut = -999.0
    frame_index = 0
    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        time_sec = (cap.get(cv2.CAP_PROP_POS_MSEC) or 0.0) / 1000.0
        if time_sec <= 0.0:
            time_sec = float(start) + frame_index / fps
        if time_sec < float(start) - 0.03:
            frame_index += 1
            continue
        if time_sec > float(end) + 0.03:
            break
        if frame_index % frame_step != 0:
            frame_index += 1
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (96, 54), interpolation=cv2.INTER_AREA)
        if prev_gray is not None and prev_time is not None:
            diff = float(cv2.mean(cv2.absdiff(prev_gray, gray))[0]) / 255.0
            if diff >= diff_threshold and time_sec - last_cut >= 0.18:
                cuts.append((prev_time + time_sec) / 2)
                last_cut = time_sec
        prev_gray = gray
        prev_time = time_sec
        frame_index += 1
    cap.release()
    return cuts


def detect_scene_cuts(video, start, end, threshold=0.32):
    if end <= start:
        return []
    cache_key = (str(video), round(float(start), 2), round(float(end), 2), round(float(threshold), 2))
    if cache_key in _SCENE_CUT_CACHE:
        return list(_SCENE_CUT_CACHE[cache_key])
    cv2_cuts = detect_scene_cuts_cv2(video, start, end, threshold=threshold)
    if cv2_cuts is not None:
        _SCENE_CUT_CACHE[cache_key] = cv2_cuts
        return list(cv2_cuts)
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(video),
            "-t",
            f"{end - start:.3f}",
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
        cuts.append(start + float(match.group(1)))
    _SCENE_CUT_CACHE[cache_key] = cuts
    return cuts


def adjust_for_tail_scene_cut(video, clip_start, clip_end, video_duration):
    lookback_start = max(clip_start, clip_end - END_SCENE_CUT_LOOKBACK)
    cuts = detect_scene_cuts(video, lookback_start, min(video_duration, clip_end + TARGET_POST_SCENE_CUT_HOLD))
    tail_cuts = [cut for cut in cuts if clip_start < cut < clip_end and clip_end - cut < MIN_POST_SCENE_CUT_HOLD]
    if not tail_cuts:
        return clip_end, None

    cut_time = max(tail_cuts)
    adjusted_end = max(clip_start, cut_time - SCENE_CUT_HARD_MARGIN)
    if adjusted_end - clip_start < MIN_HARD_CUT_CLIP_DURATION:
        return None, {
            "reason": "tail_scene_cut_too_short_after_hard_cut",
            "scene_cut": cut_time,
            "old_end": clip_end,
            "adjusted_end": adjusted_end,
        }
    return adjusted_end, {
        "mode": "hard_cut_at_scene_boundary",
        "scene_cut": cut_time,
        "old_end": clip_end,
        "adjusted_end": adjusted_end,
    }


def scene_cut_hold_segments(clip_start, clip_end, cuts):
    points = [clip_start] + [cut for cut in cuts if clip_start < cut < clip_end] + [clip_end]
    return [
        {
            "index": index,
            "start": points[index],
            "end": points[index + 1],
            "duration": points[index + 1] - points[index],
        }
        for index in range(len(points) - 1)
    ]


def adjust_for_scene_transition_pacing(video, clip_start, clip_end, keyword_start, keyword_end, video_duration):
    cuts = sorted(
        cut
        for cut in detect_scene_cuts(
            video,
            clip_start,
            min(video_duration, clip_end),
            threshold=CROP_SCENE_CUT_THRESHOLD,
        )
        if clip_start < cut < clip_end
    )
    detail = {
        "mode": "scene_transition_pacing",
        "old_start": clip_start,
        "old_end": clip_end,
        "scene_cuts": cuts,
    }
    if not cuts:
        detail["adjusted_start"] = clip_start
        detail["adjusted_end"] = clip_end
        detail["segments"] = scene_cut_hold_segments(clip_start, clip_end, cuts)
        return (clip_start, clip_end), detail

    guard_start = max(clip_start, keyword_start - KEYWORD_SCENE_CUT_GUARD)
    guard_end = min(clip_end, keyword_end + KEYWORD_SCENE_CUT_GUARD)
    guarded_cuts = [cut for cut in cuts if guard_start <= cut <= guard_end]
    if guarded_cuts:
        detail.update(
            {
                "reason": "scene_cut_during_keyword",
                "guarded_cuts": guarded_cuts,
                "keyword_start": keyword_start,
                "keyword_end": keyword_end,
            }
        )
        return None, detail

    adjusted_start = clip_start
    adjusted_end = clip_end
    trim_events = []
    first_cut = cuts[0]
    if first_cut - adjusted_start < EDGE_SCENE_CUT_GUARD and first_cut <= guard_start:
        candidate_start = min(first_cut + SCENE_CUT_HARD_MARGIN, keyword_start - 0.10)
        if candidate_start > adjusted_start and keyword_start - candidate_start >= 0.10:
            trim_events.append(
                {
                    "edge": "start",
                    "scene_cut": first_cut,
                    "old_start": adjusted_start,
                    "adjusted_start": candidate_start,
                }
            )
            adjusted_start = candidate_start

    last_cut = cuts[-1]
    if adjusted_end - last_cut < MIN_SCENE_SEGMENT_HOLD and last_cut >= guard_end:
        candidate_end = max(last_cut - SCENE_CUT_HARD_MARGIN, keyword_end + MIN_RENDERED_KEYWORD_TAIL)
        if adjusted_end - candidate_end > 0.02 and candidate_end - adjusted_start >= MIN_HARD_CUT_CLIP_DURATION:
            trim_events.append(
                {
                    "edge": "end",
                    "scene_cut": last_cut,
                    "old_end": adjusted_end,
                    "adjusted_end": candidate_end,
                }
            )
            adjusted_end = candidate_end

    adjusted_cuts = [cut for cut in cuts if adjusted_start < cut < adjusted_end]
    segments = scene_cut_hold_segments(adjusted_start, adjusted_end, adjusted_cuts)
    short_segments = [segment for segment in segments if segment["duration"] < MIN_SCENE_SEGMENT_HOLD]
    if short_segments:
        detail.update(
            {
                "reason": "rapid_scene_cut_hold_too_short",
                "adjusted_start": adjusted_start,
                "adjusted_end": adjusted_end,
                "trim_events": trim_events,
                "segments": segments,
                "short_segments": short_segments,
                "min_scene_segment_hold": MIN_SCENE_SEGMENT_HOLD,
            }
        )
        return None, detail

    detail.update(
        {
            "reason": None,
            "adjusted_start": adjusted_start,
            "adjusted_end": adjusted_end,
            "trim_events": trim_events,
            "segments": segments,
            "scene_cuts": adjusted_cuts,
            "min_scene_segment_hold": MIN_SCENE_SEGMENT_HOLD,
        }
    )
    return (adjusted_start, adjusted_end), detail


def trim_to_keyword_shot(video, clip_start, clip_end, keyword_start, keyword_end, video_duration):
    if clip_end <= clip_start:
        return None, {"reason": "invalid_keyword_shot_window"}
    cuts = sorted(
        cut
        for cut in detect_scene_cuts(
            video,
            clip_start,
            min(video_duration, clip_end),
            threshold=CROP_SCENE_CUT_THRESHOLD,
        )
        if clip_start < cut < clip_end
    )
    if not cuts:
        return (clip_start, clip_end), None

    guard_start = max(clip_start, keyword_start - KEYWORD_SCENE_CUT_GUARD)
    guard_end = min(clip_end, keyword_end + KEYWORD_SCENE_CUT_GUARD)
    guarded_cuts = [cut for cut in cuts if guard_start <= cut <= guard_end]
    if guarded_cuts:
        return None, {
            "reason": "scene_cut_during_keyword",
            "scene_cuts": cuts,
            "guarded_cuts": guarded_cuts,
            "keyword_start": keyword_start,
            "keyword_end": keyword_end,
        }

    return (
        (clip_start, clip_end),
        {
            "mode": "keyword_window_cut_aware_hard_cuts",
            "scene_cuts": cuts,
            "old_start": clip_start,
            "old_end": clip_end,
            "adjusted_start": clip_start,
            "adjusted_end": clip_end,
            "keyword_start": keyword_start,
            "keyword_end": keyword_end,
        },
    )


def refine_clip_window_frame_tight(
    video,
    detector,
    face_dir,
    clip_start,
    clip_end,
    keyword_start,
    keyword_end,
    keyword_face,
    video_duration,
):
    detail = {
        "mode": "frame_tight_face_audio_window",
        "old_start": clip_start,
        "old_end": clip_end,
        "keyword_start": keyword_start,
        "keyword_end": keyword_end,
    }
    if not FRAME_TIGHTEN_CLIP_WINDOW:
        detail["reason"] = "disabled"
        detail["adjusted_start"] = clip_start
        detail["adjusted_end"] = clip_end
        return (clip_start, clip_end), detail
    if clip_end <= clip_start:
        detail["reason"] = "invalid_window"
        return None, detail

    fps = source_video_fps(video)
    frame_step = 1.0 / max(1.0, fps)
    detail["fps"] = fps
    detail["frame_step"] = frame_step

    audio_safe_latest_start = keyword_start - FRAME_TIGHT_KEYWORD_AUDIO_LEAD
    duration_safe_latest_start = clip_end - MIN_HARD_CUT_CLIP_DURATION
    scan_latest_start = min(
        clip_start + FRAME_TIGHT_START_SCAN_SECONDS,
        audio_safe_latest_start,
        duration_safe_latest_start,
        video_duration,
    )
    scan_start = snap_time_to_frame(video, clip_start, video_duration, mode="ceil")
    if scan_start - clip_start > FRAME_TIGHT_KEYWORD_AUDIO_LEAD:
        scan_start = clip_start

    adjusted_start = clip_start
    start_face = None
    start_candidates_checked = 0
    if scan_latest_start >= scan_start:
        cursor = scan_start
        while cursor <= scan_latest_start + 1e-6:
            start_candidates_checked += 1
            face = confirmed_source_start_face(video, detector, face_dir, cursor, keyword_face, frame_step)
            if face:
                start_face = face
                adjusted_start = cursor
                break
            cursor += frame_step

    if not start_face:
        detail.update(
            {
                "reason": "no_safe_frame_tight_start_face",
                "scan_start": scan_start,
                "scan_latest_start": scan_latest_start,
                "audio_safe_latest_start": audio_safe_latest_start,
                "start_candidates_checked": start_candidates_checked,
            }
        )
        return None, detail

    if adjusted_start - clip_start < FRAME_TIGHT_MIN_START_SHIFT:
        adjusted_start = clip_start

    min_safe_end = max(
        adjusted_start + MIN_HARD_CUT_CLIP_DURATION,
        keyword_end + FRAME_TIGHT_KEYWORD_AUDIO_TAIL,
    )
    adjusted_end = snap_time_to_frame(video, clip_end, video_duration, mode="floor")
    if adjusted_end < min_safe_end:
        adjusted_end = clip_end

    end_scan_low = max(min_safe_end, adjusted_end - FRAME_TIGHT_END_SCAN_SECONDS)
    end_face = None
    end_candidates_checked = 0
    cursor = snap_time_to_frame(video, adjusted_end - frame_step, video_duration, mode="floor")
    while cursor >= end_scan_low - 1e-6:
        end_candidates_checked += 1
        face = source_frame_speaker_face(video, detector, face_dir, cursor, keyword_face)
        if face:
            end_face = face
            candidate_end = min(video_duration, cursor + frame_step)
            if clip_end - candidate_end >= FRAME_TIGHT_MIN_END_SHIFT and candidate_end >= min_safe_end:
                adjusted_end = candidate_end
            break
        cursor -= frame_step

    if adjusted_end <= adjusted_start or adjusted_end - adjusted_start < MIN_HARD_CUT_CLIP_DURATION:
        detail.update(
            {
                "reason": "frame_tight_window_too_short",
                "adjusted_start": adjusted_start,
                "adjusted_end": adjusted_end,
                "min_duration": MIN_HARD_CUT_CLIP_DURATION,
            }
        )
        return None, detail

    detail.update(
        {
            "reason": None,
            "adjusted_start": adjusted_start,
            "adjusted_end": adjusted_end,
            "start_face": start_face,
            "end_face": end_face,
            "scan_start": scan_start,
            "scan_latest_start": scan_latest_start,
            "audio_safe_latest_start": audio_safe_latest_start,
            "min_safe_end": min_safe_end,
            "start_candidates_checked": start_candidates_checked,
            "end_candidates_checked": end_candidates_checked,
        }
    )
    return (adjusted_start, adjusted_end), detail


def intervals_overlap(start_a, end_a, start_b, end_b):
    return max(start_a, start_b) < min(end_a, end_b)


def build_subtitle_scene_index(entries, max_gap=SOURCE_SCENE_MAX_SUBTITLE_GAP):
    by_entry = {}
    scenes = []
    current = None
    last_end = None
    for entry_index, entry in enumerate(entries, start=1):
        start = float(entry.get("start", 0.0))
        end = float(entry.get("end", start))
        if current is None or (last_end is not None and start - last_end > max_gap):
            current = {
                "index": len(scenes) + 1,
                "start": start,
                "end": end,
                "entry_start": entry_index,
                "entry_end": entry_index,
                "max_gap": max_gap,
            }
            scenes.append(current)
        else:
            current["end"] = max(float(current["end"]), end)
            current["entry_end"] = entry_index
        by_entry[entry_index] = current
        last_end = max(last_end if last_end is not None else end, end)
    return by_entry, scenes


def source_scene_detail(video, scene):
    if not scene:
        return None
    return {
        "key": f"{video.name}::subtitle_scene_{int(scene['index']):04d}",
        "strategy": "subtitle_gap_scene",
        "index": int(scene["index"]),
        "start": float(scene["start"]),
        "end": float(scene["end"]),
        "entry_start": int(scene["entry_start"]),
        "entry_end": int(scene["entry_end"]),
        "max_subtitle_gap": float(scene["max_gap"]),
    }


def strict_source_scene_duplicate(source_scene):
    if not source_scene:
        return False
    try:
        scene_duration = float(source_scene["end"]) - float(source_scene["start"])
    except (KeyError, TypeError, ValueError):
        return False
    return scene_duration <= SOURCE_SCENE_NEAR_DUPLICATE_SECONDS


def add_seen_source_range(index, item):
    episode = item.get("episode")
    if not episode:
        return
    try:
        start = float(item.get("start"))
        end = float(item.get("end"))
    except (TypeError, ValueError):
        return
    if end <= start:
        return
    index.setdefault(episode, []).append(
        {
            "start": start,
            "end": end,
            "midpoint": (start + end) / 2,
            "clip": item.get("clip"),
            "term": item.get("term"),
            "source_scene": item.get("source_scene"),
        }
    )


def build_seen_source_indexes(clips):
    scene_keys = set()
    source_ranges = {}
    for item in clips:
        source_scene = item.get("source_scene") or {}
        scene_key = source_scene.get("key")
        if scene_key:
            scene_keys.add(scene_key)
        add_seen_source_range(source_ranges, item)
    return scene_keys, source_ranges


def source_window_identity(item):
    try:
        return (
            item.get("episode"),
            round(float(item.get("start")), 2),
            round(float(item.get("end")), 2),
        )
    except (TypeError, ValueError):
        return None


def load_excluded_source_indexes(roots):
    excluded_items = []
    for root in roots or []:
        root = Path(root)
        if not root.exists():
            continue
        for manifest in root.glob("**/clip_pool_manifest.json"):
            try:
                data = json.loads(manifest.read_text())
            except Exception:
                continue
            if isinstance(data, list):
                excluded_items.extend(data)
            elif isinstance(data, dict):
                excluded_items.extend(data.get("items") or [])
    scene_keys, source_ranges = build_seen_source_indexes(excluded_items)
    windows = {
        identity
        for identity in (source_window_identity(item) for item in excluded_items)
        if identity and identity[0] is not None
    }
    return scene_keys, source_ranges, windows


def merge_source_ranges(target, extra):
    for episode, ranges in (extra or {}).items():
        target.setdefault(episode, []).extend(ranges)


def find_near_source_duplicate(episode, start, end, source_ranges, gap=SOURCE_SCENE_NEAR_DUPLICATE_SECONDS):
    for existing in source_ranges.get(episode, []):
        if intervals_overlap(start - gap, end + gap, existing["start"], existing["end"]):
            return existing
    return None


def clip_scene_segments(video, start, end, threshold=CROP_SCENE_CUT_THRESHOLD, min_segment=CUT_MIN_SEGMENT_DURATION):
    raw_cuts = sorted(
        cut
        for cut in detect_scene_cuts(video, start, end, threshold=threshold)
        if start < cut < end
    )
    segments = []
    accepted_cuts = []
    cursor = start
    for cut in raw_cuts:
        if cut - cursor < min_segment or end - cut < min_segment:
            continue
        accepted_cuts.append(cut)
        if cut - cursor < min_segment:
            continue
        segments.append({"start": cursor, "end": cut})
        cursor = cut
    if end - cursor < min_segment and segments:
        segments[-1]["end"] = end
    else:
        segments.append({"start": cursor, "end": end})
    return segments, accepted_cuts


def segment_sample_time(segment, preferred_time=None):
    start = float(segment["start"])
    end = float(segment["end"])
    duration_sec = max(0.0, end - start)
    pad = min(CUT_SAMPLE_EDGE_PAD, duration_sec * 0.25)
    low = start + pad
    high = end - pad
    if high < low:
        return (start + end) / 2
    if preferred_time is not None and start <= preferred_time <= end:
        return clamp(preferred_time, low, high)
    return clamp((start + end) / 2, low, high)


def subject_with_source_crop(subject, source_content_crop):
    if not subject:
        return None
    adjusted = dict(subject)
    if source_content_crop:
        adjusted["source_content_crop"] = source_content_crop
    return adjusted


def detect_cut_subject(
    video,
    detector,
    face_dir,
    sample_time,
    source_content_crop=None,
    require_face=False,
    fallback_face=None,
    segment_start=None,
    segment_end=None,
):
    face = None
    if require_face and fallback_face and segment_start is not None and segment_end is not None:
        if (
            fallback_face.get("kind") in FRONTAL_FACE_KINDS
            and segment_start <= float(fallback_face.get("time", -1)) <= segment_end
        ):
            face = dict(fallback_face)
            face["speaker_anchor_match"] = True
    if not face:
        face = first_large_face(
            video,
            detector,
            face_dir,
            sample_time,
            min_face_ratio=CUT_CROP_MIN_FACE_RATIO,
            allowed_kinds=FRONTAL_FACE_KINDS,
            max_center_bias=0.98,
            speaker_anchor=fallback_face,
        )
    if face:
        face = subject_with_source_crop(face, source_content_crop)
        face["crop_role"] = "face"
        return face, None
    if require_face:
        return None, {"reason": "keyword_cut_without_face", "sample_time": sample_time}

    body = first_large_face(
        video,
        detector,
        face_dir,
        sample_time,
        min_face_ratio=CUT_CROP_MIN_BODY_RATIO,
        allowed_kinds={"person_segmentation", "human"},
        max_center_bias=0.98,
        speaker_anchor=fallback_face,
    )
    if body:
        body = subject_with_source_crop(body, source_content_crop)
        body["crop_role"] = "body"
        return body, None

    skin = first_large_face(
        video,
        detector,
        face_dir,
        sample_time,
        min_face_ratio=0.004,
        allowed_kinds={"skin"},
        max_center_bias=0.98,
        speaker_anchor=fallback_face,
    )
    if not skin:
        skin = detect_skin_subject(video, sample_time, source_content_crop=source_content_crop)
    if skin:
        skin = subject_with_source_crop(skin, source_content_crop)
        skin["crop_role"] = "skin_subject"
        return skin, None

    return None, {"reason": "cut_without_person_subject", "sample_time": sample_time}


def build_cut_crop_plan(video, detector, face_dir, clip_start, clip_end, keyword_start, keyword_end, keyword_face, source_content_crop=None):
    segments, cuts = clip_scene_segments(video, clip_start, clip_end)
    crop_segments = []
    keyword_center = (keyword_start + keyword_end) / 2
    for index, segment in enumerate(segments):
        keyword_segment = intervals_overlap(segment["start"], segment["end"], keyword_start, keyword_end)
        sample_times = segment_subject_sample_times(segment, keyword_center if keyword_segment else None)
        subject = None
        error = None
        sample_time = sample_times[0] if sample_times else segment_sample_time(segment, keyword_center if keyword_segment else None)
        for candidate_time in sample_times:
            candidate_subject, candidate_error = detect_cut_subject(
                video,
                detector,
                face_dir,
                candidate_time,
                source_content_crop=source_content_crop,
                require_face=keyword_segment,
                fallback_face=keyword_face,
                segment_start=segment["start"],
                segment_end=segment["end"],
            )
            if candidate_subject:
                subject = candidate_subject
                error = None
                sample_time = candidate_time
                break
            error = candidate_error
        if not subject:
            return None, {
                "reason": error["reason"] if error else "cut_without_person_subject",
                "segment_index": index,
                "segment": segment,
                "keyword_segment": keyword_segment,
                "sample_time": sample_time,
                "sample_times": sample_times,
            }
        crop_segments.append(
            {
                "index": index,
                "start": segment["start"],
                "end": segment["end"],
                "rel_start": max(0.0, segment["start"] - clip_start),
                "rel_end": max(0.0, segment["end"] - clip_start),
                "sample_time": sample_time,
                "sample_times": sample_times,
                "keyword_segment": keyword_segment,
                "subject": subject,
            }
        )
    return {
        "method": "cut_aware_face_then_body_center_crop",
        "speaker_anchor": keyword_face,
        "scene_cuts": cuts,
        "segments": crop_segments,
    }, None


def subtitle_candidate_window(video, entry, video_duration, keyword_start=None, keyword_end=None):
    start = max(0.0, float(entry["start"]) - CLIP_PRE_ROLL)
    end = min(video_duration, float(entry["end"]) + CLIP_POST_ROLL)
    if end <= start:
        return None, {"reason": "invalid_subtitle_window"}

    center = (float(entry["start"]) + float(entry["end"])) / 2
    if keyword_start is not None and keyword_end is not None:
        center = (float(keyword_start) + float(keyword_end)) / 2

    if end - start < MIN_CLIP_DURATION:
        start = max(0.0, center - MIN_CLIP_DURATION / 2)
        end = min(video_duration, start + MIN_CLIP_DURATION)
        start = max(0.0, end - MIN_CLIP_DURATION)

    if end - start > MAX_CLIP_DURATION:
        start = max(0.0, center - TARGET_SHORT_CLIP_DURATION / 2)
        end = min(video_duration, start + TARGET_SHORT_CLIP_DURATION)
        start = max(0.0, end - TARGET_SHORT_CLIP_DURATION)

    return (start, end), None


def transcribe_auto_audio(media_path, transcript_path):
    if transcript_path.exists() and clipper.transcript_matches_source(
        transcript_path,
        media_path,
        WHISPER_MODEL,
        "ko_auto_transcribe",
    ):
        return json.loads(transcript_path.read_text())

    transcript_path.unlink(missing_ok=True)
    import whisper

    whisper_model = clipper._WHISPER_MODELS.get(WHISPER_MODEL)
    if whisper_model is None:
        whisper_model = whisper.load_model(WHISPER_MODEL)
        clipper._WHISPER_MODELS[WHISPER_MODEL] = whisper_model
    result = whisper_model.transcribe(
        str(media_path),
        language="ko",
        fp16=False,
        verbose=False,
        word_timestamps=False,
        task="transcribe",
        initial_prompt="한국어 드라마 대사입니다. 짧은 한국어 표현과 감탄사도 한국어로 받아쓰세요.",
    )
    clipper.write_transcript_with_metadata(
        transcript_path,
        result,
        media_path,
        WHISPER_MODEL,
        "ko_auto_transcribe",
    )
    return result


def auto_audio_keyword_detail(result, term, transcript_path):
    language = result.get("language")
    text = (result.get("text") or "").strip()
    normalized_text = clipper.normalize_korean(text)
    normalized_term = clipper.normalize_korean(term or "")
    tokens = [token for token in clipper.normalized_tokens(text) if token]
    keyword_present = (not normalized_term) or bool(clipper.normalized_text_term_match(normalized_term, text))
    detail = {
        "ok": True,
        "reason": None,
        "language": language,
        "text": text,
        "transcript": str(transcript_path),
        "term": term,
        "normalized_text": normalized_text,
        "tokens": tokens,
        "keyword_present": keyword_present,
    }
    if language != "ko":
        detail["ok"] = False
        detail["reason"] = "non_korean_auto_audio"
        return detail
    if not has_hangul(text):
        detail["ok"] = False
        detail["reason"] = "no_hangul_in_auto_audio"
        return detail
    if not keyword_present:
        detail["ok"] = False
        detail["reason"] = "keyword_missing_in_auto_audio"
        return detail
    return detail


def verify_source_auto_audio_keyword(video, work_dir, entry_index, term, start, end):
    if not VERIFY_SOURCE_AUTO_AUDIO_BEFORE_RENDER:
        return {"ok": True, "reason": "disabled"}
    audio_dir = work_dir / "source_auto_audio"
    transcript_dir = work_dir / "source_auto_audio_transcripts"
    audio_dir.mkdir(parents=True, exist_ok=True)
    transcript_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / f"{region_cache_stem(video, entry_index, term, start, end)}_auto.wav"
    transcript_path = transcript_dir / f"{audio_path.stem}.json"
    if not audio_path.exists():
        extract_audio_region(video, audio_path, start, end)
    try:
        result = transcribe_auto_audio(audio_path, transcript_path)
    except Exception as exc:
        return {
            "ok": False,
            "reason": "source_auto_audio_transcription_failed",
            "error": str(exc),
            "transcript": str(transcript_path),
        }
    detail = auto_audio_keyword_detail(result, term, transcript_path)
    detail["audio"] = str(audio_path)
    detail["start"] = start
    detail["end"] = end
    return detail


def verify_spoken_keyword(video, work_dir, entry, term, video_duration, entry_index):
    region_dir = work_dir / "regions"
    transcript_dir = work_dir / "transcripts"
    region_dir.mkdir(parents=True, exist_ok=True)
    transcript_dir.mkdir(parents=True, exist_ok=True)

    region_start = max(0.0, entry["start"] - CANDIDATE_PAD)
    region_end = min(video_duration, entry["end"] + CANDIDATE_PAD)
    estimated_keyword_start, estimated_keyword_end = estimate_keyword_window(entry, term)
    region_ext = ".wav" if SOURCE_ASR_AUDIO_ONLY else ".mp4"
    region_path = region_dir / f"{region_cache_stem(video, entry_index, term, region_start, region_end)}{region_ext}"
    if SOURCE_ASR_AUDIO_ONLY:
        extract_audio_region(video, region_path, region_start, region_end)
    else:
        clipper.render_region(video, region_path, region_start, region_end)
    transcript_path = clipper.transcribe_region(region_path, transcript_dir, WHISPER_MODEL)
    spoken_match = clipper.find_spoken_match(
        transcript_path,
        term,
        expected_start=max(0.0, estimated_keyword_start - region_start),
        expected_end=max(0.0, estimated_keyword_end - region_start),
    )
    if not spoken_match:
        return None, {"reason": "no_spoken_keyword_match", "transcript": str(transcript_path)}
    probability = spoken_match.get("probability")
    if probability is not None and float(probability) < MIN_EXACT_WORD_PROBABILITY:
        return None, {
            "reason": "low_confidence_spoken_keyword_match",
            "transcript": str(transcript_path),
            "spoken_match": spoken_match,
            "min_probability": MIN_EXACT_WORD_PROBABILITY,
        }
    audibility = rendered_keyword_audibility_check(spoken_match, term, region_end - region_start)
    if not audibility["ok"]:
        return None, {
            "reason": audibility["reason"],
            "transcript": str(transcript_path),
            "spoken_match": spoken_match,
            "audibility": audibility,
        }

    focus_ok, focus_detail = clipper.keyword_focus_ok(spoken_match, MAX_FOCUS_TOKENS)
    focus_detail["focused_text"] = spoken_match.get("utterance_text") or spoken_match.get("text") or ""
    if not focus_ok:
        return None, {
            "reason": "spoken_keyword_not_focused",
            "transcript": str(transcript_path),
            "spoken_match": spoken_match,
            "focus_detail": focus_detail,
        }

    clip_window = clipper.natural_window(
        region_start,
        region_end,
        spoken_match,
        CLIP_PRE_ROLL,
        CLIP_POST_ROLL,
        0.30,
        0.35,
        MIN_CLIP_DURATION,
        MAX_CLIP_DURATION,
    )
    if not clip_window:
        return None, {
            "reason": "unnatural_spoken_keyword_window",
            "transcript": str(transcript_path),
            "spoken_match": spoken_match,
        }

    clip_start, clip_end = clip_window
    word_start = region_start + spoken_match["word_start"]
    word_end = region_start + spoken_match["word_end"]
    shot_window, scene_adjustment = trim_to_keyword_shot(
        video,
        clip_start,
        clip_end,
        word_start,
        word_end,
        video_duration,
    )
    if shot_window is None:
        return None, {
            "reason": scene_adjustment["reason"],
            "transcript": str(transcript_path),
            "spoken_match": spoken_match,
            "scene_adjustment": scene_adjustment,
        }
    clip_start, clip_end = shot_window
    return {
        "region_start": region_start,
        "region_end": region_end,
        "transcript": str(transcript_path),
        "spoken_match": spoken_match,
        "focus_detail": focus_detail,
        "clip_start": clip_start,
        "clip_end": clip_end,
        "scene_adjustment": scene_adjustment,
        "keyword_start": word_start,
        "keyword_end": word_end,
    }, None


def verify_rendered_clip_spoken_keyword(clip_path, work_dir, term):
    transcript_dir = work_dir / "clip_transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = clipper.transcribe_region(clip_path, transcript_dir, WHISPER_MODEL)
    spoken_match = clipper.find_spoken_match(transcript_path, term)
    if not spoken_match:
        return None, {"reason": "no_spoken_keyword_match", "transcript": str(transcript_path)}
    probability = spoken_match.get("probability")
    if probability is not None and float(probability) < MIN_RENDERED_EXACT_WORD_PROBABILITY:
        return None, {
            "reason": "low_confidence_spoken_keyword_match",
            "transcript": str(transcript_path),
            "spoken_match": spoken_match,
            "min_probability": MIN_RENDERED_EXACT_WORD_PROBABILITY,
        }
    focus_ok, focus_detail = clipper.keyword_focus_ok(spoken_match, MAX_FOCUS_TOKENS)
    if not focus_ok:
        return None, {
            "reason": "rendered_spoken_keyword_not_focused",
            "transcript": str(transcript_path),
            "spoken_match": spoken_match,
            "focus_detail": focus_detail,
        }
    clip_duration = duration(clip_path)
    audibility = rendered_keyword_audibility_check(spoken_match, term, clip_duration)
    if not audibility["ok"]:
        return None, {
            "reason": audibility["reason"],
            "transcript": str(transcript_path),
            "spoken_match": spoken_match,
            "audibility": audibility,
        }
    if float(spoken_match.get("word_end") or 0.0) + MIN_RENDERED_KEYWORD_TAIL > clip_duration:
        return None, {
            "reason": "rendered_keyword_tail_too_short",
            "transcript": str(transcript_path),
            "spoken_match": spoken_match,
            "clip_duration": clip_duration,
            "min_tail": MIN_RENDERED_KEYWORD_TAIL,
        }

    return {
        "transcript": str(transcript_path),
        "spoken_match": spoken_match,
        "focus_detail": {"verified_in_rendered_clip": True, **focus_detail},
    }, None


def rendered_keyword_syllable_count(term, spoken_match=None):
    text = clipper.normalize_korean(term or "")
    count = len(re.findall(r"[가-힣]", text))
    if count:
        return count
    spoken_match = spoken_match or {}
    for value in (spoken_match.get("term"), spoken_match.get("text")):
        text = clipper.normalize_korean(value or "")
        count = len(re.findall(r"[가-힣]", text))
        if count:
            return count
    return 1


def rendered_keyword_min_audible_duration(term, spoken_match=None):
    syllables = rendered_keyword_syllable_count(term, spoken_match)
    return min(
        MAX_RENDERED_KEYWORD_DURATION_REQUIREMENT,
        max(
            MIN_RENDERED_KEYWORD_DURATION_FLOOR,
            syllables * MIN_RENDERED_KEYWORD_SECONDS_PER_SYLLABLE,
        ),
    )


def rendered_keyword_audibility_check(spoken_match, term, clip_duration):
    try:
        word_start = max(0.0, float(spoken_match.get("word_start") or 0.0))
        word_end = min(float(clip_duration), float(spoken_match.get("word_end") or 0.0))
    except (TypeError, ValueError):
        return {"ok": False, "reason": "missing_rendered_keyword_timing"}
    word_duration = max(0.0, word_end - word_start)
    min_duration = rendered_keyword_min_audible_duration(term, spoken_match)
    detail = {
        "ok": True,
        "reason": None,
        "word_start": word_start,
        "word_end": word_end,
        "word_duration": word_duration,
        "min_word_duration": min_duration,
        "syllable_count": rendered_keyword_syllable_count(term, spoken_match),
    }
    if word_duration < min_duration:
        detail["ok"] = False
        detail["reason"] = "keyword_spoken_duration_too_short"
    return detail


def has_hangul(text):
    return bool(re.search(r"[가-힣]", text or ""))


def verify_final_clip_korean_audio(clip_path, work_dir, term):
    if not VERIFY_FINAL_AUTO_KOREAN_AUDIO:
        return {"ok": True, "reason": "disabled"}

    transcript_dir = work_dir / "final_auto_audio_transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    clip_key = hashlib.sha1(str(clip_path.resolve()).encode("utf-8")).hexdigest()[:12]
    transcript_path = transcript_dir / f"{clip_path.parent.name}_{clip_path.stem}_{clip_key}_auto.json"

    if transcript_path.exists() and clipper.transcript_matches_source(
        transcript_path,
        clip_path,
        WHISPER_MODEL,
        "ko_auto_transcribe",
    ):
        result = json.loads(transcript_path.read_text())
    else:
        transcript_path.unlink(missing_ok=True)
        try:
            import whisper

            whisper_model = clipper._WHISPER_MODELS.get(WHISPER_MODEL)
            if whisper_model is None:
                whisper_model = whisper.load_model(WHISPER_MODEL)
                clipper._WHISPER_MODELS[WHISPER_MODEL] = whisper_model
            result = whisper_model.transcribe(
                str(clip_path),
                language="ko",
                fp16=False,
                verbose=False,
                word_timestamps=False,
                task="transcribe",
                initial_prompt="한국어 드라마 대사입니다. 짧은 한국어 표현과 감탄사도 한국어로 받아쓰세요.",
            )
            clipper.write_transcript_with_metadata(
                transcript_path,
                result,
                clip_path,
                WHISPER_MODEL,
                "ko_auto_transcribe",
            )
        except Exception as exc:
            return {
                "ok": False,
                "reason": "auto_audio_transcription_failed",
                "error": str(exc),
                "transcript": str(transcript_path),
            }

    language = result.get("language")
    text = (result.get("text") or "").strip()
    normalized_text = clipper.normalize_korean(text)
    normalized_term = clipper.normalize_korean(term or "")
    tokens = [token for token in clipper.normalized_tokens(text) if token]
    keyword_present = (not normalized_term) or bool(clipper.normalized_text_term_match(normalized_term, text))
    detail = {
        "ok": True,
        "reason": None,
        "language": language,
        "text": text,
        "transcript": str(transcript_path),
        "term": term,
        "normalized_text": normalized_text,
        "tokens": tokens,
        "keyword_present": keyword_present,
    }

    if language != "ko":
        detail["ok"] = False
        detail["reason"] = "non_korean_auto_audio"
        return detail
    if not has_hangul(text):
        detail["ok"] = False
        detail["reason"] = "no_hangul_in_auto_audio"
        return detail
    if REQUIRE_FINAL_AUTO_KEYWORD and normalized_term and not keyword_present:
        detail["ok"] = False
        detail["reason"] = "keyword_missing_in_auto_audio"
        return detail
    return detail


def extract_audio_region(video, output_path, start, end):
    if output_path.exists() and output_path.stat().st_size > 64:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(video),
            "-t",
            f"{max(0.2, end - start):.3f}",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(output_path),
        ],
        check=True,
    )


def verify_audio_keyword(video, work_dir, start, end, term, candidate_index):
    audio_dir = work_dir / "audio_regions"
    transcript_dir = work_dir / "audio_transcripts"
    audio_dir.mkdir(parents=True, exist_ok=True)
    transcript_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / f"{video.stem}_{candidate_index:06d}_{clipper.normalize_korean(term)}.wav"
    extract_audio_region(video, audio_path, start, end)
    transcript_path = clipper.transcribe_region(audio_path, transcript_dir, WHISPER_MODEL)
    spoken_match = clipper.find_spoken_match(transcript_path, term)
    if not spoken_match:
        return None, {"reason": "no_spoken_keyword_match", "transcript": str(transcript_path)}
    probability = spoken_match.get("probability")
    if probability is not None and float(probability) < MIN_EXACT_WORD_PROBABILITY:
        return None, {
            "reason": "low_confidence_spoken_keyword_match",
            "transcript": str(transcript_path),
            "spoken_match": spoken_match,
            "min_probability": MIN_EXACT_WORD_PROBABILITY,
        }
    return {
        "transcript": str(transcript_path),
        "spoken_match": spoken_match,
        "focus_detail": {"verified_in_audio_region": True},
    }, None


def dbfs_from_pcm16(samples):
    if not samples:
        return -120.0
    total = 0.0
    for sample in samples:
        value = float(sample) / 32768.0
        total += value * value
    rms = math.sqrt(total / len(samples))
    if rms <= 1e-9:
        return -120.0
    return 20.0 * math.log10(rms)


def peak_dbfs_from_pcm16(samples):
    if not samples:
        return -120.0
    peak = max(abs(int(sample)) for sample in samples) / 32768.0
    if peak <= 1e-9:
        return -120.0
    return 20.0 * math.log10(peak)


def decode_audio_pcm16(path, sample_rate=16000):
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "s16le",
            "-",
        ],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None, {"reason": "audio_decode_failed", "stderr": result.stderr.decode("utf-8", errors="replace")}
    samples = array.array("h")
    samples.frombytes(result.stdout)
    if sys.byteorder != "little":
        samples.byteswap()
    return samples, None


def keyword_audio_metrics(clip_path, keyword_start, keyword_end, clip_duration):
    samples, error = decode_audio_pcm16(clip_path)
    if error:
        return {"ok": False, **error}
    sample_rate = 16000
    start = max(0.0, float(keyword_start) - KEYWORD_AUDIO_PAD)
    end = min(float(clip_duration), float(keyword_end) + KEYWORD_AUDIO_PAD)
    low = max(0, int(start * sample_rate))
    high = min(len(samples), int(end * sample_rate))
    keyword_samples = samples[low:high]
    metrics = {
        "ok": True,
        "full_rms_dbfs": dbfs_from_pcm16(samples),
        "full_peak_dbfs": peak_dbfs_from_pcm16(samples),
        "keyword_rms_dbfs": dbfs_from_pcm16(keyword_samples),
        "keyword_peak_dbfs": peak_dbfs_from_pcm16(keyword_samples),
        "keyword_window": {"start": start, "end": end},
        "keyword_sample_count": len(keyword_samples),
    }
    if metrics["keyword_rms_dbfs"] < MIN_KEYWORD_RMS_DBFS:
        metrics["ok"] = False
        metrics["reason"] = "quiet_keyword_audio"
    elif metrics["keyword_peak_dbfs"] < MIN_KEYWORD_PEAK_DBFS:
        metrics["ok"] = False
        metrics["reason"] = "weak_keyword_audio_peak"
    return metrics


def expanded_keyword_validation_window(keyword_start, keyword_end, clip_duration):
    start = max(0.0, float(keyword_start) - KEYWORD_VALIDATION_EXTRA_PAD)
    end = min(float(clip_duration), float(keyword_end) + KEYWORD_VALIDATION_EXTRA_PAD)
    if end < start:
        start, end = end, start
    if end - start < MIN_KEYWORD_VALIDATION_WINDOW:
        center = (start + end) / 2
        half = MIN_KEYWORD_VALIDATION_WINDOW / 2
        start = max(0.0, center - half)
        end = min(float(clip_duration), center + half)
        if end - start < MIN_KEYWORD_VALIDATION_WINDOW:
            if start <= 0.0:
                end = min(float(clip_duration), MIN_KEYWORD_VALIDATION_WINDOW)
            elif end >= float(clip_duration):
                start = max(0.0, float(clip_duration) - MIN_KEYWORD_VALIDATION_WINDOW)
    return start, end


def rendered_face_mouth_motion(clip_path, face_box, keyword_start, keyword_end, clip_duration, sample_fps=12.0):
    if not face_box:
        return {"ok": False, "reason": "missing_rendered_face_box"}
    cv2 = lazy_cv2()
    if cv2 is None:
        return {"ok": False, "reason": "opencv_unavailable"}
    start = max(0.0, float(keyword_start) - 0.08)
    end = min(float(clip_duration), float(keyword_end) + 0.08)
    if end <= start:
        end = min(float(clip_duration), start + 0.24)
    sample_count = max(3, int(math.ceil(max(0.16, end - start) * sample_fps)) + 1)
    if sample_count == 1:
        times = [start]
    else:
        step = (end - start) / max(1, sample_count - 1)
        times = [start + step * index for index in range(sample_count)]
    cap = cv2.VideoCapture(str(clip_path))
    if not cap.isOpened():
        return {"ok": False, "reason": "video_open_failed"}
    frames = []
    for time_sec in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, float(time_sec) * 1000.0)
        ok, frame = cap.read()
        if ok and frame is not None:
            frames.append(frame)
    cap.release()
    motion = mouth_motion_from_frames(frames, face_box)
    motion["sample_times"] = times
    return motion


def verify_keyword_audio_and_speaker_clip(clip_path, keyword_start, keyword_end, rendered_face):
    if keyword_start is None or keyword_end is None:
        return {"ok": False, "reason": "missing_keyword_relative_timing"}
    clip_duration = duration(clip_path)
    validation_start, validation_end = expanded_keyword_validation_window(
        keyword_start,
        keyword_end,
        clip_duration,
    )
    audio = keyword_audio_metrics(clip_path, validation_start, validation_end, clip_duration)
    best_face = (rendered_face or {}).get("best") or {}
    face_box = best_face.get("box") or {}
    motion = rendered_face_mouth_motion(clip_path, face_box, validation_start, validation_end, clip_duration)
    detail = {
        "ok": True,
        "reason": None,
        "audio": audio,
        "mouth_motion": motion,
        "clip_duration": clip_duration,
        "validation_window": {"start": validation_start, "end": validation_end},
    }
    if not audio.get("ok"):
        detail["ok"] = False
        detail["reason"] = audio.get("reason") or "keyword_audio_validation_failed"
        return detail
    if not motion.get("ok"):
        detail["ok"] = False
        detail["reason"] = motion.get("reason") or "speaker_motion_validation_failed"
        return detail
    if float(motion.get("mouth_motion") or 0.0) < MIN_RENDERED_SPEAKER_MOUTH_MOTION:
        detail["ok"] = False
        detail["reason"] = "possible_offscreen_or_non_speaking_face"
        return detail
    return detail


def verify_fullscreen_clip(clip_path, width=1080, height=1920):
    try:
        actual_width, actual_height = clipper.ffprobe_video_size(clip_path)
    except Exception:
        return False
    return actual_width == width and actual_height == height


def detect_content_crop(clip_path, sample_duration=0.8, start_offset=None):
    input_args = []
    if start_offset is not None:
        input_args.extend(["-ss", f"{max(0, start_offset):.3f}"])
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            *input_args,
            "-i",
            str(clip_path),
            "-vf",
            "cropdetect=limit=20:round=2:reset=0",
            "-t",
            f"{sample_duration:.3f}",
            "-an",
            "-f",
            "null",
            "-",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    crops = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", result.stderr)
    if not crops:
        return None
    width, height, x, y = [int(value) for value in crops[-1]]
    return {"width": width, "height": height, "x": x, "y": y}


def detect_source_content_crop(video, start, end, limit=48):
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(video),
            "-t",
            f"{max(0.25, end - start):.3f}",
            "-vf",
            f"cropdetect=limit={limit}:round=2:reset=0",
            "-an",
            "-f",
            "null",
            "-",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    crops = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", result.stderr)
    source_width, source_height = clipper.ffprobe_video_size(video)
    if not crops:
        return detect_source_black_edge_crop(video, start, end, source_width, source_height)
    width, height, x, y = [int(value) for value in crops[-1]]
    black_edge_crop = detect_source_black_edge_crop(video, start, end, source_width, source_height)
    if width < source_width * 0.72 or height < source_height * 0.55:
        return black_edge_crop
    if width * height < source_width * source_height * 0.55:
        return black_edge_crop
    if width >= source_width * 0.995 and height >= source_height * 0.995 and x == 0 and y == 0:
        return black_edge_crop
    return {"width": width, "height": height, "x": x, "y": y}


def detect_source_black_edge_crop(video, start, end, source_width=None, source_height=None):
    source_width, source_height = (source_width, source_height) if source_width else clipper.ffprobe_video_size(video)
    sample_width = min(320, source_width)
    sample_height = max(2, int(round(source_height * sample_width / source_width)))
    if sample_height % 2:
        sample_height += 1
    scale_x = source_width / sample_width
    scale_y = source_height / sample_height
    clip_duration = max(0.25, end - start)
    sample_times = [
        start + clip_duration * 0.20,
        start + clip_duration * 0.50,
        start + clip_duration * 0.80,
    ]
    edge_samples = []
    for sample_time in sample_times:
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{max(0, sample_time):.3f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                "-vf",
                f"scale={sample_width}:{sample_height}:flags=bilinear",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ],
            check=False,
            capture_output=True,
        )
        expected = sample_width * sample_height * 3
        if len(result.stdout) < expected:
            continue
        data = result.stdout[:expected]

        def is_black(index):
            return data[index] <= 35 and data[index + 1] <= 35 and data[index + 2] <= 35

        row_ratios = []
        for y in range(sample_height):
            black_count = 0
            for x in range(sample_width):
                if is_black((y * sample_width + x) * 3):
                    black_count += 1
            row_ratios.append(black_count / sample_width)

        col_ratios = []
        for x in range(sample_width):
            black_count = 0
            for y in range(sample_height):
                if is_black((y * sample_width + x) * 3):
                    black_count += 1
            col_ratios.append(black_count / sample_height)

        def leading_count(values):
            count = 0
            for value in values:
                if value >= 0.92:
                    count += 1
                else:
                    break
            return count

        edge_samples.append(
            {
                "top": leading_count(row_ratios),
                "bottom": leading_count(list(reversed(row_ratios))),
                "left": leading_count(col_ratios),
                "right": leading_count(list(reversed(col_ratios))),
            }
        )

    if not edge_samples:
        return None

    top = min(sample["top"] for sample in edge_samples)
    bottom = min(sample["bottom"] for sample in edge_samples)
    left = min(sample["left"] for sample in edge_samples)
    right = min(sample["right"] for sample in edge_samples)
    top = int(round(top * scale_y))
    bottom = int(round(bottom * scale_y))
    left = int(round(left * scale_x))
    right = int(round(right * scale_x))
    min_bar = 4
    top = top if top >= min_bar else 0
    bottom = bottom if bottom >= min_bar else 0
    left = left if left >= min_bar else 0
    right = right if right >= min_bar else 0
    if not any((top, bottom, left, right)):
        return None

    x = clipper.even_int(left)
    y = clipper.even_int(top)
    width = clipper.even_int(source_width - left - right)
    height = clipper.even_int(source_height - top - bottom)
    if width < source_width * 0.80 or height < source_height * 0.55:
        return None
    return {"width": width, "height": height, "x": x, "y": y, "method": "black_edge"}


def black_edge_bars(clip_path, sample_time, width=90, height=160, black_threshold=35):
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{max(0.05, sample_time):.3f}",
            "-i",
            str(clip_path),
            "-frames:v",
            "1",
            "-vf",
            f"scale={width}:{height}:flags=bilinear",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        check=False,
        capture_output=True,
    )
    expected = width * height * 3
    if len(result.stdout) < expected:
        return {"top": 0, "bottom": 0, "left": 0, "right": 0}
    data = result.stdout[:expected]

    def is_black(index):
        return (
            data[index] <= black_threshold
            and data[index + 1] <= black_threshold
            and data[index + 2] <= black_threshold
        )

    row_ratios = []
    for y in range(height):
        black_count = 0
        for x in range(width):
            if is_black((y * width + x) * 3):
                black_count += 1
        row_ratios.append(black_count / width)

    col_ratios = []
    for x in range(width):
        black_count = 0
        for y in range(height):
            if is_black((y * width + x) * 3):
                black_count += 1
        col_ratios.append(black_count / height)

    def leading_count(values):
        count = 0
        for value in values:
            if value >= 0.92:
                count += 1
            else:
                break
        return count

    return {
        "top": leading_count(row_ratios) / height,
        "bottom": leading_count(list(reversed(row_ratios))) / height,
        "left": leading_count(col_ratios) / width,
        "right": leading_count(list(reversed(col_ratios))) / width,
    }


def verify_visual_fill_clip(clip_path, width=1080, height=1920):
    clip_duration = duration(clip_path)
    if FAST_VISUAL_FILL_SAMPLES:
        sample_times = [max(0.05, clip_duration * 0.50)]
    else:
        sample_times = sorted(
            {
                max(0.05, clip_duration * 0.20),
                max(0.05, clip_duration * 0.50),
                max(0.05, clip_duration * 0.80),
            }
        )
    max_bar_ratio = 0.018
    for sample_time in sample_times:
        if not FAST_VISUAL_FILL_SAMPLES:
            crop = detect_content_crop(clip_path, sample_duration=0.45, start_offset=sample_time)
            if crop is not None and (
                crop["width"] < width * 0.985 or crop["height"] < height * 0.985
            ):
                return False
        bars = black_edge_bars(clip_path, sample_time)
        if any(value > max_bar_ratio for value in bars.values()):
            return False
    return True


def sample_rgb_frame(clip_path, sample_time, width=180, height=320):
    cv2 = lazy_cv2()
    if cv2 is not None:
        cap = cv2.VideoCapture(str(clip_path))
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.05, float(sample_time)) * 1000.0)
            ok, frame = cap.read()
            cap.release()
            if ok and frame is not None:
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_LINEAR)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return frame.tobytes()
        else:
            cap.release()
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{max(0.05, sample_time):.3f}",
            "-i",
            str(clip_path),
            "-frames:v",
            "1",
            "-vf",
            f"scale={width}:{height}:flags=bilinear",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        check=False,
        capture_output=True,
    )
    expected = width * height * 3
    if len(result.stdout) < expected:
        return None
    return result.stdout[:expected]


def text_like_zone_score(data, width, height, x0_ratio, x1_ratio, y0_ratio, y1_ratio):
    x0 = max(1, int(width * x0_ratio))
    x1 = min(width - 1, int(width * x1_ratio))
    y0 = max(1, int(height * y0_ratio))
    y1 = min(height - 1, int(height * y1_ratio))
    if x1 <= x0 or y1 <= y0:
        return {"edge_ratio": 0.0, "dense_rows": 0, "dense_row_ratio": 0.0}

    total = (x1 - x0) * (y1 - y0)
    edge_pixels = 0
    dense_rows = 0
    for y in range(y0, y1):
        row_edges = 0
        for x in range(x0, x1):
            idx = (y * width + x) * 3
            r, g, b = data[idx], data[idx + 1], data[idx + 2]
            gray = (r + g + b) // 3
            if max(r, g, b) < 145:
                continue
            if min(r, g, b) < 80 and max(r, g, b) - min(r, g, b) < 95:
                continue
            left = ((data[idx - 3] + data[idx - 2] + data[idx - 1]) // 3)
            right = ((data[idx + 3] + data[idx + 4] + data[idx + 5]) // 3)
            up_idx = ((y - 1) * width + x) * 3
            down_idx = ((y + 1) * width + x) * 3
            up = (data[up_idx] + data[up_idx + 1] + data[up_idx + 2]) // 3
            down = (data[down_idx] + data[down_idx + 1] + data[down_idx + 2]) // 3
            if max(abs(gray - left), abs(gray - right), abs(gray - up), abs(gray - down)) >= 42:
                row_edges += 1
        edge_pixels += row_edges
        if row_edges / max(1, x1 - x0) >= 0.035:
            dense_rows += 1

    return {
        "edge_ratio": edge_pixels / max(1, total),
        "dense_rows": dense_rows,
        "dense_row_ratio": dense_rows / max(1, y1 - y0),
    }


def verify_clean_source_frame_clip(clip_path):
    clip_duration = duration(clip_path)
    if FAST_VISUAL_FILL_SAMPLES:
        sample_times = [max(0.05, clip_duration * 0.50)]
    else:
        sample_times = sorted(
            {
                max(0.05, clip_duration * 0.22),
                max(0.05, clip_duration * 0.50),
                max(0.05, clip_duration * 0.78),
            }
        )
    bad_frames = []
    scores = []
    width, height = 180, 320
    for sample_time in sample_times:
        data = sample_rgb_frame(clip_path, sample_time, width=width, height=height)
        if data is None:
            continue
        lower = text_like_zone_score(data, width, height, 0.04, 0.96, 0.58, 0.94)
        upper = text_like_zone_score(data, width, height, 0.02, 0.98, 0.02, 0.20)
        corner_left = text_like_zone_score(data, width, height, 0.02, 0.42, 0.02, 0.28)
        corner_right = text_like_zone_score(data, width, height, 0.58, 0.98, 0.02, 0.28)
        score = {
            "sample_time": sample_time,
            "lower": lower,
            "upper": upper,
            "corner_left": corner_left,
            "corner_right": corner_right,
        }
        scores.append(score)
        lower_bad = lower["edge_ratio"] >= 0.022 and lower["dense_rows"] >= 5
        upper_bad = upper["edge_ratio"] >= 0.034 and upper["dense_rows"] >= 4
        corner_bad = (
            corner_left["edge_ratio"] >= 0.040
            and corner_left["dense_rows"] >= 3
        ) or (
            corner_right["edge_ratio"] >= 0.040
            and corner_right["dense_rows"] >= 3
        )
        if lower_bad or upper_bad or corner_bad:
            bad_frames.append(score)
    ok = len(bad_frames) < 2
    return {
        "ok": ok,
        "reason": None if ok else "possible_embedded_logo_or_source_caption",
        "bad_frame_count": len(bad_frames),
        "sample_times": sample_times,
        "scores": scores,
    }


def dedupe_clip_pool(clips):
    deduped = []
    seen = set()
    seen_paths = set()
    seen_scene_keys = set()
    for item in clips:
        fallback = str(Path(item["clip"]).resolve()) if item.get("clip") else ""
        if fallback and fallback in seen_paths:
            continue
        scene_key = (item.get("source_scene") or {}).get("key")
        if scene_key:
            if scene_key in seen_scene_keys:
                continue
            seen_scene_keys.add(scene_key)
        key = (
            item.get("episode"),
            round(float(item.get("start", -1)), 2),
            round(float(item.get("end", -1)), 2),
        )
        identity = key if key[0] is not None and key[1] >= 0 and key[2] >= 0 else fallback
        if identity in seen:
            continue
        seen.add(identity)
        if fallback:
            seen_paths.add(fallback)
        deduped.append(item)
    return deduped


def subject_framing_score(clip_path, sample_time=None):
    clip_duration = duration(clip_path)
    sample_time = max(0.05, sample_time if sample_time is not None else clip_duration / 2)
    width, height = 270, 480
    data = sample_rgb_frame(clip_path, sample_time, width=width, height=height)
    expected = width * height * 3
    if data is None or len(data) < expected:
        return {"ok": False, "reason": "no_mid_frame"}

    data = data[:expected]
    mask = bytearray(width * height)
    for y in range(height):
        row = y * width
        for x in range(width):
            i = (row + x) * 3
            r, g, b = data[i], data[i + 1], data[i + 2]
            max_channel = max(r, g, b)
            min_channel = min(r, g, b)
            if (
                r > 70
                and g > 45
                and b > 35
                and r - g > 8
                and r - b > 18
                and max_channel - min_channel > 25
                and r < 245
                and g < 235
            ):
                mask[row + x] = 1

    visited = bytearray(width * height)
    candidates = []
    for index, value in enumerate(mask):
        if not value or visited[index]:
            continue
        stack = [index]
        visited[index] = 1
        count = 0
        min_x, min_y = width, height
        max_x, max_y = 0, 0
        while stack:
            current = stack.pop()
            count += 1
            x = current % width
            y = current // width
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            for neighbor in (current - 1, current + 1, current - width, current + width):
                if neighbor < 0 or neighbor >= len(mask) or visited[neighbor] or not mask[neighbor]:
                    continue
                if abs((neighbor % width) - x) > 1:
                    continue
                visited[neighbor] = 1
                stack.append(neighbor)

        box_w = max_x - min_x + 1
        box_h = max_y - min_y + 1
        if count < 120 or box_w < 18 or box_h < 24:
            continue
        if box_w > width * 0.96 or box_h > height * 0.92 or count > width * height * 0.46:
            continue
        center_x = (min_x + max_x + 1) / 2 / width
        center_y = (min_y + max_y + 1) / 2 / height
        center_score = 1.0 - abs(center_x - 0.5)
        candidates.append(
            {
                "count": count,
                "box": {"x": min_x, "y": min_y, "width": box_w, "height": box_h},
                "center_x": center_x,
                "center_y": center_y,
                "score": count * center_score,
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    if not candidates:
        return {"ok": False, "reason": "no_face_like_subject_component", "candidates": []}
    best = candidates[0]
    ok = 0.28 <= best["center_x"] <= 0.72 and 0.12 <= best["center_y"] <= 0.66
    return {"ok": ok, "reason": None if ok else "subject_not_centered", "best": best, "candidates": candidates[:3]}


def best_rendered_face_at(clip_path, sample_time, label):
    try:
        stat = clip_path.stat()
        cache_key = (str(clip_path.resolve()), stat.st_size, stat.st_mtime_ns, round(float(sample_time), 3))
        if cache_key in _RENDERED_FACE_CACHE:
            cached = _RENDERED_FACE_CACHE[cache_key]
            return dict(cached) if cached else None
    except OSError:
        cache_key = None
    best = None
    frame_path = WORK_ROOT / "_face_validation_frames" / f"{clip_path.stem}_{label}_{int(sample_time * 1000)}.png"
    frame_path.parent.mkdir(parents=True, exist_ok=True)
    wrote_frame = False
    cv2 = lazy_cv2()
    if cv2 is not None:
        cap = cv2.VideoCapture(str(clip_path))
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.05, float(sample_time)) * 1000.0)
            ok, frame = cap.read()
            if ok and frame is not None:
                wrote_frame = bool(cv2.imwrite(str(frame_path), frame))
        cap.release()
    if not wrote_frame:
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{sample_time:.3f}",
                "-i",
                str(clip_path),
                "-frames:v",
                "1",
                str(frame_path),
            ],
            check=False,
        )
    for face in opencv_dnn_faces(frame_path):
        area_ratio = (face["width"] * face["height"]) / (face["imageWidth"] * face["imageHeight"])
        center_x = (face["x"] + face["width"] / 2) / face["imageWidth"]
        center_y = (face["y"] + face["height"] / 2) / face["imageHeight"]
        candidate = {
            "time": sample_time,
            "area_ratio": area_ratio,
            "center_x": center_x,
            "center_y": center_y,
            "confidence": face.get("confidence"),
            "box": {key: face[key] for key in ["x", "y", "width", "height"]},
        }
        score = area_ratio * float(face.get("confidence") or 1.0) - abs(center_x - 0.5) * 0.01
        candidate["score"] = score
        if best is None or score > best["score"]:
            best = candidate
    if cache_key is not None:
        _RENDERED_FACE_CACHE[cache_key] = dict(best) if best else None
    return best


def rendered_face_quality(face, min_area=MIN_RENDERED_KEYWORD_FACE_AREA):
    if not face:
        return False, "missing_rendered_face"
    area = float(face.get("area_ratio") or 0.0)
    center_x = float(face.get("center_x") or 0.0)
    center_y = float(face.get("center_y") or 0.0)
    confidence = float(face.get("confidence") or 0.0)
    if area < min_area:
        return False, "rendered_face_too_small"
    if confidence < MIN_RENDERED_FACE_CONFIDENCE:
        return False, "rendered_face_low_confidence"
    if not (RENDERED_FACE_CENTER_X_RANGE[0] <= center_x <= RENDERED_FACE_CENTER_X_RANGE[1]):
        return False, "rendered_face_not_centered_x"
    if not (RENDERED_FACE_CENTER_Y_RANGE[0] <= center_y <= RENDERED_FACE_CENTER_Y_RANGE[1]):
        return False, "rendered_face_not_centered_y"
    if confidence < STRONG_RENDERED_FACE_CONFIDENCE and not (
        LOW_CONF_RENDERED_FACE_CENTER_X_RANGE[0] <= center_x <= LOW_CONF_RENDERED_FACE_CENTER_X_RANGE[1]
        and LOW_CONF_RENDERED_FACE_CENTER_Y_RANGE[0] <= center_y <= LOW_CONF_RENDERED_FACE_CENTER_Y_RANGE[1]
    ):
        return False, "low_confidence_rendered_face_not_centered"
    return True, None


def rendered_keyword_face_sample_times(keyword_relative_start, keyword_relative_end, clip_duration):
    if keyword_relative_start is None or keyword_relative_end is None:
        return [max(0.05, clip_duration * 0.50)]
    start = clamp(float(keyword_relative_start), 0.05, max(0.05, clip_duration - 0.05))
    end = clamp(float(keyword_relative_end), 0.05, max(0.05, clip_duration - 0.05))
    if end < start:
        start, end = end, start
    center = (start + end) / 2
    if FAST_VISUAL_FILL_SAMPLES:
        return unique_sample_times([center], 0.05, max(0.05, clip_duration - 0.05))
    return unique_sample_times(
        [center, start, end, center - 0.08, center + 0.08],
        0.05,
        max(0.05, clip_duration - 0.05),
    )


def item_keyword_face_sample_times(item, clip_duration):
    if item.get("keyword_relative_start") is not None and item.get("keyword_relative_end") is not None:
        return rendered_keyword_face_sample_times(
            item.get("keyword_relative_start"),
            item.get("keyword_relative_end"),
            clip_duration,
        )
    return [max(0.05, clip_duration * 0.50)]


def verify_rendered_face_clip(clip_path, sample_times=None, label_prefix="mid"):
    clip_duration = duration(clip_path)
    if sample_times is None:
        if FAST_VISUAL_FILL_SAMPLES:
            sample_times = [max(0.05, clip_duration * 0.50)]
        else:
            sample_times = sorted(
                {
                    max(0.05, clip_duration * 0.25),
                    max(0.05, clip_duration * 0.50),
                    max(0.05, clip_duration * 0.75),
                }
            )
    best = None
    for index, sample_time in enumerate(sample_times):
        candidate = best_rendered_face_at(clip_path, sample_time, f"{label_prefix}_{index}")
        if candidate is not None and (best is None or candidate["score"] > best["score"]):
            best = candidate
    if best is None:
        return {"ok": False, "reason": "no_rendered_face_detected", "sample_times": sample_times}
    ok, reason = rendered_face_quality(best)
    return {"ok": ok, "reason": reason, "best": best, "sample_times": sample_times}


def verify_clip_start_face_clip(clip_path):
    clip_path = Path(clip_path)
    clip_duration = duration(clip_path)
    max_time = max(0.0, min(clip_duration - 0.04, 0.32))
    sample_times = unique_sample_times(FINAL_START_FACE_SAMPLE_TIMES, 0.0, max_time)
    checked = []
    best = None
    for index, sample_time in enumerate(sample_times):
        face = best_rendered_face_at(clip_path, sample_time, f"start_face_{index}")
        ok, reason = rendered_face_quality(face, min_area=MIN_RENDERED_START_FACE_AREA)
        checked.append({"sample_time": sample_time, "ok": ok, "reason": reason, "face": face})
        if face is not None and (best is None or face["score"] > best["score"]):
            best = face
        if REQUIRE_FINAL_FIRST_FRAME_FACE and index == 0 and not ok:
            return {
                "ok": False,
                "reason": "first_frame_without_centered_face",
                "sample_times": sample_times,
                "checks": checked,
                "best": best,
            }
        if ok:
            return {"ok": True, "reason": None, "sample_times": sample_times, "checks": checked, "best": face}
    return {
        "ok": False,
        "reason": "start_without_centered_face",
        "sample_times": sample_times,
        "checks": checked,
        "best": best,
    }


def rendered_clip_segments(clip_path):
    clip_duration = duration(clip_path)
    segments, cuts = clip_scene_segments(clip_path, 0.0, clip_duration, threshold=CROP_SCENE_CUT_THRESHOLD)
    return segments, cuts, clip_duration


def verify_single_shot_clip(clip_path):
    clip_duration = duration(clip_path)
    cuts = [
        cut
        for cut in detect_scene_cuts(clip_path, 0.0, clip_duration, threshold=0.34)
        if 0.08 <= cut <= clip_duration - 0.08
    ]
    return {
        "ok": len(cuts) == 0,
        "reason": None if not cuts else "internal_scene_cut_detected",
        "scene_cuts": cuts,
        "duration": clip_duration,
    }


def verify_cut_aware_subject_clip(clip_path):
    segments, cuts, clip_duration = rendered_clip_segments(clip_path)
    short_segments = [
        {**segment, "duration": float(segment["end"]) - float(segment["start"])}
        for segment in segments
        if float(segment["end"]) - float(segment["start"]) < MIN_SCENE_SEGMENT_HOLD
    ]
    if short_segments:
        return {
            "ok": False,
            "reason": "rapid_scene_cut_hold_too_short",
            "scene_cuts": cuts,
            "duration": clip_duration,
            "segments": segments,
            "short_segments": short_segments,
            "min_scene_segment_hold": MIN_SCENE_SEGMENT_HOLD,
        }
    checks = []
    for index, segment in enumerate(segments):
        segment_checks = []
        for sample_i, sample_time in enumerate(rendered_segment_sample_times(segment)):
            face = best_rendered_face_at(clip_path, sample_time, f"cut_{index}_{sample_i}")
            face_ok, _face_reason = rendered_face_quality(face, min_area=0.006)
            if face_ok:
                segment_checks.append({"sample_time": sample_time, "mode": "face", "face": face})
                continue
            framing = subject_framing_score(clip_path, sample_time=sample_time)
            if framing["ok"]:
                segment_checks.append(
                    {
                        "sample_time": sample_time,
                        "mode": "subject_fallback",
                        "face": face,
                        "framing": framing,
                    }
                )
                continue
            return {
                "ok": False,
                "reason": "cut_without_centered_face_or_subject",
                "failed_index": index,
                "failed_segment": segment,
                "sample_time": sample_time,
                "face": face,
                "framing": framing,
                "scene_cuts": cuts,
                "duration": clip_duration,
                "checks": checks,
                "segment_checks": segment_checks,
            }
        checks.append({"index": index, "segment": segment, "sample_checks": segment_checks})
    return {"ok": True, "reason": None, "scene_cuts": cuts, "duration": clip_duration, "checks": checks}


def concat_media_files(clips, output):
    output.unlink(missing_ok=True)
    if len(clips) == 1:
        run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                clips[0],
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                output,
            ]
        )
        return
    inputs = []
    parts = []
    for index, path in enumerate(clips):
        inputs.extend(["-i", path])
        parts.append(f"[{index}:v][{index}:a]")
    filter_complex = "".join(parts) + f"concat=n={len(clips)}:v=1:a=1[v][a]"
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            *inputs,
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-profile:v",
            "main",
            "-preset",
            "veryfast",
            "-b:v",
            "10M",
            "-maxrate",
            "14M",
            "-bufsize",
            "20M",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            output,
        ]
    )


def render_face_crop_segment(video, output, start, end, face_info, source_content_crop):
    segment_face_info = dict(face_info)
    segment_face_info.pop("crop_segments", None)
    segment_face_info.pop("cut_crop_plan", None)
    if source_content_crop:
        segment_face_info["source_content_crop"] = source_content_crop
    output.unlink(missing_ok=True)
    clipper.render_face_crop_region(
        video,
        output,
        start,
        end,
        segment_face_info,
        target_width=1080,
        target_height=1920,
        output_preset="veryfast",
        video_bitrate="10M",
        maxrate="14M",
        bufsize="20M",
        profile="main",
        scale_flags="lanczos",
        color_filter=COLOR_FILTER,
        sharpen_filter="unsharp=5:5:0.24:3:3:0",
    )


def render_candidate_clip(video, output, start, end, face_info):
    if output.exists() and duration(output) > 0:
        if face_info.get("crop_segments"):
            output.unlink(missing_ok=True)
        elif verify_fullscreen_clip(output) and verify_visual_fill_clip(output):
            return
    if output.exists() and duration(output) > 0:
        if verify_fullscreen_clip(output) and verify_visual_fill_clip(output):
            return
        output.unlink(missing_ok=True)
    source_content_crop = face_info.get("source_content_crop")
    if source_content_crop is None and not FAST_VISUAL_FILL_SAMPLES:
        source_content_crop = detect_source_content_crop(video, start, end)
    adjusted_face_info = dict(face_info)
    if source_content_crop:
        adjusted_face_info["source_content_crop"] = source_content_crop
    crop_segments = adjusted_face_info.get("crop_segments") or []
    if crop_segments:
        segment_dir = output.parent / ".segments" / output.stem
        segment_dir.mkdir(parents=True, exist_ok=True)
        segment_paths = []
        for index, segment in enumerate(crop_segments, start=1):
            segment_start = max(float(start), float(segment.get("start", start)))
            segment_end = min(float(end), float(segment.get("end", end)))
            if segment_end - segment_start < 0.05:
                continue
            subject = dict(segment.get("subject") or adjusted_face_info)
            subject["render_segment_index"] = index
            segment_path = segment_dir / f"{index:02d}.mp4"
            render_face_crop_segment(
                video,
                segment_path,
                segment_start,
                segment_end,
                subject,
                source_content_crop,
            )
            segment_paths.append(segment_path)
        if not segment_paths:
            raise subprocess.CalledProcessError(1, ["render_candidate_clip", "no_segments"])
        concat_media_files(segment_paths, output)
        adjusted_face_info["render_strategy"] = "segment_hard_cut_concat"
        face_info["render_strategy"] = "segment_hard_cut_concat"
        return
    clipper.render_face_crop_region(
        video,
        output,
        start,
        end,
        adjusted_face_info,
        target_width=1080,
        target_height=1920,
        output_preset="veryfast",
        video_bitrate="10M",
        maxrate="14M",
        bufsize="20M",
        profile="main",
        scale_flags="lanczos",
        color_filter=COLOR_FILTER,
        sharpen_filter="unsharp=5:5:0.24:3:3:0",
    )
    face_info["render_strategy"] = "single_crop"


def compile_subtitle_renderer(work_dir):
    renderer = work_dir / "render_subtitle_overlay"
    if renderer.exists() and renderer.stat().st_mtime >= SUBTITLE_RENDERER_SOURCE.stat().st_mtime:
        return renderer
    module_cache = work_dir / "swift_module_cache"
    module_cache.mkdir(parents=True, exist_ok=True)
    run(["xcrun", "swiftc", "-module-cache-path", module_cache, SUBTITLE_RENDERER_SOURCE, "-o", renderer])
    return renderer


def overlay_vocab(renderer, clip, output, overlay_path, term):
    if output.exists() and duration(output) > 0:
        return
    romanization, english, label = LEXICON.get(term, (f"[{term}]", "", "Casual"))
    run([renderer, overlay_path, term, romanization, english, label])
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            clip,
            "-i",
            overlay_path,
            "-filter_complex",
            "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p,setsar=1[v]",
            "-map",
            "[v]",
            "-map",
            "0:a:0",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-profile:v",
            "main",
            "-preset",
            "slow",
            "-b:v",
            "10M",
            "-maxrate",
            "14M",
            "-bufsize",
            "20M",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            output,
        ]
    )


def concat_clips(clips, output):
    if output.exists() and duration(output) >= MIN_FINAL_DURATION:
        return
    inputs = []
    parts = []
    for index, path in enumerate(clips):
        inputs.extend(["-i", path])
        parts.append(f"[{index}:v][{index}:a]")
    filter_complex = "".join(parts) + f"concat=n={len(clips)}:v=1:a=1[v][a]"
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            *inputs,
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-profile:v",
            "main",
            "-preset",
            "slow",
            "-b:v",
            "10M",
            "-maxrate",
            "14M",
            "-bufsize",
            "20M",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            output,
        ]
    )


def add_ad_banner(base_video, output, cta_video, ad_start=3.0):
    if output.exists() and duration(output) >= MIN_FINAL_DURATION:
        return
    banner_width = 1080
    banner_height = 480
    visible_ad_width = 270
    visible_ad_height = 480
    base_duration = duration(base_video)
    filter_complex = (
        f"color=c=black:s={banner_width}x{banner_height}:r=30:d={base_duration:.3f},"
        f"format=rgba,setpts=PTS-STARTPTS+{ad_start}/TB[adbg];"
        f"[1:v]scale={visible_ad_width}:{visible_ad_height}:flags=lanczos,"
        f"setpts=PTS-STARTPTS+{ad_start}/TB[adfg];"
        f"[adbg][adfg]overlay=x=(main_w-overlay_w)/2:y=0:format=auto:shortest=1[ad];"
        f"[0:v][ad]overlay=x=0:y=0:enable='gte(t,{ad_start})':eof_action=pass:format=auto,"
        "format=yuv420p,setsar=1[v]"
    )
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            base_video,
            "-i",
            cta_video,
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "0:a:0",
            "-c:v",
            "libx264",
            "-profile:v",
            "main",
            "-preset",
            "slow",
            "-b:v",
            "10M",
            "-maxrate",
            "14M",
            "-bufsize",
            "20M",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            output,
        ]
    )


def reached_limit(count, limit):
    return limit is not None and count >= limit


def limit_label(limit):
    return str(limit) if limit is not None else "all"


def resolve_project_path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def region_cache_stem(video, entry_index, term, region_start, region_end):
    video_part = safe_slug(video)[:72]
    term_part = clipper.normalize_korean(term) or "term"
    return (
        f"{video_part}_e{int(entry_index):06d}_"
        f"{int(region_start * 1000):010d}_{int(region_end * 1000):010d}_{term_part}"
    )


def existing_pool_item_valid(item):
    clip_path = Path(item.get("clip") or "")
    if not clip_path.exists():
        return False
    if item.get("speaker_face", {}).get("kind") not in FRONTAL_FACE_KINDS:
        return False
    if REQUIRE_CUT_AWARE_CROP and not item.get("speaker_face", {}).get("crop_segments"):
        return False
    if REQUIRE_CUT_AWARE_CROP and item.get("render_strategy") != "segment_hard_cut_concat":
        return False
    if VERIFY_AUDIO_BEFORE_RENDER and item.get("spoken_match", {}).get("source") == "subtitle_exact_match":
        return False
    if VERIFY_RENDERED_SPOKEN_BEFORE_POOL and not item.get("rendered_spoken_match"):
        return False
    if not item.get("spoken_match"):
        return False
    if item.get("keyword_relative_start") is None or item.get("keyword_relative_end") is None:
        return False
    if not verify_fullscreen_clip(clip_path):
        return False
    if not verify_visual_fill_clip(clip_path):
        return False
    if REQUIRE_CLEAN_SOURCE_FRAME and not verify_clean_source_frame_clip(clip_path)["ok"]:
        return False
    if REQUIRE_SINGLE_SHOT_CLIP and not verify_single_shot_clip(clip_path)["ok"]:
        return False
    clip_duration = duration(clip_path)
    rendered_face = verify_rendered_face_clip(
        clip_path,
        sample_times=item_keyword_face_sample_times(item, clip_duration),
        label_prefix="pool_existing",
    )
    if not rendered_face["ok"]:
        return False
    overall_rendered_face = verify_rendered_face_clip(clip_path, label_prefix="pool_existing_overall")
    if not overall_rendered_face["ok"]:
        return False
    keyword_speaker = (
        item.get("keyword_speaker_validation")
        if (item.get("keyword_speaker_validation") or {}).get("ok")
        else None
    )
    if keyword_speaker is None:
        keyword_speaker = verify_keyword_audio_and_speaker_clip(
            clip_path,
            item.get("keyword_relative_start"),
            item.get("keyword_relative_end"),
            rendered_face,
        )
    if not keyword_speaker["ok"]:
        return False
    if STRICT_POOL_VALIDATION:
        return (
            subject_framing_score(clip_path)["ok"]
            and verify_cut_aware_subject_clip(clip_path)["ok"]
        )
    return True


def existing_pool_item_quick_valid(item):
    clip_path = Path(item.get("clip") or "")
    if not clip_path.exists():
        return False
    if item.get("speaker_face", {}).get("kind") not in FRONTAL_FACE_KINDS:
        return False
    if not item.get("spoken_match"):
        return False
    if REQUIRE_CUT_AWARE_CROP and item.get("render_strategy") != "segment_hard_cut_concat":
        return False
    if VERIFY_RENDERED_SPOKEN_BEFORE_POOL and not item.get("rendered_spoken_match"):
        return False
    if item.get("keyword_relative_start") is None or item.get("keyword_relative_end") is None:
        return False
    keyword_speaker = item.get("keyword_speaker_validation") or {}
    if VERIFY_KEYWORD_SPEAKER_BEFORE_POOL and not keyword_speaker.get("ok"):
        return False
    if not VERIFY_KEYWORD_SPEAKER_BEFORE_POOL and (
        not keyword_speaker.get("ok")
        and keyword_speaker.get("reason") != "deferred_to_final_validation"
    ):
        return False
    return True


def build_clip_pool(
    folder,
    slug,
    target_clip_count=None,
    max_episodes=None,
    max_candidates_per_episode=None,
    episode_offset=0,
    validate_existing=True,
    excluded_source_scenes=None,
    excluded_source_ranges=None,
    excluded_source_windows=None,
    allowed_terms=None,
    ignore_target_limit=False,
):
    out_dir = OUTPUT_ROOT / slug
    work_dir = WORK_ROOT / slug
    srt_dir = work_dir / "srt"
    face_dir = work_dir / "faces"
    clip_root = out_dir / "clip"
    srt_dir.mkdir(parents=True, exist_ok=True)
    face_dir.mkdir(parents=True, exist_ok=True)
    clip_root.mkdir(parents=True, exist_ok=True)
    detector = clipper.ensure_face_detector(work_dir)

    existing_manifest = out_dir / "clip_pool_manifest.json"
    rejected_path = out_dir / "rejected_clip_pool_candidates.json"
    clips = []
    if existing_manifest.exists():
        existing_items = json.loads(existing_manifest.read_text())
        validator = existing_pool_item_valid if validate_existing else existing_pool_item_quick_valid
        clips = [item for item in existing_items if validator(item)]
    rejected = []
    if rejected_path.exists():
        rejected = json.loads(rejected_path.read_text())

    clips = dedupe_clip_pool(clips)
    seen_source_windows = {(item["episode"], round(item["start"], 2), round(item["end"], 2)) for item in clips}
    seen_source_scenes, seen_source_ranges = build_seen_source_indexes(clips)
    seen_source_windows.update(excluded_source_windows or set())
    seen_source_scenes.update(excluded_source_scenes or set())
    merge_source_ranges(seen_source_ranges, excluded_source_ranges)
    allowed_term_keys = (
        {clipper.normalize_korean(term) for term in allowed_terms if clipper.normalize_korean(term)}
        if allowed_terms
        else None
    )
    all_episodes = list_episode_videos(folder)
    episodes = all_episodes[episode_offset:]
    if max_episodes is not None:
        episodes = episodes[:max_episodes]
    for local_episode_index, video in enumerate(episodes, start=1):
        episode_index = episode_offset + local_episode_index
        if reached_limit(len(clips), target_clip_count) and not ignore_target_limit:
            break
        before_episode = len(clips)
        inspected_for_episode = 0
        print(f"  episode {local_episode_index:02d}/{len(episodes):02d} (source {episode_index:02d}/{len(all_episodes):02d}): {video.name}", flush=True)
        srt_path = extract_korean_srt(video, srt_dir / f"{video.stem}.kor.srt")
        if srt_path is None:
            print("    no Korean subtitle stream", flush=True)
            continue
        entries = clipper.parse_srt(srt_path)
        subtitle_scene_by_entry, _subtitle_scenes = build_subtitle_scene_index(entries)
        made_for_episode = 0
        video_duration = duration(video)
        crop_probe_start = min(max(0.0, video_duration * 0.25), max(0.0, video_duration - 2.0))
        episode_content_crop = detect_source_content_crop(
            video,
            crop_probe_start,
            min(video_duration, crop_probe_start + 1.5),
        )
        candidate_entries = []
        for entry_index, entry in enumerate(entries, start=1):
            if (
                MAX_SUBTITLE_CANDIDATE_DURATION
                and float(entry["end"]) - float(entry["start"]) > MAX_SUBTITLE_CANDIDATE_DURATION
            ):
                continue
            term = exact_lexicon_term(entry["text"])
            if not term:
                continue
            term_key = clipper.normalize_korean(term)
            if allowed_term_keys is not None and term_key not in allowed_term_keys:
                continue
            focus_ok, focus_detail = keyword_focus_ok(entry["text"], term)
            focus_detail["soft_focus_ok"] = focus_ok
            candidate_entries.append((candidate_priority(entry, term, focus_detail), entry_index, entry, term, focus_detail))
        candidate_entries.sort(key=lambda item: item[0])
        for _, entry_index, entry, term, focus_detail in candidate_entries:
            if (reached_limit(len(clips), target_clip_count) and not ignore_target_limit) or reached_limit(inspected_for_episode, max_candidates_per_episode):
                break
            source_scene = source_scene_detail(video, subtitle_scene_by_entry.get(entry_index))
            source_scene_key = source_scene["key"] if source_scene else None
            inspected_for_episode += 1
            keyword_start, keyword_end = estimate_keyword_window(entry, term)
            window, window_error = subtitle_candidate_window(
                video,
                entry,
                video_duration,
                keyword_start=keyword_start,
                keyword_end=keyword_end,
            )
            if not window:
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": window_error["reason"],
                        "term": term,
                        "subtitle_text": entry["text"],
                        "focus_detail": focus_detail,
                        **window_error,
                    }
                )
                continue
            start, end = window
            near_duplicate = find_near_source_duplicate(video.name, start, end, seen_source_ranges)
            if near_duplicate:
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": "near_duplicate_source_scene",
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                        "focus_detail": focus_detail,
                        "source_scene": source_scene,
                        "near_duplicate": near_duplicate,
                    }
                )
                continue
            source_auto_audio = verify_source_auto_audio_keyword(
                video,
                work_dir,
                entry_index,
                term,
                start,
                end,
            )
            if not source_auto_audio["ok"]:
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": source_auto_audio["reason"],
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                        "focus_detail": focus_detail,
                        "source_auto_audio": source_auto_audio,
                    }
                )
                continue
            if VERIFY_AUDIO_BEFORE_RENDER:
                spoken, spoken_error = verify_spoken_keyword(video, work_dir, entry, term, video_duration, entry_index)
                if not spoken:
                    rejected.append(
                        {
                            "episode": video.name,
                            "episode_index": episode_index,
                            "entry_index": entry_index,
                            "reason": spoken_error["reason"],
                            "term": term,
                            "subtitle_text": entry["text"],
                            "candidate_start": start,
                            "candidate_end": end,
                            "focus_detail": focus_detail,
                            **spoken_error,
                        }
                    )
                    continue
                start = spoken["clip_start"]
                end = spoken["clip_end"]
                keyword_start = spoken["keyword_start"]
                keyword_end = spoken["keyword_end"]
                focus_detail = spoken.get("focus_detail") or focus_detail
                near_duplicate = find_near_source_duplicate(video.name, start, end, seen_source_ranges)
                if near_duplicate:
                    rejected.append(
                        {
                            "episode": video.name,
                            "episode_index": episode_index,
                            "entry_index": entry_index,
                            "reason": "near_duplicate_source_scene",
                            "term": term,
                            "subtitle_text": entry["text"],
                            "candidate_start": start,
                            "candidate_end": end,
                            "focus_detail": focus_detail,
                            "source_scene": source_scene,
                            "near_duplicate": near_duplicate,
                        }
                    )
                    continue
            else:
                spoken = {
                    "transcript": str(srt_path),
                    "spoken_match": {
                        "term": term,
                        "text": entry["text"],
                        "word_start": keyword_start - start,
                        "word_end": keyword_end - start,
                        "utterance_start": entry["start"] - start,
                        "utterance_end": entry["end"] - start,
                        "utterance_text": focus_detail["focused_text"],
                        "probability": None,
                        "source": "subtitle_exact_match",
                    },
                    "focus_detail": focus_detail,
                }
            scene_adjustment = spoken.get("scene_adjustment")
            transition_window, scene_transition_pacing = adjust_for_scene_transition_pacing(
                video,
                start,
                end,
                keyword_start,
                keyword_end,
                video_duration,
            )
            if transition_window is None:
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": scene_transition_pacing["reason"],
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                        "keyword_start": keyword_start,
                        "keyword_end": keyword_end,
                        "scene_transition_pacing": scene_transition_pacing,
                    }
                )
                continue
            start, end = transition_window
            if (spoken.get("spoken_match") or {}).get("source") == "subtitle_exact_match":
                spoken["spoken_match"]["word_start"] = keyword_start - start
                spoken["spoken_match"]["word_end"] = keyword_end - start
                spoken["spoken_match"]["utterance_start"] = entry["start"] - start
                spoken["spoken_match"]["utterance_end"] = entry["end"] - start
            near_duplicate = find_near_source_duplicate(video.name, start, end, seen_source_ranges)
            if near_duplicate:
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": "near_duplicate_source_scene",
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                        "focus_detail": focus_detail,
                        "source_scene": source_scene,
                        "near_duplicate": near_duplicate,
                    }
                )
                continue
            key = (video.name, round(start, 2), round(end, 2))
            if key in seen_source_windows:
                continue
            if FAST_VISUAL_FILL_SAMPLES:
                source_content_crop = episode_content_crop
            else:
                source_content_crop = detect_source_content_crop(video, start, end) or episode_content_crop
            face = choose_keyword_speaker_face(
                video,
                detector,
                face_dir,
                keyword_start,
                keyword_end,
                search_start=max(start, keyword_start - KEYWORD_FACE_SEARCH_PAD),
                search_end=min(end, keyword_end + KEYWORD_FACE_SEARCH_PAD),
                source_content_crop=source_content_crop,
            )
            if face and source_content_crop:
                face["source_content_crop"] = source_content_crop
            if not face:
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": "no_keyword_visible_speaker",
                        "term": term,
                        "subtitle_text": entry["text"],
                        "subtitle_start": entry["start"],
                        "subtitle_end": entry["end"],
                        "keyword_start": keyword_start,
                        "keyword_end": keyword_end,
                        "candidate_start": start,
                        "candidate_end": end,
                        "source_content_crop": source_content_crop,
                    }
                )
                continue
            frame_tight_window = None
            if FRAME_TIGHTEN_CLIP_WINDOW:
                tight_window, frame_tight_window = refine_clip_window_frame_tight(
                    video,
                    detector,
                    face_dir,
                    start,
                    end,
                    keyword_start,
                    keyword_end,
                    face,
                    video_duration,
                )
                if tight_window is None:
                    rejected.append(
                        {
                            "episode": video.name,
                            "episode_index": episode_index,
                            "entry_index": entry_index,
                            "reason": frame_tight_window["reason"],
                            "term": term,
                            "subtitle_text": entry["text"],
                            "candidate_start": start,
                            "candidate_end": end,
                            "keyword_start": keyword_start,
                            "keyword_end": keyword_end,
                            "frame_tight_window": frame_tight_window,
                        }
                    )
                    continue
                start, end = tight_window
                if spoken.get("spoken_match"):
                    match = spoken["spoken_match"]
                    old_start = float(frame_tight_window.get("old_start", start))
                    old_utterance_start = old_start + float(match.get("utterance_start", 0.0))
                    old_utterance_end = old_start + float(match.get("utterance_end", keyword_end - old_start))
                    match["word_start"] = max(0.0, keyword_start - start)
                    match["word_end"] = max(0.0, keyword_end - start)
                    match["utterance_start"] = max(0.0, old_utterance_start - start)
                    match["utterance_end"] = max(0.0, old_utterance_end - start)
            surface = clipper.normalize_korean(term)
            crop_plan = None
            if REQUIRE_CUT_AWARE_CROP:
                crop_plan, crop_plan_error = build_cut_crop_plan(
                    video,
                    detector,
                    face_dir,
                    start,
                    end,
                    keyword_start,
                    keyword_end,
                    face,
                    source_content_crop=source_content_crop,
                )
                if not crop_plan:
                    rejected.append(
                        {
                            "episode": video.name,
                            "episode_index": episode_index,
                            "entry_index": entry_index,
                            "reason": crop_plan_error["reason"],
                            "term": term,
                            "subtitle_text": entry["text"],
                            "candidate_start": start,
                            "candidate_end": end,
                            "keyword_start": keyword_start,
                            "keyword_end": keyword_end,
                            "crop_plan_error": crop_plan_error,
                        }
                    )
                    continue
                face = dict(face)
                face["crop_segments"] = crop_plan["segments"]
                face["cut_crop_plan"] = {key: value for key, value in crop_plan.items() if key != "segments"}
            clip_category_dir = clip_root / (surface or "unknown")
            clip_category_dir.mkdir(parents=True, exist_ok=True)
            clip_path = clip_category_dir / f"{len(clips)+1:04d}_{surface}.mp4"
            clip_path.unlink(missing_ok=True)
            try:
                render_candidate_clip(video, clip_path, start, end, face)
            except subprocess.CalledProcessError:
                clip_path.unlink(missing_ok=True)
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": "render_failed",
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                    }
                )
                continue
            if not clip_path.exists():
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": "render_missing_output",
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                    }
                )
                continue
            clip_duration = duration(clip_path)
            if not (0.95 <= clip_duration <= MAX_SCENE_AWARE_CLIP_DURATION + 0.1):
                clip_path.unlink(missing_ok=True)
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": "bad_duration",
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                        "duration": clip_duration,
                    }
                )
                continue
            if not verify_fullscreen_clip(clip_path):
                clip_path.unlink(missing_ok=True)
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": "not_fullscreen_1080x1920",
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                    }
                )
                continue
            content_crop = detect_content_crop(clip_path)
            keyword_relative_start = max(0.0, keyword_start - start)
            keyword_relative_end = max(0.0, keyword_end - start)
            if not verify_visual_fill_clip(clip_path):
                clip_path.unlink(missing_ok=True)
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": "visual_content_not_filling_frame",
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                        "content_crop": content_crop,
                    }
                )
                continue
            start_face = verify_clip_start_face_clip(clip_path)
            if REQUIRE_FINAL_START_FACE and not start_face["ok"]:
                clip_path.unlink(missing_ok=True)
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": start_face["reason"],
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                        "keyword_relative_start": keyword_relative_start,
                        "keyword_relative_end": keyword_relative_end,
                        "start_face": start_face,
                    }
                )
                continue
            clean_source_frame = verify_clean_source_frame_clip(clip_path)
            if REQUIRE_CLEAN_SOURCE_FRAME and not clean_source_frame["ok"]:
                clip_path.unlink(missing_ok=True)
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": clean_source_frame["reason"],
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                        "clean_source_frame": clean_source_frame,
                    }
                )
                continue
            single_shot = (
                verify_single_shot_clip(clip_path)
                if REQUIRE_SINGLE_SHOT_CLIP
                else {"ok": True, "reason": "disabled_hard_cuts_allowed"}
            )
            if REQUIRE_SINGLE_SHOT_CLIP and not single_shot["ok"]:
                clip_path.unlink(missing_ok=True)
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": single_shot["reason"],
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                        "single_shot": single_shot,
                    }
                )
                continue
            rendered_spoken = None
            rendered_spoken_error = None
            if VERIFY_RENDERED_SPOKEN_BEFORE_POOL:
                rendered_spoken, rendered_spoken_error = verify_rendered_clip_spoken_keyword(
                    clip_path,
                    work_dir,
                    term,
                )
                if not rendered_spoken:
                    clip_path.unlink(missing_ok=True)
                    rejected.append(
                        {
                            "episode": video.name,
                            "episode_index": episode_index,
                            "entry_index": entry_index,
                            "reason": rendered_spoken_error["reason"],
                            "term": term,
                            "subtitle_text": entry["text"],
                            "candidate_start": start,
                            "candidate_end": end,
                            "rendered_spoken_error": rendered_spoken_error,
                        }
                    )
                    continue
                keyword_relative_start = max(0.0, rendered_spoken["spoken_match"]["word_start"])
                keyword_relative_end = min(clip_duration, rendered_spoken["spoken_match"]["word_end"])
            keyword_face_sample_times = rendered_keyword_face_sample_times(keyword_relative_start, keyword_relative_end, clip_duration)
            rendered_face = verify_rendered_face_clip(
                clip_path,
                sample_times=keyword_face_sample_times,
                label_prefix="pool_keyword",
            )
            if not rendered_face["ok"]:
                clip_path.unlink(missing_ok=True)
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": rendered_face["reason"],
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                        "keyword_relative_start": keyword_relative_start,
                        "keyword_relative_end": keyword_relative_end,
                        "rendered_face": rendered_face,
                    }
                )
                continue
            overall_rendered_face = (
                verify_rendered_face_clip(clip_path, label_prefix="pool_overall")
                if VERIFY_OVERALL_FACE_BEFORE_POOL
                else {"ok": True, "reason": "deferred_to_final_validation"}
            )
            if VERIFY_OVERALL_FACE_BEFORE_POOL and not overall_rendered_face["ok"]:
                clip_path.unlink(missing_ok=True)
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": f"overall_{overall_rendered_face['reason']}",
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                        "keyword_relative_start": keyword_relative_start,
                        "keyword_relative_end": keyword_relative_end,
                        "rendered_face": rendered_face,
                        "overall_rendered_face": overall_rendered_face,
                    }
                )
                continue
            if VERIFY_KEYWORD_SPEAKER_BEFORE_POOL:
                keyword_speaker_validation = verify_keyword_audio_and_speaker_clip(
                    clip_path,
                    keyword_relative_start,
                    keyword_relative_end,
                    rendered_face,
                )
                if not keyword_speaker_validation["ok"]:
                    clip_path.unlink(missing_ok=True)
                    rejected.append(
                        {
                            "episode": video.name,
                            "episode_index": episode_index,
                            "entry_index": entry_index,
                            "reason": keyword_speaker_validation["reason"],
                            "term": term,
                            "subtitle_text": entry["text"],
                            "candidate_start": start,
                            "candidate_end": end,
                            "keyword_relative_start": keyword_relative_start,
                            "keyword_relative_end": keyword_relative_end,
                            "keyword_speaker_validation": keyword_speaker_validation,
                        }
                    )
                    continue
            else:
                keyword_speaker_validation = {
                    "ok": False,
                    "reason": "deferred_to_final_validation",
                }
            framing = subject_framing_score(clip_path) if STRICT_POOL_VALIDATION else {"ok": True, "reason": "deferred_to_final_validation"}
            if STRICT_POOL_VALIDATION and not framing["ok"]:
                clip_path.unlink(missing_ok=True)
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": framing["reason"],
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                        "framing": framing,
                    }
                )
                continue
            cut_aware_subjects = (
                verify_cut_aware_subject_clip(clip_path)
                if STRICT_POOL_VALIDATION
                else {"ok": True, "reason": "deferred_to_final_validation"}
            )
            if STRICT_POOL_VALIDATION and not cut_aware_subjects["ok"]:
                clip_path.unlink(missing_ok=True)
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": cut_aware_subjects["reason"],
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                        "cut_aware_subjects": cut_aware_subjects,
                    }
                )
                continue
            tail_scene_adjustment = None
            for event in scene_transition_pacing.get("trim_events") or []:
                if event.get("edge") == "end":
                    tail_scene_adjustment = {
                        "mode": "hard_cut_at_scene_boundary",
                        "scene_cut": event.get("scene_cut"),
                        "old_end": event.get("old_end"),
                        "adjusted_end": event.get("adjusted_end"),
                    }
                    break
            near_duplicate = find_near_source_duplicate(video.name, start, end, seen_source_ranges)
            if near_duplicate:
                clip_path.unlink(missing_ok=True)
                rejected.append(
                    {
                        "episode": video.name,
                        "episode_index": episode_index,
                        "entry_index": entry_index,
                        "reason": "near_duplicate_source_scene",
                        "term": term,
                        "subtitle_text": entry["text"],
                        "candidate_start": start,
                        "candidate_end": end,
                        "source_scene": source_scene,
                        "near_duplicate": near_duplicate,
                    }
                )
                continue
            item = {
                "clip": str(clip_path),
                "term": term,
                "episode": video.name,
                "episode_index": episode_index,
                "source_video": str(video),
                "entry_index": entry_index,
                "subtitle_start": entry["start"],
                "subtitle_end": entry["end"],
                "source_scene": source_scene,
                "subtitle_text": entry["text"],
                "spoken_focus_text": focus_detail["focused_text"],
                "focus_tokens": focus_detail["tokens"],
                "spoken_match": spoken["spoken_match"],
                "spoken_transcript": spoken["transcript"],
                "source_auto_audio": source_auto_audio,
                "rendered_spoken_match": rendered_spoken["spoken_match"] if rendered_spoken else None,
                "rendered_spoken_transcript": rendered_spoken["transcript"] if rendered_spoken else None,
                "speech_region": {"start": spoken.get("region_start"), "end": spoken.get("region_end")},
                "scene_adjustment": scene_adjustment,
                "scene_transition_pacing": scene_transition_pacing,
                "frame_tight_window": frame_tight_window,
                "tail_scene_adjustment": tail_scene_adjustment,
                "start": start,
                "end": end,
                "keyword_start": keyword_start,
                "keyword_end": keyword_end,
                "keyword_relative_start": keyword_relative_start,
                "keyword_relative_end": keyword_relative_end,
                "duration": clip_duration,
                "speaker_face": face,
                "source_content_crop": source_content_crop,
                "color_filter": COLOR_FILTER,
                "keyword": surface,
                "clip_category": str(clip_category_dir),
                "fullscreen": {"width": 1080, "height": 1920, "fills_frame": True, "content_crop": content_crop},
                "start_face": start_face,
                "clean_source_frame": clean_source_frame,
                "single_shot": single_shot,
                "subject_framing": framing,
                "cut_aware_subjects": cut_aware_subjects,
                "rendered_face": rendered_face,
                "keyword_speaker_validation": keyword_speaker_validation,
                "render_strategy": face.get("render_strategy"),
            }
            clips.append(item)
            seen_source_windows.add((video.name, round(start, 2), round(end, 2)))
            add_seen_source_range(seen_source_ranges, item)
            made_for_episode += 1
            if len(clips) % 10 == 0:
                print(f"    clip pool: {len(clips)}/{limit_label(target_clip_count)}", flush=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        existing_manifest.write_text(json.dumps(clips, ensure_ascii=False, indent=2))
        rejected_path.write_text(json.dumps(rejected, ensure_ascii=False, indent=2))
        print(f"    added {len(clips) - before_episode}; pool={len(clips)}", flush=True)
    return clips


def shuffled_clip_order(clips, seed=None):
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    buckets = {}
    for item in clips:
        buckets.setdefault(item.get("episode") or "", []).append(item)
    for bucket in buckets.values():
        rng.shuffle(bucket)

    ordered = []
    last_episode = None
    while buckets:
        choices = [episode for episode in buckets if episode != last_episode] or list(buckets)
        largest_bucket = max(len(buckets[episode]) for episode in choices)
        candidates = [episode for episode in choices if len(buckets[episode]) == largest_bucket]
        episode = rng.choice(candidates)
        ordered.append(buckets[episode].pop())
        last_episode = episode
        if not buckets[episode]:
            del buckets[episode]
    return ordered


def rebuild_video_path(path):
    path.unlink(missing_ok=True)


def validate_clip_for_final(item, work_dir=None):
    clip_path = Path(item.get("clip") or "")
    detail = {
        "clip": str(clip_path),
        "term": item.get("term"),
        "episode": item.get("episode"),
    }
    if not clip_path.exists():
        detail["reason"] = "clip_missing"
        return False, detail
    speaker_kind = (item.get("speaker_face") or {}).get("kind")
    detail["speaker_face_kind"] = speaker_kind
    if speaker_kind not in FRONTAL_FACE_KINDS:
        detail["reason"] = "keyword_speaker_not_frontal_face"
        return False, detail
    try:
        clip_duration = duration(clip_path)
    except Exception as exc:
        detail["reason"] = "duration_probe_failed"
        detail["error"] = str(exc)
        return False, detail
    detail["duration"] = clip_duration
    if not (0.95 <= clip_duration <= MAX_SCENE_AWARE_CLIP_DURATION + 0.1):
        detail["reason"] = "bad_duration"
        return False, detail
    if not verify_fullscreen_clip(clip_path):
        detail["reason"] = "not_fullscreen_1080x1920"
        return False, detail
    if work_dir is not None:
        korean_audio = verify_final_clip_korean_audio(clip_path, work_dir, item.get("term"))
        detail["korean_audio"] = korean_audio
        if not korean_audio["ok"]:
            detail["korean_audio_warning"] = korean_audio["reason"]
    if not verify_visual_fill_clip(clip_path):
        detail["reason"] = "visual_content_not_filling_frame"
        return False, detail
    start_face = verify_clip_start_face_clip(clip_path)
    detail["start_face"] = start_face
    if REQUIRE_FINAL_START_FACE and not start_face["ok"]:
        detail["reason"] = start_face["reason"]
        return False, detail
    rendered_spoken = (
        {
            "spoken_match": item.get("rendered_spoken_match"),
            "transcript": item.get("rendered_spoken_transcript"),
            "focus_detail": {"from_manifest": True},
        }
        if item.get("rendered_spoken_match")
        else None
    )
    source_asr_spoken = (
        {
            "spoken_match": item.get("source_asr_match"),
            "transcript": item.get("source_asr_transcript"),
            "focus_detail": {"from_source_asr_repair": True},
        }
        if item.get("source_asr_match")
        else None
    )
    if REQUIRE_RENDERED_SPOKEN_KEYWORD and rendered_spoken is None:
        if source_asr_spoken is not None:
            rendered_spoken = source_asr_spoken
            detail["source_asr_repair_used"] = True
        elif work_dir is None:
            detail["reason"] = "missing_rendered_spoken_keyword_validation"
            return False, detail
        else:
            rendered_spoken, rendered_spoken_error = verify_rendered_clip_spoken_keyword(
                clip_path,
                work_dir,
                item.get("term"),
            )
            if not rendered_spoken:
                detail["reason"] = rendered_spoken_error["reason"]
                detail["rendered_spoken_error"] = rendered_spoken_error
                return False, detail
    detail["rendered_spoken"] = rendered_spoken
    if rendered_spoken and rendered_spoken.get("spoken_match"):
        probability = rendered_spoken["spoken_match"].get("probability")
        if probability is not None and float(probability) < MIN_RENDERED_EXACT_WORD_PROBABILITY:
            detail["reason"] = "low_confidence_spoken_keyword_match"
            detail["rendered_spoken_error"] = {
                "reason": "low_confidence_spoken_keyword_match",
                "spoken_match": rendered_spoken["spoken_match"],
                "min_probability": MIN_RENDERED_EXACT_WORD_PROBABILITY,
            }
            return False, detail
        audibility = rendered_keyword_audibility_check(
            rendered_spoken["spoken_match"],
            item.get("term"),
            clip_duration,
        )
        detail["rendered_keyword_audibility"] = audibility
        if not audibility["ok"]:
            detail["reason"] = audibility["reason"]
            detail["rendered_spoken_error"] = {
                "reason": audibility["reason"],
                "spoken_match": rendered_spoken["spoken_match"],
                "audibility": audibility,
            }
            return False, detail
    if rendered_spoken and rendered_spoken.get("spoken_match"):
        item["rendered_spoken_match"] = rendered_spoken["spoken_match"]
        item["rendered_spoken_transcript"] = rendered_spoken.get("transcript")
        item["keyword_relative_start"] = max(0.0, rendered_spoken["spoken_match"]["word_start"])
        item["keyword_relative_end"] = min(clip_duration, rendered_spoken["spoken_match"]["word_end"])
    cut_subjects = verify_cut_aware_subject_clip(clip_path)
    detail["cut_aware_subjects"] = cut_subjects
    if REQUIRE_FINAL_CUT_AWARE_SUBJECTS and not cut_subjects["ok"]:
        detail["reason"] = cut_subjects["reason"]
        return False, detail
    rendered_face = item.get("rendered_face") if (item.get("rendered_face") or {}).get("ok") else None
    if rendered_face is None:
        rendered_face = verify_rendered_face_clip(
            clip_path,
            sample_times=item_keyword_face_sample_times(item, clip_duration),
            label_prefix="final_keyword",
        )
    detail["rendered_face"] = rendered_face
    if REQUIRE_FINAL_RENDERED_FACE and not rendered_face["ok"]:
        detail["reason"] = rendered_face["reason"]
        return False, detail
    keyword_speaker = (
        item.get("keyword_speaker_validation")
        if (item.get("keyword_speaker_validation") or {}).get("ok")
        else None
    )
    if keyword_speaker is None:
        keyword_speaker = verify_keyword_audio_and_speaker_clip(
            clip_path,
            item.get("keyword_relative_start"),
            item.get("keyword_relative_end"),
            rendered_face,
        )
    detail["keyword_speaker_validation"] = keyword_speaker
    if not keyword_speaker["ok"]:
        detail["reason"] = keyword_speaker["reason"]
        return False, detail
    framing = subject_framing_score(clip_path)
    detail["subject_framing"] = framing
    detail["reason"] = None
    return True, detail


def final_clip_internal_cuts(item, validation=None):
    validation = validation or {}
    cuts = []
    cut_subjects = validation.get("cut_aware_subjects") or item.get("cut_aware_subjects") or {}
    for cut in cut_subjects.get("scene_cuts") or []:
        try:
            cuts.append(round(float(cut), 3))
        except (TypeError, ValueError):
            pass

    speaker = item.get("speaker_face") or {}
    cut_plan = speaker.get("cut_crop_plan") or {}
    for cut in cut_plan.get("scene_cuts") or []:
        try:
            start = float(item.get("start") or 0.0)
            relative = float(cut) - start if float(cut) > 10.0 else float(cut)
            cuts.append(round(relative, 3))
        except (TypeError, ValueError):
            pass

    crop_segments = speaker.get("crop_segments") or []
    if len(crop_segments) > 1:
        for segment in crop_segments[1:]:
            value = segment.get("rel_start")
            if value is None:
                try:
                    value = float(segment.get("start")) - float(item.get("start") or 0.0)
                except (TypeError, ValueError):
                    value = None
            if value is not None:
                try:
                    cuts.append(round(float(value), 3))
                except (TypeError, ValueError):
                    pass

    duration_value = item.get("duration") or validation.get("duration") or 0.0
    try:
        clip_duration = float(duration_value)
    except (TypeError, ValueError):
        clip_duration = 0.0
    return sorted({cut for cut in cuts if 0.08 <= cut <= max(0.08, clip_duration - 0.08)})


def validate_final_clip_pacing(item, validation=None):
    validation = validation or {}
    clip_path = Path(item.get("clip") or "")
    try:
        clip_duration = float(item.get("duration") or validation.get("duration") or duration(clip_path))
    except Exception as exc:
        return False, {"reason": "pacing_duration_probe_failed", "error": str(exc)}

    detail = {
        "reason": None,
        "duration": clip_duration,
        "min_clip_duration": MIN_FINAL_CLIP_PACING_DURATION,
        "allow_internal_scene_cuts": ALLOW_FINAL_INTERNAL_SCENE_CUTS,
    }
    if clip_duration < MIN_FINAL_CLIP_PACING_DURATION:
        detail["reason"] = "pacing_clip_too_short"
        return False, detail

    cuts = final_clip_internal_cuts(item, validation)
    detail["internal_scene_cuts"] = cuts
    points = [0.0] + [cut for cut in cuts if 0.0 < cut < clip_duration] + [clip_duration]
    segments = [
        {
            "index": index,
            "start": points[index],
            "end": points[index + 1],
            "duration": points[index + 1] - points[index],
        }
        for index in range(len(points) - 1)
    ]
    short_segments = [segment for segment in segments if segment["duration"] < MIN_SCENE_SEGMENT_HOLD]
    detail["segments"] = segments
    detail["short_segments"] = short_segments
    detail["min_scene_segment_hold"] = MIN_SCENE_SEGMENT_HOLD
    if short_segments:
        detail["reason"] = "rapid_scene_cut_hold_too_short"
        return False, detail
    if cuts and not ALLOW_FINAL_INTERNAL_SCENE_CUTS:
        detail["reason"] = "pacing_internal_scene_cut"
        return False, detail

    return True, detail


def delete_failed_final_clip(item):
    if not DELETE_FAILED_FINAL_CLIPS:
        return
    clip_path = Path(item.get("clip") or "")
    if clip_path.exists() and OUTPUT_ROOT in clip_path.parents:
        clip_path.unlink(missing_ok=True)


def build_final_videos(slug, clips, count, shuffle_seed=None):
    out_dir = OUTPUT_ROOT / slug
    work_dir = WORK_ROOT / slug
    overlay_dir = work_dir / "overlays"
    subtitled_dir = work_dir / "subtitled"
    concat_dir = work_dir / "concat"
    final_dir = out_dir / "finals_ad_subtitled"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    subtitled_dir.mkdir(parents=True, exist_ok=True)
    concat_dir.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)
    renderer = compile_subtitle_renderer(work_dir)

    ordered_clips = shuffled_clip_order(dedupe_clip_pool(clips), shuffle_seed)
    clip_cursor = 0
    finals = []
    final_rejected = []
    for video_index in range(1, count + 1):
        selected = []
        skipped_for_next_video = []
        selected_terms = set()
        total = 0.0
        while clip_cursor < len(ordered_clips) and total < MIN_FINAL_DURATION:
            if MAX_FINAL_CLIPS_PER_VIDEO and len(selected) >= MAX_FINAL_CLIPS_PER_VIDEO:
                break
            item = ordered_clips[clip_cursor]
            clip_cursor += 1
            term_key = clipper.normalize_korean(item.get("term") or item.get("keyword") or "")
            if term_key in selected_terms:
                skipped_for_next_video.append(item)
                continue
            valid, validation = validate_clip_for_final(item, work_dir)
            if not valid:
                delete_failed_final_clip(item)
                final_rejected.append(
                    {
                        "video_index": video_index,
                        "reason": validation.get("reason"),
                        "validation": validation,
                    }
                )
                continue
            pacing_ok, pacing = validate_final_clip_pacing(item, validation)
            if not pacing_ok:
                final_rejected.append(
                    {
                        "video_index": video_index,
                        "reason": pacing.get("reason"),
                        "validation": validation,
                        "pacing": pacing,
                    }
                )
                continue
            item["final_validation"] = validation
            item["final_pacing"] = pacing
            selected.append(item)
            if term_key:
                selected_terms.add(term_key)
            total += float(item["duration"])
        if skipped_for_next_video:
            ordered_clips[clip_cursor:clip_cursor] = skipped_for_next_video
        if total < MIN_FINAL_DURATION:
            final_rejected.append(
                {
                    "video_index": video_index,
                    "reason": "not_enough_duration_for_reference_pacing",
                    "selected_duration": total,
                    "selected_count": len(selected),
                    "min_duration": MIN_FINAL_DURATION,
                    "max_clips_per_video": MAX_FINAL_CLIPS_PER_VIDEO,
                    "min_clip_duration": MIN_FINAL_CLIP_PACING_DURATION,
                }
            )
            break
        subtitled_paths = []
        for local_index, item in enumerate(selected, start=1):
            clip = Path(item["clip"])
            term = item["term"]
            overlay = overlay_dir / f"v{video_index:02d}_{local_index:02d}_{clip.stem}.png"
            subtitled = subtitled_dir / f"v{video_index:02d}_{local_index:02d}_{clip.stem}.mp4"
            overlay_vocab(renderer, clip, subtitled, overlay, term)
            subtitled_paths.append(subtitled)
        concat_path = concat_dir / f"{slug}_video_{video_index:02d}_base.mp4"
        final_path = final_dir / f"{video_index}.mp4"
        rebuild_video_path(concat_path)
        rebuild_video_path(final_path)
        concat_clips(subtitled_paths, concat_path)
        add_ad_banner(concat_path, final_path, CTA_VIDEO)
        finals.append(
            {
                "final": str(final_path),
                "duration": duration(final_path),
                "clips": selected,
                "clip_count": len(selected),
                "shuffle_seed": shuffle_seed,
                "min_final_duration": MIN_FINAL_DURATION,
                "trimmed_to_exact_duration": False,
                "duplicate_terms_allowed": False,
                "min_clip_duration": MIN_FINAL_CLIP_PACING_DURATION,
                "max_clips_per_video": MAX_FINAL_CLIPS_PER_VIDEO,
                "allow_internal_scene_cuts": ALLOW_FINAL_INTERNAL_SCENE_CUTS,
            }
        )
        (out_dir / "final_manifest.json").write_text(json.dumps(finals, ensure_ascii=False, indent=2))
        (out_dir / "final_rejected_clips.json").write_text(json.dumps(final_rejected, ensure_ascii=False, indent=2))
        print(f"  final {video_index:02d}/{count}: {final_path.name} ({finals[-1]['duration']:.2f}s)", flush=True)
    (out_dir / "final_rejected_clips.json").write_text(json.dumps(final_rejected, ensure_ascii=False, indent=2))
    return finals


def load_output_clip_items(output_root):
    items = []
    for manifest in sorted(Path(output_root).glob("*/clip_pool_manifest.json")):
        try:
            manifest_items = json.loads(manifest.read_text())
        except Exception:
            continue
        if not isinstance(manifest_items, list):
            continue
        drama_slug = manifest.parent.name
        for item in manifest_items:
            clip_path = Path(item.get("clip") or "")
            if not clip_path.exists() or ".segments" in clip_path.parts:
                continue
            item_copy = dict(item)
            item_copy["_drama_slug"] = drama_slug
            items.append(item_copy)
    items.sort(
        key=lambda item: (
            clipper.normalize_korean(item.get("term") or ""),
            item.get("_drama_slug") or "",
            item.get("episode_index") or 0,
            float(item.get("start") or 0.0),
            item.get("clip") or "",
        )
    )
    return items


def export_keyword_clip_view(output_root):
    output_root = Path(output_root)
    view_root = output_root / "clips_by_keyword"
    if view_root.exists():
        shutil.rmtree(view_root)
    view_root.mkdir(parents=True, exist_ok=True)

    exported = []
    items = load_output_clip_items(output_root)
    drama_labels = {}

    def drama_label(slug):
        key = slug or "drama"
        if key not in drama_labels:
            drama_labels[key] = f"D{len(drama_labels) + 1:02d}"
        return drama_labels[key]

    for index, item in enumerate(items, start=1):
        clip_path = Path(item["clip"]).resolve()
        term = clipper.normalize_korean(item.get("term") or clip_path.parent.name) or "unknown"
        keyword_dir = view_root / safe_file_component(term, "unknown")
        keyword_dir.mkdir(parents=True, exist_ok=True)

        drama = drama_label(item.get("_drama_slug") or "drama")
        episode = item.get("episode_index")
        episode_part = f"E{int(episode):02d}" if episode else "E00"
        try:
            start_part = f"{int(round(float(item.get('start') or 0.0)))}s"
        except (TypeError, ValueError):
            start_part = "0s"
        filename = (
            f"{index:03d}_{safe_file_component(term, 'keyword', limit=24)}_"
            f"{drama}_{episode_part}_{start_part}.mp4"
        )
        destination = keyword_dir / filename
        destination.unlink(missing_ok=True)
        link_mode = "hardlink"
        try:
            os.link(clip_path, destination)
        except OSError:
            shutil.copy2(clip_path, destination)
            link_mode = "copy"
        exported.append(
            {
                "index": index,
                "term": term,
                "keyword_clip": str(destination),
                "source_clip": str(clip_path),
                "link_mode": link_mode,
                "drama_label": drama,
                "drama_slug": item.get("_drama_slug"),
                "episode": item.get("episode"),
                "episode_index": item.get("episode_index"),
                "start": item.get("start"),
                "end": item.get("end"),
                "duration": item.get("duration"),
                "subtitle_text": item.get("subtitle_text"),
            }
        )

    manifest_path = output_root / "clips_by_keyword_manifest.json"
    manifest_path.write_text(json.dumps(exported, ensure_ascii=False, indent=2))
    print(f"keyword view: {view_root} ({len(exported)} clips)", flush=True)
    print(f"keyword manifest: {manifest_path}", flush=True)
    return view_root, exported


def main():
    global OUTPUT_ROOT, WORK_ROOT, VERIFY_RENDERED_SPOKEN_BEFORE_POOL
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos-per-folder", type=int, default=15)
    parser.add_argument("--max-episodes", type=int, default=0, help="0 means all episodes")
    parser.add_argument("--max-candidates-per-episode", type=int, default=0, help="0 means all matching subtitle candidates")
    parser.add_argument("--target-clips-per-folder", type=int, default=0, help="0 means build every valid clip")
    parser.add_argument("--limit-folders", type=int, default=0)
    parser.add_argument("--folder-offset", type=int, default=0, help="0-based folder offset for quick follow-up scans")
    parser.add_argument("--episode-offset", type=int, default=0, help="0-based episode offset for quick follow-up scans")
    parser.add_argument("--shuffle-seed", type=int, default=None, help="Set for reproducible final clip order")
    parser.add_argument("--output-root", type=str, default=None, help="Override output root for this run")
    parser.add_argument("--work-root", type=str, default=None, help="Override work/cache root for this run")
    parser.add_argument(
        "--skip-keyword-view",
        action="store_true",
        help="Do not create the clips_by_keyword review folder after building clips",
    )
    parser.add_argument(
        "--export-keyword-view-only",
        action="store_true",
        help="Only rebuild clips_by_keyword for the selected output root",
    )
    parser.add_argument(
        "--exclude-existing-root",
        action="append",
        default=[],
        help="Do not reuse source ranges already present in this output root's manifests",
    )
    parser.add_argument(
        "--defer-rendered-spoken-validation",
        action="store_true",
        help="Build a larger candidate pool first; verify rendered keyword ASR later during final selection",
    )
    args = parser.parse_args()

    if args.output_root:
        OUTPUT_ROOT = resolve_project_path(args.output_root)
    if args.work_root:
        WORK_ROOT = resolve_project_path(args.work_root)
    if args.defer_rendered_spoken_validation:
        VERIFY_RENDERED_SPOKEN_BEFORE_POOL = False

    if args.export_keyword_view_only:
        export_keyword_clip_view(OUTPUT_ROOT)
        return

    if not CTA_VIDEO.exists():
        raise FileNotFoundError(CTA_VIDEO)

    excluded_source_scenes, excluded_source_ranges, excluded_source_windows = load_excluded_source_indexes(
        [resolve_project_path(path) for path in args.exclude_existing_root]
    )
    if args.exclude_existing_root:
        print(
            f"excluding existing sources: scenes={len(excluded_source_scenes)} "
            f"windows={len(excluded_source_windows)} roots={len(args.exclude_existing_root)}",
            flush=True,
        )

    summaries = []
    folders = DRAMA_FOLDERS[args.folder_offset :]
    if args.limit_folders:
        folders = folders[: args.limit_folders]
    for folder in folders:
        slug = safe_slug(folder)
        print(f"\n=== {slug} ===", flush=True)
        target_clip_count = args.target_clips_per_folder or None
        clips = build_clip_pool(
            folder,
            slug,
            target_clip_count,
            args.max_episodes or None,
            args.max_candidates_per_episode or None,
            args.episode_offset,
            excluded_source_scenes=excluded_source_scenes,
            excluded_source_ranges=excluded_source_ranges,
            excluded_source_windows=excluded_source_windows,
        )
        finals = build_final_videos(slug, clips, args.videos_per_folder, args.shuffle_seed)
        summary = {
            "folder": str(folder),
            "slug": slug,
            "clip_count": len(clips),
            "final_count": len(finals),
            "finals": [item["final"] for item in finals],
        }
        summaries.append(summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "batch_summary.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2))
    print(f"\nsummary: {OUTPUT_ROOT / 'batch_summary.json'}")
    if not args.skip_keyword_view:
        export_keyword_clip_view(OUTPUT_ROOT)


if __name__ == "__main__":
    ensure_accelerated_python()
    main()
