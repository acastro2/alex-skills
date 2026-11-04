from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import trigger_eval

TOOL_USE = (
    '{"type":"assistant","message":{"content":[{"type":"tool_use",'
    '"name":"Skill","input":{"skill":"grilling"}}]}}'
)


class PickSkillTests(unittest.TestCase):
    def test_reads_the_skill_from_a_tool_use_block(self) -> None:
        self.assertEqual(trigger_eval.pick_skill(TOOL_USE), "grilling")

    def test_returns_none_when_no_skill_was_called(self) -> None:
        stream = '{"type":"assistant","message":{"content":[{"type":"text","text":"hi"}]}}'
        self.assertIsNone(trigger_eval.pick_skill(stream))
        self.assertIsNone(trigger_eval.pick_skill(""))

    def test_takes_the_first_skill_when_several_are_called(self) -> None:
        stream = TOOL_USE + "\n" + TOOL_USE.replace("grilling", "reviewer")
        self.assertEqual(trigger_eval.pick_skill(stream), "grilling")

    def test_falls_back_to_regex_on_a_line_that_is_not_json(self) -> None:
        line = 'noise "name":"Skill","input":{"skill":"reviewer"} tail'
        self.assertEqual(trigger_eval.pick_skill(line), "reviewer")


class LoadCasesTests(unittest.TestCase):
    def write(self, cases: list[dict]) -> Path:
        directory = tempfile.mkdtemp()
        path = Path(directory) / "trigger-evals.json"
        path.write_text(json.dumps(cases), encoding="utf-8")
        return path

    def test_keeps_an_explicit_expect(self) -> None:
        path = self.write([{"query": "a", "expect": "bard", "should_trigger": False}])
        self.assertEqual(trigger_eval.load_cases(path, "scribe")[0]["expect"], "bard")

    def test_infers_expect_from_should_trigger(self) -> None:
        path = self.write(
            [
                {"query": "a", "should_trigger": True},
                {"query": "b", "should_trigger": False},
            ]
        )
        cases = trigger_eval.load_cases(path, "scribe")
        self.assertEqual(cases[0]["expect"], "scribe")
        self.assertIsNone(cases[1]["expect"])

    def test_rejects_an_empty_card(self) -> None:
        path = self.write([])
        with self.assertRaises(SystemExit):
            trigger_eval.load_cases(path, "scribe")


class ScoreTests(unittest.TestCase):
    def test_a_case_passes_only_when_every_run_matches(self) -> None:
        cases = [
            {"query": "a", "expect": "scribe"},
            {"query": "b", "expect": "bard"},
        ]
        rows = trigger_eval.score(cases, {"a": ["scribe", "scribe"], "b": ["scribe", "bard"]})
        self.assertTrue(rows[0]["pass"])
        self.assertFalse(rows[1]["pass"])

    def test_report_counts_and_renders_none(self) -> None:
        rows = [
            {"query": "a", "expect": "scribe", "got": ["scribe"], "pass": True},
            {"query": "b", "expect": None, "got": [None], "pass": True},
        ]
        text = trigger_eval.report("scribe", rows)
        self.assertIn("2/2 cases pass.", text)
        self.assertIn("| none | none |", text)

    def test_a_failed_run_never_passes_and_is_called_out(self) -> None:
        cases = [{"query": "a", "expect": "reviewer"}]
        rows = trigger_eval.score(cases, {"a": [trigger_eval.ERROR]})
        self.assertFalse(rows[0]["pass"])
        text = trigger_eval.report("reviewer", rows)
        self.assertIn("0/1 cases pass.", text)
        self.assertIn("| error |", text)
        self.assertIn("must be re-run", text)


if __name__ == "__main__":
    unittest.main()
