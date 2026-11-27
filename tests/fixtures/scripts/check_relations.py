#!/usr/bin/env python3
"""关系保留软校验（关系准 · 语义关系部分，stdlib only）。

用法：
  python3 check_relations.py --segments segments.json [--json-out report.json]

- segments.json：数组 [{"seg_id","source","translation"}]，UTF-8。
- 检查五类高风险语义关系在译文中是否仍被表达（类别级，不要求逐词对应）：
  1) negation 否定：not / never / without / cannot / absence 等；
  2) quantification 限定与数量：only / all / at least / approximately / respectively 等；
  3) causality 因果：because / therefore / leads to / due to / induced by 等；
  4) concession 让步与转折：although / however / whereas / despite / but 等；
  5) reference 指代与指示：this / these / the former / respectively / above 等。

设计原则：关系表达方式多样，无法机械判定对错，因此只做"原文出现、译文是否出现
对应中文关系词"的软校验；未命中仅进入 warning（人工核验），不阻断 success。数字、
单位、公式、图表编号、引用标记的硬保留由 check_literals.py 负责，此处不重复。
"""
import argparse
import json
import re
import sys

# 每个类别：单词语料用词边界匹配，短语语料用子串匹配（小写）。
RELATION_CATEGORIES = {
    "negation": {
        "tokens": [
            "not", "never", "none", "neither", "nor", "without", "cannot",
            "unable", "absence", "lacks", "absent", "rarely", "seldom",
            "hardly", "unlikely", "failed", "fails",
        ],
        "phrases": [
            "does not", "did not", "do not", "is not", "are not", "was not",
            "were not", "free of", "fails to", "failed to",
        ],
        "zh": [
            "不", "无", "未", "没", "非", "缺", "否", "免", "罕", "极少",
            "罕见", "不能", "无法", "未能", "难以",
        ],
    },
    "quantification": {
        "tokens": [
            "only", "solely", "exclusively", "merely", "all", "every",
            "each", "most", "several", "approximately", "nearly", "almost",
            "significantly", "markedly", "mainly", "primarily", "respectively",
            "both", "either",
        ],
        "phrases": [
            "at least", "at most", "up to", "no more than", "no less than",
        ],
        "zh": [
            "仅", "只", "唯一", "所有", "全部", "每", "任何", "大多数", "多数",
            "若干", "少数", "至少", "至多", "最多", "高达", "不超过", "不低于",
            "约", "大约", "近似", "几乎", "接近", "显著", "明显", "主要",
            "首要", "分别", "两者", "均", "各", "任一",
        ],
    },
    "causality": {
        "tokens": [
            "because", "since", "therefore", "thus", "hence", "consequently",
            "thereby",
        ],
        "phrases": [
            "due to", "owing to", "as a result", "resulting in", "resulted in",
            "leads to", "leading to", "led to", "induced by", "driven by",
            "attributed to", "in order to", "so that",
        ],
        "zh": [
            "因为", "由于", "因此", "所以", "从而", "因而", "导致", "引起",
            "使得", "归因", "以便", "进而", "由此", "故而", "诱导", "驱动",
            "引发", "促成", "所致", "源于",
        ],
    },
    "concession": {
        "tokens": [
            "although", "though", "whereas", "while", "however", "nevertheless",
            "nonetheless", "despite", "unlike", "but", "yet", "instead",
            "conversely",
        ],
        "phrases": [
            "even though", "in spite of", "in contrast", "rather than",
            "on the other hand",
        ],
        "zh": [
            "虽然", "尽管", "然而", "但是", "但", "不过", "相反", "而非",
            "而不是", "另一方面", "反而", "相较", "反之", "相比之下", "不同于",
        ],
    },
    "reference": {
        "tokens": [
            "this", "these", "that", "those", "respectively", "above", "below",
            "aforementioned",
        ],
        "phrases": [
            "the former", "the latter", "the same",
        ],
        "zh": [
            "该", "这", "那", "此", "其", "前者", "后者", "分别", "上述",
            "以下", "以上", "前述", "同一", "相同",
        ],
    },
}

# 单词语料预编译：词边界 + 忽略大小写（仅单字母风险词已排除）。
_COMPILED = {}
for _cat, _spec in RELATION_CATEGORIES.items():
    _COMPILED[_cat] = {
        "tokens": [re.compile(r"\b" + re.escape(t) + r"\b", re.IGNORECASE)
                   for t in _spec["tokens"]],
        "phrases": [p.casefold() for p in _spec["phrases"]],
        "zh": _spec["zh"],
    }


def load_segments(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("segments.json 必须是数组")
    out = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("segments.json 数组元素必须是对象")
        out.append({
            "seg_id": item.get("seg_id", ""),
            "source": item.get("source", "") or "",
            "translation": item.get("translation", "") or "",
        })
    return out


def _category_markers(cat, src_lower):
    spec = _COMPILED[cat]
    phrases = [p for p in spec["phrases"] if p in src_lower]
    tokens = [t.pattern.replace(r"\b", "") for t in spec["tokens"]
              if t.search(src_lower)]
    # 短语命中时，其中单词不再单独列出（如 "failed to" 命中即不再列 "failed"）
    tokens = [t for t in tokens if not any(t in p for p in phrases)]
    return sorted(set(tokens + phrases))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--segments", required=True)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    try:
        segs = load_segments(args.segments)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    warn_items = []
    checked = 0
    warn_segments = 0
    per_cat = {c: {"checked": 0, "warn": 0} for c in RELATION_CATEGORIES}

    for seg in segs:
        src_lower = seg["source"].casefold()
        seg_cats = {c: _category_markers(c, src_lower) for c in RELATION_CATEGORIES}
        seg_cats = {c: m for c, m in seg_cats.items() if m}
        if not seg_cats:
            continue
        checked += 1
        tr = seg["translation"]
        seg_warns = []
        for cat, markers in seg_cats.items():
            per_cat[cat]["checked"] += 1
            if not any(z in tr for z in _COMPILED[cat]["zh"]):
                per_cat[cat]["warn"] += 1
                seg_warns.append({"category": cat, "markers": markers})
        for w in seg_warns:
            warn_items.append({
                "seg_id": seg["seg_id"],
                "category": w["category"],
                "markers": w["markers"],
                "hint": "检查该关系是否在译文中表达（否定/限定/因果/让步/指代）",
            })
        if seg_warns:
            warn_segments += 1

    hit = checked - warn_segments
    rate = round(hit / checked, 4) if checked else None

    print("== 关系保留软校验 ==")
    for cat in RELATION_CATEGORIES:
        c = per_cat[cat]
        print(f"{cat}: checked={c['checked']} warn={c['warn']}")
    print(f"\nsegments checked={checked} hit={hit} rate={rate}")
    for it in warn_items[:40]:
        print(f"  - {it['seg_id']} [{it['category']}] {it['markers']}")

    report = {
        "stats": per_cat,
        "warn_items": warn_items,
        "relation_retention": {
            "checked": checked,
            "hit": hit,
            "rate": rate,
            "warn_count": len(warn_items),
        },
    }
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    # 软校验：始终不因未命中而失败；仅在输入不可读时返回 2。
    return 0


if __name__ == "__main__":
    sys.exit(main())
