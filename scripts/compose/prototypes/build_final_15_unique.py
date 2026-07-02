#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path


ROOT = Path("/Users/jaewon/Documents/Codex/2026-07-02/new-chat")
RENDERER_SOURCE = ROOT / "work/subtitle_style_test/RenderSubtitleOverlay.swift"
RENDERER = ROOT / "work/subtitle_style_test/render_subtitle_overlay"
WORK = ROOT / "work/final_15_unique_video"
OVERLAYS = WORK / "overlays"
SUBTITLED = WORK / "subtitled"
OUT = ROOT / "outputs/final_15_unique_video"

CLIPS = [
    {
        "src": Path("/Users/jaewon/Desktop/koko_drama/dramas/149안녕/0.mp4"),
        "korean": "안녕",
        "romanization": "[an·nyeong]",
        "english": "Hi.",
        "label": "Casual",
    },
    {
        "src": Path("/Users/jaewon/Desktop/koko_drama/dramas/108뭐야/0.mp4"),
        "korean": "뭐야",
        "romanization": "[mwo·ya]",
        "english": "What?",
        "label": "Casual",
    },
    {
        "src": Path("/Users/jaewon/Desktop/koko_drama/dramas/78진짜/0.mp4"),
        "korean": "진짜",
        "romanization": "[jin·jja]",
        "english": "Really?",
        "label": "Casual",
    },
    {
        "src": Path("/Users/jaewon/Desktop/koko_drama/dramas/185여기요/0.mp4"),
        "korean": "여기요",
        "romanization": "[yeo·gi·yo]",
        "english": "Excuse me.",
        "label": "Polite",
    },
    {
        "src": Path("/Users/jaewon/Desktop/koko_drama/dramas/147당연하지/0.mp4"),
        "korean": "당연하지",
        "romanization": "[dang·yeon·ha·ji]",
        "english": "Of course.",
        "label": "Casual",
    },
    {
        "src": Path("/Users/jaewon/Desktop/koko_drama/dramas/178감사합니다/0.mp4"),
        "korean": "감사합니다",
        "romanization": "[gam·sa·ham·ni·da]",
        "english": "Thank you.",
        "label": "Polite",
    },
    {
        "src": Path("/Users/jaewon/Desktop/koko_drama/dramas/191알았어요/0.mp4"),
        "korean": "알았어요",
        "romanization": "[a·ra·sseo·yo]",
        "english": "Okay.",
        "label": "Polite",
    },
    {
        "src": Path("/Users/jaewon/Desktop/koko_drama/dramas/122그래요/0.mp4"),
        "korean": "그래요",
        "romanization": "[geu·rae·yo]",
        "english": "Sure.",
        "label": "Polite",
    },
    {
        "src": Path("/Users/jaewon/Desktop/koko_drama/dramas/188주세요/0.mp4"),
        "korean": "주세요",
        "romanization": "[ju·se·yo]",
        "english": "Please.",
        "label": "Polite",
    },
    {
        "src": Path("/Users/jaewon/Desktop/koko_drama/dramas/153미안해/0.mp4"),
        "korean": "미안해",
        "romanization": "[mi·an·hae]",
        "english": "Sorry.",
        "label": "Casual",
    },
]


def run(cmd):
    subprocess.run([str(part) for part in cmd], check=True)


def capture(cmd):
    return subprocess.check_output([str(part) for part in cmd], text=True).strip()


def duration(path):
    return float(capture(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path]))


def main():
    korean_terms = [item["korean"] for item in CLIPS]
    duplicates = sorted({term for term in korean_terms if korean_terms.count(term) > 1})
    if duplicates:
        raise ValueError(f"duplicate korean terms: {duplicates}")

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
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", item["src"], "-i", overlay,
                "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p,setsar=1[v]",
                "-map", "[v]", "-map", "0:a:0", "-r", "30",
                "-c:v", "libx264", "-profile:v", "main", "-preset", "veryslow",
                "-b:v", "12M", "-maxrate", "16M", "-bufsize", "24M",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
                rendered,
            ]
        )
        subtitled_paths.append(rendered)
        manifest.append({**item, "src": str(item["src"]), "subtitled": str(rendered), "duration": duration(rendered)})

    final_path = OUT / "final_15_unique_a0_drama.mp4"
    inputs = []
    concat_parts = []
    for i, path in enumerate(subtitled_paths):
        inputs.extend(["-i", path])
        concat_parts.append(f"[{i}:v][{i}:a]")
    filter_complex = "".join(concat_parts) + f"concat=n={len(subtitled_paths)}:v=1:a=1[v][a]"
    run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-profile:v", "main", "-preset", "veryslow",
            "-b:v", "12M", "-maxrate", "16M", "-bufsize", "24M",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
            final_path,
        ]
    )
    final_duration = duration(final_path)
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "final": str(final_path),
                "duration": final_duration,
                "clip_count": len(manifest),
                "unique_korean_count": len(set(korean_terms)),
                "clips": manifest,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(final_path)
    print(f"duration={final_duration:.3f}")
    print(f"unique_korean_count={len(set(korean_terms))}")


if __name__ == "__main__":
    main()
