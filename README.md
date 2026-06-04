# social-clip

**social-clip** is a command-line video formatting tool that automatically reformats any source video for every major social media platform — correct aspect ratio, resolution, bitrate, duration cap, text overlay, and audio normalization — in a single command.

## Core Functionality

The tool accepts any video file and exports platform-ready copies using OpenShot's Python library (`libopenshot`). Each export applies a "cover" scale so the video fills the target frame without black bars, centres the clip on the canvas, and optionally trims the clip to a start/end timestamp. A text overlay can be added — rendered as a fade-in/fade-out SVG caption — and audio is automatically level-matched to the -14 LUFS broadcast standard used by YouTube and Spotify. Batch mode exports all six platforms at once into an output directory.

## Supported Platforms

The tool ships presets for YouTube (1920×1080, 16:9), TikTok and Instagram Reels (1080×1920, 9:16, capped at 3 minutes), Instagram Feed (1080×1080, 1:1, capped at 60 seconds), Instagram and Facebook Story (1080×1920, 9:16, capped at 15 seconds), Twitter/X (1280×720, 16:9, capped at 2 m 20 s), and LinkedIn (1920×1080, 16:9, capped at 10 minutes). Running `python main.py --list-platforms` prints the full table.

## Technical Architecture

The project is written in Python and built entirely on the OpenShot `libopenshot` bindings. A `VideoFormatter` class manages an OpenShot `Timeline` (the master canvas) and one or more `Clip` objects placed on numbered layers — layer 1 for the video, layer 2 for the text overlay — mirroring the track-stack model used inside the OpenShot desktop editor. All transform and volume properties are expressed as `Keyframe` objects, OpenShot's core animation primitive, even when the value is static. Encoded output is written frame-by-frame through an `FFmpegWriter` configured with H.264 video and AAC audio at platform-appropriate bitrates.

## Setup Requirements

Install OpenShot from [openshot.org/download](https://www.openshot.org/download/), which bundles the `libopenshot` Python bindings. Add the bundled Python path to `PYTHONPATH` before running the tool — on Windows this is typically `C:\Program Files\OpenShot Video Editor\lib\python3`, on macOS it is inside the `.app` bundle, and on Linux it is inside the AppImage mount. No additional PyPI packages are required. Once the path is set, run `python main.py input.mp4 --platform tiktok --output out.mp4` to export a single clip, or pass `--all` with `--output-dir` to batch-export every platform at once.

**Developer:** Ry Chisholm
