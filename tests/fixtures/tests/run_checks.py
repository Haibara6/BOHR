#!/usr/bin/env python3
"""最小回归测试（仅标准库 unittest + subprocess）。

运行：python3 tests/run_checks.py

覆盖 VALIDATION.md 的边界修复与本次新增的确定性检查：
区间引用、多图编号、Unicode 负号、作者-年份引用、~≈ 中文对应、上标数字、
复合单位、单位误报、空译文、retention 枚举、inventory 重复、关系保留软校验、
契约完备性与 seg_id 悬空。
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class _TempDir:
    def __enter__(self):
        self.path = tempfile.mkdtemp(prefix="lit-check-")
        return Path(self.path)

    def __exit__(self, exc_type, exc, tb):
        shutil.rmtree(self.path, ignore_errors=True)
        return False


def _run(cmd, out):
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    report = json.loads(out.read_text(encoding="utf-8"))
    return proc.returncode, report


def run_literals(fixture):
    with _TempDir() as td:
        out = td / "report.json"
        return _run(
            [sys.executable, str(SCRIPTS / "check_literals.py"),
             "--segments", str(FIXTURES / fixture), "--json-out", str(out)],
            out,
        )


def run_segments(inventory, result):
    with _TempDir() as td:
        out = td / "report.json"
        return _run(
            [sys.executable, str(SCRIPTS / "check_segments.py"),
             "--inventory", str(FIXTURES / inventory),
             "--result", str(FIXTURES / result), "--json-out", str(out)],
            out,
        )


TERMS_TSV = {
    "missing_canonical": (
        "source_term\tsense_id\tcanonical_translation\tdomain\tcontext_clues\texample\tnotes\tretention\n"
        "cell viability\tcell-viability\t\tcell biology\t\t\t\ttranslate\n"
    ),
    "bad_retention": (
        "source_term\tsense_id\tcanonical_translation\tdomain\tcontext_clues\texample\tnotes\tretention\n"
        "cell viability\tcell-viability\t细胞活力\tcell biology\t\t\t\ttranslated\n"
    ),
    "bad_columns": (
        "source_term\tsense_id\tcanonical_translation\tdomain\tcontext_clues\texample\tnotes\tretention\n"
        "cell viability\tcell-viability\t细胞活力\tcell biology\t\t\t\n"
    ),
}


def run_terms(name, segments="segments_ok.json"):
    with _TempDir() as td:
        tsv_path = td / "terms.tsv"
        tsv_path.write_text(TERMS_TSV[name], encoding="utf-8")
        out = td / "report.json"
        return _run(
            [sys.executable, str(SCRIPTS / "check_terms.py"),
             "--terms", str(tsv_path),
             "--segments", str(FIXTURES / segments), "--json-out", str(out)],
            out,
        )


def run_contract(result, case=None):
    with _TempDir() as td:
        out = td / "report.json"
        cmd = [sys.executable, str(SCRIPTS / "check_contract.py"),
               "--result", str(FIXTURES / result), "--json-out", str(out)]
        if case:
            cmd += ["--case", str(FIXTURES / case)]
        return _run(cmd, out)


def run_relations(fixture):
    with _TempDir() as td:
        out = td / "report.json"
        return _run(
            [sys.executable, str(SCRIPTS / "check_relations.py"),
             "--segments", str(FIXTURES / fixture), "--json-out", str(out)],
            out,
        )


class LiteralChecks(unittest.TestCase):
    def test_hard_bad(self):
        code, report = run_literals("literal_hard_bad.json")
        self.assertEqual(code, 1)
        kinds = {item["kind"] for item in report["hard_miss"]}
        self.assertSetEqual(kinds, {
            "citation_marker",
            "figure_table_number",
            "relation_sign_number",
            "citation_author_year",
        })

    def test_ok_edge(self):
        code, _ = run_literals("literal_ok_edge.json")
        self.assertEqual(code, 0)

    def test_soft_warn(self):
        code, report = run_literals("literal_soft_warn.json")
        self.assertEqual(code, 0)
        kinds = {item["kind"] for item in report["warnings"]}
        self.assertSetEqual(kinds, {"superscript_number", "unit"})
        # "Fig. 2 shows" 中的 "shows" 不得误判为单位
        self.assertEqual(report["stats"]["units"]["warn"], 1)
        self.assertEqual(report["stats"]["units"]["hit"], 0)


class SegmentChecks(unittest.TestCase):
    def test_inventory_duplicate(self):
        code, report = run_segments("inventory_dup.json", "segments_ok.json")
        self.assertEqual(code, 1)
        self.assertEqual(report["duplicated_inventory"], ["S002"])
        self.assertEqual(report["missing"], [])


class TermChecks(unittest.TestCase):
    def test_missing_canonical(self):
        code, report = run_terms("missing_canonical")
        self.assertEqual(code, 1)
        self.assertTrue(report["missing_canonical"])

    def test_bad_retention(self):
        code, report = run_terms("bad_retention")
        self.assertEqual(code, 1)
        self.assertTrue(report["invalid_retention"])

    def test_bad_columns(self):
        code, report = run_terms("bad_columns")
        self.assertEqual(code, 1)
        self.assertTrue(report["bad_columns"])


class ContractChecks(unittest.TestCase):
    def test_missing_contract_field(self):
        code, report = run_contract("contract_bad.json", case="case_contract.json")
        self.assertEqual(code, 1)
        self.assertIn("custom_score", report["contract_missing"])

    def test_empty_translation(self):
        code, report = run_contract("contract_empty_translation.json")
        self.assertEqual(code, 1)
        codes = {e["code"] for e in report["structural_errors"]}
        self.assertIn("segment_missing_field", codes)

    def test_dangling_seg_id_warns_only(self):
        code, report = run_contract("contract_dangling.json")
        self.assertEqual(code, 0)
        self.assertTrue(any(w["code"] == "dangling_seg_id" for w in report["warnings"]))

    def test_success_status_inconsistent(self):
        code, report = run_contract("contract_status_bad.json")
        self.assertEqual(code, 1)
        codes = {e["code"] for e in report["structural_errors"]}
        self.assertIn("success_status_inconsistent", codes)


class RelationChecks(unittest.TestCase):
    def test_relation_soft_warn(self):
        # 软校验：关系未表达只提示，不改变退出码（0）。
        code, report = run_relations("relation_mix.json")
        self.assertEqual(code, 0)
        rr = report["relation_retention"]
        self.assertEqual(rr["checked"], 4)
        self.assertEqual(rr["hit"], 3)
        self.assertEqual(rr["warn_count"], 1)
        neg = [w for w in report["warn_items"] if w["category"] == "negation"]
        self.assertTrue(neg)
        self.assertEqual(neg[0]["seg_id"], "R3")


if __name__ == "__main__":
    unittest.main(verbosity=2)
