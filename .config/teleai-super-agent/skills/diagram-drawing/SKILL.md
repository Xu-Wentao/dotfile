---
name: diagram-drawing
description: |
  Generate professional diagrams from natural language. Supports 23 diagram types across two engines: Draw.io (structured/formal) and Excalidraw (hand-drawn/casual).

  Trigger phrases (Chinese): "画一个...", "生成...图", "帮我做...图表", "创建...", "可视化...", "画个流程图", "做一个架构图", "来个思维导图"
  Trigger phrases (English): "draw a...", "create a...diagram", "generate...chart", "visualize..."

  Diagram types: flowchart, state, swimlane, dataflow, orgchart, tree, mindmap, sequence, gantt, timeline, UML class, ER, concept map, network topology, SWOT, fishbone, matrix, pyramid, funnel, venn, architecture, infographic, auto-detect.

  Use cases: technical documentation, project planning, system design, brainstorming, data visualization, org structure, process mapping.
name_cn: "图表绘制"
description_cn: "通过自然语言即可生成各类专业图表与结构化图示。例如流程图、思维导图等"
---

## Environment Prerequisites

Before rendering, ensure runtime dependencies are installed:

```bash
pip install -r scripts/requirements.txt
python -m playwright install chromium
```

Python 3.10+ is recommended.

## Network Requirements

Rendering requires internet access because `scripts/render.py` loads:
- Draw.io viewer from `https://viewer.diagrams.net/...`
- Excalidraw module from `https://esm.sh/@excalidraw/excalidraw`

If network is unavailable, report it clearly and suggest retrying in a connected environment.

## Engine Selection Rules

Choose engine based on user intent and diagram characteristics.

### Draw.io (Structured, Formal)
Select when user requests:
- Professional/formal: "专业的", "正式的", "技术文档用"
- Precise/technical: "精确的", "技术架构", "系统设计"
- Documentation: "文档", "汇报", "演示"

Default Draw.io types: architecture, ER, UML class, sequence, network topology, gantt, swimlane, state, dataflow, SWOT, fishbone, matrix, pyramid, funnel, venn, infographic, flowchart, orgchart, tree, timeline, concept map.

### Excalidraw (Hand-drawn, Casual)
Select when user requests:
- Sketch/rough: "草图", "手绘", "涂鸦"
- Brainstorming: "头脑风暴", "白板", "讨论"
- Casual/draft: "随意的", "初稿", "快速画一下"

Preferred Excalidraw types: mindmap, concept map, brainstorming diagram.

### Ambiguous Types
For flowcharts, org charts, trees, timelines — default to Draw.io unless user explicitly says "手绘" or "草图". If still ambiguous, apply clarification rules.

## Clarification Rules

Ask BEFORE generating when:

1. **Style ambiguity** — diagram type works with either engine, no style specified.
   Ask: "您希望生成正式的专业图表，还是手绘风格的草图？"

2. **Missing context** — vague description without key entities or relationships.
   Ask: "能否提供更多细节？例如：主要模块有哪些？它们之间如何交互？"

3. **Type unclear** — user says "画个图" without specifying type.
   Ask: "您需要什么类型的图表？例如：流程图、架构图、思维导图、ER图等"

Do NOT ask when description is clear with explicit type and obvious style.

## Generation Workflow

1. **Select engine** using rules above.
2. **Read one guideline file only**:
   - Draw.io: `references/drawio-guidelines.md`
   - Excalidraw: `references/excalidraw-guidelines.md`
3. **Generate code**:

   - Input contract: user description + selected chart type (or `auto`)
   - Output contract:
     - Draw.io: output valid mxGraph XML only
     - Excalidraw: output JSON array of elements only
   - Save generated XML/JSON to a temp file.
4. **Render via CLI**:
   ```bash
   python3 <skill_path>/scripts/render.py <drawio|excalidraw> -f <temp_file> -o <output_path>
   ```
   Options: `--svg` (Excalidraw only, output SVG instead of PNG), `--no-source` (skip saving .drawio/.excalidraw source file)
5. **Parse output** — CLI prints JSON to stdout:
   - Success: `{"status":"success","file":"...","format":"png","size":...,"sourceFile":"..."}`
   - Error: `{"status":"error","error":"错误信息"}`

For diagram type templates, read `references/templates.md`.

## Output Handling

Present results: show image preview + source file path + detailed editing guide (tailored for non-technical users).

Output template (use the appropriate section based on engine):

### Draw.io output message

```
✅ 图表已生成！

📄 图片文件：{outputFile}
📝 源文件：{sourceFile}

🔧 想要自己编辑？按以下步骤操作：

1. 打开浏览器，访问 https://app.diagrams.net
2. 点击左上角「文件」菜单 →「从...打开」→「设备...」
3. 在文件选择窗口中，找到并选中上面的源文件：
   {sourceFile}
4. 图表加载后即可直接编辑（拖拽、修改文字、调整样式等）
5. 编辑完成后，点击「文件」→「导出为」→ 选择 PNG/SVG/PDF 导出

💡 小提示：
- 双击图形可以编辑文字内容
- 拖拽图形边缘的蓝色箭头可以快速连线
- 右侧面板可以修改颜色、字体、线条样式
```

### Excalidraw output message

```
✅ 图表已生成！

📄 图片文件：{outputFile}
📝 源文件：{sourceFile}

🔧 想要自己编辑？按以下步骤操作：

1. 打开浏览器，访问 https://excalidraw.com
2. 点击左上角的菜单按钮「☰」（三条横线图标）
3. 点击「Open」（打开文件）
4. 在文件选择窗口中，找到并选中上面的源文件：
   {sourceFile}
5. 图表加载后即可直接编辑（拖拽、涂鸦、修改文字等）
6. 编辑完成后，点击左上角菜单「☰」→「Export image」→ 选择 PNG/SVG 导出

💡 小提示：
- 双击图形可以编辑文字内容
- 左侧工具栏可以画矩形、圆形、箭头、自由线条等
- 选中图形后，顶部工具栏可以修改颜色、线条粗细、字体大小
- Excalidraw 自带手绘风格，非常适合做草图和头脑风暴
```

## Multi-Turn Iteration

When user requests modifications ("加上...", "改成...", "删掉...", "换个颜色"):
1. Retrieve previous code from conversation history
2. Apply incremental changes (don't regenerate from scratch)
3. Re-render with same engine
4. Maintain context for further iterations

## Known Issues & Troubleshooting

### Draw.io rendering timeout with HTML-formatted values (Fixed)

**Symptom**: `Page.wait_for_selector: Timeout exceeded` when XML contains `&quot;` entities in `value` attributes (e.g., `<font style=&quot;font-size:24px;&quot;>`).

**Root cause**: `render.py` embedded JSON in an HTML `data-mxgraph='...'` attribute without HTML-encoding ampersands. The browser decoded `&quot;` → `"` before `JSON.parse()`, breaking the JSON.

**Fix**: `render.py` line 91 — `json_data.replace('&', '&amp;')` before embedding in HTML attribute.

**Debugging approach for future render failures**:
1. Validate XML: `python3 -c "import xml.etree.ElementTree as ET; ET.parse('file.xml')"`
2. Test minimal XML first to isolate whether the issue is in the XML content or the render pipeline
3. Capture browser console errors: `page.on('console', lambda msg: print(msg.text))`
4. Save the generated HTML to a temp file and inspect it manually
