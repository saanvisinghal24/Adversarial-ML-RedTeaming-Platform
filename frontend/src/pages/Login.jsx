import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../store/auth";
import { Reveal } from "../components/primitives";

export default function Login() {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const signIn = useAuth((s) => s.signIn);
  const navigate = useNavigate();

  const isRegister = mode === "register";

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const tokens = isRegister
        ? await api.register(email, password)
        : await api.login(email, password);
      signIn(tokens, email);
      navigate("/models");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[1.15fr_1fr]">
      {/* Left: the statement. Right: the form. Deliberately uneven. */}
      <section className="flex flex-col justify-between border-rule px-6 py-12 lg:border-r lg:px-14 lg:py-16">
        <p className="t-label">Adversarial ML Red-Teaming Platform</p>

        <Reveal>
          <h1 className="t-display mt-10 lg:mt-0">
            Break
            <br />
            your model
            <br />
            first.
          </h1>
          <p className="mt-8 max-w-measure text-[17px] leading-relaxed text-muted">
            Upload a classifier, run evasion and poisoning attacks against it inside an isolated
            sandbox, and get back a robustness grade with every finding mapped to MITRE ATLAS,
            OWASP ML Top 10 and NIST AI RMF.
          </p>
        </Reveal>

        <dl className="mt-14 grid grid-cols-2 gap-x-8 gap-y-6 border-t border-rule pt-8 sm:grid-cols-4">
          {[
            ["FGSM", "White-box evasion"],
            ["PGD", "Iterative evasion"],
            ["HopSkipJump", "Black-box, budgeted"],
            ["Label-flip", "Training-set poisoning"],
          ].map(([name, what]) => (
            <div key={name}>
              <dt className="font-display text-[15px] font-semibold uppercase tracking-tight">
                {name}
              </dt>
              <dd className="mt-1 text-[13px] text-muted">{what}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="flex items-center px-6 py-16 lg:px-12">
        <div className="w-full max-w-sm">
          <h2 className="t-head">{isRegister ? "Create account" : "Sign in"}</h2>

          <form onSubmit={submit} className="mt-10 space-y-7">
            <div>
              <label htmlFor="email" className="t-label">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                className="field mt-2"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@university.edu"
              />
            </div>

            <div>
              <label htmlFor="password" className="t-label">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={isRegister ? 8 : 1}
                autoComplete={isRegister ? "new-password" : "current-password"}
                className="field mt-2"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={isRegister ? "At least 8 characters" : "••••••••"}
              />
            </div>

            {error ? (
              <p role="alert" className="border-l-2 border-signal pl-4 text-[14px] text-signal">
                {error}
              </p>
            ) : null}

            <button type="submit" className="btn btn-solid w-full" disabled={busy}>
              {busy ? "Working" : isRegister ? "Create account" : "Sign in"}
            </button>
          </form>

          <button
            type="button"
            className="mt-8 text-[14px] text-muted link-underline"
            onClick={() => {
              setMode(isRegister ? "login" : "register");
              setError(null);
            }}
          >
            {isRegister ? "Already have an account? Sign in" : "No account yet? Create one"}
          </button>
        </div>
      </section>
    </div>
  );
}
