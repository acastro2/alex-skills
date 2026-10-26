# Worked example

One finding, two shapes. The drafts are real files beside this one, so the counts can be checked:
[before.md](before.md) and [after.md](after.md).

## Before: 41 rows

> I looked into the migration status across the three environments, and I also spent some time reviewing the recent incident reports to see whether there was any correlation with the migration work.

Read those two lines again. A reader learns the topic and nothing else. The finding is in the last paragraph of a 41-row reply.

| what is wrong | anti-pattern |
|---|---|
| The opening says what was done, not what was found | The journey |
| The answer sits in section 5, under "Recommendation" | The buried lede |
| "Risks" repeats "Findings" almost word for word | The restatement |
| `might`, `could potentially`, `possible`, `would suggest` in one reply | The hedge stack |
| "Options" has no numbers, so nothing can be compared | No proof zone |
| 41 rows with no visual, for data that is a bar chart | The wall |

## After: 17 rows

Two lines of prose, one chart, three evidence lines, one ask.

```markdown
**Delay the cutover to 12 Jan.** Four September incidents all trace to the new
ledger path, and settlement is 72% done.

- Incidents: 4 in September, all on the new ledger path. INC-2291, 2298, 2304, 2311
- Settlement: 14 of 20 tasks closed; recon has not started. ADO #4412
- Quarter end: the 21 Dec window lands inside the finance close freeze. FIN-88

Next: approve 12 Jan, or name who carries the quarter-end risk.
```

The chart between the prose and the evidence, drawn by the real renderer at 70 columns:

```chart
{"type":"bar","title":"Incidents tripled after the ledger cutover","labels":["Apr","May","Jun","Jul","Aug","Sep"],"values":[1,0,2,1,1,4],"height":8}
```

```
Incidents tripled after the ledger cutover
4┤                                                         ███4████
3┤                                                         ████████
 │                                                         ████████
2┤                        ███2████                         ████████
1┤  🬭🬭🬭1🬭🬭🬭🬭              ████████   🬭🬭🬭1🬭🬭🬭🬭   🬭🬭🬭1🬭🬭🬭🬭   ████████
0┼──████████──────────────████████───████████───████████───████████───
      Apr        May        Jun        Jul        Aug        Sep
```

Where the 17 rows go: 2 answer, 1 gap, 8 chart, 1 gap, 3 evidence, 1 gap, 1 next.

## What changed, and what did not

The evidence is the same. The incident IDs, the task count, the freeze date, all carried over unchanged. Only the shape changed.

- **The title became the claim.** "Incidents tripled after the ledger cutover" says the finding. "Incidents by month" would have said nothing.
- **The chart replaced three numbers** that would otherwise sit in a sentence. That is the bar for drawing one.
- **The prose stopped narrating the chart.** Once the bars are up, saying "there were four incidents in September" again spends a row for nothing.
- **The hedge went.** "Delay to 12 Jan" is a call. "Consider whether to delay, or alternatively proceed" is not.

## The check, applied

1. Lines 1 to 3: the date and the reason. Decision possible.
2. Bold text only: one line, and it holds the answer.
3. Chart titles: one claim, with a number in the picture.
4. Rows: 17 against a budget of 40.
