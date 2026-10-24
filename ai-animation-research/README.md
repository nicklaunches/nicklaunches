# Recreating "bit_wonder"-style animated tech reels with Claude

Research notes, production recipes, prompts and four working sample renders.

> **What I could not do:** Instagram serves `instagram.com/bit_wonder` behind a login wall (302 to the login page, then 429 rate limits) and the scraper/mirror routes were blocked by this session's permissions, so I could not download or watch the actual reels. Everything below is built from (1) the public tooling ecosystem that produces this exact genre of video, (2) the style analyses those tools publish, and (3) my own test renders. Section 2 gives you a 60-second checklist to classify which pipeline bit_wonder is using once you watch a few of their clips with it in mind.

---

## 1. The short answer

There is no single "secret engine". Virtually every account in this genre uses one of three pipelines, or a mix of them, and in all three Claude (Code) is the thing writing the scenes, not the thing rendering pixels:

| Pipeline | What renders the pixels | What Claude does | Look it produces | Cost / speed |
|---|---|---|---|---|
| **A. Code-rendered motion graphics** | A headless Chrome: **Remotion** (React), **HyperFrames** (HTML + GSAP), with **Three.js** for 3D | Writes the whole composition as code from a script, iterates on stills | Crisp 2D diagrams, kinetic type, counters, "vinyl toy" low-poly 3D, perfect text, deterministic | Free, minutes per video, infinitely editable |
| **B. Generative video** | An AI video model: **Veo 3.1**, **Kling 3.0**, **Hailuo 2.3**, **Seedance**, **Sora 2**, fed with AI keyframe images (**Nano Banana**, **Flux**) | Researches, writes script + beat list, writes every image/video prompt, assembles with ffmpeg | Pixar/clay "3D animated short" look, cutaways, organic motion, fur/liquids/smoke | ~$0.5–2 per 8 s clip, 7–12 clips per reel, retakes needed |
| **C. Real 3D (Blender)** | **Blender** (Cycles/EEVEE), driven by Claude through the **Blender MCP** or `bpy` scripts | Builds scene, materials, lights, camera moves and keyframes from a prompt | True 3D with real lighting, shadows, depth of field, physics | Free, slow renders (minutes–hours), hardest to prompt well |

The "many channels started doing the same thing" effect you noticed lines up with the timing of three things: Remotion's official agent skills (`remotion-dev/skills`), HeyGen's open-source **HyperFrames** (built explicitly for coding agents) and the official **Blender MCP connector** for Claude. All three went mainstream in 2026 and dozens of ready-made Claude Code "explainer skills" now sit on top of them (see Section 4).

---

## 2. How to tell which pipeline a given reel uses (watch for these)

Pause the clips and look for:

**Code-rendered (A) signals**
- Text is pixel-perfect and never "melts"; captions pop in word by word exactly on the voice.
- Edges are perfectly straight, repeated objects are identical, shadows are simple and consistent.
- 3D objects look like soft plastic/vinyl with a studio gradient background; no fine fur, liquid, cloth.
- Camera moves are mathematically smooth (ease-in-out), scenes cut on a flash or a wipe.
- Same "set" reused across videos with different data.

**Generative video (B) signals**
- Clips are 5–8 s long and the video is a chain of them with cuts or crossfades.
- Gorgeous organic detail: subsurface skin, translucent cutaways of organs/machines, fluids, dust in light beams.
- Small inconsistencies between shots (a character's proportions drift, a prop changes), slightly "breathing" backgrounds, hands/fingers occasionally wrong.
- Any on-screen text in the footage itself is slightly off, so creators overlay text afterwards.
- Motion sometimes has that "slow dreamy drift" even when the voice is fast.

**Real 3D (C) signals**
- Physically correct contact shadows, depth of field, reflections and motion blur; consistent across the whole shot.
- Long continuous camera moves (10 s+) with no cut, objects that interlock or get taken apart precisely.
- Often mixed with A for the captions.

Most "premium" accounts in this niche are **B for hero shots + A for everything with text** (diagrams, counters, captions, end card). If bit_wonder's 3D looks "too good" for code and the shots are short, it is B.

---

## 3. The craft layer (this is where clones usually fall apart)

Tools are the smaller half. The channels that look expensive all follow the same production rules, and each is cheap to add:

**Script structure (the same four beats every time)**
1. **Hook (0–3 s):** one question or surprising claim in huge type, also used as the cover frame.
2. **Setup (3–15 s):** the wrong/naive mental model, shown not told.
3. **Mechanism (15–45 s):** one idea per frame; elements appear exactly when the narration reaches them.
4. **Payoff (last 5–10 s):** one resolving sentence, held on screen, then the series branding.

**Motion rules**
- Every motion has a *cause* (the packet arrives, so the counter ticks).
- One dominant direction per scene; exits set up the next scene's entry.
- Anticipation → move → overshoot → settle. Use spring/`backOut` easing for entrances, sine pulses for hops. Gestures 0.5–1.2 s, holds 0.3–0.75 s before a payoff.
- Camera pushes in on the hook and on impact beats, pulls back for the payoff.
- Transitions are short and physical: white flash + scale punch, wipe, circle-open, or a "slam" word. Never a plain dissolve.
- Three depth layers (far / mid / near) moving at different speeds give parallax for free.

**Look rules (the "3D toy" / clay look everybody uses)**
- Materials: `metalness 0`, `roughness 0.35–0.5`, `clearcoat ~0.3`, slight subsurface. Gloss or metal reads as a product render, not a toy.
- Lighting: one big soft key upper-left (shadows on), a weak fill at ~30 %, a coloured rim from behind, a hemisphere/ambient lift. Dark studio backdrop (charcoal, deep navy, deep red) with a radial gradient.
- Camera: 30–35° FOV, slightly above eye level, shallow depth of field, 85 mm-macro feel for close-ups.
- Tone mapping: ACES (Three.js) or AgX (Blender). Add a soft vignette and 4–6 % film grain at the end; this alone makes CSS-flat renders feel like footage.
- Colour discipline: one background, one ink, **one** accent (plus at most one secondary). Highlight key words in the accent.

**Captions, audio, delivery**
- Word-by-word captions, bold sans (Inter / Kanit / Plus Jakarta), centred at ~78 % of frame height, inside the 9:16 safe zone (keep 250 px clear at the bottom, 120 px at the top for the Instagram UI).
- Voice first, then time everything to it (transcribe with Whisper to get word timestamps). TTS: ElevenLabs, or free `edge-tts` / VoxCPM; never clone a real person without permission.
- Music under the voice, SFX on every hit (pop on reveals, whoosh on wipes, deep impact on the slam). Master to -14 LUFS.
- Export 1080×1920, 30 fps, H.264 High, CRF 16–18, AAC 320 kbps. Add sub-pixel camera drift to any still so it never looks frozen.

**Common reasons a clone looks worse**
- No hook or the hook is a sentence instead of a gap in the viewer's knowledge.
- Elements appear all at once instead of as the voice reaches them.
- Linear easing / no overshoot; everything slides instead of landing.
- Flat lighting and grey shadows; no rim light; white background.
- Captions as one block of text instead of word pops; text covered by the Instagram UI.
- Too many colours and fonts; no grain/vignette; no SFX.
- Generative clips used for text or diagrams (always do those in code).

---

## 4. Pipeline A in detail: Claude Code + Remotion / HyperFrames / Three.js

This is the route to start with. It is free, deterministic, Claude is extremely good at it, and it is what the **samples in this folder** use.

**Setup**
```bash
# Remotion (React video framework) + official agent skills
npx create-video@latest my-reels            # choose the "Three.js" or "Blank" template
cd my-reels && npx skills add remotion-dev/skills
npx remotion add @remotion/three             # React Three Fiber inside Remotion

# or HyperFrames (HTML/GSAP video framework from HeyGen, built for agents)
npx hyperframes init my-reels && npx skills add heygen-com/hyperframes
# inside Claude Code:  /plugin marketplace add heygen-com/hyperframes ; /plugin install hyperframes@hyperframes
```

**Ready-made Claude Code skills for this genre** (install with `npx skills add <repo>`; check each README):
- `PHANTOMTONYT/motion-design-skills` – five looks incl. **3D toy character** (Three.js), kinetic typography, system diagram, data-story charts, hand-drawn. Has explicit motion/style rules and a self-review loop.
- `Boom-Vitt/bbn-video-studio` – `/short-ex-3d`: 9:16 ≤45 s 3D explainers, Blender plates + Three.js overlays, open-source TTS, captions, music.
- `runesleo/claude-video-kit`, `vibe-motion/remotion-starter`, `hassancs91/claude-faceless-shorts-creator`, `misbahsy/tiktok-ig-shorts`, `hamen/app-promo-reel` – brief → 9:16 explainer pipelines on Remotion/HyperFrames.
- `Alisa0808/vox-director`, `santmun/video-vox`, `jaredcassoutt/vox-editorial` – Vox-style paper-collage explainers.
- `adithya-s-k/manim_skill`, `AmitSubhash/3brown1blue` – 3Blue1Brown-style Manim.
- Full list: `zhuyansen/awesome-claude-video-skills`.

**Working method that produces quality (not just "make me a video")**
1. Give Claude the topic and ask for a *beat list* first (hook / setup / mechanism / payoff, with the on-screen element and the narration line per beat). Approve it.
2. Record or generate the voice-over, transcribe it to word timestamps, give Claude the JSON.
3. Ask for the composition with the explicit look rules from Section 3 pasted in.
4. Have Claude render 10–20 stills across the timeline (`npx remotion still`) and inspect them for overlaps, safe zones and readability, then fix. This loop is what the good accounts do; it costs cents.
5. Render, then add SFX/music in the composition (`<Audio>`) or in ffmpeg.

**Prompt template (paste into Claude Code after installing the Remotion skills)**
```
Use the remotion best-practices skill. Build a 1080x1920, 30 fps, 24 s explainer about <TOPIC>.
First write a beat list (hook 0-3 s, setup, mechanism, payoff) with: narration line, on-screen element,
camera move, transition. Wait for my OK.
Then implement it as one composition with:
- a Three.js scene via @remotion/three for the mechanism (vinyl-toy look: MeshPhysicalMaterial
  roughness 0.45, metalness 0, clearcoat 0.35; soft key light with 2048 shadow map, 30% fill,
  coloured rim light, hemisphere light; 34° FOV camera slightly above eye level; ACES tone mapping;
  dark radial-gradient backdrop; three parallax depth layers)
- a 2D layer: word-by-word captions driven by spring() at y≈1500 px, a counter that eases between
  values, a hook title card that slams in (spring with overshoot) and a payoff card
- transitions: 8-frame white flash + scale punch on cuts; camera push-in on the hook and impact beats
- finish: vignette + 5% grain + top progress bar
All motion must be a pure function of useCurrentFrame() (no useFrame/Date/Math.random).
Give every caption/counter an end frame so nothing overlaps.
Render stills at frames 40, 150, 330, 520, 680 and check for overlaps and safe zones before rendering.
```

---

## 5. Pipeline B in detail: generative video with keyframe control

This is how the "looks like a Pixar short" accounts work. The reference implementation is the open-source **Zack-D-Films-style generator** (`Anil-matcha/zack-d-films-ai-video-generator`) and the **HowZit** build (`Gunasmart00/animated-explainers`), which both document the whole chain:

1. **Trend research → script → beat map** (Claude). Gate: you approve the script and the credit cost.
2. **Character turnaround sheets** (image model, e.g. Nano Banana / Flux) so the character is identical in every shot.
3. **One keyframe image per shot** in the chosen look. *Style is locked at the keyframe stage; motion is added afterwards.* This is the single most important trick for consistency.
4. **Image-to-video** per shot (Veo 3.1 Fast is the workhorse; Kling 3.0 for character acting and multi-shot; Hailuo 2.3 for stylised looks and cost; Sora 2 for identity across cuts). 5–8 s clips, 9:16, with the model's own SFX. Expect 7–12 clips and a few retakes per reel.
5. **Narration** (ElevenLabs / MiniMax / edge-tts) → Whisper word timings.
6. **Assembly in ffmpeg or Remotion:** fit clips to voice, impact zooms on beats, short wipes / circle-opens, captions and pop-ups in code, logo, music, mix to -14 LUFS.

**The five-part image prompt that these pipelines use (same order every time)**
```
[1 subject + action]  A translucent cutaway of a smartphone showing the battery cells glowing as they charge,
[2 character/asset ref]  same phone as reference sheet A,
[3 3D style + material]  stylized 3D animation, glossy polymer-clay material with soft subsurface scattering,
   smooth slightly exaggerated shapes, octane-render aesthetic,
[4 lighting + camera]  high-contrast studio lighting, bright key light, vibrant cyan rim light, ambient occlusion,
   85 mm macro lens, shallow depth of field, slight low angle,
[5 background + atmosphere]  dark charcoal studio backdrop with a soft blue gradient, faint volumetric haze.
Negative: photorealistic, 2D, vector, sketch, anime, text, watermark, blurry, grainy.
```
Video prompt = the same keyframe description + **one** camera move + **one** action, e.g. *"slow push-in, the cells light up one by one from the bottom, subtle particle sparks, no camera shake, 6 s"*. One action per clip; two actions is where models fail.

**Hybrid that gives total control:** block the shot in Blender (grey boxes, real camera move), render it, and feed that render as the start frame / motion reference to the video model. fal.ai documents this "clay render → AI short" pipeline; Picsart ships it as a Claude MCP (Blender grey-box → Seedance).

---

## 6. Pipeline C in detail: Claude driving Blender

- **Official Blender MCP connector** (from the Blender developers; works with Claude Desktop / Claude Code). Claude can inspect the scene, add objects, write materials, keyframe, set lights and cameras, render.
- Community plugins: `gokayfem/video-to-blender` (procedural Geometry/Shader node graphs), `sunxiayi/make-blender-education-video-skill`, `hraness/slopcamera`.
- Workflow that works: treat Claude as *scene director*, Blender as source of truth. Ask it to inspect first, give specific art direction (materials, lights, camera lens, mm, f-stop), review stills, then request targeted revisions. Keep EEVEE for iteration and Cycles for finals; export PNG sequences and encode with ffmpeg.
- **Blender prompt for Claude (MCP or a `bpy` script):**
```
Build a 9:16 scene: a small phone on a dark studio floor in the foreground, a tall server block far
back, five cube "edge nodes" in a ring. Materials: Principled BSDF, base colours from this palette,
roughness 0.45, metallic 0, coat weight 0.35, subsurface 0.15 (vinyl-toy look); floor roughness 0.9.
Lights: 6 m area key upper-left 700 W warm, 8 m fill opposite 120 W cool, cyan rim behind 600 W.
Camera 50 mm, f/2.8 focused on the phone; keyframe a push-in then widen over 60 frames with
ease-in-out. Edge nodes pop in with overshoot (scale 0 → 1.15 → 1 over 10 frames, staggered 4 frames).
A glowing emissive sphere flies on an arc from the phone to the nearest node and back.
AgX view transform, medium-high contrast. Render 540x960 Cycles 32 samples with denoising to PNGs.
```
The file `samples/blender/scene_cdn.py` is exactly this prompt turned into a script that runs headless with `pip install bpy`.

---

## 7. The samples built here

All four are original scenes rendered in this session (no assets from any channel). Sources are in `samples/`, renders in `renders/`, check-stills in `stills/`.

| Sample | Pipeline | Shows | Files |
|---|---|---|---|
| **CDN explainer, 3D** | A: Remotion + Three.js | hook card slam, far-origin "slow packet" with a counter 0→180 ms, edge nodes spring in, fast packets + counter 180→40 ms, cache replication, payoff card; flash transitions, camera push/orbit/pull, vinyl materials, shadows, ACES, grain + vignette, word-pop captions | `samples/remotion/src/Explainer3D.tsx`, `renders/explainer3d_cdn.mp4` |
| **Login explainer, 2D** | A: Remotion (HTML/SVG) | system diagram building node by node, self-drawing edges, labelled packets, a kinetic "NEVER" slam with the diagram dimmed, payoff card | `samples/remotion/src/Explainer2D.tsx`, `renders/explainer2d_login.mp4` |
| **CDN beat, real 3D** | C: Blender `bpy` (Cycles CPU) | the same beat with real lights, contact shadows, depth of field, AgX tone mapping, overshoot pop-ins, arc packet | `samples/blender/scene_cdn.py`, `renders/blender_cdn.mp4` |
| **Pixel Dungeon** | A: Remotion Canvas 2D, code-drawn pixel art | see Section 9 | `samples/remotion/src/PixelDungeon.tsx`, `renders/pixel_dungeon.mp4` |
| **Hashing explainer** | 3Blue1Brown-style Manim | text hook, boxes/arrows drawing, scrambling digest, crossed-out reverse arrow with flash, ticking counter, payoff | `samples/manim/hashing.py`, `renders/manim_hashing.mp4` |

Run them:
```bash
cd samples/remotion && npm i && npx remotion studio            # live preview; npm run render3d / render2d
cd samples/blender && pip install bpy && python3 scene_cdn.py out 60 32 && ffmpeg -framerate 24 -i out/frame_%04d.png -pix_fmt yuv420p blender_cdn.mp4
cd samples/manim && pip install manim && manim -qh -r 1080,1920 --fps 30 hashing.py HashExplainer
```
(Remotion needs Chrome; on a machine without a GPU render with `--gl=swangle`.)

Shared `samples/remotion/src/ui.tsx` is the reusable kit: `Caption` (word pops with start/end), `Counter`, `TitleCard` (slam + scrim), `Flash` (cut transition), `Finish` (vignette + grain), `Progress`.

---

## 8. Recommended path for you

1. **Week 1: Pipeline A only.** Install the Remotion skills and `motion-design-skills`, drop in the `ui.tsx` kit, and produce five reels with the beat-list → voice → timings → stills-review loop. This alone gets you to the "premium motion graphics" tier.
2. **Add generative hero shots (B)** only for things code can't do (organic cutaways, characters). Lock style at the keyframe stage, one action per clip, overlay every piece of text in code.
3. **Add Blender (C)** when you need one long continuous 3D camera move or real physics; use Claude via the MCP to build it, EEVEE to iterate, Cycles for the final.
4. **Audio last but never skipped:** SFX on every hit, music ducked under the voice, -14 LUFS.

---

## 9. Pixel-art / "2D graphics in code" (follow-up on the Studio Igor video)

You pointed me at *"2D-графика кодом — реально? Делаем 5 игр с Claude и GPT"* (Студия Игор). YouTube blocks anonymous downloads from this datacenter, so I could not watch it; the public listing says it compares **two ways to get 2D game art out of an LLM: draw everything in code, or generate images in parts**, across five games from a pixel-art dungeon to a Diablo-like. Both approaches are well documented in open projects, and they are exactly the two routes below.

### Route 1: the model writes code that draws every pixel (the one that scales)
This is what the best "code-drawn pixel art" projects do (`Gamezxz/pixel-art-studio`, `dbinky/claude-fairy-pixel-art`, most entries in `theolundqvist/frontier-games`):

- **Ask for code that draws, not for images.** Claude is far better at precise pixel placement in code (Pillow `putpixel`, Canvas 2D `fillRect(x,y,1,1)`) than at image generation. One 2,700-line Pillow script generated 163 consistent assets on its first run.
- **Spec first, palette in one place, one reference piece.** Write an asset spec (name, size, description) and a named palette dictionary before any drawing. Hand-draw or approve one reference sprite to lock the style.
- **Hue-shifted ramps instead of flat colours.** Build each material as a 5-step ramp where shadows shift cooler and highlights warmer. Lock all assets to the same palette (presets: PICO-8, Sweetie16, Endesga32, Game Boy).
- **Selective outlines and 2×2 Bayer dithering**, darkest ramp colour defines the silhouette, highlights only on existing pixels.
- **Motion is parameters, not copied frames.** A walk cycle is a body template plus `bob`, `leg phase`, `swing`; a slime is squash-and-stretch that keeps volume. 4-frame idle, 8-frame walk, 6-frame attack × 4 directions is the usual set.
- **Render tiny, scale with nearest-neighbour.** Draw at 1/5–1/8 of the output size and upscale with smoothing off (`imageSmoothingEnabled=false`, CSS `image-rendering: pixelated`, Pillow `Image.NEAREST`). Scanlines, a slight vignette and torch glow sell the "CRT" look.
- **Determinism.** No `Math.random`; use a hash of (x, y, seed) so every render is identical and every frame is editable.
- **The self-review loop is the quality mechanism:** render a contact sheet, let Claude look at it, critique against a rules file, fix the script, repeat 2–3 times before delivery.

### Route 2: generate images in parts, then "pixelate" them (fast, less consistent)
`ianlintner/ai-pixel-art-image-generation` packages this for Claude Code: `gpt-image-2` makes a base sprite/tile; Gemini 2.5 Flash Image makes animation frames conditioned on frame 0; then **nearest-neighbour downscale → palette quantise → optional outline → background removal**, with QA gates (palette fidelity, silhouette IoU between frames, tile-seam difference). Style is sampled once per set so all tiles match. Fixed prompt clauses: *pixel art, limited palette, no text, no borders*. Hybrid tools (`pixelpipe.py` in pixel-art-studio) recover the pixel grid from a generated image and emit an editable drawing script, which is the best of both.

### Prompt for Claude Code (Route 1)
```
Write a Python/Pillow script (no image generation) that draws a pixel-art asset set for a dungeon game.
Rules: 16x16 tiles, 16x24 characters, PICO-8-like 16-colour palette defined once as named ramps
(5 steps, hue-shifted: shadows cooler, highlights warmer). Darkest colour = silhouette; selective 1px
outline only where a sprite borders transparency; 2x2 Bayer dither for gradients. Characters are a
body template animated by parameters (bob, leg phase, arm swing) producing a 4-frame walk; slimes use
squash & stretch with constant volume. Export a spritesheet PNG + an 8x nearest-neighbour contact sheet.
Then look at the contact sheet, critique silhouette readability, ramp contrast and outline consistency,
fix the script, and re-render. Do at least two review passes.
```
For a *video* rather than a game, drop the same drawing functions into a Remotion `<canvas>` sized 192×342, draw the scene as a pure function of `useCurrentFrame()`, and upscale to 1080×1920 with smoothing off; captions and the hook/payoff cards stay in the HTML layer. That is exactly what `samples/remotion/src/PixelDungeon.tsx` does.

### Sample 5: Pixel Dungeon (code-drawn pixel art)
| | |
|---|---|
| Video | `renders/pixel_dungeon.mp4` (22 s, 1080×1920) |
| Scene code | `samples/remotion/src/PixelDungeon.tsx` – tiles, original hero and slime, parallax towers, torches, pixel-font HUD, scanlines, all procedural, zero assets |
| Pillow version | `samples/pixelart/gen_sprites.py` – the same sprites generated as PNGs (`sheet.png`, `stills/pixelart_sheet_x8.png`) with ramps, dithering and selective outlines |

Sources for this section: https://github.com/Gamezxz/pixel-art-studio , https://github.com/dbinky/claude-fairy-pixel-art , https://github.com/ianlintner/ai-pixel-art-image-generation , https://github.com/theolundqvist/frontier-games , https://www.youtube.com/watch?v=YQ01D9xGAnk

---

## Sources
- Remotion skills / Three.js: https://github.com/remotion-dev/skills , https://www.remotion.dev/docs/three
- HyperFrames (HeyGen): https://github.com/heygen-com/hyperframes , https://claude.com/plugins/hyperframes
- Motion-design skills (3D toy look rules): https://github.com/PHANTOMTONYT/motion-design-skills
- BBN Video Studio (Blender + Three.js short explainers): https://github.com/Boom-Vitt/bbn-video-studio
- Zack D Films-style AI generator (keyframes → Veo 3.1): https://github.com/Anil-matcha/zack-d-films-ai-video-generator
- HowZit animated explainers (Flow/Veo 3.1 + ffmpeg build, caption/pop-up specs): https://github.com/Gunasmart00/animated-explainers
- Awesome Claude video skills (full catalogue): https://github.com/zhuyansen/awesome-claude-video-skills
- Explainer-reel formula (hook/setup/mechanism/payoff): https://www.brainrotshorts.com/blog/how-to-make-animated-explainer-reels
- 5 Claude Code video prompts: https://www.sabrina.dev/p/5-insane-claude-code-video-prompts
- Blender MCP for Claude: https://www.anthropic.com/news/claude-for-creative-work , https://app.therundown.ai/guides/how-to-3d-model-anything-with-claude-blender
- Blender grey-box → AI video pipeline: https://blog.fal.ai/from-clay-3d-render-to-a-real-action-short-a-3d-to-ai-pipeline-with-total-control
- AI video model comparisons (Veo 3.1 / Kling 3.0 / Hailuo 2.3 / Sora 2): https://higgsfield.ai/blog/5-Best-AI-Video-Models-2026-Tested-Compared , https://aimlapi.com/blog/best-ai-video-generators-2026-veo-3-1-kling-sora-2-seedance-more-compared
- Claude reel editing write-ups: https://charliehills.substack.com/p/how-claude-edits-my-reels-the-full , https://github.com/tenfoldmarc/video-edit-skill
