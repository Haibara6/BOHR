#!/usr/bin/env python3
"""字面量保留校验（关系准 · 可机械检查部分，stdlib only）。

用法：
  python3 check_literals.py --segments segments.json [--json-out report.json]

- segments.json：数组 [{"seg_id","source","translation"}]，UTF-8。
- 硬校验（不一致 → 退出码 1）：图表编号、文献引用标记、比较关系符号+数字。
- 软校验（仅提示，不阻断）：已知单位（原文单位或对应中文单位，二选一）。

设计原则：只检查"字面量必须原样保留"的确定性部分，不做语义判断。
"""
import argparse
import json
import re
import sys

# 图表编号：Fig. 1 / Figure 1 / Figs. 2 and 3 / Table 2（大小写不敏感）
FIG_RE = re.compile(
    r"\b(Fig(?:ure)?s?\.?|Tables?)\s*(\d+)(?:\s*(?:and|&|,)\s*(\d+))?",
    re.IGNORECASE,
)
# 文献引用标记：[12] / [12,13] / [2–4] / [2-4] / [2,4–6]
CITE_RE = re.compile(r"\[\s*\d+(?:\s*(?:[,，]|[-–—])\s*\d+)*\s*\]")
# 比较/关系符号 + 数字：< 0.05, ≥ 3, ± 0.1, = 5, ≈ 0.9, > 10, = − 0.1719
REL_RE = re.compile(r"(<=|≥|≤|>=|<|>|=|±|≈|~)\s*([-−–]?\s*\d+(?:\.\d+)?)")

# 单位 → 可接受的中文对应（用于软校验：原文单位 或 中文单位 二者之一即可）
UNITS = {
    "μm": ["微米", "µm"], "µm": ["微米", "μm"], "nm": ["纳米"], "mm": ["毫米"],
    "cm": ["厘米"], "km": ["千米", "公里"], "eV": ["电子伏", "电子伏特"],
    "keV": ["千电子伏"], "MeV": ["兆电子伏"], "GeV": ["吉电子伏"],
    "K": ["开尔文"], "°C": ["摄氏度"], "°F": ["华氏度"], "%": [],
    "mol": ["摩尔"], "g": ["克"], "kg": ["千克", "公斤"], "s": ["秒"],
    "ms": ["毫秒"], "min": ["分钟"], "h": ["小时"], "Hz": ["赫兹"],
    "kHz": ["千赫兹"], "MHz": ["兆赫兹"], "GHz": ["吉赫兹"],
    "V": ["伏特"], "A": ["安培"], "W": ["瓦特"],
    "Pa": ["帕斯卡"], "Ω": ["欧姆"], "Å": ["埃"],
    "L": ["升"], "mL": ["毫升"], "μL": ["微升"], "µL": ["微升"],
    "M": ["摩尔每升"], "mM": ["毫摩尔每升"], "μM": ["微摩尔每升"],
    "µM": ["微摩尔每升"], "nM": ["纳摩尔每升"], "ppm": [], "ppb": [],
    "J": ["焦耳"], "kJ": ["千焦"], "N": ["牛顿"], "m": ["米"],
    "Da": ["道尔顿"], "kDa": ["千道尔顿"], "a.u.": ["原子单位"],
}
UNIT_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*([μA-Za-z°%]+(?:\.u\.)?)",
    re.IGNORECASE,
)


def _contains(text, sub):
    return sub.casefold() in text.casefold()


def _norm(s):
    # 统一比较符号，避免译文把 ≤ 写成 <= 被判不一致
    return (s.replace("≤", "<=").replace("≥", ">=")
             .replace("±", "+/-").replace("≈", "~"))


def _norm_number(s):
    # 统一 Unicode 负号/短横及符号后的空白，避免 "= − 0.1719" 漏检或误判。
    return (s.replace("−", "-").replace("–", "-")
             .replace(" ", ""))


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


def check_figures(seg):
    """返回图表编号项；Figs. 2 and 3 中的 2、3 分别检查。"""
    items = []
    for m in FIG_RE.finditer(seg["source"]):
        tr = seg["translation"]
        for num in (m.group(2), m.group(3)):
            if not num:
                continue
            ok = (num in tr) and bool(re.search(r"图|表|Fig|Table|Figure", tr, re.IGNORECASE))
            items.append({
                "literal": m.group(0), "num": num,
                "ok": ok, "kind": "figure_table_number",
            })
    return items


def check_citations(seg):
    items = []
    for m in CITE_RE.finditer(seg["source"]):
        ok = m.group(0) in seg["translation"]
        items.append({"literal": m.group(0), "ok": ok, "kind": "citation_marker"})
    return items


def check_relations(seg):
    items = []
    for m in REL_RE.finditer(seg["source"]):
        sym, num = m.group(1), m.group(2)
        tr = seg["translation"]
        ok = (_norm_number(num) in _norm_number(tr)) and (_norm(sym) in _norm(tr))
        items.append({"literal": m.group(0), "ok": ok, "kind": "relation_sign_number"})
    return items


def check_units(seg):
    items = []
    for m in UNIT_RE.finditer(seg["source"]):
        num, unit = m.group(1), m.group(2)
        # 只检查已知单位，避免把 "Fig. 2 shows" 中的 shows 误判为单位。
        if unit not in UNITS:
            continue
        tr = seg["translation"]
        # 原文单位命中，或任一中文对应命中。
        hit_orig = _contains(tr, unit)
        hit_zh = any(zh and _contains(tr, zh) for zh in UNITS.get(unit, []))
        ok = hit_orig or hit_zh
        items.append({"literal": m.group(0), "unit": unit, "ok": ok, "kind": "unit"})
    return items


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

    hard_miss = []      # 硬校验不一致 → 非零退出
    warnings = []       # 单位等软校验 → 仅提示
    stats = {"figures": {"hit": 0, "miss": 0},
             "citations": {"hit": 0, "miss": 0},
             "relations": {"hit": 0, "miss": 0},
             "units": {"hit": 0, "warn": 0}}

    for seg in segs:
        for it in check_figures(seg):
            stats["figures"]["hit" if it["ok"] else "miss"] += 1
            if not it["ok"]:
                hard_miss.append({"seg_id": seg["seg_id"], "kind": it["kind"], "literal": it["literal"]})
        for it in check_citations(seg):
            stats["citations"]["hit" if it["ok"] else "miss"] += 1
            if not it["ok"]:
                hard_miss.append({"seg_id": seg["seg_id"], "kind": it["kind"], "literal": it["literal"]})
        for it in check_relations(seg):
            stats["relations"]["hit" if it["ok"] else "miss"] += 1
            if not it["ok"]:
                hard_miss.append({"seg_id": seg["seg_id"], "kind": it["kind"], "literal": it["literal"]})
        for it in check_units(seg):
            stats["units"]["hit" if it["ok"] else "warn"] += 1
            if not it["ok"]:
                warnings.append({"seg_id": seg["seg_id"], "kind": it["kind"], "literal": it["literal"]})

    print("== 字面量保留校验 ==")
    for k in ("figures", "citations", "relations"):
        s = stats[k]
        print(f"{k}: {s['hit']} hit / {s['miss']} miss")
    print(f"units: {stats['units']['hit']} hit / {stats['units']['warn']} warn")
    print(f"\nHARD MISS: {len(hard_miss)}")
    for item in hard_miss[:40]:
        print(f"  - {item}")
    print(f"WARN (unit): {len(warnings)}")
    for item in warnings[:40]:
        print(f"  - {item}")

    report = {
        "stats": stats,
        "hard_miss": hard_miss,
        "warnings": warnings,
        "literal_retention": {
            "hard_miss_count": len(hard_miss),
            "unit_warn_count": len(warnings),
        },
    }
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    return 1 if hard_miss else 0


if __name__ == "__main__":
    sys.exit(main())
