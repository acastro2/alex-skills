// Ask one O'Reilly Answers question in the browser-control session page and capture the answer.
// The question is read from ~/.cache/oreilly-answers/q.txt (written by ask.sh), so no shell quoting
// reaches the page. Returns { q, url, complete, text, links }.
const qfile = path.join(process.env.HOME, ".cache/oreilly-answers/q.txt");
const q = fs.readFileSync(qfile, "utf8").trim();
if (!q) throw new Error(`empty question in ${qfile}`);

await page.goto("https://learning.oreilly.com/answers2/", { waitUntil: "domcontentloaded" });
const box = page.getByRole("textbox", { name: "What can we answer for you?" });
await box.waitFor({ timeout: 20000 });
await fillInput(box, q);
await page.getByRole("button", { name: "Ask question" }).click();
await page.waitForURL(/questionId=/, { timeout: 60000 });

// The answer streams in. Wait until the text stops growing for ~8 s, scrolling to the bottom each
// pass so lazily rendered sources and follow-ups load too.
const len = () => page.evaluate(() => (document.querySelector("main") || document.body).innerText.length);
let last = -1, stable = 0;
for (let i = 0; i < 90 && stable < 4; i++) {
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(2000);
  const n = await len();
  stable = n === last ? stable + 1 : 0;
  last = n;
}

const text = await page.evaluate(() => (document.querySelector("main") || document.body).innerText);
const links = await page.evaluate(() =>
  [...document.querySelectorAll("main a[href*='/library/view/']")]
    .map(a => ({ title: a.innerText.trim().slice(0, 160), href: a.href })));
// "Was this response helpful?" only renders once the answer is finished.
const complete = text.includes("Was this response helpful?");
return { q, url: page.url(), complete, text, links };
