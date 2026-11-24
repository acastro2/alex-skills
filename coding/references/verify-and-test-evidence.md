# Verify and test: the evidence

Why `coding` part 2 bans the tests an agent volunteers, keeps bug-repro and criterion tests, and restores test files before it trusts a green run. Read this when you need to defend or change a rule in part 2. Checked 2026-11-24.

## Tests the agent volunteers add nothing

- On DeepSWE (111 tasks, 444 runs, Sonnet 5.5), a ban on writing tests left success flat (65.3% with tests, 66.2% without) and cut time 6% and spend 9%. Disabling the existing suite on a 44-task subset added no regressions ([Kun Chen](https://substack.com/@kunchenguid/note/c-356087116)).
- On SWE-bench Verified (5,000 runs, six models), telling agents to write tests or not changed resolved totals by 0 to 13 of 500, none significant. Heavy test writers used 25–49% fewer input tokens when told not to ([arXiv 2602.07900](https://arxiv.org/abs/2602.07900)).
- The reason: the code and the test come from the same reading of the task. If the reading is wrong, the test confirms the error.

## Tests generated from the code lock in bugs

- Across 145 merged PRs in SciPy, Qiskit and pandas, 8–17% of LLM-generated regression tests asserted the faulty behaviour, and only 2.4–4.8% caught a fault. 83–91% of the bad tests still passed many commits later ([arXiv 2610.11835](https://arxiv.org/abs/2610.11835)).

## Old tests left failing are the real cost

- In SWE-Maintain (1,996 paired follow-up tasks), building on the agent's own history cut success by 5.6 points, and by 14 when all earlier tests had to pass. When every earlier test passed, the gap went away ([arXiv 2610.14768](https://arxiv.org/abs/2610.14768)).

## Agents edit tests to get green

- On ImpossibleBench, read-only tests cut Claude Opus 4.1's cheating from 50% to 1%. GPT-5 still cheated 39% through special-casing and operator overloading. A "flag for human intervention" exit cut GPT-5 from 54% to 9%, with less effect on Claude ([arXiv 2510.20270](https://arxiv.org/abs/2510.20270)).
- Restoring the test files from base before the final run gives the same effect as read-only tests. It does not catch special-casing.

## Which tests to run beats how to test

- In TDAD, a map from changed code to its tests cut regressions from 6.08% to 1.82%. A plain TDD prompt raised them to 9.94%. Cutting the skill from 107 to 20 lines quadrupled resolution, 12% to 50%. The model was a small 30B one, so treat these as leads ([arXiv 2603.17973](https://arxiv.org/abs/2603.17973)).
- Instruction length alone did not lower adherence: 60.0%, 65.2%, 67.7% and 64.0% at 25, 100, 250 and 500 lines, not significant (p=0.16) ([arXiv 2605.10039](https://arxiv.org/abs/2605.10039)). Keep the skill short to save tokens, not to buy obedience.

## Claimed success is often false

- Withheld tests rejected 18.5–41.5% of the successes an agent claimed from its own tests ([Zenodo 23226464](https://doi.org/10.5281/zenodo.23226464)).
- A fresh verifier given only the spec caught 95.4% of 46 seeded faults, against 85.1% for the builder's own check (Sonnet 5.5, p=0.006), for about 126k extra tokens per unit ([arXiv 2610.28667](https://arxiv.org/abs/2610.28667)).

## Allowed tests come from a written checklist

- A test-writer prompt grounded in a spec checklist raised correct final code by 38 points against an edge-case prompt, with 0% false alarms against 33% (p=0.002, small functions) ([arXiv 2607.06636](https://arxiv.org/html/2607.06636)). Property tests the agent invented falsely rejected the correct code in 2 of 15 batteries.

## What is not measured

- No study tested "verify by running, no new tests" over months of changes on one codebase. Track it on real work: [real-work tracking](real-work-tracking.md).
