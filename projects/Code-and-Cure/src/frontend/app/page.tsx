"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { API_BASE_URL, AuthChallengeResponse } from "@/lib/api";

export default function Home() {
  const { login, verifyLogin, register } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [role, setRole] = useState<"patient" | "doctor">("patient");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [pendingChallenge, setPendingChallenge] = useState<AuthChallengeResponse | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const authStep = pendingChallenge?.status === "verification_required"
    ? "verify_email"
    : pendingChallenge?.status === "mfa_required"
      ? "verify_login"
      : "form";

  const resetPending = () => {
    setPendingChallenge(null);
    setVerificationCode("");
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setLoading(true);
    try {
      const challenge = await login(email, password);
      setPendingChallenge(challenge);
      setVerificationCode("");
      setNotice(challenge.message);
      setLoading(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setLoading(true);
    try {
      const challenge = await register(email, password, fullName, role);
      setPendingChallenge(challenge);
      setVerificationCode("");
      setNotice(challenge.message);
      setLoading(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Sign up failed");
      setLoading(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pendingChallenge) return;
    setError(null);
    setNotice(null);
    setLoading(true);
    try {
      if (pendingChallenge.status === "verification_required") {
        const res = await fetch(`${API_BASE_URL}/api/v1/auth/verify-email`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            email: pendingChallenge.email,
            code: verificationCode,
            challenge_id: pendingChallenge.challenge_id,
          }),
        });
        const data = await res.json().catch(() => ({ message: "Verification failed" }));
        if (!res.ok) throw new Error(data.detail || data.message || "Verification failed");
        setMode("login");
        resetPending();
        setPassword("");
        setNotice(data.message || "Email verified. Sign in to continue.");
      } else {
        await verifyLogin(pendingChallenge.email, verificationCode, pendingChallenge.challenge_id);
      }
      setLoading(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Verification failed");
      setLoading(false);
    }
  };

  const handleResendVerification = async () => {
    if (!pendingChallenge?.email) return;
    setError(null);
    setNotice(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/auth/resend-verification`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email: pendingChallenge.email }),
      });
      const data = await res.json().catch(() => ({ message: "Unable to resend code" }));
      if (!res.ok) throw new Error(data.detail || data.message || "Unable to resend code");
      setPendingChallenge(data);
      setVerificationCode("");
      setNotice(data.message);
      setLoading(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unable to resend code");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background hero-gradient overflow-x-hidden">
      {/* ── Top Nav ───────────────────────────────────────────────────────── */}
      <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between max-w-screen-2xl mx-auto rounded-xl m-4 px-6 py-3 glass-panel border border-white/20 shadow-[0_8px_32px_rgba(0,77,64,0.1)]">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>
            health_and_safety
          </span>
          <span className="text-xl font-extrabold tracking-tight text-primary">careIT</span>
        </div>
        <nav className="hidden md:flex items-center gap-1">
          <a className="text-primary font-semibold text-sm px-3 py-1.5 rounded-lg bg-primary-fixed/40">Home</a>
          <a
            onClick={() => document.getElementById("portal")?.scrollIntoView({ behavior: "smooth" })}
            className="text-on-surface-variant text-sm px-3 py-1.5 rounded-lg hover:bg-white/40 transition-all cursor-pointer"
          >
            Services
          </a>
          <a
            onClick={() => document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" })}
            className="text-on-surface-variant text-sm px-3 py-1.5 rounded-lg hover:bg-white/40 transition-all cursor-pointer"
          >
            Providers
          </a>
        </nav>
        <button
          onClick={() => document.getElementById("portal")?.scrollIntoView({ behavior: "smooth" })}
          className="px-4 py-2 bg-primary text-on-primary rounded-xl text-sm font-bold hover:scale-[1.02] active:scale-95 transition-all shadow-md"
        >
          Get Started
        </button>
      </header>

      <main className="pt-32">
        {/* ── Hero ─────────────────────────────────────────────────────────── */}
        <section className="max-w-7xl mx-auto px-margin mb-xl">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter items-center">
            {/* Left: Text */}
            <div className="lg:col-span-5 space-y-md">
              <span className="inline-block px-4 py-1.5 rounded-full bg-secondary-fixed text-on-secondary-container font-bold text-caption uppercase tracking-wider">
                Precision Care
              </span>
              <h2 className="text-display-xl text-primary leading-tight">
                Your Health,<br />Guided by Intelligence.
              </h2>
              <p className="text-body-lg text-on-surface-variant max-w-lg">
                Seamlessly connect with top medical practitioners through AI-driven matching. Experience healthcare that's as precise as it is human.
              </p>
              <div className="flex flex-wrap gap-md pt-sm">
                <button
                  onClick={() => document.getElementById("portal")?.scrollIntoView({ behavior: "smooth" })}
                  className="px-lg py-md bg-primary text-on-primary rounded-xl font-bold shadow-lg hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-sm"
                >
                  Find a Specialist
                  <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                </button>
                <button
                  onClick={() => document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" })}
                  className="px-lg py-md border-2 border-primary/10 bg-white/40 backdrop-blur-sm text-primary rounded-xl font-bold hover:bg-white/60 active:scale-95 transition-all"
                >
                  How it Works
                </button>
              </div>
            </div>

            {/* Right: Bento grid */}
            <div className="lg:col-span-7 grid grid-cols-6 grid-rows-6 gap-sm h-[520px]">
              {/* Main visual card */}
              <div className="col-span-4 row-span-4 rounded-3xl glass-panel border border-white/20 shadow-xl relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-primary-fixed/60 via-secondary-fixed/30 to-primary/50" />
                <div className="absolute inset-0 flex items-center justify-center opacity-20">
                  <span className="material-symbols-outlined text-primary" style={{ fontSize: "220px", fontVariationSettings: "'FILL' 1" }}>
                    health_and_safety
                  </span>
                </div>
                <div className="absolute bottom-md left-md text-white">
                  <p className="font-semibold text-sm opacity-80 mb-1">Connected Network</p>
                  <h3 className="text-headline-md font-bold text-white">5,000+ Specialists</h3>
                </div>
              </div>
              {/* AI card */}
              <div className="col-span-2 row-span-3 rounded-3xl bg-secondary-fixed p-md flex flex-col justify-between shadow-lg">
                <span className="material-symbols-outlined text-on-secondary-container text-4xl">neurology</span>
                <h4 className="text-headline-md text-on-secondary-container leading-tight">AI Diagnostic Matching</h4>
              </div>
              {/* Safe card */}
              <div className="col-span-2 row-span-3 rounded-3xl bg-primary-fixed p-md flex flex-col justify-between shadow-lg">
                <span
                  className="material-symbols-outlined text-primary text-4xl"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  verified_user
                </span>
                <h4 className="text-headline-md text-primary leading-tight">Certified Safe</h4>
              </div>
              {/* Trust banner */}
              <div className="col-span-4 row-span-2 rounded-3xl glass-panel border border-white/20 p-md flex items-center gap-md shadow-md">
                <div className="flex -space-x-3">
                  {(["#afefdd", "#94d3c1", "#004d40"] as const).map((bg, i) => (
                    <div
                      key={i}
                      className="w-10 h-10 rounded-full border-2 border-white flex items-center justify-center text-xs font-bold"
                      style={{ backgroundColor: bg, color: i === 2 ? "#fff" : "#00342b" }}
                    >
                      {i === 2 ? "+12k" : ""}
                    </div>
                  ))}
                </div>
                <div>
                  <p className="text-headline-md text-primary font-bold">Trust is everything</p>
                  <p className="text-body-md text-on-surface-variant text-sm">Joined this month</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── How it Works ─────────────────────────────────────────────────── */}
        <section id="how-it-works" className="max-w-6xl mx-auto px-margin py-xl mb-xl">
          <div className="text-center mb-xl">
            <span className="inline-block px-4 py-1.5 rounded-full bg-primary-fixed text-primary font-bold text-caption uppercase tracking-wider mb-md">
              How it Works
            </span>
            <h3 className="text-display-sm text-primary font-bold">From Symptom to Specialist in 3 Steps</h3>
            <p className="text-body-lg text-on-surface-variant mt-sm max-w-xl mx-auto">
              careIT removes the guesswork from healthcare. Here's how we get you to the right doctor, fast.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter">
            {[
              {
                step: "01",
                icon: "smart_toy",
                title: "Describe Your Symptoms",
                desc: "Chat with our AI Care Navigator. Describe how you're feeling in plain language — it identifies the right specialist category for your concern in seconds.",
                color: "bg-primary-fixed",
                iconColor: "text-primary",
              },
              {
                step: "02",
                icon: "search",
                title: "Browse Matched Specialists",
                desc: "See a curated list of verified doctors filtered to exactly the specialty you need. View ratings, locations, and real-time availability at a glance.",
                color: "bg-secondary-fixed",
                iconColor: "text-on-secondary-container",
              },
              {
                step: "03",
                icon: "calendar_month",
                title: "Book in Seconds",
                desc: "Pick a time slot, fill in a quick pre-visit form, and confirm. Your doctor receives your intake details before you even arrive.",
                color: "bg-tertiary-fixed",
                iconColor: "text-tertiary",
              },
            ].map(({ step, icon, title, desc, color, iconColor }) => (
              <div
                key={step}
                className="glass-card rounded-3xl p-xl shadow-md border border-white/20 flex flex-col items-center text-center relative overflow-hidden"
              >
                <div className="absolute top-4 right-5 text-[64px] font-black text-primary/5 leading-none select-none">
                  {step}
                </div>
                <div className={`w-14 h-14 rounded-2xl ${color} flex items-center justify-center mb-md shadow-sm`}>
                  <span
                    className={`material-symbols-outlined ${iconColor} text-3xl`}
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    {icon}
                  </span>
                </div>
                <h4 className="text-headline-md text-primary font-bold mb-sm">{title}</h4>
                <p className="text-body-md text-on-surface-variant">{desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Portal Section ───────────────────────────────────────────────── */}
        <section id="portal" className="bg-white/40 backdrop-blur-xl border-y border-white/20 py-xl">
          <div className="max-w-6xl mx-auto px-margin grid grid-cols-1 md:grid-cols-2 gap-xl items-center">
            {/* Left: Features */}
            <div className="space-y-lg">
              <h3 className="text-headline-lg text-primary">Access Your Care Portal</h3>
              <p className="text-body-lg text-on-surface-variant">
                Whether you're a patient or a provider, our portal provides the tools you need for seamless health management.
              </p>
              <div className="space-y-md">
                {[
                  { icon: "calendar_month", bg: "bg-primary-fixed", iconColor: "text-primary", title: "Instant Booking", desc: "Schedule consultations in under 60 seconds." },
                  { icon: "lab_profile",   bg: "bg-secondary-fixed", iconColor: "text-on-secondary-container", title: "Unified Records",  desc: "All your medical history in one secure digital vault." },
                  { icon: "smart_toy",     bg: "bg-tertiary-fixed",  iconColor: "text-tertiary", title: "AI Care Navigator", desc: "Describe symptoms and get matched to the right specialist instantly." },
                ].map(({ icon, bg, iconColor, title, desc }) => (
                  <div key={title} className="flex items-start gap-md p-md rounded-2xl bg-white shadow-sm border border-outline-variant/30">
                    <div className={`p-2 ${bg} rounded-lg shrink-0`}>
                      <span className={`material-symbols-outlined ${iconColor}`}>{icon}</span>
                    </div>
                    <div>
                      <h5 className="font-semibold text-body-lg">{title}</h5>
                      <p className="text-body-md text-on-surface-variant">{desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right: Login card */}
            <div className="glass-panel p-xl rounded-[32px] border border-white shadow-2xl relative overflow-hidden">
              <div className="absolute -top-24 -right-24 w-48 h-48 bg-primary-fixed blur-[100px] rounded-full opacity-60 pointer-events-none" />
              <div className="relative z-10">
                <div className="mb-lg">
                  <h4 className="text-headline-lg text-primary">Portal Login</h4>
                  <p className="text-body-md text-on-surface-variant mt-1">Sign in or create an account.</p>
                </div>

                <div className="mb-md flex gap-sm rounded-xl bg-white/70 p-1">
                  <button
                    type="button"
                    onClick={() => setMode("login")}
                    className={`flex-1 rounded-lg px-4 py-2 text-sm font-semibold transition-all ${
                      mode === "login" ? "bg-primary text-on-primary" : "text-primary"
                    }`}
                  >
                    Sign In
                  </button>
                  <button
                    type="button"
                    onClick={() => setMode("signup")}
                    className={`flex-1 rounded-lg px-4 py-2 text-sm font-semibold transition-all ${
                      mode === "signup" ? "bg-primary text-on-primary" : "text-primary"
                    }`}
                  >
                    Sign Up
                  </button>
                </div>

                <div className="mb-md">
                  <h5 className="text-headline-md text-primary">
                    {authStep === "verify_email"
                      ? "Verify Your Email"
                      : authStep === "verify_login"
                        ? "Confirm Sign In"
                        : mode === "login"
                          ? "Account Sign In"
                          : "Create Account"}
                  </h5>
                  <p className="text-sm text-on-surface-variant">
                    {authStep === "verify_email"
                      ? "Enter the 6-digit code sent to your inbox."
                      : authStep === "verify_login"
                        ? "Enter the one-time sign-in code to finish authentication."
                        : mode === "login"
                          ? "Access your portal"
                          : "New accounts are stored in Supabase users."}
                  </p>
                </div>

                <form
                  onSubmit={
                    authStep === "verify_email" || authStep === "verify_login"
                      ? handleVerify
                      : mode === "login"
                        ? handleLogin
                        : handleRegister
                  }
                  className="space-y-md"
                >
                  {authStep === "form" && mode === "signup" && (
                    <>
                      <div>
                        <label className="block text-label-md text-on-surface mb-xs">Full Name</label>
                        <input
                          type="text"
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          placeholder="Jane Doe"
                          required
                          className="w-full px-md py-3 rounded-xl bg-white border border-outline-variant focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all text-body-md"
                        />
                      </div>
                      <div>
                        <label className="block text-label-md text-on-surface mb-xs">Role</label>
                        <div className="grid grid-cols-2 gap-sm">
                          <button
                            type="button"
                            onClick={() => setRole("patient")}
                            className={`rounded-xl border px-4 py-3 text-sm font-semibold transition-all ${
                              role === "patient"
                                ? "border-primary bg-primary text-on-primary"
                                : "border-outline-variant bg-white text-primary"
                            }`}
                          >
                            Patient
                          </button>
                          <button
                            type="button"
                            onClick={() => setRole("doctor")}
                            className={`rounded-xl border px-4 py-3 text-sm font-semibold transition-all ${
                              role === "doctor"
                                ? "border-primary bg-primary text-on-primary"
                                : "border-outline-variant bg-white text-primary"
                            }`}
                          >
                            Doctor
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                  {authStep === "form" ? (
                    <>
                      <div>
                        <label className="block text-label-md text-on-surface mb-xs">Email Address</label>
                        <input
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder="name@example.com"
                          required
                          className="w-full px-md py-3 rounded-xl bg-white border border-outline-variant focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all text-body-md"
                        />
                      </div>
                      <div>
                        <label className="block text-label-md text-on-surface mb-xs">Password</label>
                        <input
                          type="password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          placeholder="••••••••"
                          required
                          className="w-full px-md py-3 rounded-xl bg-white border border-outline-variant focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all text-body-md"
                        />
                      </div>
                    </>
                  ) : (
                    <>
                      <div>
                        <label className="block text-label-md text-on-surface mb-xs">Email Address</label>
                        <input
                          type="email"
                          value={pendingChallenge?.email || email}
                          disabled
                          className="w-full px-md py-3 rounded-xl bg-surface-container-low border border-outline-variant text-body-md text-on-surface-variant"
                        />
                      </div>
                      <div>
                        <label className="block text-label-md text-on-surface mb-xs">Verification Code</label>
                        <input
                          type="text"
                          inputMode="numeric"
                          pattern="[0-9]{6}"
                          value={verificationCode}
                          onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                          placeholder="123456"
                          required
                          className="w-full px-md py-3 rounded-xl bg-white border border-outline-variant focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all text-body-md tracking-[0.3em]"
                        />
                      </div>
                    </>
                  )}
                  {notice && (
                    <p className="text-primary text-sm bg-primary-fixed rounded-xl px-4 py-3">{notice}</p>
                  )}
                  {error && (
                    <p className="text-error text-sm bg-error-container rounded-xl px-4 py-3">{error}</p>
                  )}
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-3 bg-primary text-on-primary rounded-xl font-bold text-label-md hover:scale-[1.01] active:scale-[0.98] transition-all shadow-md disabled:opacity-50"
                  >
                    {loading
                      ? authStep === "verify_email"
                        ? "Verifying…"
                        : authStep === "verify_login"
                          ? "Finishing sign in…"
                          : mode === "login"
                            ? "Signing in…"
                            : "Creating account…"
                      : authStep === "verify_email"
                        ? "Verify Email"
                        : authStep === "verify_login"
                          ? "Finish Sign In"
                          : mode === "login"
                            ? "Sign In"
                            : "Create Account"}
                  </button>
                  {authStep === "verify_email" && (
                    <div className="flex gap-sm">
                      <button
                        type="button"
                        onClick={handleResendVerification}
                        disabled={loading}
                        className="flex-1 py-3 border border-outline-variant rounded-xl font-semibold text-primary bg-white/60 disabled:opacity-50"
                      >
                        Resend Code
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          resetPending();
                          setNotice(null);
                          setError(null);
                        }}
                        disabled={loading}
                        className="flex-1 py-3 border border-outline-variant rounded-xl font-semibold text-on-surface bg-white/60 disabled:opacity-50"
                      >
                        Start Over
                      </button>
                    </div>
                  )}
                </form>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="bg-white/40 border-t border-white/20 py-lg">
        <div className="max-w-7xl mx-auto px-margin flex flex-col md:flex-row justify-between items-center gap-md">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>
              health_and_safety
            </span>
            <span className="text-lg font-black text-primary">careIT</span>
          </div>
          <div className="flex gap-lg">
            {["Privacy Policy", "Terms of Service", "Contact Support"].map((l) => (
              <a key={l} className="text-on-surface-variant hover:text-primary transition-colors text-sm font-semibold">{l}</a>
            ))}
          </div>
          <p className="text-caption text-outline">© 2026 careIT Healthcare Technologies.</p>
        </div>
      </footer>
    </div>
  );
}
