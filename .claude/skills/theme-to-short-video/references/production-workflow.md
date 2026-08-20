# Production Workflow

## Overview

Turn one theme into a finished short video. Prefer action over questions. The default is a Japanese 58-60 second vertical short using Codex, Imagegen, Higgsfield, VOICEVOX, Remotion, and FFmpeg.

Primary visual pipeline:

```text
Imagegen creates still source images.
Higgsfield animates those images into scene clips.
Remotion assembles the Higgsfield clips with VOICEVOX audio, subtitles, timing, repairs, and final render.
```

Do not make Remotion the primary animation generator for Imagegen stills. Remotion may use still images only for temporary previews, freeze-frame repairs, overlays, crops, zooms, or fallback placeholders when a Higgsfield clip is unavailable.

Hard format rule:

- Always create this skill's videos as vertical 9:16 unless the user explicitly asks to change the skill itself.
- Use 1080x1920 for Imagegen source images and Remotion final renders.
- Set Higgsfield video generation `aspect_ratio` to `9:16`.
- If a Higgsfield model returns 720x1280, keep it as a valid 9:16 source clip and upscale/fit it to 1080x1920 in Remotion.
- Treat `9;16` in user text as a typo for `9:16`.

## Standard Project Setup

Run:

```bash
python scripts/create_project.py "THEME" --root WORKSPACE_OR_OUTPUT_PARENT
```

Create or update these files during production:

```text
project/
  manifest.json
  scripts/
    premise.md
    narration.md
    voicevox_lines.tsv
    voicevox_speakers.json
    scene_plan.md
    timeline.json
    captions.tsv
  images/
    imagegen_source/
    contact_sheets/
  prompts/
    imagegen/
      scene_01.md
    higgsfield/
      scene_01.md
  audio/
    voicevox/
  video/
    higgsfield/
    checks/
  subtitles/
    ass/
  remotion/
  qa/
  outputs/
```

## Default Creative Decision Tree

Choose the format from the theme:

| Theme type | Format | Scene count | Voice |
| --- | --- | --- | --- |
| History, culture, food, trivia | Narrator-led visual documentary | 10-14 | 1 narrator |
| Everyday absurd situation | Two-character anime skit | 6-9 | 2-3 voices |
| How-to, product, offer | Explainer/demo | 8-12 | 1 narrator + optional UI labels |
| Unknown | Narrator-led documentary | 10-12 | 1 narrator |

Default style for a historical or trivia short:

```text
Vertical 9:16, Japanese illustrated documentary, bold anime/ukiyo-e-inspired composition,
high-contrast captions, fast cuts, close-ups of hands/objects, strong opening hook,
lightly exaggerated narration, no direct copying from references.
```

Default style for a dialogue skit:

```text
Vertical 9:16, limited-animation anime, 2 characters,
simple fixed setting, clear left/right character positions, understated acting,
humor from premise and timing, Remotion controls exact mouth/subtitle timing.
```

## Production Pass

### 1. Theme Intake

If the user gives only a theme, infer:

- Title
- Audience
- Format
- Tone
- Duration
- Visual style
- Voice type
- Any obvious research needs

If facts could materially affect the script, browse or ask for source material. Do not invent current claims, prices, laws, or public statistics.

### 2. Premise And Hook

Create `scripts/premise.md`:

```text
Title:
Premise:
Viewer promise:
Opening hook:
Ending beat:
Avoid copying:
```

The hook must make the topic clear within the first 3 seconds.

### 3. Script

Create `scripts/narration.md` or dialogue script.

For a 58-60 second narrator-led video:

- 330-430 Japanese characters as a starting range.
- 11-14 short VOICEVOX lines.
- One idea per line.
- Add 0.1-0.25 second pause before surprise, twist, or punchline.
- Avoid long clauses that create unreadable subtitles.

For a 60-90 second dialogue skit:

- 6-9 scenes.
- 2-3 characters.
- Keep each line short.
- Include one clear broken rule or absurd twist.

### 4. Scene Plan

Create `scripts/scene_plan.md` with:

```text
scene_id
time_range
visual
motion
audio_line_ids
caption
purpose
imagegen_prompt_file
image_file
higgsfield_clip_file
higgsfield_prompt_file
```

For narrator-led shorts, prefer 3-6 second scenes. Use more close-ups than wide shots. Alternate:

- Establishing shot
- Face or object close-up
- Hand/action close-up
- Crowd or environment
- Strong final image

### 5. Imagegen Source Images For Higgsfield

Before Higgsfield generation, create one still image per scene with the `imagegen` skill. These stills are the visual anchor for Higgsfield, so design them to animate cleanly.

Use the built-in `image_gen` tool by default. After each image is generated, copy the selected final image from `$CODEX_HOME/generated_images/...` into:

```text
images/imagegen_source/scene_01.png
images/imagegen_source/scene_02.png
```

Also save every prompt in:

```text
prompts/imagegen/scene_01.md
prompts/imagegen/scene_02.md
```

Imagegen source-image rules:

- Generate vertical 9:16 stills for Shorts. Target 1080x1920 when saving final source images.
- Keep image text out of the generated image. Add title, captions, labels, rankings, and emphasis later in Remotion.
- Leave safe negative space where later captions will sit, usually upper third for title cards and lower-middle safe area for subtitles.
- Make the moving elements visible but separable: smoke, steam, flame, water, cloth, lantern glow, hands, crowd, camera depth.
- Avoid cluttered compositions that make Higgsfield invent new objects.
- Avoid tiny faces, dense hands, unreadable signs, random characters, and important details at the crop edge.
- For a multi-scene video, keep style, palette, era, character clothing, and camera language consistent across all prompts.
- For dialogue skits, create a base character/layout image first, then scene images that preserve left/right positions.
- For narrator-led documentary shorts, create scene-specific food/object/action stills rather than one reusable character image.

Imagegen prompt template:

```text
Use case: historical-scene
Asset type: Higgsfield source image for a vertical Japanese short video
Primary request: [scene purpose]. Do not include any text in the image.
Scene/backdrop: [where and when]
Subject: [main object/character/action]
Style/medium: Vertical 9:16 Japanese historical anime illustration, original, bold ink outlines, textured paper feel, cinematic short documentary look.
Composition/framing: [foreground/midground/background], clear motion anchors, safe space for later caption overlay.
Lighting/mood: [light and emotional tone]
Color palette: [consistent palette]
Materials/textures: [surfaces Higgsfield can animate or preserve]
Constraints: no text, no logo, no watermark, no modern objects, preserve the intended era and subject.
Avoid: random letters, distorted hands, extra fingers, clutter, photorealistic drift, important details near crop edges.
```

Quality check each generated source image before Higgsfield:

- Correct aspect ratio and enough resolution for the target canvas.
- No baked-in captions, logos, or random text.
- Main subject is clear in a phone-sized preview.
- At least one obvious motion anchor exists.
- No critical historical or factual mismatch.
- Hands, faces, and food are acceptable.

If an image is good enough except for missing animation, keep it. If the composition, subject, or era is wrong, regenerate the still before spending Higgsfield credits.

### 6. VOICEVOX Engine And Audio

Before creating audio, make sure VOICEVOX Engine is running. Prefer the bundled helper:

```bash
python SKILL_DIR/scripts/start_voicevox_engine.py
```

The helper checks `http://127.0.0.1:50021/version`. If the Engine is already running, continue. If not, it tries to open the macOS VOICEVOX app. For other installs, set `VOICEVOX_ENGINE_CMD` or pass `--engine-cmd`:

```bash
VOICEVOX_ENGINE_CMD="/path/to/voicevox_engine --host 127.0.0.1 --port 50021" \
python SKILL_DIR/scripts/start_voicevox_engine.py
```

Do not treat Engine startup failure as a script failure. If automatic startup fails, tell the user to open VOICEVOX manually, then rerun the audio generation step.

### 7. VOICEVOX Line List

Create `scripts/voicevox_lines.tsv`:

```text
line_id	speaker	start	end	text	direction
line_001	narrator	0.0	2.6	江戸の屋台メシ、朝が早すぎる。	強め、短く
```

Use stable speaker mapping:

```text
narrator: clear documentary voice
character_a: conversational male/female voice
character_b: dry or tsukkomi voice
ai/system: neutral announcer voice
```

If VOICEVOX can be controlled locally, generate wav files line by line. If not, provide exact copy-paste lines and expected filenames.

Generate wav files with:

```bash
python SKILL_DIR/scripts/generate_voicevox_audio.py --project PROJECT_DIR
```

Use `scripts/voicevox_speakers.json` to choose speaker IDs. When invoking the helper, pass speaker overrides as needed:

```bash
python SKILL_DIR/scripts/generate_voicevox_audio.py --project PROJECT_DIR --speaker-map narrator=3 character_a=8 character_b=2
```

The script writes:

```text
audio/voicevox/line_001.wav
audio/voicevox/line_002.wav
audio/voicevox/voicevox_audio_manifest.json
```

Use those wav files in `scripts/timeline.json` and Remotion. If the generated duration differs from the planned timestamps, update the timeline from the actual wav durations rather than forcing the audio to match the first draft.

### 8. Subtitle And Telop Plan

Create `scripts/captions.tsv` or equivalent timeline data before the final render:

```text
caption_id	start	end	text	style
cap_001	0.15	2.05	江戸時代に\N大ブーム	hook
cap_002	1.95	4.04	焼き魚四選	title
```

Rules:

- Match subtitles to the actual VOICEVOX wav timing, not the first draft.
- Use short Japanese chunks: 1-2 lines, 7-13 characters per line where possible.
- Put title/badge labels in the upper safe area and main subtitles in the lower-middle safe area.
- Burn subtitles/telops into the mp4 for Shorts delivery unless the user explicitly requests separate subtitle files.
- Keep text out of Imagegen and Higgsfield prompts. Add it only in Remotion or the FFmpeg/ASS fallback.
- Use white text with a thick black outline for readability. Use yellow/red emphasis only for keywords.

For an FFmpeg fallback or a one-clip check, write ASS subtitles to `subtitles/ass/scene_##.ass` with `PlayResX: 1080` and `PlayResY: 1920`.

### 9. Higgsfield Image-To-Video Prompts

Create one motion prompt file per Imagegen source image in `prompts/higgsfield/`.

Prompt rules:

- Put aspect ratio first: `Vertical 9:16`.
- Reference the matching still image path at the top of the prompt.
- Describe only motion that should happen to the still image; Higgsfield is responsible for converting the still into a moving video clip.
- Keep character identity, clothing, palette, and era consistent.
- Direct motion toward environmental elements: flames, steam, crowd movement, camera push, hand motion.
- Avoid asking Higgsfield to solve exact subtitles or mouth timing.
- Include negative constraints: no modern objects, no logo, no text, no distorted hands.

Narrator-led prompt template:

```text
Source image: images/imagegen_source/scene_01.png
Vertical 9:16. [Subject/action], [setting], [time of day],
subtle natural motion: [steam/smoke/flame/water/cloth/crowd], [camera movement],
energetic short documentary mood.

Preserve the source image composition, style, subject, clothing, era, and lighting.
No modern objects, no text, no logo, no photorealistic transformation, no distorted hands,
no extra fingers, no new characters.
```

Dialogue prompt template:

```text
Source image: images/imagegen_source/scene_01.png
Vertical 9:16. Two-character limited-animation anime scene in [setting].
[Character A] stays on screen left, [Character B] stays on screen right.
Subtle expression changes, natural eye movement, small gestures, mostly fixed camera.

Preserve the source image composition, character positions, clothing, and style.
No subtitles, no logo, no random text, no new characters.
```

### 10. Higgsfield Image-To-Video Generation

Before paid/credit-consuming generation, show:

- Scene count
- Expected duration
- Required aspect ratio: 9:16
- Imagegen source-image folder
- Prompt folder
- Credit-impact reminder

Upload or provide each `images/imagegen_source/scene_##.png` to Higgsfield with the matching `prompts/higgsfield/scene_##.md`. Set Higgsfield `aspect_ratio` to `9:16`. After generation, save the returned clips as:

```text
video/higgsfield/scene_01.mp4
video/higgsfield/scene_02.mp4
```

If direct Higgsfield access is unavailable, stop only at this external handoff and tell the user exactly which prompt files to paste and where to place returned mp4 files.

### 11. One-Clip VOICEVOX And Telop Check

After the first Higgsfield mp4 exists, create a checked clip that combines:

- `video/higgsfield/scene_01.mp4`
- the matching VOICEVOX wav file(s)
- burned-in Japanese subtitle/telop text
- vertical 9:16 output at 1080x1920

Use Remotion when the project is already set up. If Remotion is unavailable or a fast local check is enough, use the helper:

```bash
python SKILL_DIR/scripts/compose_voicevox_telop.py \
  --video PROJECT_DIR/video/higgsfield/scene_01.mp4 \
  --audio PROJECT_DIR/audio/voicevox/line_001.wav \
  --output PROJECT_DIR/video/checks/scene_01_voicevox_telop.mp4 \
  --badge "江戸グルメ雑学" \
  --caption '0.15,2.05,江戸時代に\N大ブーム' \
  --caption '1.95,4.04,焼き魚四選' \
  --audio-delay-ms 220
```

The helper uses `FFMPEG`, system `ffmpeg`, or Python `imageio_ffmpeg` in that order. It replaces the Higgsfield clip's original audio with the VOICEVOX track, delays audio when requested, pads it to the video duration, scales/crops to 1080x1920, burns ASS subtitles, and writes a phone-ready mp4.

Inspect the check clip before spending credits on the remaining scenes or before final assembly:

- Confirm the output is 9:16.
- Confirm VOICEVOX narration is audible and not clipped.
- Confirm subtitles appear at the intended times.
- Confirm subtitle placement does not hide the main subject.

### 12. Remotion Assembly

Create `scripts/timeline.json` as the source of truth for:

- Higgsfield scene clip
- Optional Imagegen still fallback for preview or repair
- Start/end
- Audio line IDs
- Subtitle text
- Caption emphasis
- Mouth-state rules for dialogue videos

Use Remotion for:

- Importing `video/higgsfield/scene_##.mp4` clips as the main visual layer
- Vertical 1080x1920 canvas
- Clip trimming
- Audio placement
- Subtitle rendering
- Punch-in zooms
- Freeze-frame repairs
- Mouth overlays if Higgsfield lip-sync is wrong

Do not silently replace missing Higgsfield clips with Imagegen stills in the final render. Still-image fallback is acceptable for a rough preview or explicit repair, but final animated scenes should come from Higgsfield unless the user approves a limited-motion Remotion-only fallback.

For narrator-led videos, keep all human mouths closed unless intentional. For dialogue videos, drive mouth state from `voicevox_lines.tsv`; do not rely on Higgsfield's speaker detection.

If Remotion is not installed and the requested output can be completed with deterministic local composition, use `compose_voicevox_telop.py` plus FFmpeg/ASS as the fallback renderer. State this in the completion report.

### 13. Audio And Captions

Caption defaults:

- White text
- Thick black stroke
- 1-2 lines
- Safe lower-middle placement
- Yellow/red emphasis only for key words

Audio defaults:

- Narration clear and centered.
- BGM low enough to preserve speech.
- Effects short and topic-relevant.
- Normalize final loudness if FFmpeg is available.

### 14. QA

Create `qa/final_check.md` and verify:

- Runtime is within target.
- Final render is vertical 9:16 at 1080x1920 unless explicitly approved otherwise.
- First 3 seconds communicate the theme.
- Captions are readable on mobile.
- Subtitle/telop text is burned into the delivered mp4 unless separate subtitle delivery was requested.
- Imagegen source images have no baked-in text unless explicitly required.
- Higgsfield clips preserve the source-image composition and subject.
- Remotion uses `video/higgsfield/scene_##.mp4` clips as the primary visual source.
- No modern objects appear in historical scenes.
- No copied title/script/thumbnail/branding from references.
- Audio and cuts line up.
- VOICEVOX wav files exist for every required line ID.
- The final audio track contains VOICEVOX narration/dialogue, not only the original Higgsfield audio.
- Higgsfield artifacts are hidden by trims, zooms, or replacement stills.
- Final file opens and has expected resolution/fps.

Use FFmpeg/ffprobe when available. If unavailable, use the best local inspection possible and state the limitation.

For one-clip checks, write a compact QA note next to the output that includes:

```text
source Higgsfield clip
VOICEVOX speaker and line text
duration
resolution/fps
audio codec/sample rate
caption timings
visual subtitle check
```

### 15. Delivery

Deliver:

```text
outputs/final.mp4
scripts/narration.md
scripts/scene_plan.md
scripts/voicevox_lines.tsv
audio/voicevox/
subtitles/ass/
prompts/imagegen/
images/imagegen_source/
prompts/higgsfield/
video/checks/
qa/final_check.md
```

In the final response, keep it short and user-facing. Mention any remaining manual step only if necessary.
