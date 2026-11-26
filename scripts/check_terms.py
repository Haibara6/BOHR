#!/usr/bin/env python3
"""术语一致性校验（义项级，stdlib only，无第三方依赖）。

用法：
  python3 check_terms.py --terms terms.tsv --segments segments.json [--json-out report.json]

- terms.tsv（UTF-8，制表符分隔），表头 8 列：
  source_term<TAB>sense_id<TAB>canonical_translation<TAB>domain<TAB>context_clues<TAB>example<TAB>notes<TAB>retention
  · context_clues：判定义项的关键词，用分号/逗号分隔；为空表示该词形单义。
  · retention：keep/translate/annotate，本脚本不参与判定，仅透传。
  · 同形异义词（如 cell）应拆成多条，靠 sense_id 与 context_clues 区分义项。
- segments.json：数组 [{"seg_id","source","translation"}]，UTF-8。
- 判定口径：
  1) source 中出现 source_term 的段才参与；
  2) 若给定了 context_clues，段 source 至少命中一个 clue 才归属该义项，否则记 ambiguous（不判错）；
  3) 归属该义项的段，translation 中须出现 canonical_translation 或 source_term（保留原文的情形）。
- 退出码：0=无 miss；1=存在 miss；2=参数/解析错误。
"""
import argparse
import csv
import json
import re
import sys


def _contains(text, sub):
    return sub.casefold() in text.casefold()


def split_clues(raw):
    if not raw or not raw.strip():
        return []
    return [c.strip() for c in re.split(r"[;,，；]", raw) if c.strip()]


def load_terms(path):
    terms = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader, None)
        if not header or header[0].strip() != "source_term":
            raise ValueError("terms.tsv 首行必须为表头 source_term\tsense_id\tcanonical_translation\t...")
        for row in reader:
            if not row or not row[0].strip():
                continue
            src = row[0].strip()
            sense = row[1].strip() if len(row) >= 2 else ""
            dst = row[2].strip() if len(row) >= 3 and row[2].strip() else src
            clues = split_clues(row[4]) if len(row) >= 5 else []
            terms.append({"source": src, "sense_id": sense, "canonical": dst, "clues": clues})
    return terms


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
        terms = load_terms(args.terms)
        segs = load_segments(args.segments)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    report = {"total_terms": len(terms), "terms": [], "mismatch_seg_ids": [], "ambiguous_seg_ids": []}
    mismatches = 0

    for term in terms:
        src, dst, clues = term["source"], term["canonical"], term["clues"]
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

        entry = {
            "source_term": src,
            "sense_id": term["sense_id"],
            "canonical_translation": dst,
            "context_clues": clues,
            "occurrences": len(hit_segs),
            "assigned": len(matched) + len(missed),
            "matched": len(matched),
            "missed": len(missed),
            "ambiguous": len(ambiguous),
            "missed_seg_ids": missed,
            "ambiguous_seg_ids": ambiguous,
        }
        if entry["assigned"]:
            entry["consistency"] = len(matched) / entry["assigned"]
        else:
            entry["consistency"] = None
        report["terms"].append(entry)

        print(f"[term] {src!r} (sense={term['sense_id'] or '-'}) -> {dst!r}: "
              f"{len(matched)}/{entry['assigned']} matched"
              + (f" MISS: {missed}" if missed else "")
              + (f" AMBIG: {ambiguous}" if ambiguous else ""))
        if not hit_segs:
            print("  (术语未在 source 中出现)")

    print(f"\nTOTAL: {len(terms)} terms, {mismatches} mismatch segments, "
          f"{len(set(report['ambiguous_seg_ids']))} ambiguous segments")
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
