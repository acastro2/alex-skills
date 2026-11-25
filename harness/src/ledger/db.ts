import { Database } from "bun:sqlite"
import { mkdirSync, readdirSync, readFileSync } from "node:fs"
import { homedir } from "node:os"
import { dirname, join } from "node:path"

const MIGRATIONS = join(import.meta.dir, "migrations")

function defaultPath(): string {
  const dir = process.env.HARNESS_STATE_DIR ?? join(homedir(), ".local", "state", "harness")
  return join(dir, "ledger.db")
}

export function getMeta(db: Database, key: string): string | null {
  const r = db.query("select value from schema_meta where key = ?").get(key) as { value: string } | null
  return r ? r.value : null
}

export function setMeta(db: Database, key: string, value: string): void {
  db.query("insert into schema_meta(key, value) values(?, ?) on conflict(key) do update set value = excluded.value").run(
    key,
    value,
  )
}

function currentVersion(db: Database): number {
  const t = db.query("select 1 from sqlite_master where type = 'table' and name = 'schema_meta'").get()
  return t ? Number(getMeta(db, "schema_version") ?? 0) : 0
}

// Forward-only: each file NNN_name.sql runs once, in numeric order. One writer at a time.
function migrate(db: Database): void {
  const files = readdirSync(MIGRATIONS)
    .filter((f) => /^\d+_.+\.sql$/.test(f))
    .sort((a, b) => parseInt(a, 10) - parseInt(b, 10))
  db.transaction(() => {
    let version = currentVersion(db)
    for (const f of files) {
      const n = parseInt(f, 10)
      if (n <= version) continue
      db.exec(readFileSync(join(MIGRATIONS, f), "utf8"))
      setMeta(db, "schema_version", String(n))
      version = n
    }
  }).immediate()
}

export function openLedger(path?: string): Database {
  const file = path ?? defaultPath()
  mkdirSync(dirname(file), { recursive: true })
  const db = new Database(file, { create: true })
  db.exec("PRAGMA busy_timeout = 5000")
  // auto_vacuum only takes effect on a new file, before the first table. D87 needs it for incremental_vacuum.
  db.exec("PRAGMA auto_vacuum = INCREMENTAL")
  db.exec("PRAGMA journal_mode = WAL")
  db.exec("PRAGMA foreign_keys = ON")
  migrate(db)
  return db
}
