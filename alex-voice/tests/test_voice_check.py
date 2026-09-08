import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "voice_check.py"


def run(text: str, register: str = "blog") -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
        handle.write(text)
    return subprocess.run([sys.executable, str(SCRIPT), handle.name, "--register", register], capture_output=True, text=True)


class VoiceCheckBehaviour(unittest.TestCase):
    def test_em_dash_is_a_blocker(self):
        result = run("This works well — until it does not. You will see it fail, right?\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("BLOCKER: em dash", result.stdout)

    def test_banned_phrase_is_a_blocker(self):
        result = run("Here's the thing: retries are hard. You need a plan, right?\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("here's the thing/deal", result.stdout)

    def test_clean_alex_style_text_passes(self):
        text = (
            "You don't need retries in Kafka until the day one handler starts failing, right? "
            "Then you have a choice: block consumption (and watch lag climb) or keep consuming and retry somewhere else. "
            "I tried SQS first, then Kafka itself, then a database (yes, a database). To my surprise, the database worked! "
            "It was not pretty, so let me diagram what we ended up with.\n\n"
            "The pattern is simple: commit the offset, push the failed message into a retry queue, and let the app own the policy. "
            "Cool, but where is the catch? If the process dies before the retry succeeds, that message is gone. "
            "In my honest opinion this trade is worth it when throughput matters more than ordering (which is most of the time). "
            "Do you need strict ordering? Then do not use this pattern!\n"
        )
        result = run(text)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("BLOCKER", result.stdout)

    def test_abbreviated_words_are_blockers(self):
        result = run("quick q, do we need it to be 1:1 tho?\nlets fix that directly instead!\n", "chat")
        self.assertEqual(result.returncode, 1)
        self.assertIn("abbreviated word", result.stdout)

    def test_chat_register_expects_lowercase_and_questions(self):
        result = run("do we need it to be 1:1?\nif reporting-read still opens payments db, what risk are we removing?\nlets fix that directly instead!\n", "chat")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("lower_start_pct", result.stdout)


if __name__ == "__main__":
    unittest.main()
