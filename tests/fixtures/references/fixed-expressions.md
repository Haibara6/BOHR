# 固定表达与章节标题锁定表

术语表锁定的是“概念词”，但文献翻译里还有另一类稳定性问题：**固定表达与章节标题**在全篇必须一致，否则同是 `Materials and Methods` 时而译“材料与方法”、时而译“材料和方法”，比术语漂移更显眼。

## 使用方式

- 在阶段 2 建立术语表的同时，把范围内出现的章节标题与高频固定表达按本表锁定；范围外内容不锁定。
- 标题型表达放入 `bilingual_segments`（`kind=heading`/`kind=title`），译名写进该段 `rationale`；本表作为默认译名依据，不必逐条塞进 `work/terms.tsv`。
- 若任务或领域惯例另有约定，以任务为准，并在 `change_records` 记录覆盖原因。

## 章节标题默认译名

| 源（英文） | 锁定译名 |
|-|-|
| `Abstract` | 摘要 |
| `Keywords` | 关键词 |
| `Introduction` | 引言 |
| `Materials and Methods` | 材料与方法 |
| `Methods` | 方法 |
| `Experimental` | 实验部分 |
| `Results` | 结果 |
| `Results and Discussion` | 结果与讨论 |
| `Discussion` | 讨论 |
| `Conclusion` / `Conclusions` | 结论 |
| `References` / `Bibliography` | （整块不译，原样保留） |
| `Supplementary Information` / `Supporting Information` | 补充信息 / 支持信息（按材料实际用词） |
| `Acknowledgements` / `Acknowledgments` | 致谢 |

## 高频固定表达默认译名

| 源（英文） | 锁定译名 / 处理 |
|-|-|
| `to the best of our knowledge` | 据我们所知 |
| `in this study / herein` | 本研究 / 本文（全篇统一） |
| `as shown in / as illustrated in` | 如图/如表所示（图表编号保留） |
| `the former / the latter` | 前者 / 后者 |
| `on the one hand ... on the other hand` | 一方面……另一方面…… |
| `respectively` | 分别（位置与所指对象对齐） |
| `unless otherwise stated` | 除非另有说明 |
| `in vitro / in vivo / ex vivo` | 体外 / 体内 / 离体（或按惯例保留斜体原词） |
| `state-of-the-art` | 当前最先进 / 最新（按语境统一） |
| `data not shown` | 数据未展示 |

## 铁律

- 同一表达全篇只用一种译名，跨段回填自洽（方法与术语表的回填自洽一致）。
- 不机械照搬上表：遇到否定、省略或学科特定含义时以语境优先，并在该段 `rationale` 说明取舍。
