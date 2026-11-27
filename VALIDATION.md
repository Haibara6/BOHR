# 真实 PDF 本地验证记录

验证日期：2026-11-27。本文记录使用两篇用户提供的真实科研 PDF 对 `literature-translation` Skill 所做的**范围限定本地回归**。测试目的为发现抽取、翻译约束和校验脚本的问题，不是平台正式案例、白板结果或官方评分。

## 材料与范围

| 案例 | 材料 | 页数与文字层 | 本次验证范围 |
|-|-|-|-|
| paper5 | `5-来自枸杞的均一多糖：结构表征、抗肥胖作用及对肠道菌群的影响.pdf` | 15 页，有可抽取文字层 | 标题、摘要、2.3 均一性和分子量测定，共 3 段 |
| paper6 | `6-枸杞多糖的结构表征及其对β-淀粉样肽神经毒性的神经保护作用.pdf` | 13 页，有可抽取文字层 | 标题、摘要、2.2 多糖制备、2.10 细胞活力测定，共 4 段 |

原文按段合并 PDF 换行；分子量与细胞密度的上标通过渲染原页核对，不依据抽取文本猜测。测试译文及 `result.json` 仅保留在本地验证目录，不纳入本仓库更新包。

## 端到端结果

| 指标 | paper5 | paper6 |
|-|-|-|
| 术语表条目 | 10 | 11 |
| 术语一致（matched / assigned） | 14 / 14 | 17 / 17 |
| 术语一致率 | 1.0 | 1.0 |
| 段落完整（covered / inventory） | 3 / 3 | 4 / 4 |
| 段落完整率 | 1.0 | 1.0 |
| 字面量硬校验（hit / checked） | 2 / 2 | 5 / 5 |
| 字面量保留率 | 1.0 | 1.0 |
| 单位软校验 warn | 0 | 0 |
| `segment_completeness.exact` | `true` | `true` |
| `all_hard_checks_pass` | `true` | `true` |

两份本地 `result.json` 均通过 JSON 解析，且 `case_id`、`scope`、`summary`、`bilingual_segments`、`verification` 均位于顶层；`verification` 由 `build_verification.py` 自动生成并原样并入。

这些 1.0 指标只表示上述**小规模、范围限定测试夹具**通过了脚本检查，不能外推为任意论文的翻译正确率，也不能替代对全部译文的专家审校。

## 边界测试与修复

1. **区间引用漏检**：真实论文中的 `[2–4]`、`[7–10]` 原先不进入引用检查。已扩展引用正则，支持逗号、ASCII 连字符、en dash 和 em dash；改变 `[2–4]` 为 `[2–5]` 的负例会返回非零。
2. **多图编号漏检**：`Figs. 2 and 3` 原先不进入图表检查。现已分别检查 2、3；译成“图 2 和图 4”会产生 1 个硬错误。
3. **Unicode 负号漏检**：paper5 校准方程 `Log (Mw) = − 0.1719 T + 11.585` 原先不进入关系检查。现已统一 Unicode 负号与空白；把负号改成正号的负例会返回非零。
4. **单位误报**：`Fig. 2 shows` 中的 `shows` 原先会被当成单位，产生无意义的 `unit_warn`。现仅检查已知单位；“安全”中的“安”也不再被当成电流单位 `A` 的合法译文。
5. **双栏阅读顺序**：两篇论文均为双栏排版，普通 layout 文本可能把左右栏放在同一视觉行。规范已明确要求按栏分别抽取，不直接拼接同行文字，并抽查跨页接续。
6. **上标恢复**：PDF 抽取会把 `10⁴` 变为 `104`。本次通过渲染原页确认上标后恢复；规范已要求分子量、指数、波数等先渲染核对，无法确认时标 `uncertain`。

## 本地复现命令

在 Skill 根目录准备好 `work/terms.tsv`、`work/inventory.json` 和 `work/segments.json` 后执行：

```bash
python3 scripts/check_terms.py --terms work/terms.tsv --segments work/segments.json --json-out work/terms.report.json
python3 scripts/check_segments.py --inventory work/inventory.json --result work/segments.json --json-out work/segments.report.json
python3 scripts/check_literals.py --segments work/segments.json --json-out work/literals.report.json
python3 scripts/build_verification.py --terms-report work/terms.report.json --segments-report work/segments.report.json --literals-report work/literals.report.json --out work/verification.json
```

前三个脚本发现硬错误时返回非零；修正后重跑。第四个脚本生成量化 `verification.json`，存在术语不一致、缺段/重段/多余段或字面量硬错误时返回非零。

## 限制

- 本次仅验证指定小节，不是两篇论文的全文翻译。
- 本地使用 `pdftotext`、`pdftoppm` 和 Python 标准库，未运行平台官方 DeepSeek Harness。
- 未测量 64 请求、900 秒预算下的全文完成率；因此不能据此声称平台重放的 `partial` 问题已经解决。
- 术语、段落与字面量通过脚本不等同于所有语义关系都正确；否定、限定、指代、因果和让步仍需按高风险段清单人工复核。
