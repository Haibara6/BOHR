# 核验规范（关系准 + 可核验）

译文正确性的判定不看是否通顺，而看**关系是否保留、能否指回原文**。

## 关系核验清单（逐段，必要时逐句）

对每段译文逐项核对：

1. **数字与单位**：数值、量级、单位（如 `5 μm`、`300 K`、`p < 0.05`）与原文一致，不换算错误、不丢单位。
2. **公式与符号**：保留原记法/LaTeX；变量上下标、正负号、常数不改变。
3. **图表编号**：`Fig. 1`、`Table 2`、`(3)` 与原文引用一致，不重号、不错号。
4. **文献引用标记**：`[12]`、`(Smith et al., 2020)` 原样保留，不吞、不换。
5. **否定与限定**：`not`/`cannot`/`only`/`unless`/`at most` 等如实翻译，不得漏掉或翻转。
6. **因果与让步**：`because`/`therefore`/`although`/`whereas`/`despite` 的指向与强弱保留。
7. **指代对象**：代词/`the former/the latter` 所指对象不漂移，必要时在译文中显式补出所指并加括号注释。

## 可机械校验的三类（脚本兜底）

第 1、3、4 项中"字面量必须原样保留"的部分，用 `scripts/check_literals.py` 确定性检查，不靠模型自觉：

- 图表编号（`Fig. 1`/`Table 2` 的编号）
- 文献引用标记（`[12]`/`[12,13]`）
- 比较/关系符号+数字（`< 0.05`、`≥ 3`、`± 0.1`、`≈ 0.9`）

单位作为软校验（warn）：译文含原文单位（`μm`）或对应中文单位（`微米`）二者之一即可。硬校验不一致返回非零退出码，必须修正。

## 译不准标注

译不准处**明确标注** `【待核】` 并给原因，写进该段的 `uncertain` 与全局 `uncertainty`，禁止含混。常见：OCR 不确定、公式为图片、术语义项歧义、参考文献乱码。

## 自检产物（verification）

```json
{
  "term_consistency": "check_terms.py 输出摘要（义项级）",
  "segment_completeness": "check_segments.py 输出摘要",
  "literal_retention": "check_literals.py 输出摘要（图表编号/引用标记/关系符号+数字/单位）",
  "relation_checklist": [
    {"seg_id":"S007","item":"数字单位","result":"pass|warn|fail","note":""}
  ],
  "human_confirm": [ {"seg_id":"S012","item":"公式(3)","reason":"图片转写，需人工核对"} ]
}
```

`result` 取值：`pass` 通过；`warn` 已按规则处理但建议人工复核；`fail` 未通过且未修正（此时 `status` 不能是 `success`）。
