# social-clip

**social-clip** is a command-line video formatting tool that automatically reformats any source video for every major social media platform. social-clip can correct aspect ratio, resolution, bitrate, duration cap, text overlay, and audio normalization in a single command.

## Core Functionality

The tool accepts any video file and exports platform-ready copies using OpenShot's Python library (`libopenshot`). This project was built to demonstrate a working understanding of OpenShot's core primitives `Timeline`, `Clip`, `Keyframe`, and `FFmpegWriter`.

Each export applies a "cover" scale so the video fills the target frame without black bars and centers the clip on the canvas. A text overlay can be added, rendered as a fade-in/fade-out animated caption. Audio is automatically level-matched to the broadcast standard used by YouTube and Spotify. Exports all six platforms at once into an output directory if requested.

## Supported Platforms

The tool ships presets for YouTube (1920×1080, 16:9), TikTok and Instagram Reels (1080×1920, 9:16, capped at 3 minutes), Instagram Feed (1080×1080, 1:1, capped at 60 seconds), Instagram and Facebook Story (1080×1920, 9:16, capped at 15 seconds), Twitter/X (1280×720, 16:9, capped at 2 m 20 s), and LinkedIn (1920×1080, 16:9, capped at 10 minutes).

Platform specs are defined in `formatter/presets.py`. Running `python main.py --list-platforms` prints the full table.

## Technical Architecture

The project is written in Python and built entirely on the OpenShot `libopenshot` library. A `VideoFormatter` class in `formatter/core.py` manages an OpenShot `Timeline` and one or more `Clip` objects placed on numbered layers, Layer 1 for the video, layer 2 for the text overlay. This mirrors the model used inside the OpenShot desktop editor.

All transform and volume properties are expressed as `Keyframe` objects, OpenShot's core animation primitive, even when the value is static. Text overlays and audio normalization are handled separately in `formatter/effects.py`. Encoded output is written frame-by-frame through an `FFmpegWriter`, using standard (H.264) compression at a bitrate determined by whichever platform is being exported to.

## Setup Requirements

Install OpenShot from [openshot.org/download](https://www.openshot.org/download/), which bundles the `libopenshot` Python bindings. Before running the tool, add the bundled Python path to `PYTHONPATH`:

- **Windows:** `C:\Program Files\OpenShot Video Editor\lib\python3`
- **macOS:** inside the `.app` bundle
- **Linux:** inside the AppImage mount

No additional packages are required. Once the path is set, run `python main.py input.mp4 --platform tiktok --output out.mp4` to export a single clip, change --platform ____ to request certain platform or pass `--all` with `--output-dir` to export every platform at once.

**Developer:** Ryan Chisholm
