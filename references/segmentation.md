# 分段与对齐规范（段落全）

目标：长文跨页、跨栏、跨章节时**不漏段、不重复、不错位**，段号与原文一一对应。

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

1. 覆盖要素：标题、摘要、各级标题、正文段、图题、表头/表注、脚注、公式（含编号）、文献引用标记。
2. 位置记 `page/col/para`，句子边界记到 `s`（如 `p2-col1-para2-s3`）。
3. **跨页/跨栏接续**：一段被页码或分栏截断时合并为一段，`cont_from` 指向被截断的前段；接续处不另起段号。
4. **不重复**：同一原文段只对应一个 `seg_id`；**不错位**：译文段的 `seg_id` 与原文段号严格对应。
5. 抽取结果由 `pdf-text-tool` 的结构化文本生成；若工具只给纯文本，按空行/标题模式/段落缩进启发式切分，并在 `limits` 注明"启发式分段"。

## 对齐输出（bilingual_segments）

每段：`seg_id + location + source + translation + rationale + uncertain`。`source` 必须逐字保留（公式、数字、单位、引用标记不改写）。

## 完整性校验

阶段 4 用 `scripts/check_segments.py`：
- `--inventory inventory.json`（基准段号清单）
- `--result segments.json`（译文段，含 `seg_id`）
- 校验：每个 inventory `seg_id` 在 result 中**恰好出现一次**，无缺段、无重段、无多余段；任何不一致都返回非零退出码。
