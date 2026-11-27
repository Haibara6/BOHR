---
name: literature-translation
description: 把真实科研论文（PDF）翻译成可核验的双语对照结果。当给定一篇论文材料并要求"翻译/文献翻译/双语对照/术语统一/长文分段翻译"时使用；按术语表锁定译名、建立段号清单、逐段双语对齐、给出页码/段落证据并做核验清单。不用于写文献综述、仅制作幻灯片（不涉及翻译）、泛泛改写、只给大意或脱离原文的问答。
---

# 文献翻译：范围准 · 段落全 · 术语稳 · 可核验

目标是把真实科研材料翻译成可复核的双语对照结果，而不是只给大意。预算为 64 请求、900 秒、单次响应 16384 token；**只走下面六步主路径，细节按需查 references，不扩展流程。**

## 六步主路径

### 1. 读输入，先裁剪范围

- 读 `/input/case.json`、`/input/task.md` 和实际材料，记录 `case_id`、材料路径、保留策略（默认 `annotate`）、`output_contract` 字段、可选 `term_base` 术语库及其版本。契约字段最终必须以原名放在 `/app/output/result.json` **顶层**。
- 判定并声明 `source_language`/`target_language`（默认 `en → zh-CN`）；非英文源或指定其他目标语时切换到对应 `context_clues` 词干、单位词典与命名实体规则，并把实际语言写入结果。
- 先确定 `scope`：任务指定页码、章节或段落区间时，**只处理该区间**；只有任务明确要求全文时才用 `full`。范围外的内容不建段号、不抽术语、不翻译，也不算缺段。范围不清时按任务明确对象取最小必要范围，并在 `limits` 说明。
- 只依据实际读到的文件判断文字层、扫描件、公式图片等形态，不依据文件名猜内容。

### 2. 只对范围内内容建清单、锁术语

- 用 `pdf-text-tool` 抽取范围内文本，按原文段落建立 `work/inventory.json`：标题、摘要、各级标题、正文段、图题、表头/表注、脚注、公式与编号、引用标记、作者/机构/DOI/期刊/关键词元数据均须覆盖；记录 `seg_id + location(page/col/para)`，跨页/跨栏段合并并标 `cont_from`。双栏不得拼接同一视觉行的左右栏；分子量、指数、波数等上标丢失时渲染原页核对。规则见 `references/segmentation.md`。
- **范围内每种可见要素都必须编段**：图题（`kind=caption`）、表头与表注（`kind=table`）、公式及其编号（`kind=formula`）、脚注（`kind=footnote`）、各级标题（`kind=heading`）、元数据（`kind=metadata`）。段落完整率只对照清单，**清单漏项等于静默漏译**，不会被 `check_segments` 发现，因此建清单时逐页核对"有无图/表/公式/脚注"。
- 从范围内标题、摘要、关键词、正文、图题和结论抽取术语，写 `work/terms.tsv`（8 列，义项级）。优先锁定高频核心词、多义词和缩写，不做无预算的全量 NER/WSD；同形异义词按义项拆条并给源语言 `context_clues`。结构与义项级校验见 `references/term-table.md`。章节标题与固定表达另按 `references/fixed-expressions.md` 锁定，不逐条塞进术语表。
- `References`/`Bibliography` 到结尾整块不翻译；人名、机构、化合物、方法缩写按 `references/named-entities.md` 原样保护，写 `work/protected_entities.json`。

### 3. 批量翻译，分批落盘

- 按段号顺序每次翻译 5–10 段，携带锁定术语表、固定表达表和紧邻上文 1–2 段译文；每批结束即更新 `work/segments.json`，并追加一条带 ISO 8601 时间的 `change_records`，不要等全文译完才保存。
- 每段必填 `seg_id`、`location`、`page`、`kind`、`source`（逐字原文）、`translation`。这些字段不可降级。
- **高风险段必须写 `rationale`**：含否定/限定、因果/让步、指代、数字/单位、公式、图表编号、引用标记（方括号数字 / 作者-年份 / 上标数字），或发生义项消歧、保留策略、OCR 不确定时，写明译法依据。普通直译段可省略 `rationale`；译不准处必须写 `uncertain` 并标 `【待核】`。
- 否定、限定、数字、单位、公式、图表编号和引用标记不得因通顺而改写；命中保护清单的实体原样保留。指代（this/these、该/其）、因果（because/therefore、导致/因此）、让步与转折（although/however、虽然/然而）须在译文中**仍被表达**，不得因意译丢失；`scripts/check_relations.py` 会做类别级软校验。

### 4. 跑脚本，生成量化核验报告

在 Skill 目录下依次执行（四个检查脚本发现硬错误时，修正后重跑）：

```bash
python3 scripts/check_terms.py --terms work/terms.tsv --segments work/segments.json --json-out work/terms.report.json
python3 scripts/check_segments.py --inventory work/inventory.json --result work/segments.json --json-out work/segments.report.json
python3 scripts/check_literals.py --segments work/segments.json --json-out work/literals.report.json
python3 scripts/check_relations.py --segments work/segments.json --json-out work/relations.report.json
python3 scripts/build_verification.py --terms-report work/terms.report.json --segments-report work/segments.report.json --literals-report work/literals.report.json --relations-report work/relations.report.json --out work/verification.json
```

`work/verification.json` 自动给出术语一致率、段落完整率、字面量保留率、关系保留率及失败段号/字面量明细。ambiguous 义项补 `context_clues`；缺段、重段、多余段（含 inventory 侧重复）、术语表结构错误、术语不一致和字面量硬错误不得留到 `success`。关系软校验未命中项进入 `human_confirm`，逐条复核并修正译文，再重跑。

### 5. 只补高风险人工核验

按 `references/verification.md` 复核高风险段的否定/限定、指代、因果/让步及公式图片转写，并把结果补入 `verification.relation_checklist` 或 `human_confirm`。两者统一字段结构 `{seg_id, item, result, note}`，`result` 取 `pass|warn|fail`。普通段不重复写长清单，不伪造未执行的检查。

### 6. 写 result.json，保留证据与边界

- 以 `assets/result.skeleton.json` 为骨架，写 `/app/output/result.json`：顶层包含 `case_id`、`scope`、`source_language`、`target_language`、`status`、`summary`、`bilingual_segments`、`term_table`、`evidence`、`uncertainty`、`verification`、`change_records`、`sources`、`limits`，并合并全部 `output_contract` 字段。结构见 `references/output-schema.md`。
- 把 `work/verification.json` **原样并入 `verification`**，不要只写“已检查”；`term_table` 不另写 `consistency_report`。
- 先写骨架，再分批填充 `bilingual_segments`（每批控制在单次响应 16384 token 以内），避免一次性输出超限；`sources` 记录 `extractor/renderer/ocr/ocr_confidence/version`。
- 写完后运行 `python3 scripts/check_contract.py --result /app/output/result.json [--case /input/case.json]`；契约字段缺失、段字段缺失或 `success` 与硬校验不一致时返回非零，修正后重跑。
- `success` 仅当范围内每段均有原文与译文、`segment_completeness.exact=true`、`all_hard_checks_pass=true`、`check_contract.py` 通过且无未解决的 `fail`；否则用 `partial`，在 `limits.untranslated` 列明剩余段号。材料不可读用 `unable`。
- 绝不编造原文、运行日志或分数。

## 何时使用 / 何时不用

- 使用：翻译论文、双语对照、术语统一、长文分段翻译、译文核验。
- 不用：只总结、写综述、做 PPT、问答但不要求翻译、或只给大意。

## 异常与依赖

- 扫描件用渲染+OCR；公式/表格图片转写后标“需人工核对”；参考文献无法解析则原样保留；预算耗尽立即保存 `partial` 结果；材料缺失写 `unable` 及人工接管位置。详见 `references/exception-handling.md`。
- 运行依赖 `python3`（仅标准库）及平台 PDF/OCR 工具；工作目录 `/app/work`，产物目录 `/app/output`。脚本无第三方依赖。
- 最小输入、调用与示意输出见 `examples/minimal-example.md`。

## 提交前自查

1. frontmatter 仅含 `name`/`description`；六个脚本 `--help` 可运行，失败返回非零；`python3 tests/run_checks.py` 通过。
2. 资源 ≤50 个、每个 ≤500KB、合计 ≤2MB，无符号链接、无密钥。
3. `result.json` 可解析，`case_id`、`scope`、`source_language`、`target_language` 与契约字段均在顶层，`scope` 与任务范围一致。
4. 每段必填字段齐全，高风险段有 `rationale`，`verification` 含术语一致率、段落完整率、字面量保留率、关系保留率四个量化指标与失败明细而非空字符串。
