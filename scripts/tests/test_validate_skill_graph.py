from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import validate_skill_graph


class ValidateSkillGraphTests(unittest.TestCase):
    def write_skill(self, root: Path, directory: str, content: str) -> None:
        skill_dir = root / directory
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    def test_valid_flat_repo_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_skill(
                root,
                "valid-skill",
                """---
name: valid-skill
description: A valid skill.
---
""",
            )
            self.write_skill(
                root,
                "plugins/example/skills/ignored-skill",
                "no frontmatter",
            )

            result = validate_skill_graph.validate_repo(root)

            self.assertTrue(result.passed)
            self.assertEqual(result.checked, 1)
            self.assertEqual(result.errors, ())

    def test_malformed_or_missing_frontmatter_fails(self) -> None:
        cases = {
            "missing": "name: broken\ndescription: No delimiters.\n",
            "malformed": "---\nname: [broken\ndescription: Invalid YAML.\n---\n",
        }
        for case, content in cases.items():
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as temporary_directory:
                    root = Path(temporary_directory)
                    self.write_skill(root, "broken", content)

                    result = validate_skill_graph.validate_repo(root)

                    self.assertFalse(result.passed)
                    self.assertEqual(result.checked, 1)
                    self.assertTrue(result.errors)

    def test_name_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_skill(
                root,
                "actual-name",
                """---
name: other-name
description: A mismatched skill.
---
""",
            )

            result = validate_skill_graph.validate_repo(root)

            self.assertFalse(result.passed)
            self.assertTrue(any("must equal directory" in error for error in result.errors))

    def test_unknown_frontmatter_key_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_skill(
                root,
                "typo-skill",
                """---
name: typo-skill
description: A skill with a typo.
disable-model-invokation: true
---
""",
            )

            result = validate_skill_graph.validate_repo(root)

            self.assertFalse(result.passed)
            self.assertTrue(
                any("disable-model-invokation" in error for error in result.errors)
            )

    def test_invalid_skill_name_fails(self) -> None:
        cases = {
            "uppercase": "Bad-Name",
            "underscore": "bad_name",
            "double_hyphen": "bad--name",
            "too_long": "a" * 65,
        }
        for case, name in cases.items():
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as temporary_directory:
                    root = Path(temporary_directory)
                    self.write_skill(
                        root,
                        name,
                        f"---\nname: {name}\ndescription: A badly named skill.\n---\n",
                    )

                    result = validate_skill_graph.validate_repo(root)

                    self.assertFalse(result.passed)
                    self.assertTrue(
                        any("name" in error for error in result.errors), result.errors
                    )

    def test_overlong_description_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_skill(
                root,
                "wordy-skill",
                f"---\nname: wordy-skill\ndescription: {'x' * 1025}\n---\n",
            )

            result = validate_skill_graph.validate_repo(root)

            self.assertFalse(result.passed)
            self.assertTrue(
                any("description" in error for error in result.errors), result.errors
            )

    def test_non_boolean_invocation_flag_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_skill(
                root,
                "stringly-skill",
                """---
name: stringly-skill
description: A skill with a stringly-typed flag.
disable-model-invocation: "false"
---
""",
            )

            result = validate_skill_graph.validate_repo(root)

            self.assertFalse(result.passed)
            self.assertTrue(
                any("disable-model-invocation" in error for error in result.errors),
                result.errors,
            )

    def test_broken_sibling_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.write_skill(
                root,
                "source-skill",
                """---
name: source-skill
description: A skill with a broken path.
---
See [missing](../missing-skill/SKILL.md).
""",
            )

            result = validate_skill_graph.validate_repo(root)

            self.assertFalse(result.passed)
            self.assertTrue(
                any("../missing-skill/SKILL.md" in error for error in result.errors)
            )


if __name__ == "__main__":
    unittest.main()
