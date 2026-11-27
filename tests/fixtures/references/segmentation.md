# 分段与对齐规范（段落全）

目标：长文跨页、跨栏、跨章节时**不漏段、不重复、不错位**，段号与原文一一对应。inventory 只覆盖任务声明的 `scope`；范围外内容不建段，也不计入缺段。

## inventory.json 结构（翻译前建立）

```json
{
  "doc_id": "paper.pdf",
  "pages": 12,
  "segments": [
    {"seg_id":"S001","kind":"title","location":"p1","cont_from":null},
    {"seg_id":"S002","kind":"abstract","location":"p1-col1-para1"},
    {"seg_id":"S007","kind":"paragraph","location":"p2-col1-para2","cont_from":"S006"},
    {"seg_id":"S020","kind":"caption","location":"p4","figure_id":"Fig. 2"},
    {"seg_id":"S031","kind":"formula","location":"p5","formula_id":"(3)"}
  ]
}
```

## 建段规则

1. 覆盖要素：标题、摘要、各级标题、正文段、图题、表头/表注、脚注、公式（含编号）、文献引用标记、作者/机构/DOI/期刊/关键词等元数据。`kind` 取值见 `output-schema.md`：元数据用 `authors/affiliation/doi/journal/keywords` 专用 kind；`reference` 指“正文内引文标记”；`References`/`Bibliography` 著录块整块不译、不建段。**范围内每种可见要素都必须建段**：图题（`caption`）、表头与表注（`table`）、公式及编号（`formula`）、脚注（`footnote`）、各级标题（`heading`）逐页核对，不得因为“只译正文”而漏建——完整性校验只对照清单，清单缺项等于静默漏译。
2. 位置记 `page/col/para`，句子边界记到 `s`（如 `p2-col1-para2-s3`）。
3. **跨页/跨栏接续**：一段被页码或分栏截断时合并为一段，`cont_from` 指向被截断的前段；接续处不另起段号。
4. **不重复**：同一原文段只对应一个 `seg_id`；**不错位**：译文段的 `seg_id` 与原文段号严格对应。
5. 抽取结果由 `pdf-text-tool` 的结构化文本生成；若工具只给纯文本，按空行/标题模式/段落缩进启发式切分，并在 `limits` 注明"启发式分段"。
6. **双栏阅读顺序**：不得把同一视觉行的左右栏文字直接拼接。若抽取结果出现两个栏目同行混杂，应按栏裁剪/分别抽取，先读完左栏再读右栏，并抽查段首、段尾和跨页接续；无法可靠恢复阅读顺序时标 `【待核】`，不要硬猜段义。
7. **上标/下标丢失**：抽取文本中的 `104`、`cm−1` 等可能是上标丢失。涉及分子量、指数、波数、同位素或化学式时，渲染原页核对后再规范化；依据写入 `rationale`，看不清则写 `uncertain`。

## 对齐输出（bilingual_segments）

每段：`seg_id + location + source + translation + rationale + uncertain`。`source` 必须逐字保留（公式、数字、单位、引用标记不改写）。

## 完整性校验

阶段 4 用 `scripts/check_segments.py`：
- `--inventory inventory.json`（基准段号清单）
- `--result segments.json`（译文段，含 `seg_id`）
- 校验：每个 inventory `seg_id` 在 result 中**恰好出现一次**，无缺段、无重段、无多余段；任何不一致都返回非零退出码。
