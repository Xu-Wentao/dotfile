---
name: pptx
description: "支持创建、编辑、读取和整理 PPT 演示文稿，可用于汇报、提案、课件、路演等场景，也能处理模板、版式、备注、批注及页面内容调整，方便快速生成结构清晰、视觉统一的 .pptx 文件。"
name_cn: "PPT助手"
description_cn: "支持创建、编辑、读取和整理 PPT 演示文稿，可用于汇报、提案、课件、路演等场景，也能处理模板、版式、备注、批注及页面内容调整，方便快速生成结构清晰、视觉统一的 .pptx 文件。"
license: Proprietary. LICENSE.txt has complete terms
---

# PPTX/PPT创建、编辑和分析

## 概述

用户可能要求你创建、编辑或分析.pptx或.ppt文件的内容。.pptx文件本质上是一个ZIP压缩包，包含XML文件和其他资源，你可以读取或编辑。.ppt是旧版PowerPoint格式，需要先转换为.pptx。

### 中文优化特性

本skill针对中文办公场景进行了特别优化：

- **中文触发词**：ppt、幻灯片、演示文稿
- **中文字体支持**：微软雅黑、思源黑体、思源宋体、阿里巴巴普惠体、华文细黑等
- **中国风配色方案**：科技蓝、党政红金、淡雅水墨、新中式、商务深灰等
- **中文排版规则**：遵循CJK排版规范，包括行首行尾禁则、中英文间距、字号对照等

# PPTX creation, editing, and analysis

## Overview

A user may ask you to create, edit, or analyze the contents of a .pptx file. A .pptx file is essentially a ZIP archive containing XML files and other resources that you can read or edit. You have different tools and workflows available for different tasks.

## Content Preprocessing（内容预处理 - MANDATORY）

**CRITICAL**: 在开始创建或修改任何PPT之前，必须先完成内容规划。直接动手生成PPT而不做规划，是导致内容混乱、信息丢失、排版灾难的根因。

**MANDATORY - READ ENTIRE FILE**: Read [`content_planner.md`](content_planner.md) completely before any PPT creation or editing task. This guide covers:
- 需求分析与内容结构化（从自然语言中提取结构化数据）
- 内容提炼与信息分层（提炼要点而非搬运原文）
- 页面规划与大纲设计
- 内容-模板映射（评估内容密度、类型与模板匹配度）
- 文字截断预防
- 质量自查清单

### Quick Reference: Content Preprocessing Checklist

在动手写任何代码之前，必须完成以下步骤：

1. **结构化提取**：将用户需求整理为结构化表格/列表，确保所有条目完整、无遗漏
2. **内容精简**：每页文字控制在80字以内，每条要点不超过25字
3. **受众适配**：根据受众类型（技术专家/小白/管理层）调整内容深度
4. **页面大纲**：先写出完整的页面大纲，包含每页标题和要点
5. **模板映射**：评估每页内容密度，选择匹配的模板布局
6. **截断预防**：计算目标shape可容纳的字符数，超长内容先精简再填充

### 强制规则
1. 关于解决方案的说明，**只允许输出 1 次**，输出后永久禁止重复打印。
2. 一旦确认解决方案，立即进入代码编写环节，不再重复描述原因。
3. 禁止循环输出相同的解决方案描述。

### 从外部内容源创建PPT时的特殊要求

当用户要求"基于PDF/文档内容创建PPT"时，**绝对禁止逐字搬运原文**：

- **提炼而非复制**：每页提取1-2个核心论点，精简为≤25字的要点
- **信息分层**：原文 → 核心论点 → 幻灯片文字 → 可视化图表
- **术语处理**：对小白受众，每个专业术语必须附带简短解释或类比
- **视觉优先**：能用图表/图示表达的，不用文字；能用关键词的，不用完整句子

## Reading and analyzing content

### Text extraction
If you just need to read the text contents of a presentation, you should convert the document to markdown:

```bash
# Convert document to markdown
python -m markitdown path-to-file.pptx
```

### Raw XML access
You need raw XML access for: comments, speaker notes, slide layouts, animations, design elements, and complex formatting. For any of these features, you'll need to unpack a presentation and read its raw XML contents.

#### Unpacking a file
`python ooxml/scripts/unpack.py <office_file> <output_dir>`

**Note**: The unpack.py script is located at `skills/pptx/ooxml/scripts/unpack.py` relative to the project root. If the script doesn't exist at this path, use `find . -name "unpack.py"` to locate it.

#### Key file structures
* `ppt/presentation.xml` - Main presentation metadata and slide references
* `ppt/slides/slide{N}.xml` - Individual slide contents (slide1.xml, slide2.xml, etc.)
* `ppt/notesSlides/notesSlide{N}.xml` - Speaker notes for each slide
* `ppt/comments/modernComment_*.xml` - Comments for specific slides
* `ppt/slideLayouts/` - Layout templates for slides
* `ppt/slideMasters/` - Master slide templates
* `ppt/theme/` - Theme and styling information
* `ppt/media/` - Images and other media files

#### Typography and color extraction
**When given an example design to emulate**: Always analyze the presentation's typography and colors first using the methods below:
1. **Read theme file**: Check `ppt/theme/theme1.xml` for colors (`<a:clrScheme>`) and fonts (`<a:fontScheme>`)
2. **Sample slide content**: Examine `ppt/slides/slide1.xml` for actual font usage (`<a:rPr>`) and colors
3. **Search for patterns**: Use grep to find color (`<a:solidFill>`, `<a:srgbClr>`) and font references across all XML files

## Creating a new PowerPoint presentation **without a template**

### Workflow: Creating from Scratch (PptxGenJS)

**Use when no template or reference presentation is available.**
**CRITICAL**: You MUST read the relevant reference files in the `references/` directory before and during the generation process to ensure correct API usage and styling.

#### Step 1: Research & Requirements
Search to understand user requirements — topic, audience, purpose, tone, content depth.

#### Step 2: Select Color Palette & Fonts
Use the [Design System](references/design-system.md) to select a palette matching the topic. For Chinese text, prioritize the Typography Guidelines listed above (e.g., Microsoft YaHei).

#### Step 3: Select Design Style
Use the Style Recipes in the [Design System](references/design-system.md) to choose a visual style (Sharp, Soft, Rounded, or Pill) matching the presentation tone.

#### Step 4: Plan Slide Outline
Classify **every slide** as exactly one of the 5 page types detailed in [Slide Types](references/slide-types.md). Plan the content and layout. Ensure visual variety.

#### Step 5: Generate Slide JS Files
Create one JS file per slide in the `slides/` directory. Each file must export a synchronous `createSlide(pres, theme)` function.
- **CRITICAL API REFERENCE**: You MUST read [PptxGenJS Reference](references/pptxgenjs.md) for the exact API syntax for adding text, shapes, and charts. 
- Tell subagents to strictly follow the Theme Object Contract and Slide Output Format specified in the references.

#### Step 6: Compile into Final PPTX
Create `slides/compile.js` to combine all slide modules.

#### Step 7: QA (Required)
You MUST read [Pitfalls & QA](references/pitfalls.md) and execute the QA process to catch common rendering errors before finalizing the PPTX.

### Design Principles

**CRITICAL**: Before creating any presentation, analyze the content and choose appropriate design elements:
1. **Consider the subject matter**: What is this presentation about? What tone, industry, or mood does it suggest?
2. **Check for branding**: If the user mentions a company/organization, consider their brand colors and identity
3. **Match palette to content**: Select colors that reflect the subject
4. **State your approach**: Explain your design choices before writing code

**Requirements**:
- ✅ State your content-informed design approach BEFORE writing code
- ✅ Use appropriate fonts based on content language:
  - **中文内容（推荐）**：微软雅黑、思源黑体、思源宋体、阿里巴巴普惠体、华文细黑
  - **英文内容/通用**：Arial, Helvetica, Times New Roman, Georgia, Courier New, Verdana, Tahoma, Trebuchet MS, Impact
  - **Web-safe fonts（兼容性）**：上述所有字体均为常用字体，跨平台兼容性好
- ✅ Create clear visual hierarchy through size, weight, and color
- ✅ Ensure readability: strong contrast, appropriately sized text, clean alignment
- ✅ Be consistent: repeat patterns, spacing, and visual language across slides
- ✅ For Chinese content, prefer "微软雅黑" (Microsoft YaHei) as default font family

#### Color Palette Selection

**Choosing colors creatively**:
- **Think beyond defaults**: What colors genuinely match this specific topic? Avoid autopilot choices.
- **Consider multiple angles**: Topic, industry, mood, energy level, target audience, brand identity (if mentioned)
- **Be adventurous**: Try unexpected combinations - a healthcare presentation doesn't have to be green, finance doesn't have to be navy
- **Build your palette**: Pick 3-5 colors that work together (dominant colors + supporting tones + accent)
- **Ensure contrast**: Text must be clearly readable on backgrounds

**Example color palettes** (use these to spark creativity - choose one, adapt it, or create your own):

### 中国风配色方案（Chinese Style Palettes - 适用于中文内容）

C1. **科技蓝**：科技蓝 (#0052D9), 深蓝 (#0033A0), 浅蓝 (#E6F0FF), 白色 (#FFFFFF)
C2. **党政红金**：中国红 (#DE2910), 金色 (#FFD700), 深红 (#8B0000), 米白 (#FFF8DC)
C3. **淡雅水墨**：墨黑 (#2C2C2C), 灰色 (#808080), 浅灰 (#D3D3D3), 宣纸白 (#F5F5DC)
C4. **新中式**：朱砂红 (#E86161), 青瓷色 (#7FB068), 米黄 (#F2E6CE), 深灰 (#4A4A4A)
C5. **商务深灰**：深灰 (#333333), 中灰 (#666666), 浅灰 (#CCCCCC), 白色 (#FFFFFF)
C6. **竹韵青**：竹青 (#789262), 浅绿 (#B5C99A), 米白 (#F7F7F0), 深绿 (#2F4F4F)
C7. **紫气东来**：紫罗兰 (#9370DB), 浅紫 (#DDA0DD), 金黄 (#FFD700), 白色 (#FFFFFF)
C8. **江南烟雨**：青灰 (#6B7A8F), 浅蓝灰 (#A8B8C8), 灰白 (#D9E4EC), 深蓝 (#2C3E50)

### 国际通用配色方案（International Palettes）

1. **Classic Blue**: Deep navy (#1C2833), slate gray (#2E4053), silver (#AAB7B8), off-white (#F4F6F6)
2. **Teal & Coral**: Teal (#5EA8A7), deep teal (#277884), coral (#FE4447), white (#FFFFFF)
3. **Bold Red**: Red (#C0392B), bright red (#E74C3C), orange (#F39C12), yellow (#F1C40F), green (#2ECC71)
4. **Warm Blush**: Mauve (#A49393), blush (#EED6D3), rose (#E8B4B8), cream (#FAF7F2)
5. **Burgundy Luxury**: Burgundy (#5D1D2E), crimson (#951233), rust (#C15937), gold (#997929)
6. **Deep Purple & Emerald**: Purple (#B165FB), dark blue (#181B24), emerald (#40695B), white (#FFFFFF)
7. **Cream & Forest Green**: Cream (#FFE1C7), forest green (#40695B), white (#FCFCFC)
8. **Pink & Purple**: Pink (#F8275B), coral (#FF574A), rose (#FF737D), purple (#3D2F68)
9. **Lime & Plum**: Lime (#C5DE82), plum (#7C3A5F), coral (#FD8C6E), blue-gray (#98ACB5)
10. **Black & Gold**: Gold (#BF9A4A), black (#000000), cream (#F4F6F6)
11. **Sage & Terracotta**: Sage (#87A96B), terracotta (#E07A5F), cream (#F4F1DE), charcoal (#2C2C2C)
12. **Charcoal & Red**: Charcoal (#292929), red (#E33737), light gray (#CCCBCB)
13. **Vibrant Orange**: Orange (#F96D00), light gray (#F2F2F2), charcoal (#222831)
14. **Forest Green**: Black (#191A19), green (#4E9F3D), dark green (#1E5128), white (#FFFFFF)
15. **Retro Rainbow**: Purple (#722880), pink (#D72D51), orange (#EB5C18), amber (#F08800), gold (#DEB600)
16. **Vintage Earthy**: Mustard (#E3B448), sage (#CBD18F), forest green (#3A6B35), cream (#F4F1DE)
17. **Coastal Rose**: Old rose (#AD7670), beaver (#B49886), eggshell (#F3ECDC), ash gray (#BFD5BE)
18. **Orange & Turquoise**: Light orange (#FC993E), grayish turquoise (#667C6F), white (#FCFCFC)

#### Visual Details Options

**Geometric Patterns**:
- Diagonal section dividers instead of horizontal
- Asymmetric column widths (30/70, 40/60, 25/75)
- Rotated text headers at 90° or 270°
- Circular/hexagonal frames for images
- Triangular accent shapes in corners
- Overlapping shapes for depth

**Border & Frame Treatments**:
- Thick single-color borders (10-20pt) on one side only
- Double-line borders with contrasting colors
- Corner brackets instead of full frames
- L-shaped borders (top+left or bottom+right)
- Underline accents beneath headers (3-5pt thick)

**Typography Treatments**:
- Extreme size contrast (72pt headlines vs 11pt body)
- All-caps headers with wide letter spacing
- Numbered sections in oversized display type
- Monospace (Courier New) for data/stats/technical content
- Condensed fonts (Arial Narrow) for dense information
- Outlined text for emphasis

**Chart & Data Styling**:
- Monochrome charts with single accent color for key data
- Horizontal bar charts instead of vertical
- Dot plots instead of bar charts
- Minimal gridlines or none at all
- Data labels directly on elements (no legends)
- Oversized numbers for key metrics

**Layout Innovations**:
- Full-bleed images with text overlays
- Sidebar column (20-30% width) for navigation/context
- Modular grid systems (3×3, 4×4 blocks)
- Z-pattern or F-pattern content flow
- Floating text boxes over colored shapes
- Magazine-style multi-column layouts

**Background Treatments**:
- Solid color blocks occupying 40-60% of slide
- Gradient fills (vertical or diagonal only)
- Split backgrounds (two colors, diagonal or vertical)
- Edge-to-edge color bands
- Negative space as a design element

### Layout Tips
**When creating slides with charts or tables:**
- **Two-column layout (PREFERRED)**: Use a header spanning the full width, then two columns below - text/bullets in one column and the featured content in the other. This provides better balance and makes charts/tables more readable. Use flexbox with unequal column widths (e.g., 40%/60% split) to optimize space for each content type.
- **Full-slide layout**: Let the featured content (chart/table) take up the entire slide for maximum impact and readability
- **NEVER vertically stack**: Do not place charts/tables below text in a single column - this causes poor readability and layout issues

### 中文排版规则（Chinese Typography Guidelines）

#### 字号对照表（Font Size Reference）

中文常用字号与磅值(pt)对照：

| 中文称呼 | 磅值(pt) | 英文近似 | 用途 |
|---------|---------|---------|------|
| 初号 | 42pt | - | 标题/封面 |
| 小初 | 36pt | - | 大标题 |
| 一号 | 26pt | 32pt | 主标题 |
| 小一 | 24pt | 28pt | 副标题 |
| 二号 | 22pt | 24pt | 二级标题 |
| 小二 | 18pt | 20pt | 三级标题 |
| 三号 | 16pt | 18pt | 正文大标题 |
| 小三 | 15pt | 16pt | 正文小标题 |
| 四号 | 14pt | 14pt | 正文标题 |
| 小四 | 12pt | 12pt | **正文默认** |
| 五号 | 10.5pt | 10pt | 小字正文 |
| 小五 | 9pt | 9pt | 注释/说明 |

**推荐使用**：
- 标题：18-24pt（小二至二号）
- 正文：12-14pt（小四至四号）
- 注释：9-10pt（小五至五号）

#### 行首行尾禁则（Line Start/End Prohibition Rules）

以下标点符号不应出现在行首或行尾：

**不应出现在行尾**（需要与后续字符保持在一起）：
- 开括号：`(` `（` `[` `【` `{` `「` `『`
- 前置标点：`"` `"` `'` `'`

**不应出现在行首**（需要与前置字符保持在一起）：
- 闭括号：`)` `）` `]` `】` `}` `」` `』`
- 后置标点：`,` `,` `.` `.` `;` `；` `:` `：` `!` `！` `?` `？`
- 省略号：`......` `……`
- 破折号：`——`

#### 中英文间距（Chinese-English Spacing）

在中文字符与英文字符/数字之间添加适当间距（约0.25em）：

**示例**：
- ❌ 错误：使用PowerPoint创建演示文稿
- ✅ 正确：使用 PowerPoint 创建演示文稿
- ❌ 错误：2024年度报告
- ✅ 正确：2024 年度报告

**实现方式**（在HTML/CSS中）：
```css
.chinese-text {
    letter-spacing: 0.05em;
}
.chinese-text + .english-text,
.chinese-text + .number {
    margin-left: 0.25em;
}
```

#### 推荐的中文字体设置

**默认字体栈**（按优先级排序）：
```css
font-family: "Microsoft YaHei", "微软雅黑", "Source Han Sans CN",
             "思源黑体", "Alibaba PuHuiTi", "阿里巴巴普惠体",
             "STHeiti", "华文细黑", "SimHei", "黑体",
             sans-serif;
}
```

**标题使用**（更有力量感）：
- "Microsoft YaHei Bold" / "微软雅黑 Bold"
- "Source Han Sans CN Bold" / "思源黑体 Bold"

**正文使用**（易读性优先）：
- "Microsoft YaHei" / "微软雅黑"
- "Alibaba PuHuiTi" / "阿里巴巴普惠体"

#### 标点符号使用规范

**中文标点符号优先**：
- 在纯中文文本中使用中文标点：`，。；：？！""''（）【】`
- 在中英混排文本中，根据前后内容选择合适的标点

**数字与单位**：
- 数字与中文单位之间不加空格：100元、50公斤、25%
- 英文单位前加空格：100 kg, 25 %, 30 px

### PPT旧格式支持（Legacy PPT Format Support）

#### 转换旧版PPT为PPTX

当用户提供`.ppt`格式文件（旧版PowerPoint格式）时，需要先转换为`.pptx`格式：

```bash
# 使用LibreOffice进行格式转换
soffice --headless --convert-to pptx input.ppt
```

**注意事项**：
- 转换后的文件可能需要检查格式兼容性
- 某些旧版特效可能无法完美转换
- 建议转换后进行视觉验证

**自动检测与转换脚本**：
```bash
# 检测文件格式并自动转换
python scripts/convert_legacy_ppt.py input.ppt output.pptx
```

## Editing an existing PowerPoint presentation

### CRITICAL: Choose the right editing approach (Dual-Track Routing)

Before editing an existing PPT, you MUST choose the appropriate track based on task complexity.

#### Track A: Lightweight Template Editing (Fast Path)
- **Use Cases**: Basic text replacement, title updates, or lightweight content editing using an existing template (no complex layout restructuring).
- **Action**: You MUST read and follow the [Editing Presentations](references/editing.md) guide. Use this as the primary method for medium/light editing tasks.

#### Track B: High-Fidelity/Structural Editing (High-Fidelity Structural Path)
- **Use Cases**: Table modifications (e.g., Gantt charts), complex shape alignment, XML-level refinement, or strict brand asset preservation (backgrounds, logos).
- **Action**: Use the OOXML workflow (`unpack.py` -> edit XML -> `pack.py`). You MUST strictly follow the "Pre-Edit Content Structuring (MANDATORY)" and "Table & Dense Content Editing" sections below to prevent layout corruption.

### 编辑前内容结构化预处理（MANDATORY）

**CRITICAL**: 在编辑任何现有PPT之前，**必须先完成内容结构化预处理**。直接拿到需求就写代码修改PPT，是导致内容遗漏、文字截断、布局混乱的根因。

#### 步骤1：结构化提取用户需求

将用户以自然语言描述的需求，提取为结构化表格：

```markdown
| 序号 | 任务名称 | 执行人 | 开始日期 | 结束日期 | 阶段 |
|------|---------|--------|----------|----------|------|
| 1    | 完成集团党建工作满意度测评 | 各支部 | 1月5日 | 1月9日 | 筹备期 |
| 2    | 完成党费基数核算及党费补缴方案 | — | 1月7日 | 1月9日 | 筹备期 |
| ...  | ... | ... | ... | ... | ... |
```

#### 步骤2：分析PPT结构并做内容映射规划

在动手修改之前，必须先完成以下规划：

1. **确定新内容与原PPT结构的映射关系**：
   - 原PPT有几行几列？分别对应什么含义（日期？任务？阶段？）
   - 新内容的每一项应该放在哪一行、哪一列？
   - 是否有跨行/跨列的情况？如何处理？

2. **测量目标单元格/形状的可用空间**：
   - 使用 `inventory.py` 获取每个shape的尺寸（left, top, width, height，单位英寸）
   - 计算可容纳字符数：`(宽度英寸 × 96 / 字号pt) × 行数`（96为每英寸CSS像素数）
   - **如果新内容超出可容纳字符数，必须先精简内容**

3. **文字精简策略**（按优先级）：
   - 去除冗余词汇，保留关键动作+对象（如"制作确定2026年党费预算上会版" → "制作2026年党费预算"）
   - 缩小字号（下限不低于7pt，低于7pt在投影时不可读）
   - 拆分到多个单元格/形状
   - **绝对禁止：用代码截断文字（如 `name[:13] + "…"`）**

#### 步骤3：输出修改方案并获得确认

对于复杂编辑任务，先输出修改方案（文字版），说明：
- 每个位置对应的新内容是什么
- 文字是否需要精简、如何精简
- 哪些位置可能放不下完整内容

然后再开始写代码。

### 表格/密集内容编辑指南（Table & Dense Content Editing）

当编辑包含表格、甘特图、时间线等密集信息的PPT时，**必须在修改前先分析表格结构**：

#### 修改前必做步骤

1. **Unpack并分析表格结构**：
    ```bash
    python ooxml/scripts/unpack.py template.pptx unpacked
    ```
    - 定位表格所在的 slide XML 文件（`ppt/slides/slide1.xml`）
    - 分析 `<a:tbl>` 结构：行数、列数、合并单元格、列宽
    - 分析每个单元格 `<a:tc>` 的内容结构

2. **完整记录表格结构**：
    在修改前，先用表格形式记录原始结构：
    ```markdown
    ## 表格结构分析
    - 行数：X行（含表头）
    - 列数：Y列
    - 列宽（EMU）：[col1, col2, ...]
    - 合并单元格：[描述哪些单元格被合并]
    - 每个单元格的原始内容：[记录]
    ```

3. **测量单元格可用空间**：
    - 从列宽（EMU）计算英寸：`宽度英寸 = EMU值 / 914400`
    - 估算可容纳字符数：`(宽度英寸 × 72 / 字号) × 行数`
    - **如果新内容超出可容纳字符数，必须先精简内容**

#### 表格文字修改规则

**CRITICAL RULES**:

1. **完整性优先**：宁可缩小字号，也不截断文字
   - ❌ "完成党支部履职文"（被截断）
   - ✅ "完成党支部履职文化铭牌设计制作"（完整）或精简为"履职文化铭牌制作"

2. **先精简，再填充**：
   - 如果单元格宽度有限，先提炼任务/条目名称的核心信息
   - 去除冗余词汇，保留关键动作+对象
   - 例如："制作确定2026年党费预算上会版" → "制作2026年党费预算（上会版）"

3. **保持结构一致**：
   - 不要改变表格的行列数（除非用户明确要求）
   - 不要改变合并单元格的结构
   - 不要改变列宽比例（除非需要适应新内容）

4. **验证文字完整性**：
   - 修改后检查每个单元格的文字是否完整
   - 特别注意长任务名称是否被截断
   - 使用 inventory.py 检测文字溢出

5. **保留原始样式**：
   - 复制原始 `<a:rPr>` 的格式属性（字号、字体、颜色、加粗等）
   - 不要引入新的字体或颜色
   - 不要改变对齐方式

#### 时间线/甘特图特殊注意事项（CRITICAL - 常见问题高发区）

编辑甘特图等时间线型PPT时，历史执行中频繁出现表格结构混乱、条形未对齐、文字溢出等问题。**必须严格遵循以下流程**：

##### Step 1: 完整分析原始表格结构（MANDATORY - 不要跳过）

在动手修改任何内容之前，必须完整记录原始表格的**每一个细节**：

```markdown
## 甘特图结构分析（MANDATORY）

### 表格基本信息
- 表格所在：Group Shape内（名称：xxx）
- 行数：X行（含表头行、日期行、任务行）
- 列数：Y列
- 每列含义：[描述每列代表什么——日/周/月？]
- 列宽（EMU）：[col1, col2, ...]

### 原始时间轴映射
- 原始日期范围：[起始日] ~ [结束日]
- 每列对应的日期/时间单位：[第1列=xxx, 第2列=xxx, ...]
- 行结构：[哪行是表头、哪行是日期、哪些行是任务]

### 浮动条形（甘特条）信息
- 条形数量：X个
- 每个条形的位置（x, y, width, height）和对应行
- 每个条形的内容和颜色

### 品牌元素
- 标题、编号、底部品牌信息的位置和样式
- 阶段标签的位置、颜色和内容
```

##### Step 2: 新内容的时间轴映射规划

**CRITICAL**: 在决定如何修改表格之前，必须先完成新内容到原表格结构的映射：

```markdown
## 时间轴映射规划

### 新内容时间范围
- 最早日期：X月X日
- 最晚日期：X月X日
- 总跨度：约X周

### 列映射方案
原表格有Y列（代表7天/周等），新内容需要适配到同样的列结构：
- 方案A（推荐）：保持原有列结构不变（如按天7列），只修改日期行和任务行
- 方案B：如果新内容的时间跨度与原模板差异大，考虑改变列的时间粒度

### 任务-行映射
| 新任务 | 应放置的行 | 对应的列范围 | 精简后的文字（≤目标字符数） |
|--------|-----------|-------------|--------------------------|
| 任务1  | Row[X]    | Col[Y]-Col[Z] | 精简文字 |
| ...    | ...       | ...          | ... |

### 条形-任务映射
| 条形 | 对应任务 | 新位置(y) | 新宽度(width) | 新文字 |
|------|---------|-----------|--------------|--------|
| Bar1 | 任务1+2  | 需重新计算 | 需重新计算 | 精简文字 |
| ...  | ...     | ...       | ...          | ... |
```

**时间轴映射注意事项**：
- **保持列的时间粒度与原模板一致**——如果原模板按天分列（7列=周日~周六），新内容也应按天分列
- **不要随意改变列的语义**——将"按天"改为"按周"会导致表格结构混乱
- **如果新内容时间跨度超出原表格行数**，考虑精简任务或合并相近日期的任务

##### Step 3: 文字精简与截断预防

在修改甘特图时，文字精简是避免溢出的关键：

1. **测量目标shape的可用空间**：
   - 使用 inventory.py 获取每个条形/单元格的尺寸
   - 估算可容纳字符数：`(宽度英寸 × 96 / 字号pt) × 行数`
   - **特别注意甘特条形**：它们的宽度通常较窄，可用字符数有限

2. **甘特条形文字精简规则**：
   - 优先级1：去除"完成"、"制作"等冗余动词
   - 优先级2：去除年份前缀（如"2026年"可省略，标题已标明年份）
   - 优先级3：使用简称（如"党建工作"→"党建"，"满意度测评"→"满意度测评"保持）
   - **示例**："完成集团党建工作满意度测评" → "党建工作满意度测评" 或 "满意度测评"
   - **绝对禁止**：超出条形宽度的文字不精简直接填入

##### Step 4: 条形重新定位

**CRITICAL**: 如果修改了表格行的内容，必须同步调整浮动条形的位置：

- 条形的 `y` 坐标必须与对应任务行的 `y` 坐标匹配
- 条形的 `width` 必须与任务对应的时间跨度匹配（列数 × 单列宽度）
- 条形的 `height` 应与对应行的高度一致或略小
- 多个条形之间不能重叠
- **使用OOXML workflow精确调整坐标**，不要用python-pptx（坐标精度不足）
##### Step 5: 视觉验证

修改完成后，必须验证：
- [ ] 所有文字完整无截断（特别是甘特条形中的文字）
- [ ] 条形位置与表格行精确对齐
- [ ] 任务名称出现在PPT中某处（不依赖shape与表格的"隐式对应"）
- [ ] 阶段标签正确对应实际日期范围
- [ ] 底部品牌信息已更新
- [ ] 原模板的编号等无关信息已删除或更新
- [ ] 使用 `inventory.py` 检测所有shape的文字溢出情况

### python-pptx 编辑注意事项

当选择使用 python-pptx 库直接编辑PPT时，需要注意以下限制和最佳实践：

#### 已知限制

1. **Group Shape 坐标变换**：
   - 当表格或shape嵌套在 `<p:grpSp>`（Group Shape）内时，python-pptx 的 `shape.left/top/width/height` 返回的是**组内局部坐标**，不是幻灯片绝对坐标
   - 如果需要计算shape在幻灯片上的实际位置，必须手动叠加group的变换矩阵（`<a:xfrm>` 中的 `chOff` 和 `chExt`）
   - **建议**：需要精确坐标对齐时（如甘特条形与表格行对齐），优先使用 OOXML workflow 直接编辑XML

2. **表格操作限制**：
   - python-pptx **不能**：改变表格行列数、合并/拆分单元格、精确控制单元格边框样式
   - python-pptx **可以**：修改单元格文字和填充色、调整列宽
   - 如果需要改变表格结构（行列数），必须用 OOXML workflow

3. **文本shape定位**：
   - python-pptx 无法创建精确对齐到表格单元格的浮动shape
   - 如果原模板有"浮动shape覆盖在表格上"的设计（如甘特条形），用 python-pptx 修改文字后，shape的位置/大小不会自动适应新内容

#### 最佳实践

- **适合用 python-pptx 的场景**：纯文字替换、修改标题/正文内容、简单格式调整
- **不适合用 python-pptx 的场景**：表格结构变更、精确坐标对齐、group内shape操作、甘特图等需要视觉精度的编辑
- **混合使用**：文字类修改用 python-pptx（快速），表格/图形修改用 OOXML（精确），但需注意两种方法可能产生的ID冲突

### Workflow
1. **MANDATORY - READ ENTIRE FILE**: Read [`ooxml.md`](ooxml.md) (~500 lines) completely from start to finish.  **NEVER set any range limits when reading this file.**  Read the full file content for detailed guidance on OOXML structure and editing workflows before any presentation editing.
2. Unpack the presentation: `python ooxml/scripts/unpack.py <office_file> <output_dir>`
3. Edit the XML files (primarily `ppt/slides/slide{N}.xml` and related files)
4. **CRITICAL**: Validate immediately after each edit and fix any validation errors before proceeding: `python ooxml/scripts/validate.py <dir> --original <file>`
5. Pack the final presentation: `python ooxml/scripts/pack.py <input_directory> <office_file>`

## Creating a new PowerPoint presentation **using a template**

When you need to create a presentation that follows an existing template's design, you'll need to duplicate and re-arrange template slides before then replacing placeholder context.

### Workflow
1. **Extract template text AND create visual thumbnail grid**:
   * Extract text: `python -m markitdown template.pptx > template-content.md`
   * Read `template-content.md`: Read the entire file to understand the contents of the template presentation. **NEVER set any range limits when reading this file.**
   * Create thumbnail grids: `python scripts/thumbnail.py template.pptx`
   * See [Creating Thumbnail Grids](#creating-thumbnail-grids) section for more details

2. **Analyze template and save inventory to a file**:
   * **Visual Analysis**: Review thumbnail grid(s) to understand slide layouts, design patterns, and visual structure
   * Create and save a template inventory file at `template-inventory.md` containing:
     ```markdown
     # Template Inventory Analysis
     **Total Slides: [count]**
     **IMPORTANT: Slides are 0-indexed (first slide = 0, last slide = count-1)**

     ## [Category Name]
     - Slide 0: [Layout code if available] - Description/purpose
     - Slide 1: [Layout code] - Description/purpose
     - Slide 2: [Layout code] - Description/purpose
     [... EVERY slide must be listed individually with its index ...]
     ```
   * **Using the thumbnail grid**: Reference the visual thumbnails to identify:
     - Layout patterns (title slides, content layouts, section dividers)
     - Image placeholder locations and counts
     - Design consistency across slide groups
     - Visual hierarchy and structure
   * This inventory file is REQUIRED for selecting appropriate templates in the next step

3. **Create presentation outline based on template inventory**:
   * Review available templates from step 2.
   * Choose an intro or title template for the first slide. This should be one of the first templates.
   * Choose safe, text-based layouts for the other slides.
   * **CRITICAL: Match layout structure to actual content**:
     - Single-column layouts: Use for unified narrative or single topic
     - Two-column layouts: Use ONLY when you have exactly 2 distinct items/concepts
     - Three-column layouts: Use ONLY when you have exactly 3 distinct items/concepts
     - Image + text layouts: Use ONLY when you have actual images to insert
     - Quote layouts: Use ONLY for actual quotes from people (with attribution), never for emphasis
     - Never use layouts with more placeholders than you have content
     - If you have 2 items, don't force them into a 3-column layout
     - If you have 4+ items, consider breaking into multiple slides or using a list format
   * Count your actual content pieces BEFORE selecting the layout
   * Verify each placeholder in the chosen layout will be filled with meaningful content
   * Select one option representing the **best** layout for each content section.
   * Save `outline.md` with content AND template mapping that leverages available designs
   * Example template mapping:
      ```
      # Template slides to use (0-based indexing)
      # WARNING: Verify indices are within range! Template with 73 slides has indices 0-72
      # Mapping: slide numbers from outline -> template slide indices
      template_mapping = [
          0,   # Use slide 0 (Title/Cover)
          34,  # Use slide 34 (B1: Title and body)
          34,  # Use slide 34 again (duplicate for second B1)
          50,  # Use slide 50 (E1: Quote)
          54,  # Use slide 54 (F2: Closing + Text)
      ]
      ```

4. **Duplicate, reorder, and delete slides using `rearrange.py`**:
   * Use the `scripts/rearrange.py` script to create a new presentation with slides in the desired order:
     ```bash
     python scripts/rearrange.py template.pptx working.pptx 0,34,34,50,52
     ```
   * The script handles duplicating repeated slides, deleting unused slides, and reordering automatically
   * Slide indices are 0-based (first slide is 0, second is 1, etc.)
   * The same slide index can appear multiple times to duplicate that slide

5. **Extract ALL text using the `inventory.py` script**:
   * **Run inventory extraction**:
     ```bash
     python scripts/inventory.py working.pptx text-inventory.json
     ```
   * **Read text-inventory.json**: Read the entire text-inventory.json file to understand all shapes and their properties. **NEVER set any range limits when reading this file.**

   * The inventory JSON structure:
      ```json
        {
          "slide-0": {
            "shape-0": {
              "placeholder_type": "TITLE",  // or null for non-placeholders
              "left": 1.5,                  // position in inches
              "top": 2.0,
              "width": 7.5,
              "height": 1.2,
              "paragraphs": [
                {
                  "text": "Paragraph text",
                  // Optional properties (only included when non-default):
                  "bullet": true,           // explicit bullet detected
                  "level": 0,               // only included when bullet is true
                  "alignment": "CENTER",    // CENTER, RIGHT (not LEFT)
                  "space_before": 10.0,     // space before paragraph in points
                  "space_after": 6.0,       // space after paragraph in points
                  "line_spacing": 22.4,     // line spacing in points
                  "font_name": "Arial",     // from first run
                  "font_size": 14.0,        // in points
                  "bold": true,
                  "italic": false,
                  "underline": false,
                  "color": "FF0000"         // RGB color
                }
              ]
            }
          }
        }
      ```

   * Key features:
     - **Slides**: Named as "slide-0", "slide-1", etc.
     - **Shapes**: Ordered by visual position (top-to-bottom, left-to-right) as "shape-0", "shape-1", etc.
     - **Placeholder types**: TITLE, CENTER_TITLE, SUBTITLE, BODY, OBJECT, or null
     - **Default font size**: `default_font_size` in points extracted from layout placeholders (when available)
     - **Slide numbers are filtered**: Shapes with SLIDE_NUMBER placeholder type are automatically excluded from inventory
     - **Bullets**: When `bullet: true`, `level` is always included (even if 0)
     - **Spacing**: `space_before`, `space_after`, and `line_spacing` in points (only included when set)
     - **Colors**: `color` for RGB (e.g., "FF0000"), `theme_color` for theme colors (e.g., "DARK_1")
     - **Properties**: Only non-default values are included in the output

6. **Generate replacement text and save the data to a JSON file**
   Based on the text inventory from the previous step:
   - **CRITICAL**: First verify which shapes exist in the inventory - only reference shapes that are actually present
   - **VALIDATION**: The replace.py script will validate that all shapes in your replacement JSON exist in the inventory
     - If you reference a non-existent shape, you'll get an error showing available shapes
     - If you reference a non-existent slide, you'll get an error indicating the slide doesn't exist
     - All validation errors are shown at once before the script exits
   - **IMPORTANT**: The replace.py script uses inventory.py internally to identify ALL text shapes
   - **AUTOMATIC CLEARING**: ALL text shapes from the inventory will be cleared unless you provide "paragraphs" for them
   - Add a "paragraphs" field to shapes that need content (not "replacement_paragraphs")
   - Shapes without "paragraphs" in the replacement JSON will have their text cleared automatically
   - Paragraphs with bullets will be automatically left aligned. Don't set the `alignment` property on when `"bullet": true`
   - Generate appropriate replacement content for placeholder text
   - Use shape size to determine appropriate content length
   - **CRITICAL**: Include paragraph properties from the original inventory - don't just provide text
   - **IMPORTANT**: When bullet: true, do NOT include bullet symbols (•, -, *) in text - they're added automatically
   - **ESSENTIAL FORMATTING RULES**:
     - Headers/titles should typically have `"bold": true`
     - List items should have `"bullet": true, "level": 0` (level is required when bullet is true)
     - Preserve any alignment properties (e.g., `"alignment": "CENTER"` for centered text)
     - Include font properties when different from default (e.g., `"font_size": 14.0`, `"font_name": "Lora"`)
     - Colors: Use `"color": "FF0000"` for RGB or `"theme_color": "DARK_1"` for theme colors
     - The replacement script expects **properly formatted paragraphs**, not just text strings
     - **Overlapping shapes**: Prefer shapes with larger default_font_size or more appropriate placeholder_type
   - Save the updated inventory with replacements to `replacement-text.json`
   - **WARNING**: Different template layouts have different shape counts - always check the actual inventory before creating replacements

   Example paragraphs field showing proper formatting:
   ```json
   "paragraphs": [
     {
       "text": "New presentation title text",
       "alignment": "CENTER",
       "bold": true
     },
     {
       "text": "Section Header",
       "bold": true
     },
     {
       "text": "First bullet point without bullet symbol",
       "bullet": true,
       "level": 0
     },
     {
       "text": "Red colored text",
       "color": "FF0000"
     },
     {
       "text": "Theme colored text",
       "theme_color": "DARK_1"
     },
     {
       "text": "Regular paragraph text without special formatting"
     }
   ]
   ```

   **Shapes not listed in the replacement JSON are automatically cleared**:
   ```json
   {
     "slide-0": {
       "shape-0": {
         "paragraphs": [...] // This shape gets new text
       }
       // shape-1 and shape-2 from inventory will be cleared automatically
     }
   }
   ```

   **Common formatting patterns for presentations**:
   - Title slides: Bold text, sometimes centered
   - Section headers within slides: Bold text
   - Bullet lists: Each item needs `"bullet": true, "level": 0`
   - Body text: Usually no special properties needed
   - Quotes: May have special alignment or font properties

7. **Apply replacements using the `replace.py` script**
   ```bash
   python scripts/replace.py working.pptx replacement-text.json output.pptx
   ```

   The script will:
   - First extract the inventory of ALL text shapes using functions from inventory.py
   - Validate that all shapes in the replacement JSON exist in the inventory
   - Clear text from ALL shapes identified in the inventory
   - Apply new text only to shapes with "paragraphs" defined in the replacement JSON
   - Preserve formatting by applying paragraph properties from the JSON
   - Handle bullets, alignment, font properties, and colors automatically
   - Save the updated presentation

   Example validation errors:
   ```
   ERROR: Invalid shapes in replacement JSON:
     - Shape 'shape-99' not found on 'slide-0'. Available shapes: shape-0, shape-1, shape-4
     - Slide 'slide-999' not found in inventory
   ```

   ```
   ERROR: Replacement text made overflow worse in these shapes:
     - slide-0/shape-2: overflow worsened by 1.25" (was 0.00", now 1.25")
   ```

## Creating Thumbnail Grids

To create visual thumbnail grids of PowerPoint slides for quick analysis and reference:

```bash
python scripts/thumbnail.py template.pptx [output_prefix]
```

**Features**:
- Creates: `thumbnails.jpg` (or `thumbnails-1.jpg`, `thumbnails-2.jpg`, etc. for large decks)
- Default: 5 columns, max 30 slides per grid (5×6)
- Custom prefix: `python scripts/thumbnail.py template.pptx my-grid`
  - Note: The output prefix should include the path if you want output in a specific directory (e.g., `workspace/my-grid`)
- Adjust columns: `--cols 4` (range: 3-6, affects slides per grid)
- Grid limits: 3 cols = 12 slides/grid, 4 cols = 20, 5 cols = 30, 6 cols = 42
- Slides are zero-indexed (Slide 0, Slide 1, etc.)

**Use cases**:
- Template analysis: Quickly understand slide layouts and design patterns
- Content review: Visual overview of entire presentation
- Navigation reference: Find specific slides by their visual appearance
- Quality check: Verify all slides are properly formatted

**Examples**:
```bash
# Basic usage
python scripts/thumbnail.py presentation.pptx

# Combine options: custom name, columns
python scripts/thumbnail.py template.pptx analysis --cols 4
```

## Converting Slides to Images

To visually analyze PowerPoint slides, convert them to images using a two-step process:

1. **Convert PPTX to PDF**:
   ```bash
   soffice --headless --convert-to pdf template.pptx
   ```

2. **Convert PDF pages to JPEG images**:
   ```bash
   pdftoppm -jpeg -r 150 template.pdf slide
   ```
   This creates files like `slide-1.jpg`, `slide-2.jpg`, etc.

Options:
- `-r 150`: Sets resolution to 150 DPI (adjust for quality/size balance)
- `-jpeg`: Output JPEG format (use `-png` for PNG if preferred)
- `-f N`: First page to convert (e.g., `-f 2` starts from page 2)
- `-l N`: Last page to convert (e.g., `-l 5` stops at page 5)
- `slide`: Prefix for output files

Example for specific range:
```bash
pdftoppm -jpeg -r 150 -f 2 -l 5 template.pdf slide  # Converts only pages 2-5
```

## Code Style Guidelines
**IMPORTANT**: When generating code for PPTX operations:
- Write concise code
- Avoid verbose variable names and redundant operations
- Avoid unnecessary print statements

## Dependencies

Required dependencies (should already be installed):

- **markitdown**: `pip install "markitdown[pptx]"` (for text extraction from presentations)
- **pptxgenjs**: `npm install -g pptxgenjs` (for creating presentations via html2pptx)

- **react-icons**: `npm install -g react-icons react react-dom` (for icons)
- **sharp**: `npm install -g sharp` (for SVG rasterization and image processing)
- **LibreOffice**: `sudo apt-get install libreoffice` (for PDF conversion)
- **Poppler**: `sudo apt-get install poppler-utils` (for pdftoppm to convert PDF to images)
- **defusedxml**: `pip install defusedxml` (for secure XML parsing)
