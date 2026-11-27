#!/usr/bin/env python3
"""术语一致性校验（义项级 + 术语表结构预检，stdlib only）。

用法：
  python3 check_terms.py --terms terms.tsv --segments segments.json [--json-out report.json]

- terms.tsv（UTF-8，制表符分隔），表头 8 列：
  source_term<TAB>sense_id<TAB>canonical_translation<TAB>domain<TAB>context_clues<TAB>example<TAB>notes<TAB>retention
- 结构预检（任一违反即非零退出）：
  1) 每个数据行必须正好 8 列；
  2) source_term + sense_id 唯一；
  3) retention 取值为 keep/translate/annotate；
  4) retention=translate 时 canonical_translation 不得为空（不再静默回退成 source）。
- 判定口径（义项级）：
  1) source 中出现 source_term 的段才参与；
  2) 若给定了 context_clues，段 source 至少命中一个 clue 才归属该义项，否则记 ambiguous；
  3) 归属该义项的段，translation 中须出现 canonical_translation 或 source_term。
- 退出码：0=通过；1=存在术语不一致或结构错误；2=参数/文件/JSON 解析错误。
"""
import argparse
import csv
import json
import re
import sys
from collections import defaultdict

VALID_RETENTION = {"keep", "translate", "annotate"}


def _contains(text, sub):
    if not sub:
        return False
    return sub.casefold() in text.casefold()


def split_clues(raw):
    if not raw or not raw.strip():
        return []
    return [c.strip() for c in re.split(r"[;,，；]", raw) if c.strip()]


def load_terms(path):
    terms = []
    issues = {
        "bad_columns": [],
        "duplicate_terms": [],
        "invalid_retention": [],
        "missing_canonical": [],
    }
    seen = {}
    total_rows = 0
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader, None)
        if not header or header[0].strip() != "source_term":
            raise ValueError("terms.tsv 首行必须为表头 source_term\tsense_id\tcanonical_translation\t...")
        for row in reader:
            if not row or (len(row) == 1 and not row[0].strip()):
                continue  # 空行
            total_rows += 1
            row_no = total_rows + 1  # +1 表头
            if len(row) != 8:
                issues["bad_columns"].append({
                    "row": row_no,
                    "columns": len(row),
                    "source_term": row[0].strip() if row else "",
                    "message": f"expected 8 columns, got {len(row)}",
                })
                continue
            src = row[0].strip()
            sense = row[1].strip()
            dst = row[2].strip()
            domain = row[3].strip()
            clues = split_clues(row[4])
            retention = row[7].strip()
            if not src:
                continue

            if retention not in VALID_RETENTION:
                issues["invalid_retention"].append({
                    "source_term": src,
                    "sense_id": sense,
                    "retention": retention,
                })

            skip = False
            skip_reason = ""
            if retention == "translate" and not dst:
                issues["missing_canonical"].append({
                    "source_term": src,
                    "sense_id": sense,
                })
                skip = True
                skip_reason = "missing_canonical"
            elif retention in ("keep", "annotate") and not dst:
                # keep/annotate 保留原文时 canonical 与 source 相同，属合法回退
                dst = src

            key = (src.casefold(), sense)
            if key in seen:
                issues["duplicate_terms"].append({
                    "source_term": src,
                    "sense_id": sense,
                    "rows": [seen[key], row_no],
                })
                continue  # 仅保留首个条目，避免重复计数
            seen[key] = row_no

            terms.append({
                "source": src,
                "sense_id": sense,
                "canonical": dst,
                "domain": domain,
                "clues": clues,
                "retention": retention,
                "skip": skip,
                "skip_reason": skip_reason,
            })
    return terms, issues, total_rows


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


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--terms", required=True)
    ap.add_argument("--segments", required=True)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    try:
        terms, issues, total_rows = load_terms(args.terms)
        segs = load_segments(args.segments)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    report = {
        "total_terms": len(terms),
        "total_rows": total_rows,
        "terms": [],
        "mismatch_seg_ids": [],
        "ambiguous_seg_ids": [],
        "missing_canonical": issues["missing_canonical"],
        "duplicate_terms": issues["duplicate_terms"],
        "invalid_retention": issues["invalid_retention"],
        "bad_columns": issues["bad_columns"],
        "structural_errors": [],
        "homographs": [],
    }
    mismatches = 0

    for term in terms:
        src, dst, clues = term["source"], term["canonical"], term["clues"]
        if term["skip"]:
            report["terms"].append({
                "source_term": src,
                "sense_id": term["sense_id"],
                "canonical_translation": dst,
                "domain": term["domain"],
                "retention": term["retention"],
                "context_clues": clues,
                "skipped": True,
                "skip_reason": term["skip_reason"],
                "occurrences": 0,
                "assigned": 0,
                "matched": 0,
                "missed": 0,
                "ambiguous": 0,
                "missed_seg_ids": [],
                "ambiguous_seg_ids": [],
                "consistency": None,
            })
            print(f"[term] {src!r} (sense={term['sense_id'] or '-'}) "
                  f"SKIP: {term['skip_reason']}")
            continue

        hit_segs = [s for s in segs if _contains(s["source"], src)]
        matched, missed, ambiguous = [], [], []
        for s in hit_segs:
            # 义项判定：有 clues 时须命中至少一个 clue 才归属本义项
            if clues and not any(_contains(s["source"], c) for c in clues):
                ambiguous.append(s["seg_id"])
                continue
            if _contains(s["translation"], dst) or _contains(s["translation"], src):
                matched.append(s["seg_id"])
            else:
                missed.append(s["seg_id"])
        if missed:
            mismatches += len(missed)
            report["mismatch_seg_ids"].extend(missed)
        if ambiguous:
            report["ambiguous_seg_ids"].extend(ambiguous)

        assigned = len(matched) + len(missed)
        entry = {
            "source_term": src,
            "sense_id": term["sense_id"],
            "canonical_translation": dst,
            "domain": term["domain"],
            "retention": term["retention"],
            "context_clues": clues,
            "occurrences": len(hit_segs),
            "assigned": assigned,
            "matched": len(matched),
            "missed": len(missed),
            "ambiguous": len(ambiguous),
            "missed_seg_ids": missed,
            "ambiguous_seg_ids": ambiguous,
        }
        entry["consistency"] = (len(matched) / assigned) if assigned else None
        report["terms"].append(entry)

        print(f"[term] {src!r} (sense={term['sense_id'] or '-'}) -> {dst!r}: "
              f"{len(matched)}/{assigned} matched"
              + (f" MISS: {missed}" if missed else "")
              + (f" AMBIG: {ambiguous}" if ambiguous else ""))
        if not hit_segs:
            print("  (术语未在 source 中出现)")

    # 同形异义词清单：同一 source_term 有多个义项时提示复核 sense 归属
    groups = defaultdict(list)
    for term in terms:
        groups[term["source"].casefold()].append(term)
    for key in sorted(groups):
        entries = groups[key]
        if len(entries) > 1:
            report["homographs"].append({
                "source_term": entries[0]["source"],
                "senses": [
                    {"sense_id": t["sense_id"], "domain": t["domain"], "retention": t["retention"]}
                    for t in entries
                ],
            })

    # 展平结构错误（不含 missing_canonical，后者单独成表）
    for item in issues["bad_columns"]:
        report["structural_errors"].append({"code": "bad_columns", **item})
    for item in issues["duplicate_terms"]:
        report["structural_errors"].append({"code": "duplicate_terms", **item})
    for item in issues["invalid_retention"]:
        report["structural_errors"].append({"code": "invalid_retention", **item})

    has_errors = bool(report["structural_errors"] or issues["missing_canonical"])
    print(f"\nTOTAL: {len(terms)} terms, {mismatches} mismatch segments, "
          f"{len(set(report['ambiguous_seg_ids']))} ambiguous segments, "
          f"{len(report['structural_errors'])} structural errors, "
          f"{len(issues['missing_canonical'])} missing canonical")
    if has_errors:
        for e in report["structural_errors"]:
            print(f"  STRUCT: {e}")
        for e in issues["missing_canonical"]:
            print(f"  MISSING-CANONICAL: {e}")
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    return 1 if (mismatches or has_errors) else 0


if __name__ == "__main__":
    sys.exit(main())
