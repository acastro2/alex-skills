import type { Database } from "bun:sqlite"
import { recompute } from "../proof/bundle.ts"

export interface Integrity {
  ok: boolean
  unmatchedTokens: string[]
  tamperedBundles: string[]
}

// What verifyChain cannot see: a tokens or bundles row written without its journal row (D70).
export function integrity(db: Database): Integrity {
  const unmatchedTokens = (
    db
      .query(
        `select t.id from tokens t
         where not exists (
           select 1 from journal j
           where j.seq = t.grant_seq and j.event = 'grant' and json_extract(j.data_json, '$.token_id') = t.id
         )
         order by t.id`,
      )
      .all() as { id: string }[]
  ).map((r) => r.id)
  const tamperedBundles = (db.query("select id from bundles order by id").all() as { id: string }[])
    .map((r) => r.id)
    .filter((id) => !recompute(db, id))
  return { ok: unmatchedTokens.length === 0 && tamperedBundles.length === 0, unmatchedTokens, tamperedBundles }
}
