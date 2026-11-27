#!/usr/bin/env python3
"""汇总三个校验报告，生成 result.json 的 verification 字段（stdlib only）。

用法：
  python3 build_verification.py \
    --terms-report work/terms.report.json \
    --segments-report work/segments.report.json \
    --literals-report work/literals.report.json \
    --out work/verification.json

输入分别为 check_terms.py、check_segments.py、check_literals.py 的 --json-out 输出。
`verification.term_consistency` 是术语一致率的唯一权威来源；字面量硬失败明细原样带入
`verification.literal_retention.hard_miss_items` 与 `warnings`，使 result.json 自身可定位
"哪段、哪个字面量"失败，不再依赖 work/ 目录。
退出码：0=全部硬校验通过；1=存在术语不一致/结构错误/缺段重段多余段/字面量硬错误；2=参数或解析错误。
"""
import argparse
import json
import sys

HARD_LITERAL_KINDS = ("figures", "citations", "author_year", "relations")


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} 必须是 JSON 对象")
    return data


def ratio(numerator, denominator):
    if not denominator:
        return None
    return round(numerator / denominator, 4)


def human_label(w):
    kind = w.get("kind", "")
    literal = w.get("literal", "")
    if kind == "unit":
        return f"单位 {literal}"
    if kind == "superscript_number":
        return f"上标数字 {literal}"
    return f"{kind} {literal}".strip()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--terms-report", required=True)
    ap.add_argument("--segments-report", required=True)
    ap.add_argument("--literals-report", required=True)
    ap.add_argument("--relations-report", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    try:
        terms = load_json(args.terms_report)
        segments = load_json(args.segments_report)
        literals = load_json(args.literals_report)
        relations = load_json(args.relations_report) if args.relations_report else None
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    term_entries = terms.get("terms", [])
    matched = sum(int(t.get("matched", 0)) for t in term_entries)
    assigned = sum(int(t.get("assigned", 0)) for t in term_entries)
    term_mismatch = sorted(set(terms.get("mismatch_seg_ids", [])))
    term_ambiguous = sorted(set(terms.get("ambiguous_seg_ids", [])))
    missing_canonical = list(terms.get("missing_canonical", []))
    structural_errors = list(terms.get("structural_errors", []))
    term_summary = {
        "matched": matched,
        "assigned": assigned,
        "rate": ratio(matched, assigned),
        "mismatch_segments": term_mismatch,
        "ambiguous_segments": term_ambiguous,
        "missing_canonical": missing_canonical,
        "structural_errors": structural_errors,
    }

    missing = list(segments.get("missing", []))
    extra = list(segments.get("extra", []))
    duplicated = list(segments.get("duplicated", []))
    duplicated_inventory = list(segments.get("duplicated_inventory", []))
    inventory_count = int(segments.get("inventory_unique_count",
                                       segments.get("inventory_count", 0)))
    result_count = int(segments.get("result_unique_count",
                                    segments.get("result_count", 0)))
    covered = max(0, inventory_count - len(set(missing)))
    exact = inventory_count > 0 and not (missing or extra or duplicated or duplicated_inventory)
    segment_summary = {
        "covered": covered,
        "inventory": inventory_count,
        "result": result_count,
        "rate": ratio(covered, inventory_count),
        "exact": exact,
        "missing": missing,
        "extra": extra,
        "duplicated": duplicated,
        "duplicated_inventory": duplicated_inventory,
    }

    stats = literals.get("stats", {})
    literal_hit = 0
    literal_miss = 0
    for kind in HARD_LITERAL_KINDS:
        literal_hit += int(stats.get(kind, {}).get("hit", 0))
        literal_miss += int(stats.get(kind, {}).get("miss", 0))
    literal_checked = literal_hit + literal_miss
    literal_meta = literals.get("literal_retention", {})
    hard_miss_items = list(literals.get("hard_miss", []))
    warnings = list(literals.get("warnings", []))
    hard_miss = int(literal_meta.get("hard_miss_count", len(hard_miss_items)))
    unit_warn = int(literal_meta.get("unit_warn_count", stats.get("units", {}).get("warn", 0)))
    soft_warn = int(literal_meta.get("soft_warn_count", len(warnings)))
    literal_summary = {
        "hit": literal_hit,
        "checked": literal_checked,
        "rate": ratio(literal_hit, literal_checked),
        "hard_miss": hard_miss,
        "hard_miss_items": hard_miss_items,
        "unit_warn": unit_warn,
        "soft_warn": soft_warn,
        "warnings": warnings,
    }

    # 关系保留（软校验）：类别级"原文出现、译文是否仍表达"，未命中仅提示。
    rel_warns = list(relations.get("warn_items", [])) if relations else []
    rel_meta = relations.get("relation_retention", {}) if relations else {}
    relation_summary = {
        "checked": int(rel_meta.get("checked", 0)),
        "hit": int(rel_meta.get("hit", 0)),
        "rate": rel_meta.get("rate"),
        "warn_count": int(rel_meta.get("warn_count", len(rel_warns))),
        "warn_items": rel_warns,
    }

    # 人工核验项统一为 {seg_id, item, result, note}；软校验未命中 result=warn。
    human_confirm = [
        {
            "seg_id": w.get("seg_id", ""),
            "item": human_label(w),
            "result": "warn",
            "note": "软校验未命中，需人工确认",
        }
        for w in warnings
    ]
    for w in rel_warns:
        human_confirm.append({
            "seg_id": w.get("seg_id", ""),
            "item": "关系[%s] %s" % (
                w.get("category", ""), ", ".join(w.get("markers", []))),
            "result": "warn",
            "note": "关系软校验未命中，确认否定/限定/因果/让步/指代是否仍被表达",
        })
    term_ok = not term_mismatch and not missing_canonical and not structural_errors
    all_hard_checks_pass = term_ok and exact and hard_miss == 0
    verification = {
        "term_consistency": term_summary,
        "segment_completeness": segment_summary,
        "literal_retention": literal_summary,
        "relation_retention": relation_summary,
        "relation_checklist": [],
        "human_confirm": human_confirm,
        "all_hard_checks_pass": all_hard_checks_pass,
    }

    try:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(verification, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: 无法写入 {args.out}: {e}", file=sys.stderr)
        return 2

    print(f"terms: {matched}/{assigned}, rate={term_summary['rate']}, "
          f"missing_canonical={len(missing_canonical)}, structural_errors={len(structural_errors)}")
    print(f"segments: {covered}/{inventory_count}, exact={exact}, "
          f"dup_inv={len(duplicated_inventory)}")
    print(f"literals: {literal_hit}/{literal_checked}, hard_miss={hard_miss}, "
          f"unit_warn={unit_warn}, soft_warn={soft_warn}")
    print(f"relations: {relation_summary['hit']}/{relation_summary['checked']}, "
          f"rate={relation_summary['rate']}, warn={relation_summary['warn_count']}")
    print(f"all_hard_checks_pass={all_hard_checks_pass}; wrote {args.out}")
    return 0 if all_hard_checks_pass else 1


if __name__ == "__main__":
    sys.exit(main())
