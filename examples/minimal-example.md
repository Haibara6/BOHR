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

1. 读 `case.json`/`task.md` → 记录 `case_id=demo-001`、范围 `p2–3`、`output_contract` 字段清单（`summary`、`bilingual_segments`）、保留策略（默认 `annotate`）。
2. `pdf-text-tool` 抽取 p2–3 结构化文本 → 建 `work/inventory.json`（S001…S00n）。
3. 抽取术语并做词义消歧 → `work/terms.tsv`（义项级，8 列含 retention）并锁定；识别命名实体 → `work/protected_entities.json`。
4. **批量**逐段翻译（每请求 5–10 段），每段必填 `seg_id/location/source/translation`，命中保护清单的实体原样保留 → `work/segments.json`。
5. 校验：
   - `python3 scripts/check_terms.py --terms work/terms.tsv --segments work/segments.json`
   - `python3 scripts/check_segments.py --inventory work/inventory.json --result work/segments.json`
   - `python3 scripts/check_literals.py --segments work/segments.json`
6. 写 `/app/output/result.json`：`output_contract` 声明的 `summary`、`bilingual_segments` **合并到顶层**。

## 示意输出（片段，标记为示例）

`result.json`（注意 `summary` 与 `bilingual_segments` 都在**顶层**）：
```json
{
  "case_id": "demo-001",
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
  "term_table": { "terms": [ { "source_term": "spin-orbit coupling", "sense_id": "soc", "canonical_translation": "自旋-轨道耦合", "domain": "physics", "context_clues": [], "example": "", "notes": "", "retention": "translate" } ], "consistency_report": "1/1 matched" },
  "protected_entities": [ { "type": "abbrev", "text": "DPPH", "location": "p3", "retention": "keep_strict" } ],
  "evidence": [ { "seg_id": "S007", "location": "p2-col1-para2", "type": "paragraph", "source_text": "The spin-orbit coupling drives the transition at 300 K." } ],
  "uncertainty": [],
  "verification": { "term_consistency": "1/1", "segment_completeness": "complete", "literal_retention": "hard_miss=0, unit_warn=0", "relation_checklist": [], "human_confirm": [] },
  "change_records": [],
  "sources": [ { "path": "paper.pdf", "pages": [2, 3], "kind": "pdf" } ],
  "limits": {}
}
```

## 说明

- 上面所有数值与字段为**示例**，不代表任何正式测试成绩或运行日志。
- 正式案例的 `output_contract` 字段以 `case.json` 为准，须**原样合到 `result.json` 顶层**；Skill 自带的 `term_table`/`evidence`/`verification` 等作为附加顶层字段并存。
