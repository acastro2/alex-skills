# Alex's Voice Fingerprint

> Extends `../SKILL.md`. Rebuilt in October 2026 from Alex's own typing and speech. Blog keeps its 2026-09 calibration.
> Rates are per 10,000 words unless marked `%`. "n/m" means not measured. No real corpus text is in this file: the corpus is private.
> Run `../scripts/voice_check.py <draft> --register <name>` to score a draft against the targets in section 6.

## 1. What was measured

### October 2026 (chat, channel, email, spoken, typed)

Data is May to early October 2026, one work period (email runs May to September). Only what Alex typed or said himself counts. His AI-polished messages are out: Alex decided the skill copies only his own typing (2026-10).

| Source | What it is | Size after cleaning |
| --- | --- | --- |
| chat | Teams DMs, group chats, meeting chats | ~30k messages, 214k words (29,755 messages after pastes removed) |
| channel | Teams channel posts and replies | 106 posts, 448 replies, 4.7k words |
| email | Sent work email he typed himself | 219 mails, ~5.7k words |
| spoken | His lines in Teams meeting transcripts | 24 meetings, 1,739 turns, ~70k words |
| typed | His prompts to coding agents | 10,465 messages, 207k words. Contrast only |

How each set was cleaned:

- **Chat:** 184 messages removed as likely AI pastes (an em dash, or over 120 words). They are 0.6% of messages and 14.8% of words, and they differ from his real chat on every marker.
- **Channel:** lines with an em dash or 120+ words were removed from every main number. They are 21 posts and 2 replies and hold 45% of the channel words. Near-identical reposts were also removed.
- **Email:** triage removed 79 AI-assisted mails, 34 automated mails and 1 not from him. Email is small: one mail moves a per-10k rate by about 1.8. Treat email rates as rough direction, not exact targets. 94% of the mails are replies, so this is how he answers and chases, not how he writes a cold announcement.
- **Spoken:** speech-to-text adds the punctuation. Word counts are solid. "?" and sentence-end counts are soft.
- **Typed:** how he talks to machines. Used to find habits that must stay out of people-facing writing (section 5).
- **Holdout:** a holdout set per source was kept back to test the checker. Rules come from the training sets only. The "we are" email rule failed on it.

Every claim was measured by script, then re-counted by two independent skeptics. Rules in the skill come only from claims that survived. A claim a skeptic refuted is a caveat, never a rule. Where recounts differ by a few points, this file gives a range or the rounded value.

### September 2026 (blog calibration, unchanged)

| Source | What it is | Size |
| --- | --- | --- |
| hand | Notes and drafts he wrote by hand, 2021 to 2023 | ~9k words |
| pub_early | Blog posts written by hand and lightly polished, 2023 to 2024 (3 posts) | ~4k words |
| pub_late | Blog posts drafted by an AI from his material, Dec 2025 to May 2026 (6 posts) | ~15k words |

`pub_late` is the negative baseline. Its phrases ("here's the thing", "the truth is", "let me be direct", "spoiler alert") are in none of his own typing or speech. Blog rules use `pub_early`. The 2023 Kafka post is hand-written; the 2024 Senior Engineer parts were AI-assisted, and Alex keeps them as the closest published text to his words (2026-10-05).

## 2. Why the September version missed

Alex said drafts "resemble something I write" but did not pass his own check. Three causes, ranked by how far each moves a draft from his real writing.

1. **The corpus was lopsided.** September had 200k words of typed prompts to machines, but only 145 chat messages (~1k words), 7 emails and 8 meetings of people-facing writing. Machine habits ("ok so", "no?", "help me") entered the chat and comms rules.
2. **Markers were applied to every register.** The core rules told every register to use "right?", "make sense?", "I think" and a hand-over close. Real email has "right?" in 0 of 219 mails. Real chat ends 0.36% of bursts on "make sense?". The comms register was also built from one onboarding mail: four of its signature phrases each appear in exactly that one mail of 213.
3. **The samples ran 5x to 130x real marker density.** The spoken sample scored 392 tag questions per 10k, about 5 times his real median of 72. The chat samples carried about 145 tag questions per 10k, 10 to 40 times real. The "ok so" density in a chat sample was about 130 times real. A reader spots one marker too many first.

Two smaller causes:

- The September "!" target for chat (325 per 10k) came from 145 messages. On 29,755 messages it is 57.
- The checker punished real email. All 28 of his emails with 50+ words raised at least one warning, and 219 of 219 are under 300 words, so the old "rates unreliable" note fired on every one.

## 3. Rhythm and markers by register

Units: per 10k words unless marked. "msgs" is share of messages, "mails" is share of emails, "posts" is share of channel posts.

### 3.1 Size, punctuation, casing

| Metric | chat | channel post | channel reply | email | spoken | typed (contrast) | blog (pub_early) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Size | message median 5 words, reply burst median 10, 46% of reply bursts are one message | median 12 words, 62% are 15 or fewer | median 7, mean 10.5, p90 22 | body median 17, mean 25, 59% to 61% one sentence or less | sentence mean 13.1, median 10 | n/m | 17 words per sentence, p90 32 |
| "!" | 57 per 10k, 3.2% of msgs | 11.3% of posts, 9 of 12 on the last line | 48.7 per 10k, 3.8% of replies | 73 to 88 per 10k, 16% of mails | none (speech-to-text) | 6.7 | 20 |
| "?" | 231 per 10k, 16% of msgs | 15.1% of posts end in "?" | 17.4% of replies end in "?" | 138 to 153 per 10k pooled (short-mail effect), 72 of 75 question mails hold exactly one | soft (speech-to-text), median ~141 per meeting | n/m | 41 |
| Lowercase starts | 70% (1:1 73%, group 58%, meeting 49% to 53%) | 10.4% of posts, all 15 words or fewer | follows chat, no figure | 0 of 449 sentences | 3.0% (speech-to-text) | 59% to 76% | 0% |
| End marks | none 81%, "?" 13.7%, "!" 2.9%, period 0.7% | none 63.2%, "?" 15.1%, period 9.4%, "!" 8.5% | none 75.9%, "?" 17.4%, period 2.7% | last sentence: statement 53% to 55%, question 25% to 27%, "!" statement 6% to 9% | n/a | n/m | full sentences |
| Contractions | "I will" 522 vs "I'll" 1; "we are" 315 vs 3; "I'm" 1,214 vs 11 bare | n/m | full forms 45, contracted forms 0; "I'm", "don't", "can't" kept | "I will" 16 vs "I'll" 2; "I'm" 28 vs "I am" 1; "don't" 11 vs "do not" 0. "we are" is not generalised: it failed on the holdout | n/a | n/m | n/m |

### 3.2 Signature markers

| Marker | chat | channel post | channel reply | email | spoken | typed (contrast) | blog (pub_early) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| "I think" | 38, 2.7% of msgs | n/m | 4.7% of replies | 8 mails (3.7%), hedges a fact | 33 | 39 | 0 |
| "right?" | 9.4, ~1% of msgs | n/m | tags together 1.1% of replies | 0 | 74, ends 9.0% to 9.5% of sentences | 10.1 | 5 |
| "make sense?" | 1.7, ends 0.36% of bursts | n/m | in the tag figure above | 1 mail | 1.8, 13 turns in 70k words | 3.8 | 0 |
| "ok so" | 1.3 to 1.6 | n/m | 0 | 0 | 1 (14 if "okay, so" counts) | 30.9 | 0 |
| "lol" | 49 ("haha" 11), 3.5% of msgs | n/m | 9 replies ("haha" 4) | 0 | 0 | n/m | 0 |
| "thank you" | 18.7, 3.4 times "thanks" | 3.8% of posts | 8 replies vs "thanks" 2 | closes 62% to 69% of mails, 84% to 87% of longer ones | meeting close, 18 to 20 of 24 | n/m | n/m |
| "please" | 24.6, mostly at the end of an ask | n/m | 3.3% of replies, 9 of 15 at line end | 10% of mails | n/m | 42 | 0 |

Typed "?" and "lol" are n/m: the only counts on file are September counts with no October re-count.

Other measured phrases:

| Phrase | Where | Measured |
| --- | --- | --- |
| "just" as a softener ("Just to confirm", "Just letting you know", "I just wanted to", "just FYI") | email | 28 of 216 mails (13%), 57 per 10k. More than "please" (10%). 12 to 13 mails open with a "Just" frame |
| "sorry" vs "my bad" | chat | 334 messages vs 13. "was my miss" 1. 60% of "sorry" messages open the message |
| "my pleasure", "of course", "no problem" | chat | 55, 94 and 40 messages. 37% of replies that start this way follow a message with thanks |
| "let me know" | email, chat | email 10 to 12 mails. Chat 149 messages (0.5%). The stock closer "let me know if you need anything else" is about 21 bursts in 14,048 |
| Stock closers: "anything else", "need anything", "happy to help", "hope this helps" | chat | 17, 11, 4 and 4 messages. Channel replies: 0 |
| "you guys", "everybody", "you all" | spoken | 269 hits (128, 85, 56), 38 per 10k, in 22 of 24 meetings |
| "you know" | spoken | 78 per 10k, in 23 of 24 meetings. Mid-sentence or clause-final, not mainly a turn closer |
| "Yeah, but ..." | spoken | 46 turns in 21 meetings |
| "if you want", "up to you", "feel free" | spoken | 100 to 105 hits. Rollout meetings 2.5 per 1k words, standup 1.9, forum 0.6, cohort 0.2 |

### 3.3 Chat by type

Columns are 1:1, group chat and meeting chat. The data cannot see the recipient, so chat type is the only audience cut.

| Metric | 1:1 | Group | Meeting chat |
| --- | --- | --- | --- |
| Single-message reply | 42% | 57% | 63% |
| Words per message (mean) | 6.6 | 9.2 | 9.5 |
| Lowercase start | 73% | 58% | 49% to 53% |
| "lol" per 10k | 57 | 31 | 24 |
| "!" per 10k | 64 | 42 | 34 |
| Mild swearing per 10k | 24 | 12 | 8 to 12 |
| "thank you" per 10k | 22 | 12 | 15 |
| "please" per 10k | 21 | 34 | 24 |
| "I think" per 10k | 38 | 41 | 26 (small n) |
| "?" per 10k | 230 | 208 | 215 |
| Bursts with a URL | 7% | 11% | 18% |

- Warmth markers (lol, "!", swearing) run at about half rate in group threads. "I think" and real questions do not change.
- Bootstrap intervals exclude zero for lol, "!", swearing, thanks and please between 1:1 and group. Group and meeting are close to each other.
- Caveat: chat type is a weak proxy for the person. Inside 1:1 the spread between threads is large ("lol" 35 to 112 per 10k at p10 to p90). This is why the skill asks for the last few messages and mirrors them.

### 3.4 Greetings and closers

Greeting and closer follow message size and who starts the thread. They do not follow the audience once size is held fixed.

| Metric | email | channel post | channel reply | chat |
| --- | --- | --- | --- | --- |
| Has a greeting | 60% of mails (40% have none) | 22.6% of posts (24 of 106) | 2.0% (9 of 448) | 5.0% of reply bursts, 25.8% of bursts Alex starts |
| Greeting by size | about 35% to 43% under 10 to 12 words, 64% at 11 to 25, about 87% at 26 to 60 | 10.6% at 15 words or fewer, 34.5% at 16 to 40, 63.6% at 41+ | n/m | n/m |
| Greeting word | "Hi" 116, "Hey" 12 of 128. 121 of 128 end in a comma, 4 in "!" (all welcome or first contact). Bare "Hi," 56% | "Hey" 19 of 24 (79%). News on the same line 17 of 24. "!" on the greeting line 0 | n/m | "hey" 72%, "howdy" 10%, "hi" 9.5%. 44% are the bare word, and 87% of those are followed by the ask in the same burst |
| Thanks closer | 62% to 69% overall | "Thank you" anywhere in 3.8% of posts | 2.0% (9) | a short thank-you closes 2.6% of reply bursts and opens 2.5% |
| Thanks closer by size | about 40% under 8 to 10 words, 62% to 64% at 11 to 25, 84% to 87% at 26 to 60, 100% at 60+ | n/m | n/m | n/m |
| Greeting and thanks together | 52% to 56%. Neither: 28% to 29% | n/m | 0 of 448 | n/m |
| Opens with the point | first sentence is the point in 80% (166 of 207). Thanks or reaction first 10% to 12%, background 3% to 6%, pleasantry 0 to 1 | first words are the news in the 32 news posts. A reason comes first in 5 of 32 (16%) | question word 12.0%, "I" statement 11.8%, yes or no 4.5% | question 15.5%, "I" statement 12.7%, yes or no 8.5%, greeting 5.0% |
| Ends on | statement 53% to 55%, question 25% to 27%, thanks line 4% to 5% | no mark 63.2%, "?" 15.1% | no mark 75.9%, "?" 17.4% | statement 65% to 70%, question 16%, tag 1.6% |

- Channel posts: greeting fell from 40.5% (15 of 37) in May to June to 13.0% (9 of 69) in July to October. Without the one @group channel the later figure is 15.4%.
- Email frame by type: 18 forwards had a median of 5 to 6 words and 2 were greeted. 17 of 19 alert-thread replies had no greeting and no closer.
- Override (Alex, 2026-10-05): the skill puts "Hi," and "Thank you," on every email anyway. He wants the frame always, even where his own sent mail skipped it. The numbers above stay as evidence of the old habit.
- Zero in email: "Best", "Regards", "Cheers", "Sincerely", "Dear", "Good morning", "Hope you are well".
- Chat: "Hi [Name]!" is 0 of 1,252 greeting messages, and 7% of greeting messages carry "!". When the other person greets first, Alex greets back 8% of the time.

## 4. Old versus new corrections

| Item | September | October | Note |
| --- | --- | --- | --- |
| chat "!" | 325 | 57 | 1 message in 30 |
| chat "I think" | 0 | 38 | opens a real opinion |
| chat lowercase starts | 48% | 70% | drops with length: 84% at 1 to 3 words, 18% at 31+ |
| chat "?" | 179 | 231 | 16% of messages |
| chat "right?" | 16 | 9.4 | |
| chat "lol" / "haha" | 65 / 24 | 49 / 11 | |
| chat "please" | 16 | 24.6 | |
| chat swearing: "shit" / "sucks" | 33 / 33 | 5.0 / 2.3 | 1.5% of messages |
| chat "ok so" | in vocabulary | 1.3 to 1.6 | habit from prompts to machines |
| chat "..." | 81 | 38 to 45 | |
| chat reply shape | several short messages | 46% one message, mean 2.1 | |
| chat sample base | 145 messages | 29,755 messages | |
| email "!" | 127 | 73 to 88 | on thanks and good news, not asks |
| email sentence length | avg 24, p90 46 | mean 12.2, median 10.5, p90 24 | |
| email "the" openers | 7% | 4% | |
| email greeting | "Hi [Name]!" | comma greeting: 121 of 128 end in a comma | 40% of mails have none |
| email "Thank you," | always | 62% to 69%, rises with message size | |
| email sample base | 7 mails | 219 mails | |
| spoken "right?" | 90 | 74 | |
| spoken "right?" share of sentences | 13% | 9.0% to 9.5% | mid-turn 85% of the time |
| spoken "I think" | 47 | 33 | |
| spoken "you know" | 83 | 78 | |
| spoken sentence length | avg 15, p90 30 | mean 13.1, p90 26 to 27 | |
| spoken sample tag questions | 392 | median 72 per meeting | per-meeting p10 to p90 is 27 to 91 |
| spoken sample base | 8 meetings | 24 meetings | |

## 5. Machine-facing habits

Per 10k words. These come from his prompts to coding agents. They are near zero when he writes to people, so the skill keeps them out. The last column is the action.

| Habit | typed | email | spoken | chat | Action |
| --- | --- | --- | --- | --- | --- |
| "ok so" | 30.9 (6.1% of typed messages start with it) | 0 | 1 | 1.3 to 1.6 | Out of every register. Warn |
| "so now" | 14.6 | 0 | 2.8 | n/m | Out |
| "no?" tag | 9.2 | 0 | 0.4, all "yes or no?" | 3.3 | Out of every register. In chat, 3.3 per 10k exists, but the skill does not teach it. Warns (comms and spoken score tags in their own rules) |
| "right?" | 10.1 | 0 | 74 | 9.4 | Spoken yes, chat rare, email never |
| "make sense?" | 3.8 | 1 mail | 1.8 | 1.7 | Rare in spoken and chat only |
| "help me", "I want you to", "explain to me", "are you sure" | 24.0 | 2.0 | 1.3 | n/m | Out. Ask a person: "can you walk me through X?" |
| "we need to" | 18.6 | 1.0 | 5.5 | n/m | Not taught for email |
| "can we" | 15.1 | 5.0 | 0.4 | n/m | Not taught for email or spoken |
| "I think" | 39.2 | 8 mails (3.7%) | 33 | 38 | Spoken and chat yes. Email only to hedge a fact |
| "!" | 6.7 | 73 to 88 | speech-to-text | 57 | Supported: none to machines, some to people |
| Lowercase starts | 69% | 0.4% to 1.8%, all URLs, numbers, file names | 3% | 70% | Chat only, calibrated on chat, not on typed |
| "..." | 87.6 | 2.0 | speech-to-text | 38 to 45 | Do not teach |
| "my bad", "was my miss" | 4 hits | 0 | 0 | 13 and 1 messages | Out. "sorry" plus a short reason is the real habit |
| Swearing, "lol" | 6.3% of messages | 0 | masked by Teams | 1.5% and 3.5% of messages | Chat only, mirror the thread |

The typed-leak cut measured email "!" at 61.6. The email cut gives 73 to 88. They come from different cuts.

Not leaks, do not ban: "can you" (22.2 email vs 31.8 typed), "please" (30 vs 42), "fyi" (7.1 vs 3.6), "let me know" (12.1 vs 0.8), "sorry" (12.1 vs 2.7), "thank you". The AI close is the stock offer ("anything else", "happy to help", "hope this helps", "feel free to reach out"), not "let me know" alone.

## 6. Targets used by voice_check.py

This section mirrors `scripts/voice_check.py`. If they differ, fix both in the same change. Exit code is 1 only when a blocker is found.

### 6.1 Blockers, all registers

| Check | Rule |
| --- | --- |
| Em dash | any. 0 in real chat outside pastes, 0 in speech, 1 of 219 emails |
| BANNED list | current entries kept. AI-vocabulary hits are 0 across 219 mails and near 0 in chat |
| Stock closers | "anything else", "happy to help", "hope this helps", "feel free to reach out". "anything else" is allowed in spoken only (an "Anything else?" close in 9 of 24 meetings) |
| Shorthand | "ty", "np", "idk" as whole words, plus current "quick q", "wtv", "plx", "imho", "imo", "gimme", "tho". Real in his typing, never imitated (Alex, 2026-09-08) |
| Call offers | "hop on a call", "jump on a call", "we can talk it on a call", "book a call", "set up a meeting", "schedule some time", "let's sync". Alex works async (2026-10-05). "I was on a call" is fine |
| Lowercase standalone "i" | as a word, not inside words. Ignore code and URLs. Real chat has 36 lowercase vs 7,010 capital "I" (0.5%). Capital "I" is 99.5%, even on lowercase-start lines |

AI-tell words stay blockers in spoken too (Alex's decision). Spoken hits are rare: 10 of 1,739 turns trip a blocker ("this is where" 4 hits in 2 meetings, leverage 2, foster or empower 4, seamless 1, delve 1).

### 6.2 Warnings, all registers except where noted

| Check | Rule |
| --- | --- |
| Contractions | I'll, we'll, you're, we're, I've. 1 to 6 uses each in 29,755 chat messages |
| Typing slips | bare "lets", "whats"; "its" followed by a, not, the, ok, fine, just, been, going. Alex drops the apostrophe on these (lets 96%, its 85% to 90%, whats 37%), and asked that slips are never copied |
| Machine habits | "ok so", "help me", "I want you to", "explain to me", tag "no?" (comms and spoken score tags in their own rules) |
| Old-skill phrases, outside blog | "my bad", "was my miss", "I promise", "cool, but", "trust me", "don't get me wrong", "let me diagram that", "etc!", "one quick tip" |
| Draft length | chat draft over 40 words (longer than about 94% of his replies); comms draft over 60 words (longer than 91% of his emails); blog paragraph over 120 words. Added 2026-10-05 after both lineup rounds showed drafts 30% to 60% longer than his real messages |

### 6.3 Length gate

Under 100 words: print "short-form: rates not scored" and skip every per-10k and per-sentence range warning. Count checks still run.

### 6.4 Chat

No rate targets. Chat rates are not scored. Only 2 of 1,883 real 30+ word bursts pass the old eight rate targets, and the old "!" target alone fails 93%. Treat each non-empty line as one message.

| Check | Rule |
| --- | --- |
| "?" count | warn above 3 per draft |
| "!" count | warn above 2 per draft |
| "(" count | warn above 2 per draft |
| Period at line end | warn on lines of 3 to 30 words that end with a period (real: 0.1% at 3 to 7 words, 0.4% at 8 to 15, 3% at 16 to 30) |
| Long line | warn on any line over 30 words: "this is a channel post, use comms" |
| Signature markers | warn at 2 or more in one draft: tag questions (right?, no?, correct?, make sense?), "ok so", sweet, amazing, wohoo, elongated words with 3+ repeated letters, swear words (shit, damn, wtf, sucks, crap) |
| Lowercase starts | not gated |

Any signature marker appears in about 1 reply in 10 (9.8%). Tags appear in 5.3% of 30+ word bursts. This is why 2 or more in one draft warns.

### 6.5 Comms (rates scored at 100+ words)

| Metric | Range |
| --- | --- |
| avg_sent | 8 to 18 |
| p90_sent | 14 to 50 |
| bang per 10k | 0 to 250 |
| paren per 10k | 0 to 60 |
| the_start_pct | 0 to 10 |
| lower_start_pct | 0 to 2 |
| q | not rate-scored. Warn if more than one "?" in the draft |
| one_line_para_pct | not scored |
| Tag questions | warn on right?, make sense?, no? |
| "I think" | warn at 2 or more |

avg_sent and p90_sent are provisional, set wide on purpose. Measured on the 28 emails with 50+ words: avg_sent p10/p50/p90 11.2/13.1/17.1, p90_sent 19.7/24.5/46.6. Fixed ranges fitted on that set fail 83% of the other mails, so the main protection is the 100-word gate. "q" is not scored because the pooled rate is a short-mail effect.

### 6.6 Spoken

| Metric | 300+ words | 100 to 299 words |
| --- | --- | --- |
| avg_sent | 10 to 18 | 9 to 24 |
| p90_sent | 18 to 40 | 18 to 50 |
| the_start_pct | 0 to 8 | 0 to 12 |
| tag_q per 10k | 15 to 115 | warn if over 150 |
| opinion per 10k | 10 to 80 | not scored |

Punctuation metrics (q, bang, paren, lower_start, one_line_para) are not scored. The checker prints "punctuation from speech-to-text, not calibrated".

Pass counts on the 24 real meetings: avg_sent 22, p90_sent 21, tag_q 22, opinion 21. Under 300 words, 329 of 396 long turns pass avg_sent.

### 6.7 Blog, docs, exec

Current TARGETS stay. Only the length gate and the new blockers and warnings apply on top. Old-skill phrases do not warn in blog. Docs and exec were not re-measured in October 2026.

| Register | avg sentence | p90 | `?` | `!` | `(` | "The" openers `%` | one-sentence paragraphs `%` | lowercase starts `%` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blog | 14 to 21 | 28 to 42 | 30 to 80 | 15 to 70 | 60 to 220 | 0 to 10 | 0 to 35 | 0 to 2 |
| docs (provisional) | 8 to 20 | 14 to 36 | 0 to 90 | 0 to 20 | 20 to 150 | 0 to 12 | 0 to 60 | 0 to 10 |
| exec (provisional) | 6 to 20 | 14 to 34 | 0 to 30 | 0 to 10 | 0 to 80 | 0 to 15 | 0 to 60 | 0 to 1 |

### 6.8 Defaults stated in the skill

- Excluded: "howdy", "sir", "dude". They look person-specific, and the data cannot show who received them ("howdy" is 10% of chat greetings).
- Excluded: formal connectors ("Moreover", "Hence", "That said"). They appear in 7 to 14 mails (3% to 6%), one thread holds 4 of 9 hits, and a skeptic refuted "formal connectors are his argument style".
- A short "Let me know if you have any questions." is allowed only on long or first-contact email. Offers of help appear in 7% to 9% of mails, but in 35% of mails at 60+ words.
- "hey" alone is for chat threads he starts (25.8% of bursts he starts, 5.0% of replies). Channel replies follow chat rules, with no separate register.
- The long "Hi all! ... Thank you," announcement shape is dropped from channel posts. It appears only in the AI-flagged posts (21 posts, median 207 words).
- Call offers (hop on a call, jump on a call, book a call, set up a call, schedule some time, let's sync) are never-use per Alex, 2026-10-05. He works async. This overrides the email finding that 2 to 3 mails use "hop on" or "jump on a call". The checker blocks all of these, plus "we can talk it on a call", "schedule a call" and "book a meeting" forms, in every register including blog.
- Typos and shorthand are never imitated, even though they are real in his typing.

## 7. Refreshing this file

Real, scrubbed excerpts and the corpus live only in the private vault folder `~/Developer/obsidian/Alex/40 Writing/Voice/`. Never copy them here.

- `corpus/` holds the train and holdout sets per source.
- `Voice rebuild 2026-10 findings.md` covers email, spoken and the typed leak check. The `- chat` and `- channel` notes cover Teams chat and channels. Each claim there is marked as survived or refuted.
- Older notes in the same folder: the exemplars file.

To re-measure:

1. Pull his own items read-only through an approved Microsoft 365 route, GET requests only. Never print or save credentials. Keep the method details in the private vault, not here. Sources: sent mail, his Teams chat and channel messages, his lines in meeting transcripts.
2. Scrub names, addresses, account numbers and internal identifiers before anything is saved.
3. Clean: drop automated mail, AI-assisted drafts and pasted AI text. Keep only his own typing.
4. Split into train and holdout. Measure on train. Use the holdout only to test the checker.
5. Have two skeptics re-count each headline number. Write a rule only from claims that survive. Put refuted claims in the notes as caveats.
6. Update the tables here and the `TARGETS` in `scripts/voice_check.py` in the same change.

Known limits: one work period (May to early October 2026), email rates are rough direction only, channel posts are 106, chat has no recipient identity (only chat type), and spoken punctuation comes from speech-to-text.


## Docs and exec: preference test, 2026-10-05

No hand-typed docs or exec briefs of Alex's could be verified, so these registers were tested by preference: same brief, new skill vs September skill, blind. Alex picked the September drafts 10 of 10. They explained the why with "because", warned about the next mistake, asked the reader one deciding question, marked scope, and (exec) quantified the cost of waiting and what the numbers mean. The new drafts were tighter and free of chat markers, but had lost those parts to the "cut to two thirds" rule. The docs and exec register files now keep both sides. The docs and exec checker bands above are provisional: fitted on those 10 picks, which the old bands rejected 10 of 10.
