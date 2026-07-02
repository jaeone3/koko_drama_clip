#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path


ROOT = Path("/Users/jaewon/Documents/Codex/2026-07-02/new-chat")
BASE_VIDEO = ROOT / "outputs/final_15_original_only_video/final_15_original_only_a0_drama.mp4"
CTA_VIDEO = Path("/Users/jaewon/Downloads/cta_video.mp4")
OUT = ROOT / "outputs/final_15_with_cta_stretched_banner"
FINAL = OUT / "final_15_original_only_with_cta_stretched_banner.mp4"

AD_START = 3.0
AD_WIDTH = 1080
AD_HEIGHT = 480
AD_TOP = 0


def run(cmd):
    subprocess.run([str(part) for part in cmd], check=True)


def capture(cmd):
    return subprocess.check_output([str(part) for part in cmd], text=True).strip()


def duration(path):
    return float(capture(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path]))


def main():
    if not BASE_VIDEO.exists():
        raise FileNotFoundError(BASE_VIDEO)
    if not CTA_VIDEO.exists():
        raise FileNotFoundError(CTA_VIDEO)

    OUT.mkdir(parents=True, exist_ok=True)

    filter_complex = (
        f"[1:v]scale={AD_WIDTH}:{AD_HEIGHT}:flags=lanczos,"
        f"setpts=PTS-STARTPTS+{AD_START}/TB[ad];"
        f"[0:v][ad]overlay=x=0:y={AD_TOP}:"
        f"enable='gte(t,{AD_START})':eof_action=pass:format=auto,"
        "format=yuv420p,setsar=1[v]"
    )

    run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", BASE_VIDEO,
            "-i", CTA_VIDEO,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "0:a:0",
            "-c:v", "libx264", "-profile:v", "main", "-preset", "veryslow",
            "-b:v", "12M", "-maxrate", "16M", "-bufsize", "24M",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            FINAL,
        ]
    )

    manifest = {
        "final": str(FINAL),
        "base_video": str(BASE_VIDEO),
        "cta_video": str(CTA_VIDEO),
        "duration": duration(FINAL),
        "base_duration": duration(BASE_VIDEO),
        "cta_duration": duration(CTA_VIDEO),
        "cta_audio_used": False,
        "cta_start_seconds": AD_START,
        "cta_position": {"x": 0, "top": AD_TOP},
        "cta_size": {"width": AD_WIDTH, "height": AD_HEIGHT},
        "cta_screen_height_ratio": AD_HEIGHT / 1920,
        "layout": "aspect-distorted full-width top banner, no crop, no background fill",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(FINAL)
    print(f"duration={manifest['duration']:.3f}")
    print(f"cta_start={AD_START:.3f}")
    print(f"cta_size={AD_WIDTH}x{AD_HEIGHT}")


if __name__ == "__main__":
    main()
