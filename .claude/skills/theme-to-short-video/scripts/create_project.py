#!/usr/bin/env python3
"""Create the standard short-video project folders, manifest, and seed files."""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

FOLDERS = [
    "scripts",
    "images/imagegen_source",
    "images/contact_sheets",
    "prompts/imagegen",
    "prompts/higgsfield",
    "audio/voicevox",
    "video/higgsfield",
    "video/checks",
    "subtitles/ass",
    "remotion",
    "qa",
    "outputs",
]

DEFAULT_SPEAKERS = {
    "_note": "VOICEVOX speaker ids. Verify against http://127.0.0.1:50021/speakers before a run.",
    "narrator": 3,
    "character_a": 8,
    "character_b": 2,
    "system": 13,
}

PREMISE_TEMPLATE = """Title:
Premise:
Viewer promise:
Opening hook:
Ending beat:
Avoid copying:
"""

SCENE_PLAN_TEMPLATE = """# Scene Plan

| scene_id | time_range | visual | motion | audio_line_ids | caption | purpose | imagegen_prompt_file | image_file | higgsfield_clip_file | higgsfield_prompt_file |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
"""

LINES_HEADER = "line_id\tspeaker\tstart\tend\ttext\tdirection\n"
CAPTIONS_HEADER = "caption_id\tstart\tend\ttext\tstyle\n"


def slugify(theme: str) -> str:
    slug = re.sub(r"[^\w぀-ヿ一-鿿-]+", "-", theme, flags=re.UNICODE)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:40] or "short-video"


def fetch_speakers(base_url: str) -> dict[str, object] | None:
    try:
        with urllib.request.urlopen(f"{base_url}/speakers", timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    catalog = [
        {
            "name": speaker.get("name"),
            "styles": [
                {"style": style.get("name"), "id": style.get("id")}
                for style in speaker.get("styles", [])
            ],
        }
        for speaker in data
    ]
    return {**DEFAULT_SPEAKERS, "_catalog": catalog}


def write_if_absent(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a short-video project folder.")
    parser.add_argument("theme", help="Video theme, used for the folder name and manifest")
    parser.add_argument("--root", default=".", help="Parent folder for the new project")
    parser.add_argument("--name", default="", help="Project folder name override")
    parser.add_argument("--duration", type=float, default=59.0, help="Target duration in seconds")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--format", default="narrator_documentary", help="narrator_documentary, dialogue_skit, explainer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50021)
    parser.add_argument("--force", action="store_true", help="Overwrite existing seed files")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder_name = args.name or f"{stamp}_{slugify(args.theme)}"
    project = (Path(args.root).expanduser().resolve() / folder_name)
    for folder in FOLDERS:
        (project / folder).mkdir(parents=True, exist_ok=True)

    speakers = fetch_speakers(f"http://{args.host}:{args.port}") or dict(DEFAULT_SPEAKERS)

    manifest = {
        "theme": args.theme,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "language": "ja",
        "format": args.format,
        "aspect_ratio": "9:16",
        "width": args.width,
        "height": args.height,
        "fps": args.fps,
        "target_duration_seconds": args.duration,
        "pipeline": ["imagegen", "higgsfield", "voicevox", "remotion", "ffmpeg"],
        "status": {
            "premise": "todo",
            "script": "todo",
            "scene_plan": "todo",
            "imagegen": "todo",
            "voicevox": "todo",
            "higgsfield": "todo",
            "one_clip_check": "todo",
            "assembly": "todo",
            "qa": "todo",
        },
        "outputs": {"final": "outputs/final.mp4"},
    }

    write_if_absent(project / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", args.force)
    write_if_absent(project / "scripts/premise.md", PREMISE_TEMPLATE, args.force)
    write_if_absent(project / "scripts/narration.md", f"# {args.theme}\n\n", args.force)
    write_if_absent(project / "scripts/voicevox_lines.tsv", LINES_HEADER, args.force)
    write_if_absent(project / "scripts/captions.tsv", CAPTIONS_HEADER, args.force)
    write_if_absent(project / "scripts/scene_plan.md", SCENE_PLAN_TEMPLATE, args.force)
    write_if_absent(project / "scripts/timeline.json", json.dumps({"fps": args.fps, "width": args.width, "height": args.height, "scenes": []}, ensure_ascii=False, indent=2) + "\n", args.force)
    write_if_absent(project / "scripts/voicevox_speakers.json", json.dumps(speakers, ensure_ascii=False, indent=2) + "\n", args.force)

    print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
