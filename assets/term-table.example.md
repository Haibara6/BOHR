# 术语表模板（TSV，制表符分隔）

首行表头，8 列，UTF-8 编码，制表符（`\t`）分隔。示例：

```
source_term	sense_id	canonical_translation	domain	context_clues	example	notes	retention
cell	cell-biology	细胞	biology	culture;tissue;proliferat;medium	The cells were cultured in DMEM.		translate
cell	cell-battery	电池	electrochem	electrode;electrolyt;anode;cathode;voltage	Each cell delivers 1.5 V between its electrodes.		translate
DPPH	DPPH	DPPH	chemistry		1,1-二苯基-2-三硝基苯肼，缩写		keep
FRAP	FRAP	FRAP	biochem		ferric reducing antioxidant power，保留缩写		annotate
```

列说明：
- `source_term`：词形。
- `sense_id`：义项编号；同形异义词拆成多条。
- `canonical_translation`：该义项的锁定译名；保留原文时与 source_term 相同。
- `context_clues`：判定义项的关键词，用**源语言**（匹配原文 source），分号分隔；空表示单义。
- `example`：锁定义项的原文例句（可选）。
- `notes`：禁用译法、首次出现位置、缩写全称/中文注释等。
- `retention`：`keep`（保留原文）/ `translate`（翻译）/ `annotate`（首次注释+后续保留原文）。

实际运行时的术语表写为 `work/terms.tsv`（同上 8 列），由 `scripts/check_terms.py` 读取校验。本模板仅供 Agent 参考格式。
