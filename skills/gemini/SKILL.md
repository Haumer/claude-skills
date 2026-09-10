---
name: gemini
description: Call the Gemini API from the shell — image generation (nano-banana bakes: pack shots, reveal scene layers, card art) and text. Handles key lookup, reference-image composition, base64 output decoding.
---

# /gemini — call Gemini from the shell

Generate or edit images (and run text prompts) against the Gemini API with
plain curl. Built for product asset bakes: pack shots, reveal scene layers,
card heroes. No SDK, no deps beyond `curl`, `jq`, `base64`.

## 0. Key

```bash
[ -n "$GEMINI_API_KEY" ] || echo "MISSING KEY"
```

If missing, STOP and ask the user to provide one (aistudio.google.com/apikey).
Suggest they run `! export GEMINI_API_KEY=...` for the session, or add it to
`~/.zshenv` for persistence. Never paste the key into files that could be
committed; never echo it into output.

## 1. Models

- `gemini-2.5-flash-image` — image generation + editing ("nano-banana").
  Default for all image work. Supports reference images (composition/editing)
  and `imageConfig.aspectRatio`.
- `gemini-2.5-flash` — text; `gemini-2.5-pro` — harder text/reasoning.
- If a model 404s, list what this key can see:
  `curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY" | jq -r '.models[].name'`

## 2. Text → image

```bash
curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" -H "Content-Type: application/json" \
  -d @- <<'JSON' > /tmp/gem-out.json
{
  "contents": [{ "parts": [{ "text": "PROMPT HERE" }] }],
  "generationConfig": {
    "responseModalities": ["IMAGE"],
    "imageConfig": { "aspectRatio": "3:4" }
  }
}
JSON
jq -r '.candidates[0].content.parts[] | select(.inlineData) | .inlineData.data' /tmp/gem-out.json \
  | base64 -d > out.png
```

Aspect ratios: `1:1 2:3 3:2 3:4 4:3 9:16 16:9` (card fronts: `3:4`;
full-screen phone scenes: `9:16`).

## 3. Reference image(s) + prompt (the bake)

Attach input images as parts alongside the text. This is how pack shots keep
the real product and how scenes stay on-brand:

```bash
IMG=$(base64 -i input.png | tr -d '\n')
jq -n --arg img "$IMG" --arg prompt "PROMPT" '{
  contents: [{ parts: [
    { inline_data: { mime_type: "image/png", data: $img } },
    { text: $prompt }
  ]}],
  generationConfig: { responseModalities: ["IMAGE"], imageConfig: { aspectRatio: "3:4" } }
}' | curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" -H "Content-Type: application/json" -d @- > /tmp/gem-out.json
```

Multiple references: multiple `inline_data` parts. Decode as in §2.

Failure handling: if there's no `inlineData` in the response, print
`jq '.candidates[0].finishReason, .promptFeedback' /tmp/gem-out.json` and read
the text parts — safety blocks and prompt refusals come back as text.

## 4. House rules for bakes (opinionated defaults — edit for your brand)

- **Pack shots**: QR small and on the BACK; fronts carry branding, never
  QR-as-hero. AI-generated EANs never scan — don't fake barcodes as real.
- **Reveal/card scenes**: generate LAYERS when possible — background scene
  and product hero separately (hero re-lit, on transparency or flat
  background for later removal) — so code can parallax them. One flat
  composite is the fallback, not the goal. Card fronts 3:4; full-screen
  reveal scenes 9:16.
- **Brand voice**: premium/tactile, story-rich; no confetti-arcade styling,
  no text baked into images (type is set in HTML/SVG, never rasterized).
- Generated assets are drafts: show the user before wiring anything in, and
  never commit binaries without their say-so.

## 5. Iterating

Regenerate with the previous output as a reference part plus the correction
("same scene, warmer light, jar 20% smaller"). Keep prompts in a scratchpad
file so a good recipe can be replayed; a bake worth keeping should have its
prompt recorded next to the asset it produced.
