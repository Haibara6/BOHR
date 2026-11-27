# 最小调用示例（示意，非正式案例）

> 本文件内容均为**示意**，用于说明接口与流程；不冒充正式案例结果。正式案例与白板由平台提供。

## 输入

`/input/case.json`（片段）：
```json
{
  "case_id": "demo-001",
  "task": "把论文第 2–3 页翻译成双语对照，术语统一，保留证据定位",
  "materials": ["paper.pdf"],
  "output_contract": { "required_fields": ["summary", "bilingual_segments"] }
}
```

`/input/task.md`：要求按原文逐段翻译、保留段号与页码、产出术语表与核验清单。

## 调用方式（Agent 按 SKILL.md 执行）

1. 读输入，确定 `case_id=demo-001`、`scope=pages:2-3`、`source_language=en`、`target_language=zh-CN`、契约字段和保留策略；第 2–3 页以外不处理。
2. 只抽取第 2–3 页，建立 `work/inventory.json`；从范围内文本生成 `work/terms.tsv` 和 `work/protected_entities.json`。
3. 每次请求翻译 5–10 段，每批更新 `work/segments.json`；高风险段写 `rationale`。
4. 校验并生成量化报告：

   ```bash
   python3 scripts/check_terms.py --terms work/terms.tsv --segments work/segments.json --json-out work/terms.report.json
   python3 scripts/check_segments.py --inventory work/inventory.json --result work/segments.json --json-out work/segments.report.json
   python3 scripts/check_literals.py --segments work/segments.json --json-out work/literals.report.json
   python3 scripts/check_relations.py --segments work/segments.json --json-out work/relations.report.json
   python3 scripts/build_verification.py --terms-report work/terms.report.json --segments-report work/segments.report.json --literals-report work/literals.report.json --relations-report work/relations.report.json --out work/verification.json
   ```

5. 写 `/app/output/result.json`：契约字段在顶层，`work/verification.json` 原样并入 `verification`，再运行 `check_contract.py` 校验契约与结构。

## 示意输出（片段，标记为示例）

```json
{
  "case_id": "demo-001",
  "scope": "pages:2-3",
  "source_language": "en",
  "target_language": "zh-CN",
  "status": "success",
  "summary": "(示例) 已译第 2–3 页全部段落，术语一致，段落完整，字面量保留。",
  "bilingual_segments": [
    {
      "seg_id": "S007",
      "location": "p2-col1-para2",
      "page": 2,
      "kind": "paragraph",
      "source": "The spin-orbit coupling drives the transition at 300 K.",
      "translation": "自旋-轨道耦合在 300 K 下驱动了该相变。",
      "rationale": "spin-orbit coupling 用锁定译名；transition 依上下文译「相变」；300 K 原样保留。",
      "uncertain": null
    }
  ],
  "term_table": { "terms": [ { "source_term": "spin-orbit coupling", "sense_id": "soc", "canonical_translation": "自旋-轨道耦合", "domain": "physics", "context_clues": [], "example": "", "notes": "", "retention": "translate" } ] },
  "protected_entities": [ { "type": "abbrev", "text": "DPPH", "location": "p3", "retention": "keep_strict" } ],
  "evidence": [ { "seg_id": "S007", "location": "p2-col1-para2", "type": "paragraph", "source_text": "The spin-orbit coupling drives the transition at 300 K." } ],
  "uncertainty": [],
  "verification": {
    "term_consistency": { "matched": 1, "assigned": 1, "rate": 1.0, "mismatch_segments": [], "ambiguous_segments": [], "missing_canonical": [], "structural_errors": [] },
    "segment_completeness": { "covered": 1, "inventory": 1, "result": 1, "rate": 1.0, "exact": true, "missing": [], "extra": [], "duplicated": [], "duplicated_inventory": [] },
    "literal_retention": { "hit": 0, "checked": 0, "rate": null, "hard_miss": 0, "hard_miss_items": [], "unit_warn": 0, "soft_warn": 0, "warnings": [] },
    "relation_retention": { "checked": 0, "hit": 0, "rate": null, "warn_count": 0, "warn_items": [] },
    "relation_checklist": [ { "seg_id": "S007", "item": "数字单位", "result": "pass", "note": "300 K 保留" } ],
    "human_confirm": [],
    "all_hard_checks_pass": true
  },
  "change_records": [],
  "sources": [ { "path": "paper.pdf", "pages": [2, 3], "kind": "pdf", "extractor": "pdf-text-tool", "renderer": null, "ocr": null, "ocr_confidence": null, "version": null } ],
  "limits": {}
}
```

## 说明

- 上面所有数值与字段为**示例**，不代表任何正式测试成绩或运行日志。
- 正式案例的 `output_contract` 字段以 `case.json` 为准，须原样合到 `result.json` 顶层；Skill 自带字段作为附加顶层字段并存。
- `verification.term_consistency` 是术语一致率的唯一权威来源；`term_table` 不再重复写 `consistency_report`。
