# Alex's Voice Fingerprint

> Extends `../SKILL.md`. Measured on 2026-09-05 from Alex's own words. Numbers are per 10,000 words unless marked `%`.
> Use this file to calibrate a draft or to argue with a reviewer. Run `../scripts/voice_check.py <draft> --register <name>` to score a draft against the targets below.

## What was measured

| Source | What it is | Size |
| --- | --- | --- |
| typed | Alex's own prompts to coding agents (three tools, Jun to Sep 2026), pasted content removed | ~200k words |
| spoken | Alex's lines in meeting transcripts, speaker-labeled (8 meetings) | ~11k words |
| chat | Alex's own Teams messages to colleagues (145 messages) | ~1k words |
| email | Alex's sent work email (7 messages) | ~300 words |
| hand | Notes and drafts Alex wrote by hand, 2021 to 2023 | ~9k words |
| pub_early | Blog posts written by hand and lightly polished, 2023 to 2024 (3 posts) | ~4k words |
| pub_late | Blog posts drafted by an AI from Alex's material, Dec 2025 to May 2026 (6 posts) | ~15k words |

`pub_late` is the negative baseline. It is what the old version of this skill was calibrated on, which is why it taught the wrong phrases.

## The phrase audit that started this

Hits across every source. Zero in Alex's own words means the phrase is not his.

| Phrase in the old skill | typed (200k words) | hand | pub_early | pub_late |
| --- | --- | --- | --- | --- |
| "here's the thing" | 0 | 0 | 0 | 5 |
| "here's the deal" | 0 | 0 | 1 (2024 polish) | 2 |
| "the truth is" | 0 | 0 | 1 (2024 polish) | 1 |
| "let me be direct", "full disclosure", "I'll be honest" | 0 | 0 | 0 | 4 |
| "spoiler alert" | 0 | 0 | 1 (2024 polish) | 1 |
| "cool, but" | 0 | 0 | 1 (2023, hand) | 2 |
| "don't get me wrong" | 2 | 1 | 0 | 2 |
| "trust me" | 2 | 1 | 0 | 0 |
| "make sense?" | 40 | 0 | 0 | 2 |
| "right?" | 62 | 0 | 4 | 4 |
| "I think" | 258 | 1 | 0 | 0 |
| "ok so" | 169 | 0 | 0 | 0 |

Verdict: keep "cool, but", "don't get me wrong", "trust me", "right?", "make sense?", "I think". Drop the rest.

## Rhythm by register

| Metric | typed | spoken | chat | email | hand | pub_early | pub_late |
| --- | --- | --- | --- | --- | --- | --- | --- |
| avg words per sentence | 22 | 15 | 25 | 24 | 27 | 17 | 15 |
| p90 words per sentence | 49 | 30 | 46 | 46 | 57 | 32 | 27 |
| sentences starting lowercase `%` | 58 | 3 | 48 | 0 | 3 | 0 | 0 |
| `?` | 253 | 156 | 179 | 32 | 105 | 41 | 58 |
| `!` | 6 | 0 | 325 | 127 | 12 | 20 | 4 |
| `(` asides | 33 | 0 | 33 | n/a | 92 | 112 | 61 |
| `...` | 55 | 33 | 81 | 64 | 0 | 0 | 7 |
| em dash | 5 (pasted) | 0 | 0 | 32 | 2 | 22 (polish) | 79 |
| "right?" | 11 | 90 | 16 | 0 | 0 | 5 | 1 |
| "I think" | 36 | 47 | 0 | 0 | 3 | 0 | 0 |
| "you know" | 3 | 83 | 0 | 0 | 0 | 0 | 3 |
| "please" | 46 | 3 | 16 | 64 | 6 | 0 | 1 |
| "lol" / "haha" | 8 | 0 | 65 / 24 | 0 | 0 | 0 | 0 |
| "shit" / "sucks" | 15 | 0 | 33 / 33 | 0 | 0 | 0 | 0 |
| "its", "lets" without apostrophe | 10 / 39 | 3 / 1 | 33 / 0 | 0 | 4 / 0 | 0 | 5 / 1 |
| "the" as `%` of words | 3.6 | 3.6 | 1.8 | 4.8 | 3.8 | 4.2 | 5.4 |
| sentences starting with "The" `%` | 2 | 2 | 0 | 7 | 2 | 8 | 14 |

## What the numbers say

1. **Alex thinks in questions.** Every register he writes himself runs 100 to 250 questions per 10k words. The AI-drafted posts run 58. In meetings, 13% of all his sentences end in "right?".
2. **Alex is loud with people and quiet with machines.** Exclamation marks: 325 in chat, 127 in email, 20 in his early posts, 6 when typing to an AI, 4 in the AI-drafted posts. Public writing lost his warmth.
3. **Em dashes are not his.** Zero in speech, zero in chat, zero in hand drafts. The 2025 to 2026 posts run 44 to 141 per 10k words. He said "I hate em dashes" in his own prompts.
4. **He writes long, then gets polished short.** Hand drafts average 27 to 40 words per sentence with comma splices. His published 2023 to 2024 posts average 17. The AI-drafted posts average 15 with p90 of 27, which reads as staccato. Target for blog: 14 to 21 average, p90 up to 42, and one long thinking sentence per section is welcome.
5. **Asides in parentheses are a real marker.** 92 to 253 per 10k in hand drafts and early posts. Example shape: "(this last book is CRAZY heavy reading, so be advised)".
6. **Opinion is hedged, then strong.** "I think", "to me", "in my personal opinion" open the sentence, and the sentence itself is blunt. The AI-drafted posts removed every "I think".
7. **Sentence openers.** Spoken: "So" 16%, "I" 8%, "And" 8%, "Yeah" 8%, "But" 4%. Chat and typed: "ok so", "hey", "so", "also", "can you". AI-drafted posts open 14% of sentences with "The".
8. **Chat is fragments.** One thought per message, 3 to 10 words, sent in bursts. Lowercase start 48%. "its" and "lets" without apostrophes. Elongated words ("sweeeet", "daaaaaamn", "wohoo!!!!"). "lol" and "haha" close a line.

## Distinctive n-grams

Frequent in Alex's own words and near zero in the AI-drafted posts: "I think", "I want", "ok so", "can you", "we need", "we can", "I don't", "so now", "help me", "do it", "can we", "for me", "right now", "I think we", "ok so now", "I want to", "we need to".

Frequent in the AI-drafted posts and near zero in Alex's own words: "here's the", "here's what", "but here's", "this is where", "the model", "the agent", "a senior engineer", "the difference between", "you need to", "the first", "the best".

## ESL shape (Portuguese first language)

The dropped subjects, calques, tags, and CAPS are real and can survive in chat and spoken registers; fix them in blog, docs, comms, and exec only when they block understanding. Typos and abbreviated words ("wtv", "plx", "quick q", "tho") are also real in the data but are never imitated: Alex asked for whole words, spelled right, in every register (2026-09-08).

- Dropped subject "it": "is not infra", "is a simple idea", "is nice to fix it tho".
- Dropped verb or article: "I not really that interested", "was my miss", "in special".
- Calques: "explain to me", "let me ask you something", "make sense?" (no s), "per say".
- Lists end with "etc" or "etc!".
- Sentence-final tags: "right?", "no?", "correct?".
- CAPS for emphasis inside a sentence: "CRAZY heavy", "A LOT better", "NOT in aws".

## Targets used by voice_check.py

| Register | avg sentence | p90 | `?` | `!` | `(` | "The" openers `%` | one-sentence paragraphs `%` | lowercase starts `%` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blog | 14 to 21 | 28 to 42 | 30 to 80 | 15 to 70 | 60 to 220 | 0 to 10 | 0 to 35 | 0 to 2 |
| docs | 12 to 20 | 24 to 36 | 5 to 40 | 0 to 20 | 20 to 150 | 0 to 12 | 0 to 60 | 0 to 2 |
| comms | 12 to 24 | 22 to 46 | 10 to 80 | 40 to 200 | 0 to 120 | 0 to 10 | 0 to 80 | 0 to 2 |
| exec | 12 to 20 | 22 to 34 | 0 to 30 | 0 to 10 | 0 to 80 | 0 to 15 | 0 to 60 | 0 to 1 |
| chat | 4 to 30 | 8 to 55 | 80 to 260 | 60 to 350 | 0 to 60 | 0 to 5 | 40 to 100 | 30 to 100 |
| spoken | 10 to 20 | 20 to 34 | 80 to 220 | 0 to 40 | 0 to 20 | 0 to 5 | any | 0 to 5 |

Em dash and the banned phrase list are blockers in every register.

## Refreshing this file

Real excerpts and the extraction commands live in Alex's private vault note `40 Writing/Voice/Alex voice exemplars.md`, not in this public repo. Re-run the measurement when a new register appears or when Alex catches a new AI tell, and update the tables above.
