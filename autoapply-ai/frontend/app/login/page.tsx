"use client";

import React, { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { setAuth } from "@/lib/auth";
import { Shield, ArrowLeft, Loader2, AlertCircle } from "lucide-react";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isExpired = searchParams.get("expired") === "true";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(
    isExpired ? "Your session has expired. Please sign in again." : null
  );
  const [loading, setLoading] = useState(false);

  // Forgot password flow
  const [showForgot, setShowForgot] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [forgotStep, setForgotStep] = useState<1 | 2>(1);
  const [forgotMessage, setForgotMessage] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await api.login({ email, password });
      setAuth(res.access_token, res.user);
      router.push("/dashboard");
    } catch (err: any) {
      setError("Invalid email or password. Please check your credentials.");
      setLoading(false);
    }
  };

  const handleSendForgot = async () => {
    if (!forgotEmail) return;
    try {
      const res = await api.forgotPassword(forgotEmail);
      setForgotMessage(res.message || "Reset token generated. Check console logs in dev mode.");
      setForgotStep(2);
    } catch (err: any) {
      setError(err.message || "Failed to generate password reset token.");
    }
  };

  const handleConfirmReset = async () => {
    if (!resetToken || !newPassword) return;
    try {
      const res = await api.resetPassword(resetToken, newPassword);
      setForgotMessage(res.message || "Password reset successfully. You can now log in.");
      setShowForgot(false);
      setForgotStep(1);
    } catch (err: any) {
      setError(err.message || "Password reset failed.");
    }
  };

  return (
    <div className="min-h-screen bg-base text-text-primary flex flex-col items-center justify-center p-4 relative">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[250px] bg-accent/10 blur-[100px] pointer-events-none rounded-full" />

      {/* Top logo */}
      <Link
        href="/"
        className="flex items-center gap-2 mb-8 text-xs text-text-tertiary hover:text-text-primary transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to AutoApply AI overview</span>
      </Link>

      <Card className="w-full max-w-sm p-7 bg-surface border-border shadow-2xl relative z-10">
        <div className="flex flex-col items-center text-center mb-6">
          <div className="w-9 h-9 rounded-lg bg-accent/20 border border-accent/40 flex items-center justify-center font-mono font-bold text-sm text-accent mb-3">
            AA
          </div>
          <h1 className="font-display text-xl font-bold text-text-primary">
            Sign In to Console
          </h1>
          <p className="text-xs text-text-secondary mt-1">
            Access your autonomous candidate agent &amp; review queue
          </p>
        </div>

        {error && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-semantic-red-dim border border-semantic-red/30 text-semantic-red text-xs mb-4">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {forgotMessage && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-accent/15 border border-accent/30 text-accent text-xs mb-4">
            <span>{forgotMessage}</span>
          </div>
        )}

        {!showForgot ? (
          <form onSubmit={handleLogin} className="flex flex-col gap-3.5">
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="candidate@example.com"
                className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-medium text-text-secondary">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => setShowForgot(true)}
                  className="text-[11px] text-accent hover:underline"
                >
                  Forgot?
                </button>
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>

            <Button
              type="submit"
              variant="signature"
              size="md"
              disabled={loading}
              className="w-full mt-2"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                "Sign In"
              )}
            </Button>
          </form>
        ) : (
          <div className="flex flex-col gap-3">
            <span className="text-xs font-semibold text-text-primary">
              Reset Your Password
            </span>

            {forgotStep === 1 ? (
              <>
                <input
                  type="email"
                  value={forgotEmail}
                  onChange={(e) => setForgotEmail(e.target.value)}
                  placeholder="Enter your account email"
                  className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                />
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleSendForgot}
                  disabled={!forgotEmail}
                >
                  Request Reset Token
                </Button>
              </>
            ) : (
              <>
                <input
                  type="text"
                  value={resetToken}
                  onChange={(e) => setResetToken(e.target.value)}
                  placeholder="Paste reset token here"
                  className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-text-primary font-mono placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                />
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="New password (min 6 chars)"
                  className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                />
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleConfirmReset}
                  disabled={!resetToken || !newPassword}
                >
                  Confirm New Password
                </Button>
              </>
            )}

            <button
              type="button"
              onClick={() => setShowForgot(false)}
              className="text-[11px] text-text-tertiary hover:text-text-primary mt-1"
            >
              ← Back to Sign In
            </button>
          </div>
        )}

        <div className="mt-6 pt-4 border-t border-border text-center text-xs text-text-secondary">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="text-accent hover:underline font-medium">
            Create account
          </Link>
        </div>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-base" />}>
      <LoginForm />
    </Suspense>
  );
}
