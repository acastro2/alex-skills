// Resource sampler: parsers on fixture text, series downsampling, tone thresholds.
import { expect, test } from "bun:test";
import {
  buildSeries,
  cpuPercent,
  evaluateTone,
  parseDf,
  parseDiskstats,
  parseLoadavg,
  parseMeminfo,
  parsePressure,
  parseProcStat,
  parsePs,
  procRows,
  type Sample,
} from "../src/serve/resources.ts";

const STAT_1 = `cpu  100 0 100 800 0 0 0 0 0 0
cpu0 50 0 50 400 0 0 0 0 0 0
cpu1 50 0 50 400 0 0 0 0 0 0
intr 12345
ctxt 999
`;
const STAT_2 = `cpu  350 0 100 1350 0 0 0 0 0 0
cpu0 250 0 50 600 0 0 0 0 0 0
cpu1 100 0 50 750 0 0 0 0 0 0
intr 22345
`;

test("two /proc/stat samples give known total and per-core CPU %", () => {
  const a = parseProcStat(STAT_1);
  const b = parseProcStat(STAT_2);
  expect(a.cores).toHaveLength(2);
  expect(cpuPercent(a.total!, b.total!)).toBeCloseTo(31.25, 5);
  expect(cpuPercent(a.cores[0], b.cores[0])).toBeCloseTo(50, 5);
  expect(cpuPercent(a.cores[1], b.cores[1])).toBeCloseTo(12.5, 5);
  expect(cpuPercent(a.total!, a.total!)).toBeNull();
});

test("loadavg, meminfo and pressure parse", () => {
  expect(parseLoadavg("0.52 0.40 0.31 2/845 12345\n")).toEqual({ one: 0.52, five: 0.4, fifteen: 0.31 });
  const mem = parseMeminfo("MemTotal:       16000000 kB\nMemFree:  100 kB\nMemAvailable:    8000000 kB\nSwapTotal:       2000000 kB\nSwapFree:        1500000 kB\n");
  expect(mem).toEqual({ memTotal: 16000000, memAvailable: 8000000, swapTotal: 2000000, swapFree: 1500000 });
  expect(parseMeminfo("nothing")).toBeNull();
  expect(parsePressure("some avg10=12.34 avg60=5.00 avg300=1.00 total=123\nfull avg10=1.00 avg60=0.00 avg300=0.00 total=5\n")).toBe(12.34);
  expect(parsePressure("")).toBeNull();
});

test("diskstats sums whole disks only", () => {
  const text = `   8       0 sda 100 0 2000 50 200 0 4000 80 0 10 130
   8       1 sda1 90 0 1900 40 190 0 3900 70 0 9 110
   7       0 loop0 5 0 999 1 0 0 0 0 0 1 1
   1       0 ram0 0 0 0 0 0 0 0 0 0 0 0
 259       0 nvme0n1 10 0 300 5 20 0 500 8 0 3 13
 259       1 nvme0n1p1 9 0 290 4 19 0 490 7 0 2 11
 253       0 dm-0 7 0 777 1 7 0 777 1 0 1 2
`;
  expect(parseDiskstats(text)).toEqual({ sectorsRead: 2300, sectorsWritten: 4500 });
});

test("ps rows keep spaces in args", () => {
  const rows = parsePs(`  4242 12.5 204800 01:02:03 node node /usr/bin/node --flag "a b c" server.js
     1  0.0   9000    5-04:03:02 systemd /sbin/init splash
`);
  expect(rows).toHaveLength(2);
  expect(rows[0]).toEqual({ pid: 4242, cpu: 12.5, rss_kb: 204800, etime: "01:02:03", comm: "node", args: 'node /usr/bin/node --flag "a b c" server.js' });
  expect(rows[1].etime).toBe("5-04:03:02");
});

test("df rows parse", () => {
  const d = parseDf(`Filesystem     1024-blocks      Used Available Capacity Mounted on
/dev/sda2        104857600  52428800  52428800      50% /
/dev/sdb1         10485760   1048576   9437184      10% /mnt/my data
`);
  expect(d[0]).toMatchObject({ mount: "/", total_gb: 100, used_gb: 50, free_gb: 50, used_pct: 50 });
  expect(d[1].mount).toBe("/mnt/my data");
});

const sample = (t: number, o: Partial<Sample> = {}): Sample => ({ t, cpu: 10, mem: 40, avail: 60, swap: 0, load1: 1, psi_mem: 0, ...o });
const run = (n: number, o: Partial<Sample> = {}, step = 5000): Sample[] => Array.from({ length: n }, (_, i) => sample(i * step, o));

test("series: 2 hours of 5 s samples give 60 points, one per minute, oldest first", () => {
  const samples: Sample[] = Array.from({ length: 1440 }, (_, i) => sample(i * 5000, { cpu: i % 2 === 0 ? 0 : 100 }));
  const series = buildSeries(samples.slice(-720));
  expect(series).toHaveLength(60);
  for (let i = 1; i < series.length; i++) expect(series[i].t - series[i - 1].t).toBe(60_000);
  expect(series[0].cpu).toBeCloseTo(50, 5);
  expect(series[59].t).toBe(Math.floor(samples[1439].t / 60_000) * 60_000);
});

test("series: a minute averages its samples and skips null values", () => {
  const series = buildSeries([sample(0, { cpu: 10 }), sample(5000, { cpu: 30 }), sample(10000, { cpu: null }), sample(60_000, { cpu: 50 })]);
  expect(series).toHaveLength(2);
  expect(series[0].cpu).toBe(20);
  expect(series[1].cpu).toBe(50);
});

test("tone: ok when quiet", () => {
  expect(evaluateTone(run(40), 40 * 5000)).toEqual({ tone: "ok", reasons: [] });
});

test("tone: amber after CPU above 85 % for 1 min, not before", () => {
  const hot = run(14, { cpu: 90 }); // 65 s
  expect(evaluateTone(hot, 14 * 5000)).toEqual({ tone: "amber", reasons: ["CPU above 85 % for 1 min"] });
  expect(evaluateTone(run(8, { cpu: 90 }), 8 * 5000).tone).toBe("ok");
  const dip = run(14, { cpu: 90 });
  dip[10] = sample(dip[10].t, { cpu: 50 });
  expect(evaluateTone(dip, 14 * 5000).tone).toBe("ok");
});

test("tone: red after CPU above 95 % for 3 min", () => {
  const r = evaluateTone(run(40, { cpu: 97 }), 40 * 5000);
  expect(r.tone).toBe("red");
  expect(r.reasons).toEqual(["CPU above 95 % for 3 min"]);
});

test("tone: memory, swap and pressure thresholds", () => {
  const at = (o: Partial<Sample>) => evaluateTone([sample(0, o)], 0);
  expect(at({ avail: 9 }).tone).toBe("amber");
  expect(at({ avail: 4 }).tone).toBe("red");
  expect(at({ swap: 30 }).tone).toBe("amber");
  expect(at({ swap: 60 }).tone).toBe("red");
  expect(at({ psi_mem: 11 }).tone).toBe("amber");
  expect(at({ psi_mem: 30 }).tone).toBe("red");
  const both = at({ avail: 8, swap: 60 });
  expect(both.tone).toBe("red");
  expect(both.reasons).toEqual(["Memory available below 10 %", "Swap used above 50 %"]);
});

// Seen live 2026-11-25: the sampler's own ps call topped the CPU list, and $HOME paths filled the command column.
test("procRows drops the sampler's own ps call and shortens the home folder to ~", () => {
  const rows = parsePs(`  100 99.0 4000 00:00 ps ps -eo pid=,pcpu=,rss=,etime=,comm=,args= --sort=-pcpu
  200 50.0 8000 01:00 rex /home/u/.local/bin/rex serve --port 1`);
  const { top_cpu } = procRows(rows, new Map([[200, "ses_X"]]), "/home/u");
  expect(top_cpu.map((p) => p.pid)).toEqual([200]);
  expect(top_cpu[0].args).toBe("~/.local/bin/rex serve --port 1");
  expect(top_cpu[0].session).toBe("ses_X");
});
