# 双语对照段模板（示意，复制此结构）

```json
{
  "seg_id": "S007",
  "location": "p2-col1-para2-s3",
  "page": 2,
  "kind": "paragraph",
  "source": "The spin-orbit coupling drives the transition at 300 K.",
  "translation": "自旋-轨道耦合在 300 K 下驱动了该相变。",
  "rationale": "spin-orbit coupling 使用术语表锁定译名「自旋-轨道耦合」；drives 译「驱动」保留因果指向；transition 依上下文译「相变」；300 K 原样保留。",
  "uncertain": null
}
```

字段说明：
- `seg_id`/`location`：与 `inventory.json` 一一对应（可核验）。
- `source`：原文逐字，不增删改。
- `translation`：译文；术语必须等于锁定译名。
- `rationale`：高风险段必填，说明术语、关系、指代、数字单位等实际处理依据；普通直译段可省略。
- `uncertain`：译不准项；`null` 表示无，OCR/图片转写等不确定处必填。
