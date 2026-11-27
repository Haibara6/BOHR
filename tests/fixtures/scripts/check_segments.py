#!/usr/bin/env python3
"""段落完整性校验（stdlib only，无第三方依赖）。

用法：
  python3 check_segments.py --inventory inventory.json --result result.json [--json-out report.json]

- inventory.json：数组 [{"seg_id": "S001", ...}]，为翻译前建立的段号清单。
- result.json：数组 [{"seg_id": "S007", ...}]，为译文段。
- 校验：每个 inventory 段在 result 中恰好出现一次；无缺段、无重段、无多余段。
  · duplicated：result 侧重复段号。
  · duplicated_inventory：inventory 侧重复段号。
  · inventory 侧重复段会抬高完整率并掩盖缺段，因此一并判错；完整率用去重后的
    inventory 计算。
- 退出码：0=完整；1=缺段/重段/多余段；2=参数/解析错误。
"""
import argparse
import json
import sys


def load_ids(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} 必须是数组")
    ids = []
    for item in data:
        if not isinstance(item, dict) or "seg_id" not in item:
            raise ValueError(f"{path} 数组元素必须含 seg_id")
        ids.append(str(item["seg_id"]))
    return ids


def duplicates(seq):
    return sorted({i for i in set(seq) if seq.count(i) > 1})


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--result", required=True)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    try:
        inv = load_ids(args.inventory)
        res = load_ids(args.result)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    inv_unique = sorted(set(inv))
    res_unique = sorted(set(res))
    inv_set = set(inv_unique)
    res_set = set(res_unique)

    missing = [i for i in inv_unique if i not in res_set]
    extra = [r for r in res_unique if r not in inv_set]
    dup_inv = duplicates(inv)
    dup_res = duplicates(res)

    report = {
        "inventory_count": len(inv),
        "inventory_unique_count": len(inv_unique),
        "result_count": len(res),
        "result_unique_count": len(res_unique),
        "missing": missing,
        "extra": extra,
        "duplicated": dup_res,
        "duplicated_inventory": dup_inv,
    }
    print(f"inventory={len(inv)} (unique={len(inv_unique)}) "
          f"result={len(res)} (unique={len(res_unique)})")
    print(f"missing={len(missing)} {missing}")
    print(f"extra={len(extra)} {extra}")
    print(f"duplicated(result)={len(dup_res)} {dup_res}")
    print(f"duplicated(inventory)={len(dup_inv)} {dup_inv}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    return 1 if (missing or extra or dup_res or dup_inv) else 0


if __name__ == "__main__":
    sys.exit(main())
