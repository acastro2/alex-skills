// TLS files for the page. 1Password does not handle passkeys on plain http://localhost, so the page serves
// HTTPS when a cert exists. The RP ID stays "localhost" on every host. `bin/harness-tls` makes the cert.
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

export interface TlsFiles {
  cert: string;
  key: string;
}

export function tlsDir(): string {
  return process.env.HARNESS_TLS_DIR || join(homedir(), ".config", "harness", "tls");
}

/** The cert and key paths, or null when either file is missing. */
export function tlsFiles(): TlsFiles | null {
  const dir = tlsDir();
  const cert = join(dir, "localhost.pem");
  const key = join(dir, "localhost-key.pem");
  return existsSync(cert) && existsSync(key) ? { cert, key } : null;
}
