"use client";

import { useAuth as useClerkAuth, useClerk, useSignIn, useSignUp } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { api, clearStoredToken, setStoredToken } from "@/lib/api";

type Mode = "login" | "signup";
type Role = "patient" | "doctor";
type AuthView = "patient" | "doctor";
const DEMO_AUTH_ENABLED = process.env.NEXT_PUBLIC_ENABLE_DEMO_AUTH !== "false";

export default function AuthPortal() {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return (
      <div className="space-y-md">
        {DEMO_AUTH_ENABLED ? <DemoAccessPanel /> : null}
        <div className="rounded-3xl border border-error/20 bg-error-container p-xl text-error shadow-xl">
          <h4 className="text-headline-md font-bold">Clerk authentication setup required</h4>
          <p className="mt-sm text-sm">
            Set `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` in the frontend and the matching Clerk backend variables on the API.
            Demo login remains available so reviewers can still test the patient and doctor flow.
          </p>
        </div>
      </div>
    );
  }

  return <ConfiguredAuthPortal />;
}

function ConfiguredAuthPortal() {
  const router = useRouter();
  const { getToken, isLoaded: authLoaded, isSignedIn } = useClerkAuth();
  const { setActive, signOut } = useClerk();
  const { isLoaded: signInLoaded, signIn } = useSignIn();
  const { isLoaded: signUpLoaded, signUp } = useSignUp();
  const portalRef = useRef<HTMLDivElement | null>(null);

  const [authView, setAuthView] = useState<AuthView>("patient");
  const [mode, setMode] = useState<Mode>("login");
  const [role, setRole] = useState<Role>("patient");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [verificationCode, setVerificationCode] = useState("");
  const [pendingVerification, setPendingVerification] = useState(false);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [redirecting, setRedirecting] = useState(false);
  const [sessionValidated, setSessionValidated] = useState(false);
  const [sessionChecking, setSessionChecking] = useState(false);

  const clerkReady = authLoaded && signInLoaded && signUpLoaded;
  const authStepTitle = useMemo(() => {
    if (pendingVerification) return "Verify Your Email";
    return mode === "login" ? `${authView === "doctor" ? "Doctor" : "Patient"} Sign In` : `Create ${authView === "doctor" ? "Doctor" : "Patient"} Account`;
  }, [authView, mode, pendingVerification]);

  useEffect(() => {
    setRole(authView);
    setPendingVerification(false);
    setVerificationCode("");
    setNotice(null);
    setError(null);
  }, [authView, mode]);

  const ensureApiToken = async () => {
    const template = process.env.NEXT_PUBLIC_CLERK_TOKEN_TEMPLATE?.trim();
    let token: string | null = null;

    if (template) {
      try {
        token = await getToken({ template });
      } catch {
        token = null;
      }
    }

    if (!token) {
      token = await getToken();
    }

    const normalized = token?.trim() || null;
    setStoredToken(normalized);
    return normalized;
  };

  const redirectByRole = async () => {
    setRedirecting(true);
    await ensureApiToken();
    const session = await api.auth.syncSession();
    if (session.role !== authView) {
      clearStoredToken();
      await signOut();
      throw new Error(
        `This account is registered as a ${session.role}. Use the ${session.role === "doctor" ? "Doctor" : "Patient"} sign-in panel instead.`
      );
    }
    router.push(session.role === "doctor" ? "/doctor/dashboard" : "/patient/dashboard", { scroll: false });
  };

  const captureScrollY = () => window.scrollY;
  const restoreScrollY = (scrollY: number) => {
    window.requestAnimationFrame(() => {
      window.scrollTo({ top: scrollY });
      portalRef.current?.scrollIntoView({ block: "nearest" });
    });
  };

  const readAuthError = (err: unknown, fallback: string) => {
    if (err && typeof err === "object") {
      const clerkError = err as {
        errors?: Array<{ code?: string; longMessage?: string; message?: string }>;
        message?: string;
      };
      const first = clerkError.errors?.[0];
      if (first?.code === "session_exists") {
        return "You are already signed in. Continue to your portal or sign out to use a different account.";
      }
      if (typeof first?.longMessage === "string" && first.longMessage.trim()) return first.longMessage;
      if (typeof first?.message === "string" && first.message.trim()) return first.message;
      if (typeof clerkError.message === "string" && clerkError.message.trim()) return clerkError.message;
    }
    return err instanceof Error ? err.message : fallback;
  };

  useEffect(() => {
    if (!authLoaded) return;

    if (!isSignedIn) {
      setSessionValidated(false);
      setSessionChecking(false);
      clearStoredToken();
      return;
    }

    let cancelled = false;
    setSessionChecking(true);

    ensureApiToken()
      .then((token) => {
        if (!token) {
          throw new Error("Authentication token unavailable.");
        }
        return api.auth.me();
      })
      .then(() => {
        if (!cancelled) {
          setSessionValidated(true);
          setError(null);
        }
      })
      .catch(async () => {
        if (cancelled) return;
        setSessionValidated(false);
        clearStoredToken();
        try {
          await signOut();
        } catch {
          // Best effort cleanup of stale Clerk cookies.
        }
      })
      .finally(() => {
        if (!cancelled) {
          setSessionChecking(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [authLoaded, getToken, isSignedIn, signOut]);

  const handleUseDifferentAccount = async () => {
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      await signOut();
      setPendingVerification(false);
      setVerificationCode("");
      setPassword("");
    } catch (err: unknown) {
      setError(readAuthError(err, "Unable to sign out."));
    } finally {
      setRedirecting(false);
      setLoading(false);
    }
  };

  const handleContinueToPortal = async () => {
    setError(null);
    try {
      await redirectByRole();
    } catch (err: unknown) {
      setRedirecting(false);
      setError(readAuthError(err, "Unable to load your portal."));
    }
  };

  const handleLogin = async (event: FormEvent) => {
    event.preventDefault();
    if (!clerkReady || !signIn) return;
    const scrollY = captureScrollY();
    setError(null);
    setNotice(null);
    setLoading(true);

    try {
      const result = await signIn.create({
        identifier: email.trim(),
        password,
      });

      if (result.status !== "complete" || !result.createdSessionId) {
        throw new Error("Sign-in could not be completed. Check your credentials and Clerk setup.");
      }

      await setActive({ session: result.createdSessionId });
      await redirectByRole();
    } catch (err: unknown) {
      restoreScrollY(scrollY);
      setError(readAuthError(err, "Sign-in failed."));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (event: FormEvent) => {
    event.preventDefault();
    if (!clerkReady || !signUp) return;
    const scrollY = captureScrollY();
    setError(null);
    setNotice(null);
    setLoading(true);

    try {
      const [firstName, ...rest] = fullName.trim().split(/\s+/);
      const lastName = rest.join(" ");
      await signUp.create({
        emailAddress: email.trim(),
        password,
        firstName: firstName || undefined,
        lastName: lastName || undefined,
        unsafeMetadata: { role },
      });
      await signUp.prepareEmailAddressVerification({ strategy: "email_code" });
      setPendingVerification(true);
      setNotice("Verification code sent. Enter the 6-digit code to finish account creation.");
    } catch (err: unknown) {
      restoreScrollY(scrollY);
      setError(readAuthError(err, "Sign-up failed."));
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (event: FormEvent) => {
    event.preventDefault();
    if (!clerkReady || !signUp) return;
    const scrollY = captureScrollY();
    setError(null);
    setNotice(null);
    setLoading(true);

    try {
      const result = await signUp.attemptEmailAddressVerification({
        code: verificationCode.trim(),
      });

      if (result.status !== "complete" || !result.createdSessionId) {
        throw new Error("Verification did not complete. Try the code again.");
      }

      await setActive({ session: result.createdSessionId });
      await redirectByRole();
    } catch (err: unknown) {
      restoreScrollY(scrollY);
      setError(readAuthError(err, "Verification failed."));
    } finally {
      setLoading(false);
    }
  };

  const handleStartOver = () => {
    setPendingVerification(false);
    setVerificationCode("");
    setPassword("");
    setNotice(null);
    setError(null);
  };

  if (authLoaded && isSignedIn && sessionValidated && !pendingVerification) {
    return (
      <div className="rounded-[32px] border border-white bg-white/85 p-xl shadow-2xl">
        <h4 className="text-headline-lg text-primary">Session Detected</h4>
        <p className="mt-2 text-body-md text-on-surface-variant">
          Your account is already signed in. Continue to the correct portal, or sign out to switch between doctor and patient accounts.
        </p>
        {error && <p className="mt-md text-error text-sm bg-error-container rounded-xl px-4 py-3">{error}</p>}
        <div className="mt-lg space-y-sm">
          <button
            type="button"
            onClick={() => void handleContinueToPortal()}
            disabled={loading || redirecting}
            className="w-full py-3 bg-primary text-on-primary rounded-xl font-bold text-label-md disabled:opacity-50"
          >
            {redirecting ? "Opening portal..." : "Continue to Portal"}
          </button>
          <button
            type="button"
            onClick={() => void handleUseDifferentAccount()}
            disabled={loading || redirecting}
            className="w-full py-3 border border-outline-variant rounded-xl font-semibold text-on-surface bg-white/60 disabled:opacity-50"
          >
            Use Different Account
          </button>
        </div>
      </div>
    );
  }

  return (
    <div ref={portalRef} className="space-y-md">
      {DEMO_AUTH_ENABLED ? <DemoAccessPanel signOutClerk={isSignedIn ? () => signOut() : undefined} /> : null}

      {!pendingVerification && (
        <div className="grid gap-md md:grid-cols-2">
          <button
            type="button"
            onClick={() => setAuthView("patient")}
            className={`group relative overflow-hidden rounded-[28px] border p-lg text-left shadow-xl transition-all ${
              authView === "patient"
                ? "border-primary bg-primary text-on-primary"
                : "border-white bg-white/80 text-primary hover:-translate-y-1"
            }`}
          >
            <div className={`absolute inset-0 opacity-80 ${authView === "patient" ? "bg-[radial-gradient(circle_at_top_right,_rgba(255,255,255,0.18),_transparent_50%)]" : "bg-[radial-gradient(circle_at_top_right,_rgba(175,239,221,0.7),_transparent_50%)]"}`} />
            <div className="relative z-10">
              <div className="mb-md flex items-center justify-between">
                <span className={`inline-flex h-12 w-12 items-center justify-center rounded-2xl ${authView === "patient" ? "bg-white/15" : "bg-primary-fixed/80"}`}>
                  <span className={`material-symbols-outlined text-2xl ${authView === "patient" ? "text-on-primary" : "text-primary"}`}>person</span>
                </span>
                {authView === "patient" && (
                  <span className="rounded-full bg-white/15 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.18em]">
                    Active
                  </span>
                )}
              </div>
              <h4 className={`text-headline-md font-bold ${authView === "patient" ? "text-on-primary" : "text-primary"}`}>Patient Portal</h4>
              <p className={`mt-2 text-sm ${authView === "patient" ? "text-on-primary/85" : "text-on-surface-variant"}`}>
                Book appointments, complete intake forms, and manage your care journey.
              </p>
              <p className={`mt-md text-xs font-semibold uppercase tracking-[0.14em] ${authView === "patient" ? "text-on-primary/75" : "text-outline"}`}>
                Sign in as a patient only
              </p>
            </div>
          </button>

          <button
            type="button"
            onClick={() => setAuthView("doctor")}
            className={`group relative overflow-hidden rounded-[28px] border p-lg text-left shadow-xl transition-all ${
              authView === "doctor"
                ? "border-primary bg-primary text-on-primary"
                : "border-white bg-white/80 text-primary hover:-translate-y-1"
            }`}
          >
            <div className={`absolute inset-0 opacity-80 ${authView === "doctor" ? "bg-[radial-gradient(circle_at_top_right,_rgba(255,255,255,0.18),_transparent_50%)]" : "bg-[radial-gradient(circle_at_top_right,_rgba(196,231,255,0.8),_transparent_50%)]"}`} />
            <div className="relative z-10">
              <div className="mb-md flex items-center justify-between">
                <span className={`inline-flex h-12 w-12 items-center justify-center rounded-2xl ${authView === "doctor" ? "bg-white/15" : "bg-secondary-fixed/80"}`}>
                  <span className={`material-symbols-outlined text-2xl ${authView === "doctor" ? "text-on-primary" : "text-on-secondary-container"}`}>stethoscope</span>
                </span>
                {authView === "doctor" && (
                  <span className="rounded-full bg-white/15 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.18em]">
                    Active
                  </span>
                )}
              </div>
              <h4 className={`text-headline-md font-bold ${authView === "doctor" ? "text-on-primary" : "text-primary"}`}>Doctor Portal</h4>
              <p className={`mt-2 text-sm ${authView === "doctor" ? "text-on-primary/85" : "text-on-surface-variant"}`}>
                Review schedules, approve SOAP notes, and manage prescriptions and records.
              </p>
              <p className={`mt-md text-xs font-semibold uppercase tracking-[0.14em] ${authView === "doctor" ? "text-on-primary/75" : "text-outline"}`}>
                Sign in as a doctor only
              </p>
            </div>
          </button>
        </div>
      )}

      <div className="glass-panel rounded-[32px] border border-white p-xl shadow-2xl relative overflow-hidden">
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-primary-fixed blur-[100px] rounded-full opacity-60 pointer-events-none" />
        <div className="relative z-10">
          <div className="mb-lg">
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-outline">
              {authView === "doctor" ? "Doctor Access" : "Patient Access"}
            </p>
            <h4 className="mt-2 text-headline-lg text-primary">{authView === "doctor" ? "Doctor Authentication" : "Patient Authentication"}</h4>
            <p className="text-body-md text-on-surface-variant mt-1">
              {authView === "doctor"
                ? "Only doctor accounts can continue from this panel."
                : "Only patient accounts can continue from this panel."}
            </p>
          </div>

          {!pendingVerification && (
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
          )}

          <div className="mb-md">
            <h5 className="text-headline-md text-primary">{authStepTitle}</h5>
            <p className="text-sm text-on-surface-variant">
              {pendingVerification
                ? "Enter the 6-digit code from your email to activate the account."
                : mode === "login"
                  ? `Sign in to the ${authView} portal. You will only be redirected if the account role matches this portal.`
                  : `New ${authView} users are created in Clerk and mirrored into Supabase after verification.`}
            </p>
          </div>

          <form onSubmit={pendingVerification ? handleVerify : mode === "login" ? handleLogin : handleRegister} className="space-y-md">
          {!pendingVerification && mode === "signup" && (
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
                <label className="block text-label-md text-on-surface mb-xs">Account Type</label>
                <div className="rounded-xl border border-outline-variant bg-white px-md py-3 text-body-md text-on-surface">
                  {role === "doctor" ? "Doctor" : "Patient"}
                </div>
              </div>
            </>
          )}

          {!pendingVerification ? (
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
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    required
                    className="w-full px-md py-3 pr-14 rounded-xl bg-white border border-outline-variant focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all text-body-md"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((value) => !value)}
                    className="absolute inset-y-0 right-0 flex items-center px-4 text-sm font-semibold text-primary"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
              </div>
            </>
          ) : (
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
          )}

          {notice && <p className="text-primary text-sm bg-primary-fixed rounded-xl px-4 py-3">{notice}</p>}
          {error && <p className="text-error text-sm bg-error-container rounded-xl px-4 py-3">{error}</p>}

          <button
            type="submit"
            disabled={!clerkReady || loading || sessionChecking}
            className="w-full py-3 bg-primary text-on-primary rounded-xl font-bold text-label-md hover:scale-[1.01] active:scale-[0.98] transition-all shadow-md disabled:opacity-50"
          >
            {loading
              ? pendingVerification
                ? "Verifying..."
                : mode === "login"
                  ? "Signing in..."
                  : "Creating account..."
              : sessionChecking
                ? "Checking session..."
              : pendingVerification
                ? "Verify Email"
                : mode === "login"
                  ? "Sign In"
                  : "Create Account"}
          </button>

          {pendingVerification && (
            <button
              type="button"
              onClick={handleStartOver}
              disabled={loading}
              className="w-full py-3 border border-outline-variant rounded-xl font-semibold text-on-surface bg-white/60 disabled:opacity-50"
            >
              Start Over
            </button>
          )}
          </form>
        </div>
      </div>
    </div>
  );
}

function DemoAccessPanel({ signOutClerk }: { signOutClerk?: (() => Promise<void>) | undefined }) {
  const router = useRouter();
  const [loadingRole, setLoadingRole] = useState<Role | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runDemoLogin = async (role: Role) => {
    setLoadingRole(role);
    setError(null);
    try {
      if (signOutClerk) {
        await signOutClerk();
      }
      clearStoredToken();
      const session = await api.auth.demoLogin(role);
      setStoredToken(session.access_token || null);
      router.push(role === "doctor" ? "/doctor/dashboard" : "/patient/dashboard", { scroll: false });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Demo login failed.");
    } finally {
      setLoadingRole(null);
    }
  };

  return (
    <div className="rounded-[32px] border border-secondary/20 bg-white/85 p-lg shadow-2xl">
      <div className="flex flex-col gap-sm">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-outline">Instant Demo</p>
          <h4 className="mt-2 text-headline-lg text-primary">Test Both Sides Without Signup</h4>
          <p className="mt-1 text-body-md text-on-surface-variant">
            Use the demo patient to book, then switch to the demo doctor to review the same appointment flow.
          </p>
        </div>
        <div className="w-fit rounded-2xl bg-secondary-fixed/60 px-4 py-2 text-caption text-on-secondary-container font-semibold">
          Demo mode uses shared seeded accounts.
        </div>
      </div>

      <div className="mt-md grid gap-sm">
        <button
          type="button"
          onClick={() => void runDemoLogin("patient")}
          disabled={Boolean(loadingRole)}
          className="rounded-[24px] border border-primary/15 bg-primary-fixed/40 p-md text-left transition-all hover:-translate-y-1 disabled:opacity-50"
        >
          <div className="flex items-center justify-between">
            <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-on-primary">
              <span className="material-symbols-outlined text-2xl">person</span>
            </span>
            <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-primary">Demo Patient</span>
          </div>
          <h5 className="mt-md text-headline-md text-primary font-bold">Book an appointment</h5>
          <p className="mt-2 text-sm text-on-surface-variant">
            Enter the patient portal, choose a doctor, and create the booking that the doctor can review.
          </p>
          <p className="mt-md text-label-md font-semibold text-primary">
            {loadingRole === "patient" ? "Opening patient demo..." : "Continue as Demo Patient"}
          </p>
        </button>

        <button
          type="button"
          onClick={() => void runDemoLogin("doctor")}
          disabled={Boolean(loadingRole)}
          className="rounded-[24px] border border-secondary/15 bg-secondary-fixed/40 p-md text-left transition-all hover:-translate-y-1 disabled:opacity-50"
        >
          <div className="flex items-center justify-between">
            <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-secondary text-on-secondary">
              <span className="material-symbols-outlined text-2xl">stethoscope</span>
            </span>
            <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-on-secondary-container">Demo Doctor</span>
          </div>
          <h5 className="mt-md text-headline-md text-primary font-bold">Review booked appointments</h5>
          <p className="mt-2 text-sm text-on-surface-variant">
            Open the doctor portal, inspect the appointment, add the meeting link, and continue the consultation workflow.
          </p>
          <p className="mt-md text-label-md font-semibold text-primary">
            {loadingRole === "doctor" ? "Opening doctor demo..." : "Continue as Demo Doctor"}
          </p>
        </button>
      </div>

      <div className="mt-md rounded-2xl bg-surface-container-low px-md py-sm text-sm text-on-surface-variant">
        Demo path: log in as patient, book the demo doctor, then switch to the demo doctor account to see that exact appointment.
      </div>

      {error && <p className="mt-md text-error text-sm bg-error-container rounded-xl px-4 py-3">{error}</p>}
    </div>
  );
}
