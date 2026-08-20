---
name: theme-to-short-video
description: Create complete Japanese short videos from only a user-provided theme using Codex-led planning, Imagegen source-image creation for Higgsfield, Higgsfield animation, VOICEVOX Engine startup and narration/dialogue wav generation, subtitle/telop burn-in, Remotion assembly, and FFmpeg export. Use when the user says a theme, topic, reference URL, or title and wants Codex to take it all the way to a finished vertical YouTube Shorts/TikTok/Reels-style video, including script, scene plan, Imagegen prompts and images, Higgsfield prompts and clips, VOICEVOX voice files, subtitles/telops, one-clip checks, final render, and QA.
---

# Theme To Short Video

## Core Behavior

Use this skill to run a one-stop short-video factory. If the user provides only a theme, choose sensible defaults and start production without asking for extra creative details.

Default output:

- Language: Japanese
- Format: vertical 9:16 short video
- Resolution: 1080x1920
- Duration: 58-60 seconds
- Frame rate: 30fps
- Structure: hook, context, 8-12 visual beats, punchy close
- Audio: VOICEVOX narration or dialogue, light BGM, concise effects
- Text: baked-in Japanese subtitle telops synced to VOICEVOX, plus optional short title/badge labels
- Visuals: Imagegen still images designed for Higgsfield, animated into video clips by Higgsfield, then assembled precisely in Remotion
- Final: mp4 in the current project's `outputs/` directory

Hard format rule: create videos in vertical 9:16. Use 1080x1920 for Imagegen source images and Remotion final renders. When submitting Higgsfield image-to-video jobs, set `aspect_ratio` to `9:16`. Treat user text such as `9;16` as `9:16`.

Keep the user's experience as "tell Codex the theme, then review the result." Codex should create the script, scene list, prompts, timeline files, VOICEVOX audio, baked-in subtitles/telops, render code, QA notes, and final handoff.

Visual pipeline contract:

```text
Imagegen still image -> Higgsfield image-to-video clip -> Remotion edit/render -> final mp4
```

Do not use Remotion as the primary tool for turning generated still images into animated scenes. Use Remotion to arrange Higgsfield clips, sync VOICEVOX audio, render subtitles, add safe zooms/crops, and repair timing or subtitle issues. When Remotion is unavailable or a single Higgsfield clip needs a fast check, use `scripts/compose_voicevox_telop.py` to produce a verified 9:16 mp4 with VOICEVOX audio and burned-in ASS subtitles.

## Required First Step

Read `references/production-workflow.md` before starting a video production run. It contains the complete one-shot workflow, default creative decisions, artifact checklist, Imagegen-to-Higgsfield source-image rules, VOICEVOX Engine startup and audio generation, Remotion assembly, and fallback behavior.

Before creating still images for Higgsfield, use the `imagegen` skill if available. Follow its built-in image generation path by default, then copy project-bound generated images from `$CODEX_HOME/generated_images/...` into the project's `images/imagegen_source/` folder.

Use `scripts/create_project.py` to create the standard working folders and initial manifest before generating assets.

Use `scripts/start_voicevox_engine.py` before VOICEVOX audio generation. Then use `scripts/generate_voicevox_audio.py` to create wav files from `scripts/voicevox_lines.tsv` whenever VOICEVOX Engine is reachable. Use `scripts/compose_voicevox_telop.py` for tested one-clip checks and FFmpeg fallback renders that combine a Higgsfield mp4, VOICEVOX wav, and subtitle/telop file.

## One-Shot Defaults

When the user only gives a theme:

1. Infer the best video type:
   - Historical, food, money, culture, science, or trivia theme: use narrator-led documentary short.
   - Everyday situation, relationship, school, work, or family theme: use two-character comedy skit.
   - Product, service, offer, or tutorial theme: use explainer/demo short.
2. Choose a clear title and a 1-sentence premise.
3. Write a 58-60 second script.
4. Split speech into VOICEVOX line IDs.
5. Create 10-14 scenes for narrator-led shorts or 6-9 scenes for dialogue shorts.
6. Generate Imagegen prompts and still source images for each scene.
7. Use Higgsfield to turn each generated image into a scene video clip.
8. After at least one Higgsfield clip exists, create a one-clip check with VOICEVOX narration and burned-in subtitles/telops.
9. Assemble Higgsfield clips, subtitles, and VOICEVOX audio in Remotion, then render and inspect with Remotion/FFmpeg.

Do not stop at a proposal unless a required external tool or permission is unavailable.

## Approval Policy

The skill is designed for speed, but do not silently spend Higgsfield credits or publish online.

Ask for a short confirmation only before:

- Generating paid/credit-consuming Higgsfield clips.
- Publishing or uploading the final video.
- Using a copyrighted reference beyond extracting reusable structure.

For local planning, script writing, prompt generation, VOICEVOX file preparation, Remotion code, preview assembly, QA, and deterministic repair, continue without waiting.

## Copyright And Reference Safety

Use reference videos or channels only to extract structure, pacing, visual grammar, and production constraints. Do not copy exact scripts, titles, thumbnails, characters, branding, watermarks, or distinctive identity.

If a reference URL is provided, inspect what can be legally and practically inspected, then convert observations into an original production plan.

## Completion Report

Finish with:

- Final video path.
- Runtime, resolution, frame rate, and codec if available.
- Imagegen source-image folder and Higgsfield prompt folder.
- Whether Higgsfield credits were used.
- Whether VOICEVOX Engine started automatically or required a manual launch.
- Any manual user step still required, such as uploading Higgsfield outputs when direct access was unavailable.
- A compact note on what was generated: script, Imagegen prompts/images, Higgsfield prompts/clips, VOICEVOX line list/wav files, subtitle/telop files, one-clip checks, Remotion project, final mp4.
