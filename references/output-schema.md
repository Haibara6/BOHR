# result.json 输出规范

评测端要求每个案例返回一份结构化结果，保留输入标识、主结果、证据/来源定位、运行状态和不确定性。`result.json` 必须同时满足两个来源：

1. `case.json` 中 `output_contract` 声明的**全部字段**：**必须原样出现在 `result.json` 顶层**（字段名不改、不嵌套、不塞进 `main_result` 等子对象）。若契约给出了字段类型/结构，按该结构填值。
2. 本规范定义的通用字段（用于复核与评分），也全部放在顶层。

## 通用字段（全部顶层）

```json
{
  "case_id": "string，必填，来自 case.json",
  "status": "success | partial | unable | refused",
  "status_reason": "string，status 非 success 时说明原因",
  "summary": "string，一句话说明做了什么、覆盖范围",
  "bilingual_segments": [
    {
      "seg_id": "S007",
      "location": "p2-col1-para2-s3",
      "page": 2,
      "kind": "paragraph | title | abstract | heading | caption | table | formula | footnote | reference",
      "source": "原文逐字",
      "translation": "译文",
      "rationale": "译法依据（可选，仅在义项消歧/关系处理/译不准时出现）",
      "uncertain": "译不准项（可选，无则省略或为 null）"
    }
  ],
  "figures": [ { "figure_id": "Fig. 1", "location": "p3", "caption_source": "...", "caption_translation": "...", "note": "..." } ],
  "tables": [ { "table_id": "Table 2", "location": "p4", "header_source": "...", "header_translation": "...", "note": "..." } ],
  "formulas": [ { "formula_id": "(1)", "location": "p2", "latex": "E=mc^2", "translation_note": "符号保留" } ],
  "citations": [ { "marker": "[12]", "location": "p3-para2", "status": "preserved" } ],
  "term_table": { "terms": [ { "source_term":"...", "sense_id":"...", "canonical_translation":"...", "context_clues":[...], "example":"...", "retention":"translate|keep|annotate" } ], "consistency_report": "..." },
  "protected_entities": [ { "type":"person|org|place|compound|reagent|abbrev", "text":"...", "location":"...", "retention":"keep_strict" } ],
  "evidence": [ { "seg_id": "S007", "location": "p2-col1-para2", "type": "paragraph|caption|table|formula|reference", "source_text": "..." } ],
  "uncertainty": [ { "seg_id": "S007", "item": "公式编号", "note": "OCR 转写，需人工核对", "severity": "high|medium|low" } ],
  "verification": { "term_consistency": "...", "segment_completeness": "...", "literal_retention": "...", "relation_checklist": [ ... ] },
  "change_records": [ { "time": "ISO", "change": "术语 X 由 Y 改为 Z 并回填", "reason": "..." } ],
  "sources": [ { "path": "paper.pdf", "pages": [1, 2, 3], "kind": "pdf" } ],
  "limits": { "untranslated": ["S012", "S013"], "unparsed_references": true, "ocr_regions": 2 }
}
```

说明：
- `bilingual_segments` 是核心交付物，放在**顶层**；`figures`/`tables`/`formulas`/`citations` 是可选的结构化补充，也放顶层。不再使用 `main_result` 包裹，避免与 `output_contract` 的顶层字段约定冲突。
- `rationale` 与 `uncertain` 默认省略；只有发生义项消歧、指代/关系特殊处理、保留策略生效或译不准时才写。**`seg_id`、`location`、`source`、`translation` 每段必填，不可降级。**

## output_contract 合并规则（硬规则）

1. 从 `case.json.output_contract` 读出要求保留的全部字段名（可能带类型/路径/默认值）。
2. 在 `result.json` 中**为每个契约字段在顶层建同名键**，填入本 Skill 实际产生的值；不得改名、不得嵌套。
3. 若契约字段名与本规范字段重名（如 `summary`、`bilingual_segments`），直接填在顶层该键，不另建子对象。
4. 本规范的其余字段作为附加顶层字段并存。

## status 语义

- `success`：范围内全部完成且关键结果可核验（每段都有 `source+translation`，脚本校验通过）。
- `partial`：完成一部分，`limits.untranslated` 列明边界。
- `unable`：材料缺失/无法读取，`status_reason` 写明缺什么、可人工接管位置。
- `refused`：超出能力或与约束冲突，写明理由。

## 硬性要求

- 可被 `json.load` 解析；字符串用 UTF-8。
- `case_id` 必须存在且与输入一致。
- `output_contract` 全部字段在顶层。
- 关键结论必须有 `evidence`（页码/段落/图表/字段/公式位置）。
- 无法判断的信息**不得写成事实**，须进 `uncertainty` 或 `limits`。
- 不编造分数、运行日志、未读到的原文内容或软件状态。
