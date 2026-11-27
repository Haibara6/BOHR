# 核验规范（关系准 + 可核验）

译文正确性不看是否通顺，而看**关系是否保留、能否指回原文**。核验分两层：三个检查脚本提供确定性证据，人工只补脚本无法判断的高风险语义关系。

## 高风险段与 rationale 规则

满足以下任一条件的段为高风险段，**必须填写 `rationale`**，说明具体译法依据；普通直译段可省略：

1. 含否定或限定：`not`、`cannot`、`only`、`unless`、`at most`、`without` 等。
2. 含因果、让步或指代：`because`、`therefore`、`although`、`whereas`、`despite`、`the former/latter` 等。
3. 含数字/单位、公式、图表编号或文献引用标记。
4. 发生术语义项消歧、缩写/专名保留策略或文化负载词注释。
5. 来源为 OCR/图片转写，或存在其他译不准风险。

`rationale` 只写实际处理依据，例如“`cell` 依 `electrode` 归为电池义项，译‘电池’；`1.5 V` 原样保留”，不写空泛的“已核对”。译不准处另写 `uncertain` 并标 `【待核】`。

## 关系核验清单

1. **数字与单位**：数值、量级、单位（如 `5 μm`、`300 K`、`p < 0.05`）与原文一致。
2. **公式与符号**：保留原记法/LaTeX；变量上下标、正负号、常数不改变。
3. **图表编号**：`Fig. 1`、`Table 2`、`(3)` 与原文一致。
4. **文献引用标记**：`[12]`、`(Smith et al., 2020)` 原样保留。
5. **否定与限定**：不得漏掉或翻转。
6. **因果与让步**：指向与强弱保留。
7. **指代对象**：不漂移；必要时显式补出所指并加括号注释。

## 四个脚本与量化报告

在 Skill 目录下执行：

```bash
python3 scripts/check_terms.py --terms work/terms.tsv --segments work/segments.json --json-out work/terms.report.json
python3 scripts/check_segments.py --inventory work/inventory.json --result work/segments.json --json-out work/segments.report.json
python3 scripts/check_literals.py --segments work/segments.json --json-out work/literals.report.json
python3 scripts/build_verification.py --terms-report work/terms.report.json --segments-report work/segments.report.json --literals-report work/literals.report.json --out work/verification.json
```

前三个脚本分别检查：

- 术语一致（义项级）：归属某义项的段，译文须含锁定译名或按保留策略保留原文；ambiguous 段需补 `context_clues` 后归属。
- 段落完整：inventory 中每个段号在 result 中恰好出现一次，无缺段、重段、多余段。
- 字面量保留：图表编号（含 `Figs. 2 and 3` 多图形式）、文献引用标记（含 `[2–4]` 区间形式）、比较关系符号+数字（含 Unicode 负号 `−`）为硬校验；已知单位为软校验，未命中项进入 `human_confirm`，不把数字后的普通英文单词误判为单位。

`build_verification.py` 只读取三个 JSON 报告并生成：

```json
{
  "term_consistency": { "matched": 13, "assigned": 15, "rate": 0.8667, "mismatch_segments": ["S009"], "ambiguous_segments": [] },
  "segment_completeness": { "covered": 20, "inventory": 20, "result": 20, "rate": 1.0, "exact": true, "missing": [], "extra": [], "duplicated": [] },
  "literal_retention": { "hit": 8, "checked": 8, "rate": 1.0, "hard_miss": 0, "unit_warn": 0 },
  "relation_checklist": [],
  "human_confirm": [],
  "all_hard_checks_pass": false
}
```

将 `work/verification.json` 原样并入 `result.json.verification`。`rate` 为 0–1；没有可检查项时为 `null`。术语不一致、缺段/重段/多余段或字面量硬错误存在时，汇总脚本返回非零，`all_hard_checks_pass=false`，必须修正后重跑。

## 人工补验与状态约束

- 对高风险段复核否定/限定、指代、因果/让步、公式图片转写，结果写入 `relation_checklist` 或 `human_confirm`；普通段无需重复写长清单。
- `relation_checklist.result`：`pass` 通过；`warn` 已处理但建议人工复核；`fail` 未通过且未修正。
- 存在未解决的 `fail` 或 `all_hard_checks_pass=false` 时，`status` 不得为 `success`。
- 不伪造未执行的检查；预算不足时保留脚本量化报告，并如实缩小人工清单范围。
