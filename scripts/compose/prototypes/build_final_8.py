#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path


ROOT = Path("/Users/jaewon/Documents/Codex/2026-07-02/new-chat")
RENDERER_SOURCE = ROOT / "work/subtitle_style_test/RenderSubtitleOverlay.swift"
RENDERER = ROOT / "work/subtitle_style_test/render_subtitle_overlay"
WORK = ROOT / "work/final_8_video"
OVERLAYS = WORK / "overlays"
SUBTITLED = WORK / "subtitled"
OUT = ROOT / "outputs/final_8_video"

CLIPS = [
    {
        "src": ROOT / "outputs/current_2char_ultra_quality/안녕_안녕_001.mp4",
        "korean": "안녕",
        "romanization": "[an·nyeong]",
        "english": "Hi.",
        "label": "Casual",
    },
    {
        "src": ROOT / "outputs/current_2char_ultra_quality/뭐야_뭐야_001.mp4",
        "korean": "뭐야",
        "romanization": "[mwo·ya]",
        "english": "What?",
        "label": "Casual",
    },
    {
        "src": ROOT / "outputs/final_8_raw_clips/지금_지금_001.mp4",
        "korean": "지금",
        "romanization": "[ji·geum]",
        "english": "Now.",
        "label": "Casual",
    },
    {
        "src": ROOT / "outputs/final_8_raw_clips/진짜_진짜_001.mp4",
        "korean": "진짜",
        "romanization": "[jin·jja]",
        "english": "Really?",
        "label": "Casual",
    },
    {
        "src": ROOT / "outputs/final_8_raw_clips/좋아요_좋아요_001.mp4",
        "korean": "좋아요",
        "romanization": "[jo·a·yo]",
        "english": "Good.",
        "label": "Polite",
    },
    {
        "src": ROOT / "outputs/final_8_raw_clips/여기요_여기요_001.mp4",
        "korean": "여기요",
        "romanization": "[yeo·gi·yo]",
        "english": "Excuse me.",
        "label": "Polite",
    },
    {
        "src": ROOT / "outputs/current_8_clip_test/당연하지_당연하지_001.mp4",
        "korean": "당연하지",
        "romanization": "[dang·yeon·ha·ji]",
        "english": "Of course.",
        "label": "Casual",
    },
    {
        "src": ROOT / "outputs/final_8_raw_clips/감사합니다_감사합니다_001.mp4",
        "korean": "감사합니다",
        "romanization": "[gam·sa·ham·ni·da]",
        "english": "Thank you.",
        "label": "Polite",
    },
]


def run(cmd):
    subprocess.run([str(part) for part in cmd], check=True)


def main():
    OVERLAYS.mkdir(parents=True, exist_ok=True)
    SUBTITLED.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    module_cache = WORK / "swift_module_cache"
    module_cache.mkdir(parents=True, exist_ok=True)

    run(["xcrun", "swiftc", "-module-cache-path", module_cache, RENDERER_SOURCE, "-o", RENDERER])

    subtitled_paths = []
    manifest = []
    for index, item in enumerate(CLIPS, start=1):
        if not item["src"].exists():
            raise FileNotFoundError(item["src"])
        overlay = OVERLAYS / f"{index:02d}_{item['korean']}.png"
        rendered = SUBTITLED / f"{index:02d}_{item['korean']}.mp4"
        run([RENDERER, overlay, item["korean"], item["romanization"], item["english"], item["label"]])
        run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                item["src"],
                "-i",
                overlay,
                "-filter_complex",
                "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]",
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
                "veryslow",
                "-b:v",
                "12M",
                "-maxrate",
                "16M",
                "-bufsize",
                "24M",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                rendered,
            ]
        )
        subtitled_paths.append(rendered)
        manifest.append({**item, "src": str(item["src"]), "subtitled": str(rendered)})

    final_path = OUT / "final_8_a0_drama.mp4"
    inputs = []
    concat_parts = []
    for i, path in enumerate(subtitled_paths):
        inputs.extend(["-i", path])
        concat_parts.append(f"[{i}:v][{i}:a]")
    filter_complex = "".join(concat_parts) + f"concat=n={len(subtitled_paths)}:v=1:a=1[v][a]"
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
            "veryslow",
            "-b:v",
            "12M",
            "-maxrate",
            "16M",
            "-bufsize",
            "24M",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            final_path,
        ]
    )

    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(final_path)


if __name__ == "__main__":
    main()
