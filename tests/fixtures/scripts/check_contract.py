#!/usr/bin/env python3
"""result.json 结构与 output_contract 完备性校验（stdlib only）。

用法：
  python3 check_contract.py --result result.json [--case case.json] [--json-out report.json]

- --result：最终 /app/output/result.json。
- --case（可选）：/input/case.json，读取 output_contract 逐项断言字段在 result.json 顶层存在并按类型填值。
- 结构校验（总是执行）：
  1) bilingual_segments 每段必填 seg_id/location/page/kind/source/translation；
  2) bilingual_segments 无重复 seg_id；
  3) uncertainty/evidence/protected_entities 的 seg_id 引用指向存在的段（悬空仅 warning）；
  4) status=success 时必须 all_hard_checks_pass=true 且 segment_completeness.exact=true 且无 fail 关系项。
- 退出码：0=通过（含仅 warning）；1=契约或结构错误；2=参数/解析错误。
"""
import argparse
import json
import sys


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def type_matches(value, hint):
    hint = (hint or "").strip().lower()
    if not hint or hint in ("any", "*"):
        return True
    if hint in ("string", "str", "text"):
        return isinstance(value, str)
    if hint in ("number", "float", "double"):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if hint in ("integer", "int"):
        return isinstance(value, int) and not isinstance(value, bool)
    if hint in ("boolean", "bool"):
        return isinstance(value, bool)
    if hint in ("array", "list"):
        return isinstance(value, list)
    if hint in ("object", "dict", "map"):
        return isinstance(value, dict)
    if hint == "null":
        return value is None
    # 复合类型提示（array<...> / object<...>）只断言容器类型
    if hint.startswith("array"):
        return isinstance(value, list)
    if hint.startswith("object"):
        return isinstance(value, dict)
    return True


def extract_contract_fields(contract):
    """返回 (fields, type_hints)，兼容多种 output_contract 形态。"""
    fields = []
    hints = {}
    if contract is None:
        return fields, hints
    if isinstance(contract, list):
        for item in contract:
            if isinstance(item, str):
                fields.append(item)
            elif isinstance(item, dict):
                for k, v in item.items():
                    fields.append(k)
                    hints[k] = v
        return fields, hints
    if isinstance(contract, dict):
        if "required_fields" in contract and isinstance(contract["required_fields"], list):
            for item in contract["required_fields"]:
                if isinstance(item, str):
                    fields.append(item)
                elif isinstance(item, dict):
                    for k, v in item.items():
                        fields.append(k)
                        hints[k] = v
            extra = contract.get("fields")
            if isinstance(extra, dict):
                for k, v in extra.items():
                    if k not in fields:
                        fields.append(k)
                    hints[k] = v
            return fields, hints
        if "fields" in contract and isinstance(contract["fields"], dict):
            for k, v in contract["fields"].items():
                fields.append(k)
                hints[k] = v
            return fields, hints
        for k, v in contract.items():
            fields.append(k)
            hints[k] = v
        return fields, hints
    return fields, hints


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", required=True)
    ap.add_argument("--case", default=None)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    try:
        result = load_json(args.result)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: 无法读取 result.json: {e}", file=sys.stderr)
        return 2

    if not isinstance(result, dict):
        print("ERROR: result.json 必须是对象", file=sys.stderr)
        return 2

    report = {
        "contract_checked": False,
        "required_fields": [],
        "contract_missing": [],
        "contract_type_errors": [],
        "structural_errors": [],
        "warnings": [],
        "passed": True,
    }

    # --- output_contract 完备性 ---
    if args.case:
        try:
            case = load_json(args.case)
        except Exception as e:  # noqa: BLE001
            print(f"ERROR: 无法读取 case.json: {e}", file=sys.stderr)
            return 2
        contract = case.get("output_contract") if isinstance(case, dict) else None
        fields, hints = extract_contract_fields(contract)
        report["contract_checked"] = True
        report["required_fields"] = fields
        for name in fields:
            if name not in result:
                report["contract_missing"].append(name)
                continue
            if name in hints and not type_matches(result[name], hints[name]):
                report["contract_type_errors"].append({
                    "field": name,
                    "expected": hints[name],
                    "actual": type(result[name]).__name__,
                })

    # --- 结构校验 ---
    core_fields = (
        "case_id", "scope", "source_language", "target_language",
        "status", "summary", "bilingual_segments", "verification",
    )
    for field in core_fields:
        if field not in result:
            report["structural_errors"].append({"code": "missing_core_field", "field": field})

    segs = result.get("bilingual_segments", [])
    seg_ids = []
    if not isinstance(segs, list):
        report["structural_errors"].append({"code": "bilingual_segments_not_array"})
    else:
        for i, seg in enumerate(segs):
            if not isinstance(seg, dict):
                report["structural_errors"].append({"code": "segment_not_object", "index": i})
                continue
            for field in ("seg_id", "location", "page", "kind", "source", "translation"):
                val = seg.get(field)
                if val is None or (isinstance(val, str) and not val.strip()):
                    report["structural_errors"].append({
                        "code": "segment_missing_field",
                        "seg_id": seg.get("seg_id", ""),
                        "field": field,
                        "index": i,
                    })
            sid = str(seg.get("seg_id", ""))
            if sid in seg_ids:
                report["structural_errors"].append({"code": "duplicate_seg_id", "seg_id": sid})
            seg_ids.append(sid)

    seg_id_set = set(seg_ids)

    # seg_id 引用校验（悬空仅 warning，不阻断）
    for key in ("uncertainty", "evidence", "protected_entities"):
        entries = result.get(key, [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and entry.get("seg_id"):
                sid = str(entry["seg_id"])
                if sid and sid not in seg_id_set:
                    report["warnings"].append({
                        "code": "dangling_seg_id",
                        "field": key,
                        "seg_id": sid,
                    })

    # status=success 一致性
    status = result.get("status", "")
    verification = result.get("verification")
    if isinstance(verification, dict):
        all_pass = verification.get("all_hard_checks_pass")
        seg_comp = verification.get("segment_completeness")
        exact = seg_comp.get("exact") if isinstance(seg_comp, dict) else None
        rel = verification.get("relation_checklist", [])
        has_fail = any(isinstance(r, dict) and r.get("result") == "fail" for r in rel)
        if status == "success":
            if all_pass is not True or exact is not True or has_fail:
                report["structural_errors"].append({
                    "code": "success_status_inconsistent",
                    "all_hard_checks_pass": all_pass,
                    "segment_completeness_exact": exact,
                    "has_fail_relation": has_fail,
                })

    has_errors = bool(report["contract_missing"] or report["contract_type_errors"]
                      or report["structural_errors"])
    report["passed"] = not has_errors

    print(f"contract_checked={report['contract_checked']}")
    print(f"contract_missing={len(report['contract_missing'])} {report['contract_missing']}")
    print(f"contract_type_errors={len(report['contract_type_errors'])}")
    print(f"structural_errors={len(report['structural_errors'])}")
    for e in report["structural_errors"][:40]:
        print(f"  - {e}")
    print(f"warnings={len(report['warnings'])}")
    for w in report["warnings"][:40]:
        print(f"  - {w}")
    print(f"passed={report['passed']}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
