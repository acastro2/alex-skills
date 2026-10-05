import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "voice_check.py"


def warn_lines(result: subprocess.CompletedProcess) -> str:
    """Only the 'warn:' lines, so tests do not depend on the header layout."""
    return "\n".join(line for line in result.stdout.splitlines() if line.startswith("  warn:"))


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
        result = run("quick q, do we need two copies tho?\nlet's fix that directly instead\n", "chat")
        self.assertEqual(result.returncode, 1)
        self.assertIn("abbreviated word", result.stdout)

    def test_clean_lowercase_chat_burst_exits_zero_with_no_warnings(self):
        result = run("do we need two copies of this?\nif the old job still reads the shared table, what risk are we removing?\nlet's fix that directly instead\n", "chat")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PASS", result.stdout)


class LowercaseI(unittest.TestCase):
    def test_lowercase_standalone_i_is_a_blocker_in_every_register(self):
        for register in ("chat", "comms", "spoken", "blog", "docs", "exec"):
            with self.subTest(register=register):
                result = run("i think we should wait for the retry window to close.\n", register)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("BLOCKER: lowercase standalone i", result.stdout)

    def test_lowercase_i_inside_contraction_is_a_blocker(self):
        result = run("sounds fine, i'm on it\n", "chat")
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_i_inside_words_code_and_urls_is_ignored(self):
        text = "this is fine, see `i = 0` and https://example.com/i/page and the i.e. case, plus disk i/o\n"
        result = run(text, "chat")
        self.assertNotIn("lowercase standalone i", result.stdout)

    def test_capital_I_is_fine(self):
        result = run("I think we should wait\n", "chat")
        self.assertNotIn("lowercase standalone i", result.stdout)


class StockClosersAndShorthand(unittest.TestCase):
    def test_stock_closers_are_blockers(self):
        for closer in ("Anything else?", "Happy to help.", "Hope this helps.", "Feel free to reach out."):
            with self.subTest(closer=closer):
                result = run(f"Short answer is no.\n{closer}\n", "comms")
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("BLOCKER", result.stdout)


class Shorthand(unittest.TestCase):
    def test_ty_np_idk_are_blockers_as_whole_words(self):
        for word in ("ty", "np", "idk", "Ty"):
            with self.subTest(word=word):
                result = run(f"{word} for the update\n", "chat")
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("abbreviated word", result.stdout)

    def test_words_that_contain_the_letters_are_fine(self):
        result = run("a typical npm tyre idea\n", "chat")
        self.assertNotIn("abbreviated word", result.stdout)


class WarningPhrases(unittest.TestCase):
    def test_flagged_contractions_warn_in_every_register(self):
        for text in ("I'll check it today", "we'll ship it", "you're right on this", "we're done", "I've seen it", "I’ll check it"):
            with self.subTest(text=text):
                result = run(text + "\n", "chat")
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("warn: contraction", result.stdout)

    def test_common_contractions_do_not_warn(self):
        result = run("don't worry, it's fine and I'm on it\n", "chat")
        self.assertNotIn("contraction", result.stdout)


class TypingSlips(unittest.TestCase):
    def test_bare_lets_whats_and_its_a_warn(self):
        for text in ("lets fix it", "whats the plan", "its a good point", "its not ready", "its just a draft", "its been slow"):
            with self.subTest(text=text):
                result = run(text + "\n", "chat")
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("warn: typing slip", result.stdout)

    def test_proper_forms_do_not_warn(self):
        result = run("let's fix it, what's the plan, and the team sets its goals\n", "chat")
        self.assertNotIn("typing slip", result.stdout)


class MachineHabits(unittest.TestCase):
    def test_machine_habits_warn(self):
        for text in ("ok so here is the plan", "help me understand the gap", "I want you to check the config", "explain to me why it fails", "we can ship on Friday, no?"):
            with self.subTest(text=text):
                result = run(text + "\n", "chat")
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("warn: machine habit", result.stdout)

    def test_no_question_tag_is_not_flagged_when_it_is_a_plain_answer(self):
        result = run("is it ready? no, not yet\n", "chat")
        self.assertNotIn("machine habit", result.stdout)


class OldSkillPhrases(unittest.TestCase):
    PHRASES = ("my bad", "that was my miss", "I promise", "Cool, but", "trust me", "don't get me wrong", "let me diagram that", "etc!", "one quick tip")

    def test_old_skill_phrases_warn_outside_blog(self):
        for phrase in self.PHRASES:
            with self.subTest(phrase=phrase):
                result = run(f"Short note here. {phrase} on this one.\n", "comms")
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("warn: old-skill phrase", result.stdout)

    def test_old_skill_phrases_are_silent_in_blog(self):
        for phrase in self.PHRASES:
            with self.subTest(phrase=phrase):
                result = run(f"Short note here. {phrase} on this one.\n", "blog")
                self.assertNotIn("old-skill phrase", result.stdout)


class LengthGate(unittest.TestCase):
    def test_under_100_words_prints_note_and_skips_rate_warnings(self):
        for register in ("blog", "docs", "exec", "comms", "spoken", "chat"):
            with self.subTest(register=register):
                result = run("Retries are hard. We ship it.\n", register)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("short-form: rates not scored", result.stdout)
                self.assertNotIn(" is LOW for", result.stdout)
                self.assertNotIn(" is HIGH for", result.stdout)

    def test_100_words_or_more_still_scores_rates(self):
        result = run("We ship it now. " * 40, "blog")
        self.assertNotIn("short-form", result.stdout)
        self.assertIn("avg_sent=4.0 is LOW for blog", result.stdout)


class ChatLines(unittest.TestCase):
    def test_short_line_ending_with_a_period_warns(self):
        result = run("sounds good, sending it now.\n", "chat")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("warn: chat line ends with a period", result.stdout)

    def test_one_and_two_word_lines_and_ellipsis_may_end_with_a_period(self):
        result = run("done.\nhmm, maybe...\n", "chat")
        self.assertNotIn("ends with a period", result.stdout)

    def test_a_line_over_30_words_warns_to_use_comms(self):
        long_line = " ".join(["word"] * 31)
        result = run(long_line + "\n", "chat")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("this is a channel post, use comms", result.stdout)

    def test_a_30_word_line_is_fine(self):
        result = run(" ".join(["word"] * 30) + "\n", "chat")
        self.assertNotIn("use comms", result.stdout)

    def test_period_and_length_checks_do_not_apply_to_other_registers(self):
        result = run("sounds good, sending it now.\n", "comms")
        self.assertNotIn("ends with a period", result.stdout)


class ChatCountCaps(unittest.TestCase):
    def test_more_than_3_question_marks_warns(self):
        four = "who owns it?\nwhen is it due?\nis it blocked?\ndo we need it?\n"
        three = "who owns it?\nwhen is it due?\nis it blocked?\n"
        self.assertIn("warn: chat has 4 '?'", run(four, "chat").stdout)
        self.assertNotIn("'?'", run(three, "chat").stdout)

    def test_more_than_2_exclamation_marks_warns(self):
        three = "nice one!\ngood catch!\nthanks!\n"
        two = "nice one!\ngood catch\nthanks!\n"
        self.assertIn("warn: chat has 3 '!'", run(three, "chat").stdout)
        self.assertNotIn("'!'", run(two, "chat").stdout)

    def test_more_than_2_parentheses_warns(self):
        three = "that is fine (mostly)\nsee the doc (v2)\nand the log (today)\n"
        two = "that is fine (mostly)\nsee the doc (v2)\nand the log\n"
        self.assertIn("warn: chat has 3 '('", run(three, "chat").stdout)
        self.assertNotIn("'('", run(two, "chat").stdout)

    def test_count_caps_do_not_apply_to_comms(self):
        four = "who owns it?\nwhen is it due?\nis it blocked?\ndo we need it?\n"
        self.assertNotIn("chat has", run(four, "comms").stdout)


class ChatMarkerBudget(unittest.TestCase):
    def test_two_signature_markers_warn(self):
        pairs = [
            "sweet\namazing",
            "that works, right?\nok so we ship",
            "wohoo\nsooo good",
            "that is shit\nthe vendor sucks",
            "can we ship it, make sense?\nit is damn slow",
        ]
        for text in pairs:
            with self.subTest(text=text):
                result = run(text + "\n", "chat")
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("warn: chat has 2 signature markers", result.stdout)

    def test_one_marker_is_fine(self):
        for text in ("sweet, shipping it", "that works, right?", "this is sooo slow", "the vendor sucks"):
            with self.subTest(text=text):
                self.assertNotIn("signature markers", run(text + "\n", "chat").stdout)

    def test_marker_budget_does_not_apply_to_comms(self):
        self.assertNotIn("signature markers", run("sweet\namazing\n", "comms").stdout)

    def test_normal_double_letters_are_not_elongated(self):
        self.assertNotIn("signature markers", run("the book is good\nsee you soon\n", "chat").stdout)


class ChatHasNoRateTargets(unittest.TestCase):
    def test_a_long_capitalised_chat_burst_gets_no_rate_warnings(self):
        line = "The plan covers the first two releases and the owner signs off before we start the work"
        result = run("\n".join([line] * 9) + "\n", "chat")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn(" is LOW for", result.stdout)
        self.assertNotIn(" is HIGH for", result.stdout)
        self.assertIn("PASS", result.stdout)


class CommsChecks(unittest.TestCase):
    BODY = (
        "Vendor review ends on Friday. We need one owner for the open items. "
        "I will send the list to the team today, with a date and a name next to each item. "
        "Please check your own lines before the call. If a date is wrong, tell me in the thread. "
        "Two items block the release, so we start with those. Everything else can wait for the next sprint. "
        "I plan to close the review by the end of next week, and then we move to the build plan. "
        "That plan has three steps and one risk. Data load is the risk, and its owner is already set. "
        "Send me your changes by Thursday so I can update the list before the call.\n"
    )

    def test_baseline_comms_draft_has_no_warnings(self):
        result = run(self.BODY, "comms")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PASS", result.stdout)

    def test_more_than_one_question_mark_warns(self):
        result = run(self.BODY + "Can you take the first item? Can you take the second?\n", "comms")
        self.assertIn("warn: comms has 2 '?'", result.stdout)

    def test_one_question_mark_is_fine(self):
        result = run(self.BODY + "Can you take the first item?\n", "comms")
        self.assertNotIn("comms has", result.stdout)

    def test_question_rate_is_not_scored(self):
        result = run(self.BODY, "comms")
        self.assertNotRegex(warn_lines(result), r"\bq=")

    def test_tag_questions_warn(self):
        for tag in ("This works, right?", "That makes sense, make sense?", "We ship Friday, no?"):
            with self.subTest(tag=tag):
                result = run(self.BODY + tag + "\n", "comms")
                self.assertIn("warn: tag question", result.stdout)

    def test_two_i_think_warn(self):
        result = run(self.BODY + "I think it is fine. I think we can ship.\n", "comms")
        self.assertIn("warn: 'I think' x2", result.stdout)

    def test_one_i_think_is_fine(self):
        result = run(self.BODY + "I think it is fine.\n", "comms")
        self.assertNotIn("'I think'", result.stdout)

    def test_comms_rates_are_not_scored_under_100_words(self):
        result = run("Ship it Friday. Owner is set.\n", "comms")
        self.assertIn("short-form: rates not scored", result.stdout)
        self.assertNotIn(" is LOW for", result.stdout)


SPOKEN_SENTENCES = [
    "We moved the batch job to a new queue last week and nothing broke on the first night",
    "Most of the delay came from waiting on approvals, not from the code itself",
    "Our team now checks the handoff notes before each release, which saves about an hour",
    "You can see the pattern when you look at three releases in a row",
    "A small change in the order of steps removed most of the rework",
    "People ask me why we did not start with the big plan",
    "Big plans need many owners, and many owners need many meetings, and by the time the meetings end the first problem has moved somewhere else",
    "So we picked one service and fixed the slowest part first",
    "After two weeks the error count dropped and the on call load dropped with it, and nobody had to stay late to make that happen",
    "That gave us proof, and proof is what moves a budget conversation",
    "Next we wrote down the steps so a new person can follow them alone, without asking the three people who built the thing",
    "Documents like that last longer than any slide deck I have made",
    "When something breaks at night, the person on call needs a short page, not a story",
    "Short pages get read and long pages get skipped, even by the people who wrote them, which is why every runbook now fits on one screen",
    "We also agreed on one rule for changes on Friday afternoon",
    "No change goes out unless the owner is still online after the release",
]


def spoken(sentences: int, tags: int = 0, opinions: int = 0, bangs: bool = False) -> str:
    out = [SPOKEN_SENTENCES[i % len(SPOKEN_SENTENCES)] + ("!" if bangs else ".") for i in range(sentences)]
    out += ["We start small, right?"] * tags + ["I think that is the right call."] * opinions
    return " ".join(out) + "\n"


class SpokenBands(unittest.TestCase):
    def test_300_plus_words_in_band_passes_and_prints_punctuation_note(self):
        result = run(spoken(22, tags=2, opinions=2), "spoken")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PASS", result.stdout)
        self.assertIn("punctuation from speech-to-text, not calibrated", result.stdout)

    def test_300_plus_words_without_tag_questions_warns_low(self):
        result = run(spoken(24, tags=0, opinions=2), "spoken")
        self.assertIn("tag_q=0.0 is LOW for spoken (target 15-115)", result.stdout)

    def test_300_plus_words_without_opinions_warns_low(self):
        result = run(spoken(24, tags=2, opinions=0), "spoken")
        self.assertIn("opinion=0.0 is LOW for spoken (target 10-80)", result.stdout)

    def test_100_to_299_words_do_not_need_tag_questions(self):
        result = run(spoken(10), "spoken")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("tag_q", warn_lines(result))
        self.assertNotIn("opinion=", warn_lines(result))

    def test_100_to_299_words_warn_when_tag_questions_pile_up(self):
        result = run(spoken(8, tags=4), "spoken")
        self.assertRegex(result.stdout, r"warn: tag_q=\d+(\.\d+)? is HIGH for spoken \(target 0-150\)")

    def test_punctuation_is_not_scored_for_spoken(self):
        result = run(spoken(22, tags=2, opinions=2, bangs=True), "spoken")
        self.assertNotIn("bang=", warn_lines(result))
        self.assertIn("punctuation from speech-to-text, not calibrated", result.stdout)

    def test_note_prints_even_for_short_spoken_drafts(self):
        result = run("We start small.\n", "spoken")
        self.assertIn("punctuation from speech-to-text, not calibrated", result.stdout)


def sample(sentence: str, words: int) -> str:
    """Repeat a sentence until the draft has exactly the given number of words."""
    per = len(sentence.split())
    assert words % per == 0, (sentence, words)
    return (sentence + " ") * (words // per) + "\n"


def padded(words: int) -> str:
    """Exactly `words` words in 4-word sentences plus a short tail."""
    body = "We ship it now. " * (words // 4)
    tail = {0: "", 1: "Go. ", 2: "Go on. ", 3: "Fine by me. "}[words % 4]
    return body + tail + "\n"


NUM = r"\d+(\.\d+)?"


class CommsBands(unittest.TestCase):
    BODY = CommsChecks.BODY

    def assert_band(self, text, key, side, low, high, register="comms"):
        self.assertRegex(warn_lines(run(text, register)), rf"{key}={NUM} is {side} for {register} \(target {low}-{high}\)")

    def test_avg_sent_low_and_high(self):
        self.assert_band(padded(120), "avg_sent", "LOW", 8, 18)
        self.assert_band(sample("one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty twentyone twentytwo twentythree twentyfour twentyfive.", 125), "avg_sent", "HIGH", 8, 18)

    def test_p90_sent_low_and_high(self):
        self.assert_band(padded(120), "p90_sent", "LOW", 14, 50)
        long_tail = "We ship it now. " * 9 + " ".join(["word"] * 70) + ".\n"
        self.assert_band(long_tail, "p90_sent", "HIGH", 14, 50)

    def test_bang_high(self):
        self.assert_band("We ship it now! " * 40 + "\n", "bang", "HIGH", 0, 250)

    def test_paren_high(self):
        self.assert_band(self.BODY + "See the list (attached).\n", "paren", "HIGH", 0, 60)

    def test_the_start_high(self):
        self.assert_band("The plan is set now. " * 30 + "\n", "the_start_pct", "HIGH", 0, 10)

    def test_lower_start_high(self):
        self.assert_band("we ship it now. " * 40 + "\n", "lower_start_pct", "HIGH", 0, 2)

    def test_baseline_has_no_band_warnings(self):
        self.assertNotRegex(warn_lines(run(self.BODY, "comms")), r"is (LOW|HIGH)")


class DocsAndExecKeepTheirBands(unittest.TestCase):
    def test_docs_and_exec_score_rates_at_100_words(self):
        text = "We ship it now.\n" * 40
        self.assertIn("avg_sent=4.0 is LOW for docs (target 12-20)", run(text, "docs").stdout)
        self.assertIn("avg_sent=4.0 is LOW for exec (target 12-20)", run(text, "exec").stdout)


class LengthBoundaries(unittest.TestCase):
    def test_99_words_is_short_form_and_100_is_scored(self):
        short = run(padded(99), "blog")
        scored = run(padded(100), "blog")
        self.assertIn("words=99", short.stdout)
        self.assertIn("short-form: rates not scored", short.stdout)
        self.assertNotRegex(warn_lines(short), r"is (LOW|HIGH)")
        self.assertIn("words=100", scored.stdout)
        self.assertNotIn("short-form", scored.stdout)
        self.assertIn("avg_sent=4.0 is LOW for blog", scored.stdout)

    def test_299_words_uses_the_short_spoken_band_and_300_the_long_one(self):
        short = run(padded(299), "spoken")
        long = run(padded(300), "spoken")
        self.assertIn("words=299", short.stdout)
        self.assertNotIn("tag_q=", warn_lines(short))
        self.assertIn("avg_sent=4.0 is LOW for spoken (target 9-24)", short.stdout)
        self.assertIn("words=300", long.stdout)
        self.assertIn("tag_q=0.0 is LOW for spoken (target 15-115)", long.stdout)
        self.assertIn("avg_sent=4.0 is LOW for spoken (target 10-18)", long.stdout)


class SpokenOtherBands(unittest.TestCase):
    def test_300_plus_avg_p90_and_the_start(self):
        high_avg = run(sample("one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty twentyone twentytwo twentythree twentyfour twentyfive.", 325), "spoken")
        self.assertIn("avg_sent=25.0 is HIGH for spoken (target 10-18)", high_avg.stdout)
        long_sentence = run(("We ship it now. " * 9 + " ".join(["word"] * 80) + ". ") * 3 + "\n", "spoken")
        self.assertRegex(long_sentence.stdout, rf"p90_sent={NUM} is HIGH for spoken \(target 18-40\)")
        self.assertIn("p90_sent=4 is LOW for spoken (target 18-40)", run(padded(320), "spoken").stdout)
        the_start = run("The plan is set now. " * 80 + "\n", "spoken")
        self.assertIn("the_start_pct=100.0 is HIGH for spoken (target 0-8)", the_start.stdout)

    def test_100_to_299_avg_p90_and_the_start(self):
        low = run(padded(160), "spoken")
        self.assertIn("avg_sent=4.0 is LOW for spoken (target 9-24)", low.stdout)
        self.assertIn("p90_sent=4 is LOW for spoken (target 18-50)", low.stdout)
        the_start = run("The plan is set now. " * 30 + "\n", "spoken")
        self.assertIn("the_start_pct=100.0 is HIGH for spoken (target 0-12)", the_start.stdout)


class AiTellsInSpoken(unittest.TestCase):
    def test_ai_tell_word_blocks_in_spoken(self):
        result = run("We should leverage it.\n", "spoken")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("BLOCKER: leverage", result.stdout)

    def test_anything_else_is_allowed_in_spoken_only(self):
        spoken_result = run("Thank you all. Anything else?\n", "spoken")
        self.assertEqual(spoken_result.returncode, 0, spoken_result.stdout)
        for register in ("chat", "comms", "blog", "docs", "exec"):
            with self.subTest(register=register):
                self.assertEqual(run("Thank you all. Anything else?\n", register).returncode, 1)


class CurlyApostrophes(unittest.TestCase):
    def test_banned_phrases_with_curly_apostrophes_block(self):
        phrases = ("Here’s the thing", "Here’s the deal", "But here’s a twist", "I’ll be honest", "Let’s dive in", "Let’s unpack it", "It’s important to note this", "It’s worth noting this", "In today’s market", "Here’s what I found")
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                result = run(f"{phrase}.\n", "comms")
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("BLOCKER", result.stdout)


class NewBlockersAndCallOffers(unittest.TestCase):
    def test_cutting_edge_and_heres_what_block(self):
        for text in ("This is cutting-edge work.", "It is cutting edge.", "Here's what I found."):
            with self.subTest(text=text):
                self.assertEqual(run(text + "\n", "chat").returncode, 1)

    def test_call_offers_block_in_every_register_including_blog(self):
        offers = ("Let me hop on a call", "We can jump on a call", "Let's book a call", "I can set up a call", "I can set up those calls", "Let me schedule some time", "Let's sync tomorrow", "We can talk on a call", "Let me jump on a quick call", "We can talk it on a call", "We can talk about it over a call", "Let's schedule a call", "I can book a meeting", "Happy to set up a quick meeting")
        for register in ("chat", "comms", "spoken", "blog", "docs", "exec"):
            for offer in offers:
                with self.subTest(register=register, offer=offer):
                    result = run(f"Short note here. {offer} for this one.\n", register)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("BLOCKER: call offer", result.stdout)

    def test_saying_you_were_on_a_call_is_fine(self):
        for text in ("Sorry, I was on a call.", "The call ran long, so I missed the thread.", "The meeting moved to Friday."):
            with self.subTest(text=text):
                self.assertNotIn("call offer", run(text + "\n", "comms").stdout)


class ShorthandEdgeCases(unittest.TestCase):
    def test_imo_blocks(self):
        self.assertEqual(run("imo we should wait\n", "chat").returncode, 1)

    def test_hyphenated_terms_do_not_block(self):
        result = run("This is an NP-hard problem, and a ty-pe of idk-like case.\n", "docs")
        self.assertNotIn("abbreviated word", result.stdout)


class LowercaseIQuotes(unittest.TestCase):
    def test_i_after_a_quote_mark_blocks(self):
        for text in ("he said 'i will go'", "he said ‘i think so’", "he said \"i will go\"", "i'm on it", "i’m on it"):
            with self.subTest(text=text):
                result = run(text + "\n", "chat")
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("lowercase standalone i", result.stdout)

    def test_quoted_single_letter_is_ignored(self):
        result = run("the loop counter is called 'i' here\n", "chat")
        self.assertNotIn("lowercase standalone i", result.stdout)


class TypingSlipFalsePositives(unittest.TestCase):
    def test_lets_as_a_verb_does_not_warn(self):
        for text in ("This lets you rotate the key.", "The flag lets the team ship early.", "It lets us retry."):
            with self.subTest(text=text):
                self.assertNotIn("typing slip", run(text + "\n", "docs").stdout)


class TagQuestionEdgeCases(unittest.TestCase):
    def test_yes_or_no_is_a_plain_question_in_every_register(self):
        for register in ("chat", "comms", "spoken"):
            with self.subTest(register=register):
                out = warn_lines(run("Is it a yes or no?\n", register))
                self.assertNotIn("tag question", out)
                self.assertNotIn("machine habit", out)

    def test_no_tag_warns_in_chat_as_a_machine_habit(self):
        self.assertIn("warn: machine habit: tag question 'no?'", run("we ship Friday, no?\n", "chat").stdout)

    def test_no_tag_in_comms_and_spoken_gets_the_register_rule_not_the_machine_habit(self):
        comms = run("We ship Friday, no?\n", "comms")
        self.assertIn("warn: tag question", comms.stdout)
        self.assertNotIn("machine habit", comms.stdout)
        self.assertNotIn("machine habit", run("We ship Friday, no?\n", "spoken").stdout)


class ChatPeriodWordCounts(unittest.TestCase):
    def test_two_word_line_with_period_is_fine_and_three_words_warn(self):
        self.assertNotIn("ends with a period", run("two words.\n", "chat").stdout)
        self.assertIn("warn: chat line ends with a period", run("three word line.\n", "chat").stdout)


if __name__ == "__main__":
    unittest.main()
