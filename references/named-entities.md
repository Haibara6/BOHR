# 命名实体保护清单（人名 / 机构 / 地名 / 化合物 / 试剂）

命名实体**不属于术语**，不进入义项级术语表的"翻译"流程，而是进入**保护清单**，翻译时**原样保留**。翻译命名实体会破坏引用的可回溯性，并造成张冠李戴。

## 保护对象（retention = keep_strict，强制保留原文）

| 类别 | 例子 | 处理 |
|-|-|-|
| 人名（作者名） | `Smith J`、`Wang W`、`Einstein` | 保留原文 |
| 机构名 | `MIT`、`Chinese Academy of Sciences` | 保留原文（有官方中文名可注释） |
| 地名 | `Berlin`、`Guangzhou` | 保留原文或规范译名 |
| 化合物 / 试剂名 | `DPPH`、`ABTS`、`NaCl`、`H₂O₂` | 保留原文（缩写见 term-table 的 retention=keep） |
| 方法名缩写 | `NMR`、`HPLC`、`SDS-PAGE` | 保留原文 |
| 基因 / 蛋白名 | `p53`、`β-actin` | 保留原文 |

## 人名分层策略

| 场景 | 例子 | 策略 |
|-|-|-|
| **参考文献列表** | `Smith J, Wang W. ...` | **整个著录块保留原文**（作者名/标题/期刊名一律不翻） |
| **正文引用** | `Smith et al. (2020)`、`Wang et al. reported` | 作者名保留原文，不译成"史密斯等"/"王等" |
| **正文作为人物** | `Einstein showed` | 仅当有**通行译名**才译（Einstein→爱因斯坦、Darwin→达尔文），否则保留原文 |

`scripts/check_literals.py` 对作者-年份引用做硬校验：`(Smith et al., 2020)` / `Smith et al. (2020)` 的年份与首作者名必须保留，作者名译成“史密斯等”会触发 `citation_author_year` 硬错误；方括号数字引用与上标数字引用另由对应检查覆盖。月份词（如 `January 2020`）不作为作者-年份引用处理，避免误报。

## 中国学者拼音（不猜中文名）

拼音 → 汉字是**多对一映射**（`Wang Wei` 可能是王伟/王威/王薇），信息上不可逆，任何猜测都会张冠李戴。

**默认规则：保留拼音原文，不搜索、不猜测中文名。** 处理方式：
1. 译文保留 `Wang Wei`（或 `Wang W`），首现可加 `uncertain` 注"中文名未核实，保留拼音"。
2. `uncertainty` 写一条：`{"seg_id":"...","item":"人名 Wang Wei","note":"拼音无法确定对应中文字，保留原文","severity":"low"}`。
3. 不因保留拼音而把 `status` 判为失败——这是正确做法，不是缺陷。

**绿色通道（仅当任务明确要求中文名时）：**
- 触发条件：`case.json`/`task.md` 明确要求给出中文人名（如人名索引、专名翻译），且评分对此计分。
- 限额：**最多核实 3 个**高频/核心作者，超限放弃，其余保留拼音。
- 方法：用**元数据 API 一次查询**（Crossref/OpenAlex 按 DOI 返回作者 affiliation、ORCID），不进行 LLM 多轮读检索结果；优先用输入里已有的中文对照表。
- 查不到或不确定：立即标 `uncertain` + 保留拼音，**不臆造**。

**默认不查**：仅为了一个人名中文名去搜索是弊大于利（消耗 token/时间，得分收益极低，且保留拼音本就正确）。

## 识别方法（NER）

- 作者列表位置、`et al.` 前后、首字母大写连续串、`References`/`Bibliography` 段落 → 人名。
- `References` 段落后到正文结束 → **整块标记为"不翻译"**，原样保留（比逐人名匹配更可靠）。
- 机构/地名/化合物/试剂：靠领域常识 + 上下文（大写缩写、化学式、方法名）。
- 识别结果写 `work/protected_entities.json`（数组：`{"type":"person|org|place|compound|reagent|abbrev","text":"...","location":"...","retention":"keep_strict"}`）。

## 与 term-table 的关系

- 概念词 → `work/terms.tsv`（义项级，`retention=translate/keep/annotate`）。
- 命名实体 → `work/protected_entities.json`（`retention=keep_strict`，强制保留）。
- 两者都由全局保留策略（`prefer_original / prefer_translation / annotate`）统一驱动；人名/机构/化合物无论全局策略如何，**始终保留原文**（除非绿色通道核实后任务明确要求译名）。
