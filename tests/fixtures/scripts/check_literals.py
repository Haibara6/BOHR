#!/usr/bin/env python3
"""字面量保留校验（关系准 · 可机械检查部分，stdlib only）。

用法：
  python3 check_literals.py --segments segments.json [--json-out report.json]

- segments.json：数组 [{"seg_id","source","translation"}]，UTF-8。
- 硬校验（不一致 → 退出码 1）：
  1) 图表编号（Fig. 1 / Figures 2 and 3 / Table 2）；
  2) 方括号数字引用 [12] / [2–4] / [12,13]；
  3) 作者-年份引用 (Smith et al., 2020) / Smith et al. (2020)：年份与首作者名须保留；
  4) 比较/关系符号 + 数字：数字必须保留，符号可按映射表用中文对应
     （< 小于、> 大于、= 等于/为、~ 约/大约 等）。
- 软校验（仅提示，不阻断）：
  1) 已知单位（原文单位或对应中文单位二选一），含 cm⁻¹、m²、μg/mL、cells/mL、
     M⁻¹s⁻¹ 等复合/指数单位；波数等须保留原文的单位，对应中文列表为空；
  2) 上标数字 ²³⁴ 等（可能是上标引用或指数，须渲染原页确认）。

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
# 方括号数字引用：[12] / [12,13] / [2–4] / [2-4] / [2,4–6]
CITE_RE = re.compile(r"\[\s*\d+(?:\s*(?:[,，]|[-–—])\s*\d+)*\s*\]")

# 作者名片段：首字母大写 + 字母/撇号/连字符（O'Brien、García-Morales 等常见写法）
NAME = r"[A-Z][A-Za-z'’\-]+"
AUTHORS = NAME + r"(?:\s+(?:and|&)\s+" + NAME + r"|\s+et\s+al\.?)?"
# 括号式作者-年份：(Smith et al., 2020) / (Smith, 2020) / (Smith and Wang, 2020)。
# 不要求右括号紧跟，故也能覆盖 "(Smith et al., 2020; Wang, 2019)" 的首个作者-年份对。
AUTHOR_YEAR_PAREN_RE = re.compile(
    r"\(" + "(" + AUTHORS + ")" + r"(?:,\s*|\s+)((?:19|20)\d{2}[a-z]?)"
)
# 叙述式：Smith et al. (2020) / Smith (2020)
AUTHOR_YEAR_NARR_RE = re.compile(
    r"\b(" + AUTHORS + r")\s*\(((?:19|20)\d{2}[a-z]?)\)"
)
# 英文月份：避免 "January 2020" 这类日期被当作作者-年份引用
MONTH_NAMES = {"january", "february", "march", "april", "may", "june",
               "july", "august", "september", "october", "november", "december"}

# 比较/关系符号 + 数字：< 0.05, ≥ 3, ± 0.1, = 5, ≈ 0.9, > 10, = − 0.1719
REL_RE = re.compile(r"(<=|≥|≤|>=|<|>|=|±|≈|~)\s*([-−–]?\s*\d+(?:\.\d+)?)")

# 关系符号的可接受对应（数字必须另保留；符号可用中文对应，双通道通过）
RELATION_EQUIV = {
    "<": ["<", "小于", "低于", "不足"],
    "<=": ["<=", "≤", "小于等于", "不超过"],
    "≤": ["≤", "<=", "小于等于", "不超过"],
    ">": [">", "大于", "高于", "超过"],
    ">=": [">=", "≥", "大于等于", "不低于", "至少"],
    "≥": ["≥", ">=", "大于等于", "不低于", "至少"],
    "=": ["=", "等于", "为", "是"],
    "±": ["±", "+/-", "正负"],
    "≈": ["≈", "~", "约", "大约", "近似"],
    "~": ["~", "≈", "约", "大约", "近似"],
}

# 上标数字（上标引用或指数，须渲染原页确认后保留）
SUPERSCRIPT_RE = re.compile(r"[¹²³⁴⁵⁶⁷⁸⁹⁰]+")

# 单位 → 可接受的中文对应（软校验：原文单位或中文单位二者之一即可；空列表=只能保留原文）。
# 键统一用希腊字母 μ；µ（U+00B5）会在 _norm_unit 中归一到 μ。
UNITS = {
    # 长度/面积/体积
    "μm": ["微米"], "nm": ["纳米"], "mm": ["毫米"], "cm": ["厘米"],
    "cm²": ["平方厘米"], "cm³": ["立方厘米"],
    "m": ["米"], "m²": ["平方米"], "m³": ["立方米"],
    "m⁻¹": [], "cm⁻¹": [],  # 波数：保留原文
    "km": ["千米", "公里"],
    # 质量/浓度
    "μg": ["微克"], "mg": ["毫克"], "g": ["克"], "kg": ["千克", "公斤"],
    "μg/mL": ["微克每毫升", "微克/毫升"],
    "mg/mL": ["毫克每毫升", "毫克/毫升"],
    "mg/L": ["毫克每升", "毫克/升"],
    "μg/L": ["微克每升", "微克/升"],
    "cells/mL": ["细胞每毫升", "个每毫升", "细胞/毫升"],
    "mol/L": ["摩尔每升", "摩尔/升"],
    "μmol/L": ["微摩尔每升", "微摩尔/升"],
    "mmol/L": ["毫摩尔每升", "毫摩尔/升"],
    "mL/min": ["毫升每分钟", "毫升/分钟"],
    "L/min": ["升每分钟", "升/分钟"],
    # 能量/温度/频率
    "eV": ["电子伏", "电子伏特"], "keV": ["千电子伏"],
    "MeV": ["兆电子伏"], "GeV": ["吉电子伏"],
    "K": ["开尔文"], "°C": ["摄氏度"], "°F": ["华氏度"], "%": [],
    "Hz": ["赫兹"], "kHz": ["千赫兹"], "MHz": ["兆赫兹"], "GHz": ["吉赫兹"],
    # 电学
    "V": ["伏特"], "A": ["安培"], "W": ["瓦特"],
    # 力学/压强/其他
    "Pa": ["帕斯卡"], "Ω": ["欧姆"], "Å": ["埃"],
    "L": ["升"], "mL": ["毫升"], "μL": ["微升"],
    # 摩尔浓度（M）及复合/指数单位
    "M": ["摩尔每升"], "mM": ["毫摩尔每升"], "μM": ["微摩尔每升"], "nM": ["纳摩尔每升"],
    "M⁻¹s⁻¹": [], "s⁻¹": [],
    # 时间/摩尔
    "mol": ["摩尔"], "s": ["秒"], "ms": ["毫秒"], "min": ["分钟"], "h": ["小时"],
    # 其他
    "J": ["焦耳"], "kJ": ["千焦"], "N": ["牛顿"],
    "Da": ["道尔顿"], "kDa": ["千道尔顿"], "a.u.": ["原子单位"],
    "ppm": [], "ppb": [],
}

_SUPER_DIGITS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


def _norm_unit(s):
    # 统一 micro sign 与希腊 μ、各类减号与上标，供单位匹配；1:1 映射，长度不变。
    s = s.replace("µ", "μ")
    s = s.replace("−", "-").replace("–", "-").replace("—", "-")
    s = s.replace("⁻", "-").replace("⁺", "+")
    return s.translate(_SUPER_DIGITS)


_UNIT_ENTRIES = []
for _key, _zh in UNITS.items():
    _nkey = _norm_unit(_key)
    _UNIT_ENTRIES.append({
        "key": _key,
        "nkey": _nkey,
        "zh": _zh,
        "nzh": [_norm_unit(z) for z in _zh],
    })
_UNIT_ENTRIES.sort(key=lambda e: len(e["nkey"]), reverse=True)
_UNIT_MAP = {e["nkey"]: e for e in _UNIT_ENTRIES}
_UNIT_ALT = "|".join(re.escape(e["nkey"]) for e in _UNIT_ENTRIES)
# 大小写敏感：M（摩尔浓度）与 m（米）等必须区分；单位后不得紧跟字母/数字，避免 "shows" 误判。
UNIT_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*(" + _UNIT_ALT + r")(?![A-Za-z0-9])")


def _contains(text, sub):
    if not sub:
        return False
    return sub.casefold() in text.casefold()


def _norm_number(s):
    # 统一 Unicode 负号/短横及符号后的空白，避免 "= − 0.1719" 漏检或误判。
    return s.replace("−", "-").replace("–", "-").replace(" ", "")


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


def _author_year_item(seg, literal, authors, year, tr):
    year_ok = year in tr
    first_author = authors.split()[0] if authors else ""
    author_ok = _contains(tr, first_author)
    ok = year_ok and author_ok
    detail = ""
    if not year_ok and not author_ok:
        detail = "年份与首作者名均缺失"
    elif not year_ok:
        detail = "年份缺失"
    elif not author_ok:
        detail = "首作者名缺失（可能被译成中文）"
    return {
        "literal": literal, "authors": authors, "year": year,
        "first_author": first_author, "ok": ok,
        "kind": "citation_author_year", "detail": detail,
    }


def _is_month_date(authors):
    tokens = authors.split()
    if len(tokens) != 1:
        return False
    return tokens[0].casefold() in MONTH_NAMES


def check_author_year(seg):
    items = []
    tr = seg["translation"]
    for m in AUTHOR_YEAR_PAREN_RE.finditer(seg["source"]):
        authors, year = m.group(1), m.group(2)
        if _is_month_date(authors):
            continue
        items.append(_author_year_item(seg, m.group(0), authors, year, tr))
    for m in AUTHOR_YEAR_NARR_RE.finditer(seg["source"]):
        authors, year = m.group(1), m.group(2)
        if _is_month_date(authors):
            continue
        items.append(_author_year_item(seg, m.group(0), authors, year, tr))
    return items


def check_relations(seg):
    items = []
    for m in REL_RE.finditer(seg["source"]):
        sym, num = m.group(1), m.group(2)
        tr = seg["translation"]
        num_ok = _norm_number(num) in _norm_number(tr)
        sym_ok = any(e in tr for e in RELATION_EQUIV.get(sym, [sym]))
        ok = num_ok and sym_ok
        items.append({
            "literal": m.group(0), "sym": sym, "num": num,
            "ok": ok, "kind": "relation_sign_number",
        })
    return items


def check_units(seg):
    items = []
    src = seg["source"]
    nsrc = _norm_unit(src)
    ntr = _norm_unit(seg["translation"])
    for m in UNIT_RE.finditer(nsrc):
        num, nunit = m.group(1), m.group(2)
        # 归一化是 1:1 字符替换，同位置切回原文以保留展示用原记法
        literal = src[m.start():m.end()]
        entry = _UNIT_MAP[nunit]
        hit_orig = nunit in ntr
        hit_zh = any(nzh and nzh in ntr for nzh in entry["nzh"])
        ok = hit_orig or hit_zh
        items.append({
            "literal": literal, "unit": entry["key"],
            "ok": ok, "kind": "unit",
            "start": m.start(), "end": m.end(),
        })
    return items


def check_superscripts(seg, unit_spans):
    items = []
    tr = seg["translation"]
    for m in SUPERSCRIPT_RE.finditer(seg["source"]):
        # 复合/指数单位（cm⁻¹、m² 等）已由单位软校验覆盖，不重复作为"上标数字"警告
        if any(s <= m.start() < e for s, e in unit_spans):
            continue
        ok = m.group(0) in tr
        items.append({"literal": m.group(0), "ok": ok, "kind": "superscript_number"})
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
    warnings = []       # 单位/上标等软校验 → 仅提示
    stats = {
        "figures": {"hit": 0, "miss": 0},
        "citations": {"hit": 0, "miss": 0},
        "author_year": {"hit": 0, "miss": 0},
        "relations": {"hit": 0, "miss": 0},
        "units": {"hit": 0, "warn": 0},
        "superscripts": {"hit": 0, "warn": 0},
    }

    for seg in segs:
        for it in check_figures(seg):
            stats["figures"]["hit" if it["ok"] else "miss"] += 1
            if not it["ok"]:
                hard_miss.append({"seg_id": seg["seg_id"], "kind": it["kind"], "literal": it["literal"]})
        for it in check_citations(seg):
            stats["citations"]["hit" if it["ok"] else "miss"] += 1
            if not it["ok"]:
                hard_miss.append({"seg_id": seg["seg_id"], "kind": it["kind"], "literal": it["literal"]})
        for it in check_author_year(seg):
            stats["author_year"]["hit" if it["ok"] else "miss"] += 1
            if not it["ok"]:
                hard_miss.append({
                    "seg_id": seg["seg_id"], "kind": it["kind"], "literal": it["literal"],
                    "detail": it.get("detail", ""),
                })
        for it in check_relations(seg):
            stats["relations"]["hit" if it["ok"] else "miss"] += 1
            if not it["ok"]:
                hard_miss.append({"seg_id": seg["seg_id"], "kind": it["kind"], "literal": it["literal"]})
        unit_items = check_units(seg)
        for it in unit_items:
            stats["units"]["hit" if it["ok"] else "warn"] += 1
            if not it["ok"]:
                warnings.append({
                    "seg_id": seg["seg_id"], "kind": it["kind"],
                    "literal": it["literal"], "unit": it.get("unit", ""),
                })
        unit_spans = [(it["start"], it["end"]) for it in unit_items]
        for it in check_superscripts(seg, unit_spans):
            stats["superscripts"]["hit" if it["ok"] else "warn"] += 1
            if not it["ok"]:
                warnings.append({"seg_id": seg["seg_id"], "kind": it["kind"], "literal": it["literal"]})

    print("== 字面量保留校验 ==")
    for k in ("figures", "citations", "author_year", "relations"):
        s = stats[k]
        print(f"{k}: {s['hit']} hit / {s['miss']} miss")
    print(f"units: {stats['units']['hit']} hit / {stats['units']['warn']} warn")
    print(f"superscripts: {stats['superscripts']['hit']} hit / {stats['superscripts']['warn']} warn")
    print(f"\nHARD MISS: {len(hard_miss)}")
    for item in hard_miss[:40]:
        print(f"  - {item}")
    print(f"WARN (soft): {len(warnings)}")
    for item in warnings[:40]:
        print(f"  - {item}")

    report = {
        "stats": stats,
        "hard_miss": hard_miss,
        "warnings": warnings,
        "literal_retention": {
            "hard_miss_count": len(hard_miss),
            "unit_warn_count": stats["units"]["warn"],
            "soft_warn_count": len(warnings),
        },
    }
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    return 1 if hard_miss else 0


if __name__ == "__main__":
    sys.exit(main())
