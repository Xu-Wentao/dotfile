# Excalidraw Drawing Guidelines

## Table of Contents
- Output Contract
- JSON Rules
- Element Rules
- Bound Text (Text Inside Shapes)
- Arrow Bindings
- Required Element Properties (excalidraw.com Compatibility)
- .excalidraw File Format
- Layout Rules
- Visual Rules
- Common Errors to Avoid
- Minimal JSON Example

## Output Contract
- Output a JSON array of Excalidraw elements only.
- Do not output markdown fences, comments, or explanations.
- If arrows bind elements, referenced elements must have ids.

## JSON Rules
- Array must start with `[` and end with `]`.
- Use double quotes for keys and string values.
- Do not leave trailing commas.
- Booleans must be lowercase `true`/`false`.
- Numeric fields must be numbers, not strings.

## Element Rules
- Common node types: `rectangle`, `ellipse`, `diamond`, `text`.
- Connector types: `arrow`, `line`.
- **IMPORTANT**: Excalidraw does NOT support a `label` property on shapes. To put text inside a shape, you must use the Bound Text pattern (see below).
- Keep properties practical and minimal for render.py rendering; add full properties for .excalidraw file compatibility (see Required Element Properties).

## Bound Text (Text Inside Shapes)

Excalidraw requires a **separate text element** bound to the shape via `containerId` / `boundElements`. Never use a `label` property — it does not exist in Excalidraw's schema.

Pattern:
1. Shape element: add `"boundElements": [{"id": "<text-id>", "type": "text"}]`
2. Text element: set `"containerId": "<shape-id>"`, `"textAlign": "center"`, `"verticalAlign": "middle"`

**Text sizing and positioning** (critical for correct rendering):
- Estimate text dimensions based on content: `width ≈ max_line_chars × fontSize × 0.75`, `height ≈ num_lines × fontSize × 1.25`
- Position text at the **top-left of the centered area** within the container: `x = container_x + (container_w - text_w) / 2`, `y = container_y + (container_h - text_h) / 2`
- Do NOT set text x/y to the container center point — Excalidraw renders text from its top-left corner, so this would shift text downward
- Do NOT set text width/height to tiny values (e.g., 10) — this clips the text to that area in excalidraw.com

```json
{
  "id": "rect-1", "type": "rectangle",
  "x": 100, "y": 100, "width": 200, "height": 80,
  "strokeColor": "#1976d2", "backgroundColor": "#e3f2fd",
  "boundElements": [{"id": "text-1", "type": "text"}]
},
{
  "id": "text-1", "type": "text",
  "x": 130, "y": 125,
  "width": 140, "height": 30,
  "text": "Hello", "fontSize": 16, "fontFamily": 1,
  "textAlign": "center", "verticalAlign": "middle",
  "containerId": "rect-1", "originalText": "Hello",
  "autoResize": true, "lineHeight": 1.25
}
```

## Arrow Bindings

For render.py (exportToBlob), simple `start`/`end` with `id` works:
```json
"start": {"id": "node-1"}, "end": {"id": "node-2"}
```

For .excalidraw file compatibility, use `startBinding`/`endBinding`:
```json
"startBinding": {"elementId": "node-1", "focus": 0, "gap": 5},
"endBinding": {"elementId": "node-2", "focus": 0, "gap": 5}
```

Always include `"endArrowhead": "arrow"` for directional arrows and `"startArrowhead": null`.

## Required Element Properties (excalidraw.com Compatibility)

The render.py `exportToBlob` API is forgiving and fills in defaults. But excalidraw.com requires complete element definitions. Without these properties, elements may exist (selectable) but not render visually.

**All elements** must include:
```
seed, version, versionNonce, isDeleted, groupIds, frameId,
roundness, boundElements, updated, link, locked, angle
```

**Text elements** additionally need:
```
originalText, autoResize, lineHeight (1.25), textAlign, verticalAlign, containerId (null if standalone)
```

**Arrow elements** additionally need:
```
points, startArrowhead, endArrowhead, startBinding, endBinding, width (non-zero), height (non-zero)
```

Recommended base template:
```python
def _base(typ, x, y, extra):
    return {
        "id": nid(), "type": typ, "x": x, "y": y,
        "width": 0, "height": 0, "angle": 0,
        "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
        "fillStyle": "hachure", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 2, "opacity": 100,
        "seed": random.randint(1, 2**31),
        "version": 1, "versionNonce": random.randint(1, 2**31),
        "isDeleted": False, "groupIds": [], "frameId": None,
        "roundness": None, "boundElements": None,
        "updated": int(time.time() * 1000), "link": None, "locked": False,
        **extra
    }
```

## .excalidraw File Format

The render.py saves raw JSON array as source file, which is NOT a valid .excalidraw file. To produce a file that excalidraw.com can open, wrap elements in this structure:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [ ... ],
  "appState": {
    "gridSize": null,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```

**IMPORTANT**: Generate this wrapper separately and save it alongside the PNG output. Do not rely on render.py's `--no-source` default behavior for .excalidraw compatibility.

## Layout Rules
- Default shape size: `160x80`.
- Small shape size: `120x60`.
- Typical spacing: `60-100`.
- Recommended arrangements:
  - Flow-like diagrams: left-right or top-down.
  - Hierarchies: top-down with centered parents.
  - Mindmap/concept: center + radial branches.
- Avoid overlap and crossing lines where possible.

## Visual Rules
- Use no more than 3-4 primary colors.
- Keep typography consistent:
  - `fontFamily: 1` (Virgil) for hand-drawn style, `fontFamily: 6` for standard.
- Keep stroke widths and styles consistent for the same semantic level.
- Use concise labels.
- `fillStyle: "hachure"` creates diagonal line patterns — may reduce text readability in small cards. Consider `"solid"` or lighter background colors for text-heavy diagrams.

## Common Errors to Avoid
- Returning an object instead of an array.
- Single quotes or unquoted keys.
- Trailing commas.
- Arrow bindings to missing ids.
- Mixed prose with JSON output.
- **Using `label` property on shapes** — does not exist, use bound text pattern.
- **Setting bound text width/height to tiny values** — clips text in excalidraw.com.
- **Setting bound text x/y to container center** — text renders from top-left, causing downward shift.
- **Missing `seed`/`version`/`versionNonce`** — elements invisible in excalidraw.com.
- **Saving raw JSON array as .excalidraw file** — invalid format, needs wrapper object.

## Minimal JSON Example
```json
[
  {
    "id": "rect-1",
    "type": "rectangle",
    "x": 100, "y": 100, "width": 160, "height": 80,
    "strokeColor": "#1976d2",
    "backgroundColor": "#e3f2fd",
    "fillStyle": "hachure",
    "roughness": 2,
    "boundElements": [{"id": "text-1", "type": "text"}],
    "seed": 12345, "version": 1, "versionNonce": 67890,
    "isDeleted": false, "groupIds": [], "frameId": null,
    "roundness": {"type": 3}, "updated": 1700000000000,
    "link": null, "locked": false, "angle": 0,
    "strokeWidth": 1, "strokeStyle": "solid", "opacity": 100
  },
  {
    "id": "text-1",
    "type": "text",
    "x": 130, "y": 125, "width": 100, "height": 30,
    "text": "Start", "fontSize": 16, "fontFamily": 1,
    "textAlign": "center", "verticalAlign": "middle",
    "containerId": "rect-1", "originalText": "Start",
    "autoResize": true, "lineHeight": 1.25,
    "strokeColor": "#1976d2",
    "seed": 11111, "version": 1, "versionNonce": 22222,
    "isDeleted": false, "groupIds": [], "frameId": null,
    "roundness": null, "boundElements": null, "updated": 1700000000000,
    "link": null, "locked": false, "angle": 0,
    "strokeWidth": 1, "strokeStyle": "solid", "opacity": 100,
    "backgroundColor": "transparent", "fillStyle": "hachure", "roughness": 2
  }
]
```
