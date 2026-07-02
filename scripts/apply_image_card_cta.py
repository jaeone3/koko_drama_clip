#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER_SOURCE = ROOT / "scripts/render_image_card_overlay.swift"


def run(cmd):
    subprocess.run([str(part) for part in cmd], check=True)


def capture(cmd):
    return subprocess.check_output([str(part) for part in cmd], text=True).strip()


def ffprobe_float(path, field):
    return float(
        capture(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                f"format={field}",
                "-of",
                "default=nw=1:nk=1",
                path,
            ]
        )
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Add a transparent 3:7 image/text CTA card near the ad banner area."
    )
    parser.add_argument("--input", required=True, help="Input video path")
    parser.add_argument("--person", required=True, help="Transparent PNG used on the left side")
    parser.add_argument("--output", required=True, help="Output video path")
    parser.add_argument("--ad-start", type=float, default=3.0, help="Ad start time in seconds")
    parser.add_argument("--ad-duration", type=float, default=7.314286, help="Ad duration in seconds")
    parser.add_argument("--lead", type=float, default=1.0, help="Show CTA this many seconds before ad")
    parser.add_argument("--tail", type=float, default=1.0, help="Show CTA this many seconds after ad")
    parser.add_argument("--canvas-width", type=int, default=1080)
    parser.add_argument("--canvas-height", type=int, default=1920)
    parser.add_argument("--card-x", type=int, default=62, help="CTA x position, top-left coordinates")
    parser.add_argument("--card-y", type=int, default=74, help="CTA y position, top-left coordinates")
    parser.add_argument("--card-width", type=int, default=960)
    parser.add_argument("--card-height", type=int, default=344)
    parser.add_argument("--video-bitrate", default="12M")
    parser.add_argument("--maxrate", default="16M")
    parser.add_argument("--bufsize", default="24M")
    return parser.parse_args()


def main():
    args = parse_args()
    input_video = Path(args.input).expanduser().resolve()
    person_image = Path(args.person).expanduser().resolve()
    output_video = Path(args.output).expanduser().resolve()

    if not input_video.exists():
        raise FileNotFoundError(input_video)
    if not person_image.exists():
        raise FileNotFoundError(person_image)

    output_video.parent.mkdir(parents=True, exist_ok=True)
    work_dir = output_video.parent / ".image_card_cta_work"
    work_dir.mkdir(parents=True, exist_ok=True)

    renderer = work_dir / "render_image_card_overlay"
    overlay = work_dir / "image_card_cta_overlay.png"
    module_cache = work_dir / "swift_module_cache"
    module_cache.mkdir(parents=True, exist_ok=True)

    run(["xcrun", "swiftc", "-module-cache-path", module_cache, RENDERER_SOURCE, "-o", renderer])
    run(
        [
            renderer,
            person_image,
            overlay,
            args.canvas_width,
            args.canvas_height,
            args.card_x,
            args.card_y,
            args.card_width,
            args.card_height,
        ]
    )

    ad_end = args.ad_start + args.ad_duration
    pre_start = max(0.0, args.ad_start - args.lead)
    post_end = ad_end + args.tail
    enable_expr = (
        f"between(t\\,{pre_start:.6f}\\,{args.ad_start:.6f})"
        f"+between(t\\,{ad_end:.6f}\\,{post_end:.6f})"
    )

    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            input_video,
            "-i",
            overlay,
            "-filter_complex",
            f"[0:v][1:v]overlay=0:0:format=auto:enable='{enable_expr}',format=yuv420p,setsar=1[v]",
            "-map",
            "[v]",
            "-map",
            "0:a:0?",
            "-c:v",
            "libx264",
            "-profile:v",
            "main",
            "-preset",
            "veryslow",
            "-b:v",
            args.video_bitrate,
            "-maxrate",
            args.maxrate,
            "-bufsize",
            args.bufsize,
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            output_video,
        ]
    )

    manifest = {
        "input": str(input_video),
        "person": str(person_image),
        "output": str(output_video),
        "duration": ffprobe_float(output_video, "duration"),
        "ad_start": args.ad_start,
        "ad_end": ad_end,
        "visible_ranges": [[pre_start, args.ad_start], [ad_end, post_end]],
        "card": {
            "x": args.card_x,
            "y": args.card_y,
            "width": args.card_width,
            "height": args.card_height,
            "layout": "left image 30%, right text 70%",
            "background": "transparent",
        },
    }
    manifest_path = output_video.with_suffix(".image_card_cta.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(output_video)
    print(f"visible={pre_start:.3f}-{args.ad_start:.3f},{ad_end:.3f}-{post_end:.3f}")


if __name__ == "__main__":
    main()
