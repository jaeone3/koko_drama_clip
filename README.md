# koko_drama_clip

Small utilities for composing Koko drama vocabulary clips.

## Repository Layout

- `scripts/extract/`: keyword and A0-level drama clip extraction prototypes
- `scripts/analyze/`: reference clip and frame-sheet analysis helpers
- `scripts/render/`: Swift renderers used for subtitle/face/overlay experiments
- `scripts/compose/prototypes/`: final-video composition prototypes from the current experiments
- `scripts/apply_image_card_cta.py`: reusable CTA image-card overlay step
- `scripts/render_image_card_overlay.swift`: transparent CTA overlay PNG renderer

Generated videos, extracted frames, transcripts, and local media assets are intentionally not committed.

## Image Card CTA Overlay

The cleanest reusable script right now is the standalone image-card CTA overlay step.

It creates a transparent overlay with:

- image/text horizontal layout
- left image area: 30%
- right text area: 70%
- no background panel
- default top banner placement for a 1080x1920 vertical video
- default visibility from 1 second before the ad to ad start, and from ad end to 1 second after ad end

### Requirements

- macOS
- `xcrun swiftc`
- `ffmpeg`
- `ffprobe`

### Usage

```bash
python3 scripts/apply_image_card_cta.py \
  --input /path/to/input.mp4 \
  --person /path/to/cta_person.png \
  --output /path/to/output.mp4 \
  --ad-start 3.0 \
  --ad-duration 7.314286
```

## Clip Extraction Prototypes

The extraction scripts are experimental but contain the current clip-selection rules:

- avoid cutting in the middle of Korean surface forms
- add natural lead/tail padding around the spoken keyword
- prefer clips where the speaking face is visible and centered
- support short A0-style expressions and polite/casual label metadata

Primary script:

```bash
python3 scripts/extract/a0_refined_clipper.py
```

Older/smaller variants are kept in the same folder for reference:

- `scripts/extract/a0_subtitle_clipper.py`
- `scripts/extract/keyword_clipper.py`

## Composition Prototypes

The scripts in `scripts/compose/prototypes/` are snapshots of the current composition experiments.
Some of them still contain local absolute paths from the test environment, so treat them as reference implementations
until they are converted into fully parameterized CLI tools.

Default card geometry for a 1080x1920 video:

- `x=62`
- `y=74`
- `width=960`
- `height=344`

Override those values with:

```bash
python3 scripts/apply_image_card_cta.py \
  --input /path/to/input.mp4 \
  --person /path/to/cta_person.png \
  --output /path/to/output.mp4 \
  --card-x 62 \
  --card-y 74 \
  --card-width 960 \
  --card-height 344
```
