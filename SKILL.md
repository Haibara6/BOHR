---
name: literature-translation
description: 把真实科研论文（PDF）翻译成可核验的双语对照结果。当给定一篇论文材料并要求"翻译/文献翻译/双语对照/术语统一/长文分段翻译"时使用；按术语表锁定译名、建立段号清单、逐段双语对齐、给出页码/段落证据并做核验清单。不用于写文献综述、仅制作幻灯片（不涉及翻译）、泛泛改写、只给大意或脱离原文的问答。
---

# 文献翻译：术语稳 · 段落全 · 关系准 · 可核验

把一个真实科研材料（通常为 PDF）翻译成**可复核的双语对照结果**。核心不是"译文通顺"，而是：术语一致、段落不丢不重、关系（否定/限定/因果/数字/单位/公式/引用）准确、每段译文能指回原文并说明译法依据。

## 核心原则：先求全，再求细

预算有限（64 请求 / 900 秒 / 16384 token）。**必须先保证"范围内每一段都有译文"，再谈逐段依据与细化**。

- **硬目标（不可降级）**：范围内每段都有 `seg_id + location + source + translation`；`output_contract` 全部字段出现在 `result.json` 顶层；`result.json` 可被 JSON 解析；关键结论有页码/段落证据。
- **软目标（预算不足时降级）**：逐段 `rationale`、`uncertain` 细粒度、全量 NER、全量词义消歧、关系逐条核验、可编辑 Office/幻灯片产物。降级顺序：先砍 `rationale`，再砍 NER/WSD 深度，再砍关系清单粒度，最后砍可编辑产物。
- **批量翻译**：每次模型请求携带 5–10 段一起翻译，而不是一段一个请求，把 64 请求留给真正必要的抽取、校验与修复。
- **先落盘再改进**：任何阶段先写 `work/` 与 `result.json`，绝不编造运行日志、分数或未读到的原文内容。

## 何时使用 / 何时不用

- 使用：任务要求"翻译这篇论文 / 产出双语对照 / 统一术语 / 分段翻译 / 译文核验"。
- 不用：只要求总结、写综述、做 PPT、问答但不要求翻译、或只需大意改写。

## 输入（评测时）

- `/input/case.json`：包含 `case_id`、材料路径、任务说明、输入约束、以及评分所需的 `output_contract` 字段。
- `/input/task.md`：题目说明。
- 论文材料：以 PDF 为主，可能含扫描页、公式图、表格图、参考文献。
- 运行时可用工具：`pdf-text-tool`、`pdf-render-tool`、`ocr-tool`、`latex-compiler`、`office-renderer`、`scientific-python` 等；工作目录 `/app/work`，产物目录 `/app/output`。

## 输出（评测时）

- `/app/output/result.json`：必须包含 `case_id`，并且 **`case.json` 里 `output_contract` 声明的全部字段必须原样出现在 `result.json` 顶层**（字段名不改、不嵌套），外加本 Skill 定义的结构化结果（见 `references/output-schema.md`）。
- 可选：可编辑的双语对照 Markdown/Office 产物；若产出 Office/幻灯片/图表，必须同时给真实渲染的 PDF/PNG 预览。
- 部分完成也必须写 `result.json`，`status=partial`，列出已完成与未完成边界。

## 执行顺序（严格按序，每阶段落盘一次）

### 阶段 0：识别输入与边界
1. 读 `case.json` 与 `task.md`。记录：`case_id`、材料路径、翻译范围（全文或指定段落区间）、输入约束。
2. **记录 `output_contract` 字段清单**：这是评分器会逐字段核对的字段名，最终必须**全部以原字段名放在 `result.json` 顶层**；若契约里给了字段结构/类型，按该结构填，不能改名、不能塞进 `main_result` 等子对象。
3. 读**术语保留策略**：从 `case.json` 输入约束取 `retention`（`prefer_original` / `prefer_translation` / `annotate`）；无则默认 `annotate`（首次注释+后续保留原文）。
4. 判定材料形态：有文字层 PDF / 扫描件 / 图片 / LaTeX / 混合。**只依据实际读到的文件，不依据文件名或领域标签猜内容。**

### 阶段 1：抽取并建立「段号清单」（保证"段落全"）
1. 用 `pdf-text-tool` 抽取全文，保留**页码、栏、章节、段落、句子**位置。
2. 建立 inventory：标题、摘要、各级标题、正文段、图题、表头/表注、脚注、公式（含编号）、文献引用标记，逐段编号 `S001, S002, …`，记录位置（`page/col/para`，句子起止）。
3. **跨页/跨栏/跨章节接续**：把被分页截断的段落合并为一段，标记 `cont_from`；不得漏段、不得重复、不得错位。段号与原文一一对应。
4. 写 `work/inventory.json`（格式见 `references/segmentation.md`）。这是后续"段落全"校验的基准。
5. **命名实体保护（轻量）**：`References`/`Bibliography` 段落到结尾**整块标记为"不翻译"**；正文里的人名/机构/化合物缩写尽量标记，命中后原样保留。写 `work/protected_entities.json`（规则见 `references/named-entities.md`）。预算不足时只保留 References 整块标记，全量 NER 可降级。

### 阶段 2：抽取并「锁定」术语表（保证"术语稳"，义项级 + retention）
1. 从标题、摘要、关键词、正文、图题、结论中抽取领域术语、专名、缩写、命名实体、固定词组。
2. 对每个术语做**词义消歧（WSD）**：判断本篇可能出现的义项；同形异义词（如 `cell` 细胞/电池、`field` 场/字段）**按义项拆成多条**，各条给出 `sense_id` 与 `context_clues`（判定义项的关键词）。
3. 建立 `work/terms.tsv`，8 列：`source_term<TAB>sense_id<TAB>canonical_translation<TAB>domain<TAB>context_clues<TAB>example<TAB>notes<TAB>retention`（格式见 `references/term-table.md`）。保留原文的术语，`canonical_translation` 填与 `source_term` 相同。
4. **标注 retention**：缩写、方法名、试剂名、化合物名、专名默认 `keep` 或 `annotate`（保留原文/首注+保留），概念词默认 `translate`；依据全局保留策略统一口径。
5. **按义项锁定**：此后全篇"同一义项用同一译名"，而非"同一词形用同一译名"。新增/修改术语必须回填已译段落。
6. 术语表是逐段执行的约束：每段翻译先据 `context_clues` 判定义项，再取对应译名；最后用 `scripts/check_terms.py`（义项级）全篇校验，并复查标题/摘要/正文/图注/结论。**首版术语表快速抽取即可，预算不足时后续段按需增量补充，不必一次穷尽。**

### 阶段 3：批量逐段翻译（覆盖优先，先求全）
1. 按 `S001…` 顺序**分批**翻译：每次模型请求携带 5–10 段，上下文 = 已锁定术语表 + 紧邻上文 1–2 段译文。目标是**先让范围内每一段都有译文**。
2. 每段**必填**字段（模板见 `assets/bilingual-segment.md`）：
   - `seg_id`、`location`（页码/栏/段/句）、`page`、`kind`
   - `source`（原文逐字，不增删改）
   - `translation`（译文）
   - `rationale` / `uncertain` **默认省略**，仅当发生「义项消歧、指代/关系特殊处理、保留策略生效、译不准」时按需填写。
3. **降级纪律**：预算不足时优先砍 `rationale`，**绝不砍 `location` / `source` / `translation`**。三者保证"段落全 + 可核验"。
4. **命名实体保护**：命中 `work/protected_entities.json` 的实体**原样保留，不进入翻译**；`References` 段落到结尾整块不翻译；人名保留原文（中国学者拼音不猜中文名，规则见 `references/named-entities.md`）。
5. **关系保护（关系准）**：否定、限定条件、因果/让步、指代对象、数字、单位、公式、图表编号、文献引用标记（[1]、(Smith et al., 2020)）必须与原文一致，不因通顺而改写语义。公式/符号保留原记法，必要时括号注释。
6. 译不准的段落**明确标注**【待核】+原因，禁止含混过去。

### 阶段 4：核验（关系准 + 可核验，脚本必跑）
1. 术语一致（义项级）：跑 `python3 scripts/check_terms.py --terms work/terms.tsv --segments work/segments.json`；不一致项**回填修正**后重跑；ambiguous 义项补 `context_clues` 再归属。
2. 段落完整：跑 `python3 scripts/check_segments.py --inventory work/inventory.json --result work/segments.json`；缺段/重段/错位必须修正。
3. 字面量保留：跑 `python3 scripts/check_literals.py --segments work/segments.json`；图表编号/文献引用标记/比较关系符号+数字不一致必须修正，单位 warn 需人工确认。
4. 关系核验清单：尽力逐条检查数字/单位/公式/图表编号/文献引用/否定/限定/因果/让步；预算不足时只保留脚本输出作为证据，人工清单可简化，但不得伪造。

### 阶段 5：写结果并落盘
1. 写 `/app/output/result.json`（schema 见 `references/output-schema.md`），**`output_contract` 全部字段合并到顶层**，同时含：`case_id`、`status`、`summary`、`bilingual_segments`（顶层）、`term_table`、`evidence`、`uncertainty`、`verification`、`change_records`、`sources`、`limits`。
2. `status` 判定：范围内**每段都有 `source+translation` 且脚本校验通过** → `success`；部分段缺译文或脚本未过 → `partial` 并列明边界；材料缺失/不可读 → `unable`。
3. 若有可编辑产物，另存并渲染预览。
4. 预算有限时先落部分结果再逐步改进；绝不编造运行日志、分数或未读到的原文内容。

## 异常处理（降级模式，见 `references/exception-handling.md`）

- **无文字层/扫描件**：`pdf-render-tool` 逐页渲染 → `ocr-tool` 识别；OCR 不确定处标 `【待核】`，不补造。扫不清/拍照歪斜/反光时写结构化人工接管项：`页码/区域 + 原因 + 需要动作`，`status` 标 `partial`。
- **公式/表格为图片**：渲染该区域，转写并在 `uncertain` 标注"图片/OCR 转写，需人工核对"；无法可靠转写则明确"未翻译"。
- **参考文献无法解析**：原样保留原始字符串，`status` 说明"references 未结构化"。
- **原文残缺/语言混杂**：逐段标注语言与完整度，只翻译可识别部分，其余标 `【无法判断】`。
- **预算耗尽/中断**：立即落 `status=partial` 的 `result.json`，列出已完成段号与剩余清单。
- **材料缺失**：`status=unable`，写明缺失文件与可人工接管位置。

## 依赖与调用

- 运行依赖：`python3`（仅标准库）+ 平台提供的 `pdf-text-tool`/`pdf-render-tool`/`ocr-tool`。脚本无第三方依赖。
- 脚本路径相对本 Skill 目录：`scripts/check_terms.py`（义项级术语一致）、`scripts/check_segments.py`（段落完整）、`scripts/check_literals.py`（字面量保留）；用 `python3 <skill>/scripts/...` 调用，参数见各自 `--help`。
- 关键规范：`references/term-table.md`（义项级+retention）、`references/named-entities.md`（命名实体/人名保护）、`references/verification.md`（核验清单）、`references/exception-handling.md`（降级）。

## 最小调用示例（示意，非正式案例）

输入 `case.json`（片段）：
```json
{"case_id":"demo-01","task":"翻译论文第2–4页并做双语对照","materials":["paper.pdf"],"output_contract":{"required_fields":["summary","bilingual_segments"]}}
```
Agent 执行：阶段 0–5 后产出 `result.json`（片段，标记为示例）。注意 `output_contract` 声明的 `summary`、`bilingual_segments` 均出现在**顶层**：
```json
{"case_id":"demo-01","status":"success","summary":"(示例) 已译第2–3页全部段落",
  "bilingual_segments":[{"seg_id":"S007","location":"p2-col1-para2","page":2,"kind":"paragraph","source":"...","translation":"...","rationale":"...","uncertain":null}]}
```

## 自查清单（提交前）

1. `SKILL.md` frontmatter 仅含 `name`/`description`，二者有效。
2. 所有脚本 `python3 --help` 可跑通，失败返回非零退出码。
3. 资源文件 ≤50 个、每个 ≤500KB、合计 ≤2MB，无符号链接、无密钥。
4. `result.json` 含 `case_id`，`output_contract` 全部字段在顶层，可被 JSON 解析。
5. 范围内每段都有 `seg_id + location + source + translation`；`rationale` 只在需要时出现。
