# 术语表规范（术语稳 · 义项级）

术语表是**被执行**的约束，不是写在提示里的一句话。全篇（标题、摘要、正文、图注、表头、结论）必须使用同一译名——但"同一译名"指**同一义项（sense）**，不是同一词形。词形相同、义项不同时，必须使用不同译名，否则就是语义失真。

## 格式（TSV，`work/terms.tsv`）

8 列，制表符分隔，首行为表头：

```
source_term	sense_id	canonical_translation	domain	context_clues	example	notes	retention
cell	cell-biology	细胞	biology	culture;tissue;proliferat;medium	The cells were cultured in DMEM.		translate
cell	cell-battery	电池	electrochem	electrode;electrolyt;anode;cathode;voltage	Each cell delivers 1.5 V between its electrodes.		translate
field	field-physics	场	physics	magnetic;electric;coupling	The electric field drives the charge.		translate
entanglement	entanglement	量子纠缠	physics		摘要首次出现		translate
DPPH	DPPH	DPPH	chemistry		1,1-二苯基-2-三硝基苯肼，缩写		keep
FRAP	FRAP	FRAP	biochem		ferric reducing antioxidant power，保留缩写		annotate
NMR	NMR	NMR	chemistry		核磁共振，缩写		keep
```

列说明：
- `source_term`：词形。
- `sense_id`：义项编号；同形异义词用不同 sense_id 拆成多条（如 `cell-biology` / `cell-battery`）。单义词也建议填一个稳定 id。
- `canonical_translation`：该义项的锁定译名；若保留原文（缩写/公式/专名），填与 source_term 相同。
- `context_clues`：判定义项的关键词，**必须用源语言（匹配原文 source）**，用分号/逗号分隔；为空表示该词形单义（不需要消歧）。可只写词干（如 `proliferat` 覆盖 proliferation/proliferating）。
- `example`：一个锁定义项的原文例句（可选，供 Agent 参考）。
- `notes`：禁用译法、首次出现位置、单复数/大小写约定、缩写全称/中文注释等。
- `retention`：术语保留策略，取值 `keep`（始终保留原文）/ `translate`（翻译成中文）/ `annotate`（首次注释+后续保留原文）。**缩写、方法名、试剂名、化合物名、专名默认 `keep` 或 `annotate`；概念词默认 `translate`。**

## 抽取与义项判定（WSD）

1. 从标题、摘要、关键词、各章节标题、正文、图题、表头、结论抽取术语。
2. 对每个术语，判断它在本篇**可能出现的义项**；多义词按义项拆条，并给每条 `context_clues`。
3. 同一个义项只在表中出现一次；同义异形（单复数、连字符、缩写展开）合并到 `notes` 或单独成条，避免同一义项两个译名。

## 锁定与执行

1. 抽取后写 `work/terms.tsv`，从此视为**锁定**（按义项锁定，不是按词形锁定）。
2. 逐段翻译时，先据 `context_clues` 判定本段该词形属于哪个义项，再用该义项的锁定译名。
3. **回填自洽判定**（翻译后，把锁定译名放回译文句，逐一核对）：
   - 该译名放入后，句义是否仍与原文一致？
   - 是否与句中搭配词冲突（如 `tissue` 前是"结缔"→组织，不是"组织机构"）？
   - 本段学科语境与术语条目的义项是否匹配？
   - 若不符：是"选错义项"还是"需要意译/加注"？结论写进该段 `rationale`。
4. 阶段 4 用 `scripts/check_terms.py` 做**义项级**校验：只有"归属本义项"的段才要求出现锁定译名；无法归属义项的段列入 ambiguous，提示 Agent 补义项，不误判为不一致。

## 术语保留策略（缩写 / 方法名 / 试剂名）

领域缩写（DPPH、ABTS、FRAP、NMR、HPLC、SDS-PAGE、PCR、ELISA 等）对深耕该领域的读者而言，保留原文比直译更可读、更稳。全局策略从 `case.json` 输入约束（或交互式用户偏好）读取，取值：

- `prefer_original`：缩写/方法名一律保留原文，只在首次出现加中文注释。
- `prefer_translation`：尽量给中文译名。
- `annotate`（**默认**）：首次出现 = 原文缩写 + 中文全称/注释；此后 = 只用原文缩写。

`annotate` 模板（以 DPPH 为例）：

```
原文：DPPH radical scavenging activity was measured.
译文：DPPH（1,1-二苯基-2-三硝基苯肼，1,1-diphenyl-2-picrylhydrazyl）自由基清除活性被测定。
此后全篇：DPPH 自由基清除活性……
```

硬规则：缩写型术语在术语表里必须标 `keep` 或 `annotate`，**禁止硬译成冗长中文全称**；概念型术语标 `translate`。`keep`/`annotate` 的术语，`canonical_translation` 填原缩写，`check_terms.py` 校验其原文保留即可。

## 文化差异与负载词

- 习语、历史/法律/宗教负载词、机构名、人名：采用"直译+括号注释"或"保留原文+脚注"，在 `uncertain` 说明，不强行字面直译。
- 度量单位：数值不变；单位保留原文或换算为规范单位并标注，不得只改单位不改数值或反之。

## 术语一致率口径（供自评，不冒充官方分数）

`一致率 = 命中段数 / 归属该义项的段数`。标题、摘要、图注、结论四类位置单独复核一遍。
