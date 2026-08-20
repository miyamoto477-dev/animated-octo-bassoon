#!/usr/bin/env python3
"""Create the standard folder structure for a Codex-led short-video project."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


def make_slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return slug[:48] or "short-video"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a short-video project scaffold.")
    parser.add_argument("theme", help="Video theme or topic")
    parser.add_argument("--root", default=".", help="Directory where the project folder will be created")
    parser.add_argument("--name", help="Optional project folder name")
    parser.add_argument("--duration", type=int, default=60, help="Target duration in seconds")
    parser.add_argument("--format", default="vertical-9x16", help="Target format label")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    project_name = args.name or f"{stamp}-{make_slug(args.theme)}"
    project = Path(args.root).expanduser().resolve() / project_name

    dirs = [
        "scripts",
        "prompts/imagegen",
        "prompts/higgsfield",
        "images/imagegen_source",
        "images/contact_sheets",
        "audio/voicevox",
        "video/higgsfield",
        "video/checks",
        "subtitles/ass",
        "remotion",
        "qa",
        "outputs",
    ]
    for rel in dirs:
        (project / rel).mkdir(parents=True, exist_ok=True)

    manifest = {
        "theme": args.theme,
        "target_duration_seconds": args.duration,
        "format": args.format,
        "resolution": "1080x1920" if args.format == "vertical-9x16" else "1280x720",
        "frame_rate": 30,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "initialized",
    }
    (project / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    placeholders = {
        "scripts/premise.md": "# Premise\n\n",
        "scripts/narration.md": "# Narration\n\n",
        "scripts/scene_plan.md": "# Scene Plan\n\n",
        "scripts/voicevox_lines.tsv": "line_id\tspeaker\tstart\tend\ttext\tdirection\n",
        "scripts/captions.tsv": "caption_id\tstart\tend\ttext\tstyle\n",
        "scripts/voicevox_speakers.json": '{\n  "default_speaker_id": 3,\n  "speaker_map": {\n    "narrator": 3,\n    "character_a": 3,\n    "character_b": 3,\n    "ai": 3\n  }\n}\n',
        "scripts/timeline.json": "[]\n",
        "prompts/imagegen/scene_01.md": "# Imagegen Prompt: scene_01\n\n",
        "prompts/higgsfield/scene_01.md": "# Higgsfield Motion Prompt: scene_01\n\nSource image: images/imagegen_source/scene_01.png\n",
        "subtitles/ass/scene_01.ass": "",
        "qa/final_check.md": "# Final Check\n\n",
    }
    for rel, content in placeholders.items():
        path = project / rel
        if not path.exists():
            path.write_text(content, encoding="utf-8")

    print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
