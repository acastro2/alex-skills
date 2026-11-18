import { useState } from "react";

export function Signup({ onDone }: { onDone: () => void }) {
  const [email, setEmail] = useState("");
  return (
    <form onSubmit={(e) => { e.preventDefault(); onDone(); }}>
      <img src="/logo.png" />
      <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
      <button type="button" onClick={() => setEmail("")}>
        <svg width="16" height="16"><path d="M2 2 L14 14 M14 2 L2 14" /></svg>
      </button>
      <div onClick={() => (window.location.href = "/terms")}>Read the terms</div>
      <button type="submit">Sign up</button>
    </form>
  );
}
