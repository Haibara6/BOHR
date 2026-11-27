# 使用与方法说明（literature-translation）

本题作品为「文献翻译」Skill：把真实科研论文翻译成可核验的双语对照结果。Skill 本体即本目录（`SKILL.md` 及 `references/`、`assets/`、`scripts/`、`examples/`、`tests/`）。

## 核心策略：范围裁剪 + 六步主路径 + 选择性严谨

预算为 64 请求、900 秒、单次响应 16384 token。任务指定页码或章节时只处理该范围，不扩展到全文。主流程固定为“读输入与范围 → 建段号清单 → 锁术语 → 批量翻译 → 脚本与高风险核验 → 写结果”，不额外展开全量 NER/WSD。每段必须有 `seg_id + location + page + kind + source + translation`；高风险段必须有 `rationale`，普通直译段可省略。

## 完整调用步骤（Agent 视角）

1. 读 `/input/case.json` 与 `/input/task.md`，记录 `case_id`、`output_contract`、保留策略（默认 `annotate`）、可选 `term_base` 术语库及版本；判定并声明 `source_language`/`target_language`（默认 `en → zh-CN`）。范围外内容不建清单、不抽术语、不翻译。
2. 用 `pdf-text-tool` 只抽取范围内文本，建立 `work/inventory.json`（跨页/跨栏接续合并，元数据用专用 kind）。
3. 从范围内文本抽取术语并锁定 `work/terms.tsv`（8 列）；章节标题与固定表达按 `references/fixed-expressions.md` 锁定。
4. 每次请求翻译 5–10 段，每批更新 `work/segments.json` 并追加带时间的 `change_records`。每段必填定位、原文和译文；高风险段必须写 `rationale`。
5. 运行四个脚本，生成量化核验报告：

   ```bash
   python3 <skill>/scripts/check_terms.py --terms work/terms.tsv --segments work/segments.json --json-out work/terms.report.json
   python3 <skill>/scripts/check_segments.py --inventory work/inventory.json --result work/segments.json --json-out work/segments.report.json
   python3 <skill>/scripts/check_literals.py --segments work/segments.json --json-out work/literals.report.json
   python3 <skill>/scripts/build_verification.py --terms-report work/terms.report.json --segments-report work/segments.report.json --literals-report work/literals.report.json --out work/verification.json
   ```

6. 复核高风险语义关系，然后写 `/app/output/result.json`：合并 `case_id`、`scope`、`source_language`/`target_language`、`output_contract` 全部字段（顶层）、`bilingual_segments`（顶层）及证据/不确定/变更记录，并把 `work/verification.json` 原样并入 `verification`。写完后运行：

   ```bash
   python3 <skill>/scripts/check_contract.py --result /app/output/result.json --case /input/case.json
   ```

## 输入输出

- 输入：`case.json`、`task.md`、论文 PDF（可能为扫描件/LaTeX/混合）。
- 输出：`result.json`（必），可选可编辑双语 Markdown/Office 产物及其渲染 PDF/PNG 预览。

## 关键方法

- 范围准：严格按任务区间建立清单和翻译，范围外不计缺段。
- 术语稳：义项级术语表锁定 + 逐段执行 + `check_terms.py` 结构预检与全篇校验；`verification.term_consistency` 是术语一致率唯一权威来源。
- 段落全：段号清单、跨页/跨栏接续、`check_segments.py` 1:1 对齐，inventory 侧重复段一并判错。
- 关系准：图表编号/方括号引用/作者-年份引用/关系符号+数字由 `check_literals.py` 硬校验，复合单位与上标数字软校验，其余高风险关系人工复核。
- 可核验：每段有定位证据，高风险段有译法依据；`verification` 直接给出术语一致率、段落完整率和字面量保留率（0–1）及失败明细，而不是只写“已检查”。

## 适用场景与限制

- 适用：单篇科研论文的全文或指定区间双语对照翻译。
- 限制：不适用于仅总结/综述/问答；扫描件依赖 OCR 精度，OCR 不确定处须人工复核；参考文献不保证结构化。脚本内置的确定性检查面向英文源、中文目标；其他语言需切换对应线索词典与单位表。

## 失败处理

无文字层则渲染+OCR；公式/表格图片转写并标注；参考文献无法解析则原样保留；材料缺失用 `status=unable`；预算耗尽先保存 `status=partial` 并列明剩余段号。存在未解决的硬校验失败、契约错误或 `fail` 时不得标 `success`。

## 自查方法

`SKILL.md` frontmatter 仅 name/description；五个脚本 `--help` 可跑、失败非零退出；`python3 tests/run_checks.py` 通过；文件 ≤50 个/≤500KB/≤2MB，无 symlink/密钥；`result.json` 可解析且含 `case_id`、`scope`、`source_language`、`target_language` 与顶层契约字段；`verification` 含三个量化对象与失败明细。
