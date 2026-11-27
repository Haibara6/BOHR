# BOHR｜阅读03：文献翻译

本仓库为玻尔产品周赛 `product-arena-01-5a9928c1`「阅读03｜文献翻译」的参赛作品。作品是一个可被 Agent 调用的 Skill，用于把真实科研论文翻译成带页码、段落定位、术语表和量化核验报告的双语对照结果。

## 作品入口

- [`SKILL.md`](SKILL.md)：六步主流程，包含范围裁剪、批量翻译、选择性严谨和结果写出规则。
- [`USAGE.md`](USAGE.md)：完整调用步骤、输入输出、关键方法、限制与失败处理。
- [`examples/minimal-example.md`](examples/minimal-example.md)：最小输入、调用方式与示意输出（仅示例，非正式案例结果）。
- [`references/`](references/)：输出契约、分段、术语表、命名实体、核验与异常处理规范。
- [`assets/`](assets/)：双语段模板、术语表模板与 `result.json` 骨架。
- [`scripts/`](scripts/)：四个仅依赖 Python 标准库的确定性校验脚本。

## 方法概览

1. **范围裁剪**：任务指定页码或章节时只处理该范围，避免把预算浪费在范围外内容。
2. **段落完整**：建立段号清单，合并跨页/跨栏接续段，并校验原文与译文段号一一对应。
3. **术语稳定**：使用义项级术语表锁定译名，同形异义词按上下文分别处理。
4. **选择性严谨**：每段保留定位、原文与译文；含否定、数字、公式、引用或义项消歧的高风险段必须说明译法依据。
5. **量化核验**：自动汇总术语一致率、段落完整率和字面量保留率，写入 `result.json.verification`。

## 本地脚本校验

在作品根目录准备好 `work/terms.tsv`、`work/inventory.json` 和 `work/segments.json` 后运行：

```bash
python3 scripts/check_terms.py --terms work/terms.tsv --segments work/segments.json --json-out work/terms.report.json
python3 scripts/check_segments.py --inventory work/inventory.json --result work/segments.json --json-out work/segments.report.json
python3 scripts/check_literals.py --segments work/segments.json --json-out work/literals.report.json
python3 scripts/build_verification.py --terms-report work/terms.report.json --segments-report work/segments.report.json --literals-report work/literals.report.json --out work/verification.json
```

前三个脚本分别检查术语一致、段落完整和字面量保留；第四个脚本读取三份 JSON 报告，生成可并入 `result.json` 的 `verification` 对象。所有脚本仅使用 Python 标准库，无需安装第三方依赖。

## 真实 PDF 验证

两篇真实科研 PDF 的范围限定本地验证记录见 [`VALIDATION.md`](VALIDATION.md)。测试覆盖双栏抽取、区间引用、多图编号、Unicode 负号、上下标恢复及量化报告生成。该记录是本地回归证据，不是平台正式案例结果或官方评分。

## 适用范围与限制

适用于单篇科研论文的全文或指定区间双语对照翻译。扫描件依赖 OCR 精度；公式、表格图片转写及无法判断的内容必须明确标注，不能写成确定事实。仓库示例均为接口示意，不代表平台正式案例、白板或评测成绩。
