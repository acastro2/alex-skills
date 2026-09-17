# m365 CLI — command reference

Read-only. Every command is a `GET` or a read-only `POST /search/query`. There is no write
verb in the surface.

## JSON policy

`--json` on any command returns exactly one object on stdout.

**Success** — HTTP 200, `ok: true`, payload under `data`:

```json
{ "ok": true, "data": { "messages": [ { "id": "...", "subject": "...", "from": "a@b.c",
  "received": "2026-09-16T19:47:25Z", "preview": "...", "unread": false, "webLink": "..." } ] } }
```

**Failure** — exit code 1, `ok: false`, machine-readable error, never a credential:

```json
{ "ok": false, "error": { "code": "ErrorAccessDenied", "message": "Access is denied." } }
```

`code` is Microsoft's Graph error code when Graph supplied one, otherwise `http_<status>`,
`no_token`, `refresh_failed`, or `login_failed`. Without `--json`, errors go to stderr as
`error: <code>: <message>` and successes print the raw payload indented.

The payload is a **trimmed envelope, not a Graph pass-through**: ids, subjects, senders,
dates and short previews. Fields the verbs drop are reachable with `request`.

## Commands

| Command | Graph call | Returns |
|---|---|---|
| `doctor [--json]` | `/me`, then one probe per surface | auth state, cache path, per-surface `ok` / `fail:<code>` |
| `whoami` | `/me` | displayName, userPrincipalName |
| `login` | authorize + token | caches a refresh token |
| `logout` | — | deletes the cache |
| `mail search [query] [--sender S] [--after ISO] [--limit N]` | `/me/messages` | `messages[]` trimmed |
| `mail read <id> [--max-chars N]` | `/me/messages/{id}` | full `body`, recipients, `webLink` |
| `calendar search [--after ISO] [--before ISO] [--limit N]` | `/me/events` | `events[]` trimmed, `online` flag |
| `teams chats [--limit N]` | `/me/chats` | `chats[]` |
| `teams messages <chat-id> [--limit N] [--max-chars N]` | `/me/chats/{id}/messages` | `messages[]` with sender and text |
| `teams search <query> [--limit N]` | `POST /search/query` `chatMessage` | `hits[]` |
| `sharepoint search <query> [--sites] [--limit N]` | `/sites?search=` or `POST /search/query` `driveItem` | `sites[]` or `documents[]` |
| `sharepoint read <url> [--drive ID]` | `/shares/u!<b64>` or `/drives/{d}/items/{i}` | name, size, webUrl, downloadUrl, lastModified |
| `request GET <path> [--param k=v]` | any read endpoint | `response` |

Defaults: `--limit` 20 (messages, events, documents, sites), 25 (chats, hits), 50 (chat
messages). Nothing pages automatically; if a result set looks truncated, raise `--limit`.

`--after` / `--before` take ISO 8601 (`2026-09-01` or `2026-09-01T00:00:00Z`).

`mail search` accepts a query **or** `--sender` **or** `--after`. Graph rejects combining
`$search` with `$filter`; the CLI drops the query when you pass `--after`, so pass one axis
at a time.

## Auth

Authorization code + PKCE, loopback redirect, public client, **no secret**. Refresh token at
`~/.m365-readonly/token.json`, mode `0600`, overridable with `M365_CACHE`.

Scopes requested: `User.Read`, `Mail.Read`, `Calendars.Read`, `Chat.Read`,
`ChannelMessage.Read.All`, `Team.ReadBasic.All`, `TeamMember.Read.All`,
`Channel.ReadBasic.All`, `Sites.Read.All`, `OnlineMeetings.Read`, `offline_access`.

The access token AAD issues for this client also carries the client's pre-existing
tenant-wide scope set. The CLI never uses those — the surface has no write verb — but a
future reader should know the credential is broader than the interface.

## Verification

Proven live 2026-09-17 with real data, not fixtures:

- `doctor` — `auth: ok`, all four surfaces `ok`
- `mail search "SOW"` — rows returned with sender and preview
- `calendar search --after 2026-09-01` — events with organiser and start time
- `teams chats` / `teams search` — chats listed, message search returned hits
- `sharepoint search` — tenant-wide site and document search

Unit tests cover the two boundaries — network and token cache — in `scripts/tests.py`:

```bash
cd scripts && python3 -m unittest tests
```

## Known gaps

- **Meeting transcripts** — need `OnlineMeetingTranscript.Read.All`, which requires admin
  consent the tenant has not granted. Not reachable from this CLI.
- **Files content** — `sharepoint read` returns metadata and a `downloadUrl`, not the file's
  bytes.
- **Channels** — `teams messages` reads chats. Channel message reading is reachable with
  `request GET /teams/{id}/channels/{id}/messages`, not yet a verb.
