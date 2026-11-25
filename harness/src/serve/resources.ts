// Resource monitor: how hard this machine is working. The types are the contract between the
// sampler (server) and the Machine panel and view (page). The sampler fills in the rest.

/** One process in a top list. `session` is the harness session that registered this PID, if any. */
export interface ProcSample {
  pid: number;
  cpu: number; // percent of one core, as ps reports it
  rss_mb: number;
  etime: string; // ps elapsed time, e.g. "01:02:03"
  comm: string;
  args: string; // command line, cut to 200 chars
  session: string | null; // session id from the `processes` table
  slug: string | null; // short session name, filled by the snapshot
}

/** One point of the series. Null when that sample had no value (for example no PSI on macOS). */
export interface ResourcePoint {
  t: number; // Unix ms, start of the minute
  cpu: number | null; // total CPU %, 0-100
  mem: number | null; // memory used %, 0-100 (100 - available %)
  swap: number | null; // swap used %, 0-100
  load1: number | null;
  psi_mem: number | null; // memory pressure some avg10
}

export type Tone = "ok" | "amber" | "red";

export interface Resources {
  at: number; // Unix ms of the newest sample
  os: "linux" | "macos" | "other";
  source: "proc" | "macos-fallback"; // the macOS path is untested
  cpu: { total: number | null; cores: (number | null)[]; count: number };
  load: { one: number; five: number; fifteen: number } | null;
  memory: {
    total_mb: number;
    used_mb: number;
    available_mb: number;
    available_pct: number;
    swap_total_mb: number;
    swap_used_mb: number;
    swap_pct: number; // 0 when there is no swap
  } | null;
  disks: { mount: string; total_gb: number; used_gb: number; free_gb: number; used_pct: number }[];
  io: { read_mb_s: number; write_mb_s: number } | null;
  pressure: { cpu: number | null; memory: number | null; io: number | null } | null; // PSI some avg10
  top_cpu: ProcSample[]; // 8 rows
  top_rss: ProcSample[]; // 8 rows
  /** 60 min, 1 point per minute, oldest first. */
  series: ResourcePoint[];
  /** Overall tone and the reasons for it, in plain words ("CPU above 85 % for 1 min"). */
  tone: Tone;
  reasons: string[];
}

// ---------------------------------------------------------------------------------------------
// Implementation. Parsers are pure functions on text so tests can feed fixtures.
// ---------------------------------------------------------------------------------------------
import type { Database } from "bun:sqlite";
import { homedir } from "node:os";

export interface CpuTimes {
  busy: number;
  total: number;
}

/** Jiffies from /proc/stat: the total line and one entry per core. */
export function parseProcStat(text: string): { total: CpuTimes | null; cores: CpuTimes[] } {
  let total: CpuTimes | null = null;
  const cores: CpuTimes[] = [];
  for (const line of text.split("\n")) {
    const m = line.match(/^(cpu\d*)\s+(.*)$/);
    if (!m) continue;
    const f = m[2].trim().split(/\s+/).map(Number);
    if (f.length < 4 || f.some((n) => !Number.isFinite(n))) continue;
    const sum = f.slice(0, 8).reduce((a, b) => a + b, 0); // user nice system idle iowait irq softirq steal
    const idle = f[3] + (f[4] ?? 0);
    const t = { busy: sum - idle, total: sum };
    if (m[1] === "cpu") total = t;
    else cores.push(t);
  }
  return { total, cores };
}

/** CPU % between two samples. Null when no time passed. */
export function cpuPercent(prev: CpuTimes, cur: CpuTimes): number | null {
  const dt = cur.total - prev.total;
  if (dt <= 0) return null;
  return Math.max(0, Math.min(100, ((cur.busy - prev.busy) / dt) * 100));
}

export function parseLoadavg(text: string): { one: number; five: number; fifteen: number } | null {
  const f = text.trim().split(/\s+/).map(Number);
  return f.length >= 3 && f.slice(0, 3).every(Number.isFinite) ? { one: f[0], five: f[1], fifteen: f[2] } : null;
}

/** Values in kB. */
export function parseMeminfo(text: string): { memTotal: number; memAvailable: number; swapTotal: number; swapFree: number } | null {
  const get = (k: string) => {
    const m = text.match(new RegExp(`^${k}:\\s+(\\d+)`, "m"));
    return m ? Number(m[1]) : null;
  };
  const memTotal = get("MemTotal");
  const memAvailable = get("MemAvailable");
  if (memTotal === null || memAvailable === null) return null;
  return { memTotal, memAvailable, swapTotal: get("SwapTotal") ?? 0, swapFree: get("SwapFree") ?? 0 };
}

/** The "some avg10" value of a /proc/pressure/* file. */
export function parsePressure(text: string): number | null {
  const m = text.match(/^some\s.*?avg10=([\d.]+)/m);
  return m ? Number(m[1]) : null;
}

const WHOLE_DISK = /^(sd[a-z]+|vd[a-z]+|xvd[a-z]+|hd[a-z]+|nvme\d+n\d+|mmcblk\d+)$/;

/** Sectors read and written, summed over whole disks only (no partitions, loop, ram or dm). */
export function parseDiskstats(text: string): { sectorsRead: number; sectorsWritten: number } {
  let sectorsRead = 0;
  let sectorsWritten = 0;
  for (const line of text.split("\n")) {
    const f = line.trim().split(/\s+/);
    if (f.length < 10 || !WHOLE_DISK.test(f[2])) continue;
    sectorsRead += Number(f[5]) || 0;
    sectorsWritten += Number(f[9]) || 0;
  }
  return { sectorsRead, sectorsWritten };
}

export interface PsRow {
  pid: number;
  cpu: number;
  rss_kb: number;
  etime: string;
  comm: string;
  args: string;
}

/** Output of `ps -eo pid=,pcpu=,rss=,etime=,comm=,args= --sort=-pcpu`. Args may hold spaces. */
export function parsePs(text: string): PsRow[] {
  const rows: PsRow[] = [];
  for (const line of text.split("\n")) {
    const m = line.trim().match(/^(\d+)\s+([\d.]+)\s+(\d+)\s+(\S+)\s+(\S+)\s*(.*)$/);
    if (!m) continue;
    rows.push({ pid: Number(m[1]), cpu: Number(m[2]), rss_kb: Number(m[3]), etime: m[4], comm: m[5], args: m[6] });
  }
  return rows;
}

/** Output of `df -P -k <paths>`: one row per data line. */
export function parseDf(text: string): Resources["disks"] {
  const out: Resources["disks"] = [];
  for (const line of text.split("\n").slice(1)) {
    const f = line.trim().split(/\s+/);
    if (f.length < 6) continue;
    const total = Number(f[1]);
    const used = Number(f[2]);
    const free = Number(f[3]);
    if (![total, used, free].every(Number.isFinite)) continue;
    const gb = (kb: number) => Math.round((kb / 1048576) * 10) / 10;
    out.push({ mount: f.slice(5).join(" "), total_gb: gb(total), used_gb: gb(used), free_gb: gb(free), used_pct: total > 0 ? Math.round((used / (used + free)) * 100) : 0 });
  }
  return out;
}

/** Raw sample kept in memory. */
export interface Sample {
  t: number;
  cpu: number | null;
  mem: number | null; // used %
  avail: number | null; // available %
  swap: number | null; // used %
  load1: number | null;
  psi_mem: number | null;
}

export const MAX_SAMPLES = 720;
const MINUTE = 60_000;

/** 60 points, 1 per minute, average per minute, oldest first. */
export function buildSeries(samples: Sample[]): ResourcePoint[] {
  const buckets = new Map<number, Sample[]>();
  for (const s of samples) {
    const k = Math.floor(s.t / MINUTE) * MINUTE;
    const b = buckets.get(k);
    if (b) b.push(s);
    else buckets.set(k, [s]);
  }
  const avg = (b: Sample[], f: (s: Sample) => number | null) => {
    const v = b.map(f).filter((n): n is number => n !== null);
    return v.length ? v.reduce((a, c) => a + c, 0) / v.length : null;
  };
  return [...buckets.keys()]
    .sort((a, b) => a - b)
    .slice(-60)
    .map((t) => {
      const b = buckets.get(t) as Sample[];
      return { t, cpu: avg(b, (s) => s.cpu), mem: avg(b, (s) => s.mem), swap: avg(b, (s) => s.swap), load1: avg(b, (s) => s.load1), psi_mem: avg(b, (s) => s.psi_mem) };
    });
}

/** True when every sample in the last `windowMs` is above `limit` and the history covers the window. */
function cpuAbove(samples: Sample[], now: number, windowMs: number, limit: number, intervalMs: number): boolean {
  if (samples.length === 0) return false;
  if (samples[0].t > now - windowMs + intervalMs * 1.5) return false; // not enough history yet
  const inWindow = samples.filter((s) => s.t > now - windowMs);
  return inWindow.length > 0 && inWindow.every((s) => s.cpu !== null && s.cpu > limit);
}

/** Tone and reasons from the raw history. The newest sample drives memory, swap and pressure. */
export function evaluateTone(samples: Sample[], now: number, intervalMs = 5000): { tone: Tone; reasons: string[] } {
  const reasons: string[] = [];
  let tone: Tone = "ok";
  const raise = (to: Tone, reason: string) => {
    reasons.push(reason);
    if (to === "red" || tone === "ok") tone = to;
  };
  const last = samples[samples.length - 1];
  if (!last) return { tone, reasons };
  if (cpuAbove(samples, now, 3 * MINUTE, 95, intervalMs)) raise("red", "CPU above 95 % for 3 min");
  else if (cpuAbove(samples, now, MINUTE, 85, intervalMs)) raise("amber", "CPU above 85 % for 1 min");
  if (last.avail !== null) {
    if (last.avail < 5) raise("red", "Memory available below 5 %");
    else if (last.avail < 10) raise("amber", "Memory available below 10 %");
  }
  if (last.swap !== null) {
    if (last.swap > 50) raise("red", "Swap used above 50 %");
    else if (last.swap > 25) raise("amber", "Swap used above 25 %");
  }
  if (last.psi_mem !== null) {
    if (last.psi_mem > 25) raise("red", "Memory pressure above 25");
    else if (last.psi_mem > 10) raise("amber", "Memory pressure above 10");
  }
  return { tone, reasons };
}

// ---- Sampler -------------------------------------------------------------------------------

async function readText(path: string): Promise<string> {
  try {
    return await Bun.file(path).text();
  } catch {
    return "";
  }
}

async function run(cmd: string[]): Promise<string> {
  try {
    const p = Bun.spawn(cmd, { stdout: "pipe", stderr: "ignore" });
    const text = await new Response(p.stdout).text();
    await p.exited;
    return text;
  } catch {
    return "";
  }
}

const mb = (kb: number) => Math.round((kb / 1024) * 10) / 10;

/** The sampler's own `ps` call: it always shows near 100 % CPU, so it never counts. */
const SELF_PS = /^ps -eo pid=,pcpu=/;

export function procRows(all: PsRow[], sessions: Map<number, string>, home = process.env.HOME ?? ""): { top_cpu: ProcSample[]; top_rss: ProcSample[] } {
  const rows = all.filter((r) => !SELF_PS.test(r.args));
  // `~` for the home folder, so the command column shows the program, not the path to it.
  const short = (s: string) => (home ? s.split(home).join("~") : s);
  const conv = (r: PsRow): ProcSample => ({
    pid: r.pid,
    cpu: r.cpu,
    rss_mb: mb(r.rss_kb),
    etime: r.etime,
    comm: r.comm,
    args: short(r.args).slice(0, 200),
    session: sessions.get(r.pid) ?? null,
    slug: null,
  });
  return {
    top_cpu: [...rows].sort((a, b) => b.cpu - a.cpu).slice(0, 8).map(conv),
    top_rss: [...rows].sort((a, b) => b.rss_kb - a.rss_kb).slice(0, 8).map(conv),
  };
}

function sessionPids(db: Database): Map<number, string> {
  const out = new Map<number, string>();
  try {
    for (const r of db.query("SELECT session_id, pid FROM processes WHERE ended_at IS NULL").all() as { session_id: string | null; pid: number | null }[]) {
      if (r.session_id && r.pid) out.set(r.pid, r.session_id);
    }
  } catch {
    /* no table: no session names */
  }
  return out;
}

async function disks(): Promise<Resources["disks"]> {
  const home = process.env.HOME ?? homedir();
  const rows = parseDf(await run(["df", "-P", "-k", "/", home]));
  const seen = new Set<string>();
  return rows.filter((d) => (seen.has(d.mount) ? false : (seen.add(d.mount), true)));
}

const PS_ARGS = ["ps", "-eo", "pid=,pcpu=,rss=,etime=,comm=,args=", "--sort=-pcpu"];

export interface Sampler {
  latest(): Resources | null;
  stop(): void;
}

export function startSampler(db: Database, opts: { intervalMs?: number; clock?: () => number } = {}): Sampler {
  const intervalMs = opts.intervalMs ?? 5000;
  const clock = opts.clock ?? Date.now;
  const samples: Sample[] = [];
  let latest: Resources | null = null;
  let busy = false;
  let prevStat: { total: CpuTimes | null; cores: CpuTimes[] } | null = null;
  let prevDisk: { t: number; r: number; w: number } | null = null;
  const isMac = process.platform === "darwin";

  async function tickLinux(now: number): Promise<Resources> {
    const [stat, load, mem, psiC, psiM, psiI, dstat, ps, dk] = await Promise.all([
      readText("/proc/stat"),
      readText("/proc/loadavg"),
      readText("/proc/meminfo"),
      readText("/proc/pressure/cpu"),
      readText("/proc/pressure/memory"),
      readText("/proc/pressure/io"),
      readText("/proc/diskstats"),
      run(PS_ARGS),
      disks(),
    ]);
    const cur = parseProcStat(stat);
    const total = prevStat?.total && cur.total ? cpuPercent(prevStat.total, cur.total) : null;
    const cores = cur.cores.map((c, i) => (prevStat?.cores[i] ? cpuPercent(prevStat.cores[i], c) : null));
    prevStat = cur;

    const d = parseDiskstats(dstat);
    let io: Resources["io"] = null;
    if (dstat && prevDisk && now > prevDisk.t) {
      const secs = (now - prevDisk.t) / 1000;
      io = { read_mb_s: Math.max(0, ((d.sectorsRead - prevDisk.r) * 512) / 1e6 / secs), write_mb_s: Math.max(0, ((d.sectorsWritten - prevDisk.w) * 512) / 1e6 / secs) };
    }
    if (dstat) prevDisk = { t: now, r: d.sectorsRead, w: d.sectorsWritten };

    const mi = parseMeminfo(mem);
    const memory: Resources["memory"] = mi
      ? {
          total_mb: mb(mi.memTotal),
          used_mb: mb(mi.memTotal - mi.memAvailable),
          available_mb: mb(mi.memAvailable),
          available_pct: (mi.memAvailable / mi.memTotal) * 100,
          swap_total_mb: mb(mi.swapTotal),
          swap_used_mb: mb(mi.swapTotal - mi.swapFree),
          swap_pct: mi.swapTotal > 0 ? ((mi.swapTotal - mi.swapFree) / mi.swapTotal) * 100 : 0,
        }
      : null;
    const pressure = psiC || psiM || psiI ? { cpu: parsePressure(psiC), memory: parsePressure(psiM), io: parsePressure(psiI) } : null;
    const lo = parseLoadavg(load);
    const procs = procRows(parsePs(ps), sessionPids(db));
    samples.push(sampleOf(now, total, memory, lo?.one ?? null, pressure?.memory ?? null));
    return finish(now, "linux", "proc", total, cores, cur.cores.length, lo, memory, dk, io, pressure, procs);
  }

  // macOS fallback. UNTESTED: written from the sysctl, vm_stat and ps man pages, never run on a Mac.
  async function tickMac(now: number): Promise<Resources> {
    const [sc, vm, ps, dk] = await Promise.all([
      run(["sysctl", "-n", "hw.ncpu", "vm.loadavg", "hw.memsize", "vm.swapusage"]),
      run(["vm_stat"]),
      run(["ps", "-eo", "pid=,pcpu=,rss=,etime=,comm=,args=", "-r"]),
      disks(),
    ]);
    const lines = sc.trim().split("\n");
    const ncpu = Number(lines[0]) || 1;
    const la = (lines[1] ?? "").match(/[\d.]+/g)?.map(Number) ?? [];
    const load = la.length >= 3 ? { one: la[0], five: la[1], fifteen: la[2] } : null;
    const memBytes = Number(lines[2]) || 0;
    const swapM = (lines[3] ?? "").match(/total = ([\d.]+)M\s+used = ([\d.]+)M/);
    const pageSize = Number(vm.match(/page size of (\d+) bytes/)?.[1] ?? 4096);
    const pages = (k: string) => Number(vm.match(new RegExp(`Pages ${k}:\\s+(\\d+)`))?.[1] ?? 0);
    const availBytes = (pages("free") + pages("inactive")) * pageSize;
    const swapTotal = swapM ? Number(swapM[1]) : 0;
    const swapUsed = swapM ? Number(swapM[2]) : 0;
    const memory: Resources["memory"] = memBytes
      ? {
          total_mb: mb(memBytes / 1024),
          used_mb: mb((memBytes - availBytes) / 1024),
          available_mb: mb(availBytes / 1024),
          available_pct: (availBytes / memBytes) * 100,
          swap_total_mb: swapTotal,
          swap_used_mb: swapUsed,
          swap_pct: swapTotal > 0 ? (swapUsed / swapTotal) * 100 : 0,
        }
      : null;
    const rows = parsePs(ps);
    const total = Math.min(100, rows.reduce((a, r) => a + r.cpu, 0) / ncpu);
    const procs = procRows(rows, sessionPids(db));
    samples.push(sampleOf(now, total, memory, load?.one ?? null, null));
    return finish(now, "macos", "macos-fallback", total, [], ncpu, load, memory, dk, null, null, procs);
  }

  function sampleOf(t: number, cpu: number | null, m: Resources["memory"], load1: number | null, psi: number | null): Sample {
    return { t, cpu, mem: m ? 100 - m.available_pct : null, avail: m ? m.available_pct : null, swap: m ? m.swap_pct : null, load1, psi_mem: psi };
  }

  function finish(
    now: number,
    os: Resources["os"],
    source: Resources["source"],
    total: number | null,
    cores: (number | null)[],
    count: number,
    load: Resources["load"],
    memory: Resources["memory"],
    dk: Resources["disks"],
    io: Resources["io"],
    pressure: Resources["pressure"],
    procs: { top_cpu: ProcSample[]; top_rss: ProcSample[] },
  ): Resources {
    while (samples.length > MAX_SAMPLES) samples.shift();
    const { tone, reasons } = evaluateTone(samples, now, intervalMs);
    return { at: now, os, source, cpu: { total, cores, count }, load, memory, disks: dk, io, pressure, ...procs, series: buildSeries(samples), tone, reasons };
  }

  async function tick() {
    if (busy) return; // the last tick is still running: skip this one
    busy = true;
    try {
      const now = clock();
      latest = process.platform === "linux" || !isMac ? await tickLinux(now) : await tickMac(now);
    } catch {
      /* keep the last good sample */
    } finally {
      busy = false;
    }
  }

  void tick();
  const timer = setInterval(() => void tick(), intervalMs);
  return {
    latest: () => latest,
    stop() {
      clearInterval(timer);
    },
  };
}
