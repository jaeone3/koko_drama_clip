# koko_drama_clip

Small utilities for composing Koko drama vocabulary clips.

## Image Card CTA Overlay

This repository currently contains the standalone image-card CTA overlay step.

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
