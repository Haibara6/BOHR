# 双语对照段模板（示意，复制此结构）

```json
{
  "seg_id": "S007",
  "location": "p2-col1-para2-s3",
  "page": 2,
  "kind": "paragraph",
  "source": "The spin-orbit coupling drives the transition.",
  "translation": "自旋-轨道耦合驱动了该相变。",
  "rationale": "spin-orbit coupling 使用术语表锁定译名「自旋-轨道耦合」；drives 译「驱动」保留因果指向；transition 依上下文译「相变」。",
  "uncertain": null
}
```

字段说明：
- `seg_id`/`location`：与 `inventory.json` 一一对应（可核验）。
- `source`：原文逐字，不增删改。
- `translation`：译文；术语必须等于锁定译名。
- `rationale`：译法依据（术语、关系、指代如何处理）。
- `uncertain`：译不准项；`null` 表示无。
