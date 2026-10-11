import { useState } from "react";
import { login, register } from "../api/client";

export default function AuthForm({ onAuthenticated }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const call = mode === "login" ? login : register;
      const res = await call(username, password);
      localStorage.setItem("sentinel_token", res.data.token);
      localStorage.setItem("sentinel_username", res.data.username);
      onAuthenticated(res.data.username);
    } catch (err) {
      const msg =
        err.response?.data?.error ||
        err.response?.data?.non_field_errors?.[0] ||
        "Something went wrong.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="h-screen flex items-center justify-center relative overflow-hidden">
      <div className="dot-field absolute inset-0 pointer-events-none" />

      <form
        onSubmit={handleSubmit}
        className="relative w-full max-w-sm bg-[var(--color-ink-raised)] border border-[var(--color-wire)] rounded p-8"
      >
        <h1 className="font-display font-semibold text-xl mb-1">Sentinel</h1>
        <p className="text-xs text-[var(--color-ash)] font-mono mb-6">
          {mode === "login" ? "sign in to continue" : "create an account"}
        </p>

        <label className="block text-xs font-mono text-[var(--color-ash)] mb-1.5">
          Username
        </label>
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          autoFocus
          className="w-full bg-[var(--color-ink)] border border-[var(--color-wire)] rounded px-3 py-2
                     font-mono text-sm text-[var(--color-paper)]
                     focus:border-[var(--color-signal)] outline-none transition-colors duration-200 mb-4"
        />

        <label className="block text-xs font-mono text-[var(--color-ash)] mb-1.5">
          Password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full bg-[var(--color-ink)] border border-[var(--color-wire)] rounded px-3 py-2
                     font-mono text-sm text-[var(--color-paper)]
                     focus:border-[var(--color-signal)] outline-none transition-colors duration-200 mb-2"
        />

        {error && (
          <p className="text-xs font-mono mb-4" style={{ color: "var(--color-fail)" }}>
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full mt-4 px-4 py-2 text-sm font-medium rounded bg-[var(--color-signal)] text-[var(--color-ink)]
                     cursor-pointer hover:opacity-90 active:scale-[0.98]
                     disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
        >
          {submitting ? "..." : mode === "login" ? "Sign in" : "Create account"}
        </button>

        <button
          type="button"
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError(null);
          }}
          className="w-full mt-3 text-xs font-mono text-[var(--color-ash)] hover:text-[var(--color-paper)]
                     cursor-pointer transition-colors duration-200"
        >
          {mode === "login" ? "need an account? register" : "have an account? sign in"}
        </button>
      </form>
    </div>
  );
}
