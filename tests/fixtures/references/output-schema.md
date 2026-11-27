# result.json 输出规范

每个案例返回一份结构化结果，保留输入标识、翻译范围、源/目标语言、主结果、证据定位、运行状态和不确定性。`result.json` 必须同时满足：

1. `case.json.output_contract` 声明的**全部字段原样出现在顶层**：字段名不改、不嵌套、不塞进 `main_result` 等子对象；契约给出类型/结构时按该结构填值。
2. 下列通用字段也放在顶层；`scripts/check_contract.py` 会对核心字段、契约字段和交叉引用做确定性检查。

## 通用字段（全部顶层）

```json
{
  "case_id": "string，必填，来自 case.json",
  "scope": "full | pages:2-4 | sections:... | paragraphs:S001-S020",
  "source_language": "en | de | fr | ...（源语言，默认 en）",
  "target_language": "zh-CN | en | ...（目标语言，默认 zh-CN）",
  "status": "success | partial | unable | refused",
  "status_reason": "string，status 非 success 时说明原因",
  "summary": "string，一句话说明做了什么、覆盖范围",
  "bilingual_segments": [
    {
      "seg_id": "S007",
      "location": "p2-col1-para2-s3",
      "page": 2,
      "kind": "paragraph | title | abstract | heading | caption | table | formula | footnote | reference | authors | affiliation | doi | journal | keywords",
      "source": "原文逐字",
      "translation": "译文",
      "rationale": "高风险段的译法依据；普通直译段可省略",
      "uncertain": "译不准项；无则省略或为 null"
    }
  ],
  "figures": [ { "figure_id": "Fig. 1", "location": "p3", "note": "译文以 bilingual_segments 中 kind=caption 的段为准" } ],
  "tables": [ { "table_id": "Table 2", "location": "p4", "note": "译文以 bilingual_segments 中 kind=caption/table 的段为准" } ],
  "formulas": [ { "formula_id": "(1)", "location": "p2", "latex": "E=mc^2", "translation_note": "符号保留" } ],
  "citations": [ { "marker": "[12]", "location": "p3-para2", "status": "preserved" } ],
  "term_table": { "terms": [ { "source_term":"...", "sense_id":"...", "canonical_translation":"...", "domain":"...", "context_clues":[...], "example":"...", "notes":"...", "retention":"translate|keep|annotate" } ] },
  "protected_entities": [ { "type":"person|org|place|compound|reagent|abbrev", "text":"...", "location":"...", "retention":"keep_strict" } ],
  "evidence": [ { "seg_id": "S007", "location": "p2-col1-para2", "type": "paragraph|caption|table|formula|reference|metadata", "source_text": "..." } ],
  "uncertainty": [ { "seg_id": "S007", "item": "公式编号", "note": "OCR 转写，需人工核对", "severity": "high|medium|low" } ],
  "verification": {
    "term_consistency": { "matched": 15, "assigned": 15, "rate": 1.0, "mismatch_segments": [], "ambiguous_segments": [], "missing_canonical": [], "structural_errors": [] },
    "segment_completeness": { "covered": 20, "inventory": 20, "result": 20, "rate": 1.0, "exact": true, "missing": [], "extra": [], "duplicated": [], "duplicated_inventory": [] },
    "literal_retention": { "hit": 8, "checked": 8, "rate": 1.0, "hard_miss": 0, "hard_miss_items": [], "unit_warn": 0, "soft_warn": 0, "warnings": [] },
    "relation_retention": { "checked": 6, "hit": 5, "rate": 0.8333, "warn_count": 1, "warn_items": [ { "seg_id":"S014", "category":"negation", "markers":["without"] } ] },
    "relation_checklist": [ { "seg_id":"S007", "item":"数字单位", "result":"pass|warn|fail", "note":"" } ],
    "human_confirm": [ { "seg_id":"S007", "item":"单位 5 μm", "result":"warn", "note":"单位软校验未命中，需人工确认" } ],
    "all_hard_checks_pass": true
  },
  "change_records": [ { "time": "ISO 8601", "change": "术语 X 由 Y 改为 Z 并回填", "reason": "..." } ],
  "sources": [ { "path": "paper.pdf", "pages": [2, 3, 4], "kind": "pdf", "extractor": "pdf-text-tool", "renderer": "pdf-render-tool", "ocr": null, "ocr_confidence": null, "version": null } ],
  "term_base": null,
  "limits": { "untranslated": ["S012", "S013"], "unparsed_references": true, "ocr_regions": 2 }
}
```

## 字段与范围规则

- `scope` 必须与任务明确要求的页码、章节或段落区间一致。范围外内容不进入 inventory、术语表和译文，也不算缺段。
- `source_language`/`target_language` 顶层声明语言；主路径先做语言判定，默认 `en → zh-CN`。非英文源或指定其他目标语时，`context_clues` 词干、单位词典与命名实体规则须切换到对应语言，并把实际语言写入这两个字段。脚本目前内置的是英文源 + 中文目标的可机械检查。
- `bilingual_segments` 是核心交付物，放在顶层。每段 `seg_id`、`location`、`page`、`kind`、`source`、`translation` 必填且不可降级。`kind` 新增元数据专用值 `authors/affiliation/doi/journal/keywords`；`reference` 重新定义为“正文内引文标记”，不再表示“参考文献著录块”（`References`/`Bibliography` 整块不译）。
- `figures`/`tables` 只做汇总引用（`figure_id`/`table_id`/`location`/`note`），**不再重复译文**；图题/表头译文的唯一来源是 `bilingual_segments` 中 `kind=caption|table` 的段，避免两处副本不同步。
- `term_table` 只放术语条目；术语一致率**唯一权威来源**是 `verification.term_consistency`，不再在 `term_table` 里手写 `consistency_report`，杜绝两处数字打架。
- `verification` 由 `scripts/build_verification.py` 从四个检查报告自动生成并原样并入。`literal_retention.hard_miss_items`/`warnings` 与 `relation_retention.warn_items` 自带“哪段、哪个字面量/关系”的明细，`result.json` 自身即可定位，不依赖 `work/` 目录。`rate` 取 0–1；没有可检查项时为 `null`。
- `relation_checklist` 与 `human_confirm` 统一使用 `{seg_id, item, result, note}` 结构；`result` 取 `pass|warn|fail`。
- `evidence` 至少覆盖关键结论和高风险段；每段自身的 `location + source` 是逐段回查的基本证据。
- `change_records` 每次落盘 `segments.json`/`result.json` 都追加一条带 ISO 8601 时间戳的记录，中断后可追溯已完成批次。
- `sources` 记录抽取工具链与置信信息：`extractor`、`renderer`、`ocr`、`ocr_confidence`、`version`，供复现与复核。
- `term_base` 可选：从 `case.json` 或环境注入的持久/领域术语库（对象或版本号）；使用外部术语库时记录其版本，保证可复现。

## output_contract 合并规则（硬规则）

1. 从 `case.json.output_contract` 读出要求保留的全部字段名（可能带类型/路径/默认值）。
2. 在 `result.json` 顶层为每个契约字段建同名键并填实际值；不得改名或嵌套。
3. 若契约字段名与本规范字段重名（如 `summary`、`bilingual_segments`），直接填在顶层该键，不另建子对象。
4. 本规范其余字段作为附加顶层字段并存。
5. 写完 `result.json` 后用 `scripts/check_contract.py --result result.json [--case case.json]` 逐项断言契约字段与结构，非零退出须修正。

## status 语义

- `success`：范围内每段均有原文与译文，`segment_completeness.exact=true`、`all_hard_checks_pass=true`，且没有未解决的 `fail`。
- `partial`：只完成一部分，`limits.untranslated` 列明边界。
- `unable`：材料缺失或无法读取，`status_reason` 写明缺什么、可人工接管位置。
- `refused`：超出能力或与约束冲突，写明理由。

## 硬性要求

- UTF-8，且可被 `json.load` 解析；`case_id` 与输入一致。
- `output_contract` 全部字段在顶层；核心字段 `case_id/scope/source_language/target_language/status/summary/bilingual_segments/verification` 在顶层。
- 无法判断的信息不得写成事实，须进 `uncertainty` 或 `limits`。
- 不编造分数、运行日志、未读到的原文内容或软件状态。
