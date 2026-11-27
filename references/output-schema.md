# result.json 输出规范

每个案例返回一份结构化结果，保留输入标识、翻译范围、主结果、证据定位、运行状态和不确定性。`result.json` 必须同时满足：

1. `case.json.output_contract` 声明的**全部字段原样出现在顶层**：字段名不改、不嵌套、不塞进 `main_result` 等子对象；契约给出类型/结构时按该结构填值。
2. 下列通用字段也放在顶层。

## 通用字段（全部顶层）

```json
{
  "case_id": "string，必填，来自 case.json",
  "scope": "full | pages:2-4 | sections:... | paragraphs:S001-S020",
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
      "rationale": "高风险段的译法依据；普通直译段可省略",
      "uncertain": "译不准项；无则省略或为 null"
    }
  ],
  "figures": [ { "figure_id": "Fig. 1", "location": "p3", "caption_source": "...", "caption_translation": "...", "note": "..." } ],
  "tables": [ { "table_id": "Table 2", "location": "p4", "header_source": "...", "header_translation": "...", "note": "..." } ],
  "formulas": [ { "formula_id": "(1)", "location": "p2", "latex": "E=mc^2", "translation_note": "符号保留" } ],
  "citations": [ { "marker": "[12]", "location": "p3-para2", "status": "preserved" } ],
  "term_table": { "terms": [ { "source_term":"...", "sense_id":"...", "canonical_translation":"...", "context_clues":[...], "example":"...", "retention":"translate|keep|annotate" } ], "consistency_report": "matched/assigned 及一致率" },
  "protected_entities": [ { "type":"person|org|place|compound|reagent|abbrev", "text":"...", "location":"...", "retention":"keep_strict" } ],
  "evidence": [ { "seg_id": "S007", "location": "p2-col1-para2", "type": "paragraph|caption|table|formula|reference", "source_text": "..." } ],
  "uncertainty": [ { "seg_id": "S007", "item": "公式编号", "note": "OCR 转写，需人工核对", "severity": "high|medium|low" } ],
  "verification": {
    "term_consistency": { "matched": 15, "assigned": 15, "rate": 1.0, "mismatch_segments": [], "ambiguous_segments": [] },
    "segment_completeness": { "covered": 20, "inventory": 20, "result": 20, "rate": 1.0, "exact": true, "missing": [], "extra": [], "duplicated": [] },
    "literal_retention": { "hit": 8, "checked": 8, "rate": 1.0, "hard_miss": 0, "unit_warn": 0 },
    "relation_checklist": [ { "seg_id":"S007", "item":"数字单位", "result":"pass|warn|fail", "note":"" } ],
    "human_confirm": [],
    "all_hard_checks_pass": true
  },
  "change_records": [ { "time": "ISO", "change": "术语 X 由 Y 改为 Z 并回填", "reason": "..." } ],
  "sources": [ { "path": "paper.pdf", "pages": [2, 3, 4], "kind": "pdf" } ],
  "limits": { "untranslated": ["S012", "S013"], "unparsed_references": true, "ocr_regions": 2 }
}
```

## 字段与范围规则

- `scope` 必须与任务明确要求的页码、章节或段落区间一致。范围外内容不进入 inventory、术语表和译文，也不算缺段。
- `bilingual_segments` 是核心交付物，放在顶层；`figures`/`tables`/`formulas`/`citations` 是可选补充，也放顶层。
- 每段 `seg_id`、`location`、`source`、`translation` 必填且不可降级。高风险段必须写 `rationale`，其判定与内容见 `references/verification.md`；普通直译段可省略。`uncertain` 在译不准时必填。
- `verification` 的三个量化对象由 `scripts/build_verification.py` 从三个检查报告自动生成，并原样并入结果。`rate` 取 0–1；没有可检查项时为 `null`。不得把实际数字替换成“已检查”等空泛描述。
- `evidence` 至少覆盖关键结论和高风险段；每段自身的 `location + source` 是逐段回查的基本证据。

## output_contract 合并规则（硬规则）

1. 从 `case.json.output_contract` 读出要求保留的全部字段名（可能带类型/路径/默认值）。
2. 在 `result.json` 顶层为每个契约字段建同名键并填实际值；不得改名或嵌套。
3. 若契约字段名与本规范字段重名（如 `summary`、`bilingual_segments`），直接填在顶层该键，不另建子对象。
4. 本规范其余字段作为附加顶层字段并存。

## status 语义

- `success`：范围内每段均有原文与译文，`segment_completeness.exact=true`、`all_hard_checks_pass=true`，且没有未解决的 `fail`。
- `partial`：只完成一部分，`limits.untranslated` 列明边界。
- `unable`：材料缺失或无法读取，`status_reason` 写明缺什么、可人工接管位置。
- `refused`：超出能力或与约束冲突，写明理由。

## 硬性要求

- UTF-8，且可被 `json.load` 解析；`case_id` 与输入一致。
- `output_contract` 全部字段在顶层。
- 无法判断的信息不得写成事实，须进 `uncertainty` 或 `limits`。
- 不编造分数、运行日志、未读到的原文内容或软件状态。
