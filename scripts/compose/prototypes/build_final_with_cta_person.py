#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path


ROOT = Path("/Users/jaewon/Documents/Codex/2026-07-02/new-chat")
BASE_VIDEO = ROOT / "outputs/final_15_fullscreen_with_cta_black_side_banner/final_15_fullscreen_with_cta_black_side_banner.mp4"
PERSON_IMAGE = Path("/Users/jaewon/Downloads/cta_person.png")
RENDERER_SOURCE = ROOT / "work/final_with_cta_person/RenderPersonCTA.swift"
RENDERER = ROOT / "work/final_with_cta_person/render_person_cta"
WORK = ROOT / "work/final_with_cta_person"
OUT = ROOT / "outputs/final_15_fullscreen_with_cta_person"
OVERLAY = WORK / "person_cta_overlay.png"
FINAL = OUT / "final_15_fullscreen_with_cta_person.mp4"

AD_START = 3.0
AD_DURATION = 7.314286
AD_END = AD_START + AD_DURATION
CTA_LEAD_SECONDS = 1.0
CTA_TAIL_SECONDS = 1.0


def run(cmd):
    subprocess.run([str(part) for part in cmd], check=True)


def capture(cmd):
    return subprocess.check_output([str(part) for part in cmd], text=True).strip()


def duration(path):
    return float(capture(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path]))


def main():
    if not BASE_VIDEO.exists():
        raise FileNotFoundError(BASE_VIDEO)
    if not PERSON_IMAGE.exists():
        raise FileNotFoundError(PERSON_IMAGE)

    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    module_cache = WORK / "swift_module_cache"
    module_cache.mkdir(parents=True, exist_ok=True)

    run(["xcrun", "swiftc", "-module-cache-path", module_cache, RENDERER_SOURCE, "-o", RENDERER])
    run([RENDERER, PERSON_IMAGE, OVERLAY])

    cta_pre_start = max(0.0, AD_START - CTA_LEAD_SECONDS)
    cta_post_end = AD_END + CTA_TAIL_SECONDS
    enable_expr = (
        f"between(t\\,{cta_pre_start:.6f}\\,{AD_START:.6f})"
        f"+between(t\\,{AD_END:.6f}\\,{cta_post_end:.6f})"
    )
    run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", BASE_VIDEO,
            "-i", OVERLAY,
            "-filter_complex",
            f"[0:v][1:v]overlay=0:0:format=auto:enable='{enable_expr}',format=yuv420p,setsar=1[v]",
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
        "person_image": str(PERSON_IMAGE),
        "duration": duration(FINAL),
        "ad_start_seconds": AD_START,
        "ad_end_seconds": AD_END,
        "person_overlay_visible_when": (
            f"{cta_pre_start:.3f} <= t <= {AD_START:.3f} "
            f"or {AD_END:.3f} <= t <= {cta_post_end:.3f}"
        ),
        "person_position": {"x": 51, "bottom": 1519, "width": 310, "height": 310},
        "cta_card": {
            "x": 62,
            "bottom": 1502,
            "width": 960,
            "height": 344,
            "background": "transparent",
            "layout": "image 30%, text 70%",
        },
        "label": {"text": "koko AI", "style": "large black text with light outline on transparent background"},
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(FINAL)
    print(f"duration={manifest['duration']:.3f}")
    print(f"person_hidden_from={AD_START:.3f}_to={AD_END:.3f}")


if __name__ == "__main__":
    main()
