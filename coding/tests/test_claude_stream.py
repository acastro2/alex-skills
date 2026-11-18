import json
import unittest

from claude_stream import final_result, skills_invoked, triggered


def asst(*blocks):
    return json.dumps({"type": "assistant", "message": {"content": list(blocks)}})


def tool(name, **inp):
    return {"type": "tool_use", "name": name, "input": inp}


class StreamTests(unittest.TestCase):
    def test_coding_after_read(self):
        lines = [
            json.dumps({"type": "system"}),
            asst(tool("Read", file_path="/x")),
            asst({"type": "text", "text": "hi"}, tool("Skill", skill="coding")),
            json.dumps({"type": "result", "result": "done"}),
        ]
        s = skills_invoked(lines)
        self.assertEqual(s, ["coding"])
        self.assertTrue(triggered(s, "coding"))
        self.assertEqual(final_result(lines)["result"], "done")

    def test_only_reviewer(self):
        s = skills_invoked([asst(tool("Skill", skill="reviewer"))])
        self.assertEqual(s, ["reviewer"])
        self.assertFalse(triggered(s, "coding"))

    def test_garbage_lines(self):
        lines = ["not json", "", "{broken", "[1,2]", asst(tool("Skill", skill="coding:x"))]
        s = skills_invoked(lines)
        self.assertEqual(s, ["coding:x"])
        self.assertTrue(triggered(s, "coding"))
        self.assertEqual(final_result(["junk"]), {})

    def test_prefix_not_match(self):
        self.assertFalse(triggered(["coding-v0"], "coding"))


if __name__ == "__main__":
    unittest.main()
