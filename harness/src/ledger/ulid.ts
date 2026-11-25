const ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ" // Crockford base32

let lastTime = -1
let lastRandom: number[] = []

function encodeTime(ms: number): string {
  let out = ""
  for (let i = 0; i < 10; i++) {
    out = ALPHABET[ms % 32] + out
    ms = Math.floor(ms / 32)
  }
  return out
}

// Same millisecond: add one to the last random part, so ids sort in call order.
export function ulid(now: number = Date.now()): string {
  if (now === lastTime) {
    let i = 15
    while (i >= 0 && ++lastRandom[i] === 32) lastRandom[i--] = 0
  } else {
    lastTime = now
    lastRandom = Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) => b & 31)
  }
  return encodeTime(now) + lastRandom.map((d) => ALPHABET[d]).join("")
}
