// Entry for `harness serve`: bun src/serve/main.ts. The CLI (src/cli.ts) can call serve() instead.
import { startServer } from "./server.ts";
import { openDatabase } from "./db.ts";
import { tlsFiles } from "./tls.ts";
import { startJobs } from "../jobs/jobs.ts";
import { startSampler } from "./resources.ts";

export async function serve(): Promise<void> {
  const { db } = await openDatabase();
  const sampler = startSampler(db);
  const s = await startServer({ db, tls: tlsFiles(), sharedPasskey: true, resources: sampler.latest });
  // The jobs runner owns every schedule: prune, conflict watch (5 min), waker (2 min), and the env jobs.
  // HARNESS_NO_JOBS=1 starts the page only (tests, screenshots).
  const jobs = process.env.HARNESS_NO_JOBS ? null : startJobs(db);
  console.log(`harness page: ${s.url}  (127.0.0.1 only; open it as localhost so the passkey works)${jobs ? "; jobs running" : ""}`);
  const quit = () => {
    jobs?.stop();
    sampler.stop();
    s.stop();
    process.exit(0);
  };
  process.on("SIGINT", quit);
  process.on("SIGTERM", quit);
}

if (import.meta.main) {
  serve().catch((e) => {
    console.error(`harness serve: ${(e as Error).message}`);
    process.exit(1);
  });
}
