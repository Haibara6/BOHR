# 核验规范（关系准 + 可核验）

译文正确性不看是否通顺，而看**关系是否保留、能否指回原文**。核验分两层：五个脚本提供确定性证据，人工只补脚本无法判断的高风险语义关系。

## 高风险段与 rationale 规则

满足以下任一条件的段为高风险段，**必须填写 `rationale`**，说明具体译法依据；普通直译段可省略：

1. 含否定或限定：`not`、`cannot`、`only`、`unless`、`at most`、`without` 等。
2. 含因果、让步或指代：`because`、`therefore`、`although`、`whereas`、`despite`、`the former/latter` 等。
3. 含数字/单位、公式、图表编号或文献引用标记（方括号数字、作者-年份、上标数字三种风格均算）。
4. 发生术语义项消歧、缩写/专名保留策略或文化负载词注释。
5. 来源为 OCR/图片转写，或存在其他译不准风险。

`rationale` 只写实际处理依据，例如“`cell` 依 `electrode` 归为电池义项，译‘电池’；`1.5 V` 原样保留”，不写空泛的“已核对”。译不准处另写 `uncertain` 并标 `【待核】`。

## 关系核验清单

1. **数字与单位**：数值、量级、单位（如 `5 μm`、`300 K`、`p < 0.05`）与原文一致。
2. **公式与符号**：保留原记法/LaTeX；变量上下标、正负号、常数不改变。
3. **图表编号**：`Fig. 1`、`Table 2`、`(3)` 与原文一致。
4. **文献引用标记**：`[12]`、`(Smith et al., 2020)`、上标数字 `²,³` 原样保留。
5. **否定与限定**：不得漏掉或翻转。
6. **因果与让步**：指向与强弱保留。
7. **指代对象**：不漂移；必要时显式补出所指并加括号注释。

## 五个脚本与量化报告

在 Skill 目录下执行：

```bash
python3 scripts/check_terms.py --terms work/terms.tsv --segments work/segments.json --json-out work/terms.report.json
python3 scripts/check_segments.py --inventory work/inventory.json --result work/segments.json --json-out work/segments.report.json
python3 scripts/check_literals.py --segments work/segments.json --json-out work/literals.report.json
python3 scripts/build_verification.py --terms-report work/terms.report.json --segments-report work/segments.report.json --literals-report work/literals.report.json --out work/verification.json
python3 scripts/check_contract.py --result result.json [--case /input/case.json] --json-out work/contract.report.json
```

前三个脚本分别检查：

- 术语一致（义项级）：归属某义项的段，译文须含锁定译名或按保留策略保留原文；ambiguous 段需补 `context_clues` 后归属。同时做术语表结构预检：每行 8 列、`source_term+sense_id` 唯一、`retention` 取 `keep/translate/annotate`、`translate` 术语的 `canonical_translation` 不得为空（空则进 `missing_canonical`，不静默回退成 source）。
- 段落完整：inventory 中每个段号在 result 中恰好出现一次；无缺段、重段、多余段。重复检测**同时覆盖 inventory 侧与 result 侧**（`duplicated_inventory`/`duplicated`），完整率用去重后的 inventory 计算。
- 字面量保留：图表编号（含 `Figs. 2 and 3` 多图形式）、方括号数字引用（含 `[2–4]` 区间）、作者-年份引用（`(Smith et al., 2020)` / `Smith et al. (2020)`，年份与首作者名保留）、比较关系符号+数字（含 Unicode 负号 `−`；符号可用中文对应，`~80%`→“约 80%”不误判）为硬校验；已知单位（含 `cm⁻¹`、`m²`、`μg/mL`、`cells/mL`、`M⁻¹s⁻¹` 等复合/指数单位）与上标数字为软校验，未命中项进 `human_confirm`，不把数字后的普通英文单词误判为单位。

`build_verification.py` 只读取三个 JSON 报告并生成：

```json
{
  "term_consistency": { "matched": 13, "assigned": 15, "rate": 0.8667, "mismatch_segments": ["S009"], "ambiguous_segments": [], "missing_canonical": [], "structural_errors": [] },
  "segment_completeness": { "covered": 20, "inventory": 20, "result": 20, "rate": 1.0, "exact": true, "missing": [], "extra": [], "duplicated": [], "duplicated_inventory": [] },
  "literal_retention": { "hit": 8, "checked": 8, "rate": 1.0, "hard_miss": 0, "hard_miss_items": [], "unit_warn": 0, "soft_warn": 0, "warnings": [] },
  "relation_checklist": [],
  "human_confirm": [],
  "all_hard_checks_pass": false
}
```

`verification.term_consistency` 是术语一致率的唯一权威来源；`literal_retention.hard_miss_items`/`warnings` 携带失败明细。将 `work/verification.json` 原样并入 `result.json.verification`。`rate` 为 0–1；没有可检查项时为 `null`。术语不一致、缺段/重段/多余段、术语表结构错误或字面量硬错误存在时，汇总脚本返回非零，`all_hard_checks_pass=false`，必须修正后重跑。

第五个脚本 `check_contract.py` 在写完 `result.json` 后执行：逐项断言 `output_contract` 字段在顶层存在并按类型填值，检查每段六个必填字段、无重复 `seg_id`、`uncertainty/evidence/protected_entities` 的 `seg_id` 引用有效（悬空仅 warning），并校验 `status=success` 与 `all_hard_checks_pass=true` 的一致性。

## 人工补验与状态约束

- 对高风险段复核否定/限定、指代、因果/让步、公式图片转写，结果写入 `relation_checklist` 或 `human_confirm`；普通段无需重复写长清单。两者统一字段结构 `{seg_id, item, result, note}`。
- `result` 取值：`pass` 通过；`warn` 已处理但建议人工复核；`fail` 未通过且未修正。
- 存在未解决的 `fail`、`all_hard_checks_pass=false` 或 `check_contract.py` 非零退出时，`status` 不得为 `success`。
- 不伪造未执行的检查；预算不足时保留脚本量化报告，并如实缩小人工清单范围。

## 回归测试

`tests/run_checks.py` 及 `tests/fixtures/` 固化上述边界：区间引用、多图编号、Unicode 负号、作者-年份引用、`~≈` 中文对应、上标数字、复合单位、单位误报、空译文、retention 枚举、inventory 重复、契约完备性与 seg_id 悬空。修改脚本后运行 `python3 tests/run_checks.py` 防回归。
