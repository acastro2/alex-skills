// Opens the ledger. Prefers openLedger() from src/ledger/db.ts (another lane writes it); until that file exists,
// opens HARNESS_STATE_DIR/ledger.db by path. The fallback never creates the file.
import { Database } from "bun:sqlite";
import { homedir } from "node:os";
import { join } from "node:path";

const LEDGER_URL = new URL("../ledger/db.ts", import.meta.url);

export function stateDir(): string {
  return process.env.HARNESS_STATE_DIR ?? join(homedir(), ".local", "state", "harness");
}

export interface OpenedLedger {
  db: Database;
  source: "openLedger" | "file";
  path: string | null;
}

export async function openDatabase(): Promise<OpenedLedger> {
  if (await Bun.file(LEDGER_URL).exists()) {
    const mod = (await import(LEDGER_URL.href)) as { openLedger?: () => unknown };
    if (typeof mod.openLedger === "function") {
      const opened = (await mod.openLedger()) as Database | { db: Database };
      const db = opened instanceof Database ? opened : (opened as { db: Database }).db;
      return { db, source: "openLedger", path: null };
    }
  }
  const path = join(stateDir(), "ledger.db");
  if (!(await Bun.file(path).exists())) throw new Error(`No ledger at ${path}`);
  const db = new Database(path, { readwrite: true });
  db.exec("PRAGMA busy_timeout = 5000;");
  return { db, source: "file", path };
}
