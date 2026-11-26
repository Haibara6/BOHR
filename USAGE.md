# 使用与方法说明（literature-translation）

本题作品为「文献翻译」Skill：把真实科研论文翻译成可核验的双语对照结果。Skill 本体即本目录（`SKILL.md` 及 `references/`、`assets/`、`scripts/`、`examples/`）。

## 核心策略：先求全，再求细

预算有限（64 请求 / 900 秒 / 16384 token）。先保证"范围内每一段都有译文"，再谈逐段依据与细化。硬目标不可降级：每段都有 `seg_id + location + source + translation`；`output_contract` 全部字段在 `result.json` 顶层；`result.json` 可解析。软目标（`rationale`、全量 NER/WSD、关系逐条核验）在预算不足时按序降级。

## 完整调用步骤（Agent 视角，评测运行时）

1. 读 `/input/case.json` 与 `/input/task.md`，记录 `case_id`、材料路径、翻译范围、`output_contract` 字段清单、保留策略（默认 `annotate`）。
2. 用 `pdf-text-tool` 抽取结构化文本（保留页码/栏/段/句），建立段号清单 `work/inventory.json`（跨页/跨栏接续合并）。
3. 抽取术语并锁定 `work/terms.tsv`（TSV 8 列：`source_term / sense_id / canonical_translation / domain / context_clues / example / notes / retention`，义项级）。
4. **批量**逐段翻译（每次请求 5–10 段），每段必填 `seg_id / location / source / translation`；`rationale`/`uncertain` 仅在义项消歧、关系处理或译不准时填写 → `work/segments.json`。
5. 校验（三个脚本，必跑）：
   - `python3 <skill>/scripts/check_terms.py --terms work/terms.tsv --segments work/segments.json`
   - `python3 <skill>/scripts/check_segments.py --inventory work/inventory.json --result work/segments.json`
   - `python3 <skill>/scripts/check_literals.py --segments work/segments.json`
6. 写 `/app/output/result.json`：`case_id` + `output_contract` 全部字段（**顶层合并**）+ `bilingual_segments`（顶层）+ 状态/证据/不确定/核验/变更记录。

## 输入输出

- 输入：`case.json`、`task.md`、论文 PDF（可能为扫描件/LaTeX/混合）。
- 输出：`result.json`（必），可选可编辑双语 Markdown/Office 产物及其渲染 PDF/PNG 预览。

## 关键方法

- 术语稳：术语表锁定（义项级，同形异义拆条）+ 逐段执行 + `check_terms.py` 全篇校验（标题/摘要/正文/图注/结论一致）。
- 段落全：先建段号清单，跨页/跨栏接续合并，`check_segments.py` 校验 1:1 对齐。
- 关系准：数字/单位/公式/图表编号/文献引用/否定/限定/因果/让步逐项核验，其中图表编号/引用标记/关系符号+数字由 `check_literals.py` 确定性硬校验。
- 可核验：每段译文带 `location`（页码/段落/句子）证据；`rationale` 只写译法依据，译不准处标 `【待核】`。

## 适用场景与限制

- 适用：单篇科研论文的全文/指定区间的双语对照翻译。
- 限制：不适用于仅总结/综述/问答；扫描件依赖 OCR 精度，OCR 不确定处须人工复核；参考文献不保证结构化。

## 失败处理

- 无文字层：渲染+OCR；公式/表格为图片：转写并标注；参考文献无法解析：原样保留并注明；材料缺失：`status=unable`；预算耗尽：先落 `status=partial`，列已完成与剩余段号。

## 自查方法

- `SKILL.md` frontmatter 仅 name/description；脚本 `--help` 可跑、失败非零退出；文件 ≤50 个/≤500KB/≤2MB；无 symlink/密钥；`result.json` 可被 JSON 解析且含 `case_id`，`output_contract` 全部字段在顶层。
