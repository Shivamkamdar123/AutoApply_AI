"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { setAuth } from "@/lib/auth";
import { ArrowLeft, Loader2, AlertCircle } from "lucide-react";

export default function SignupPage() {
  const router = useRouter();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match. Please verify.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setLoading(true);

    try {
      const res = await api.signup({
        email,
        password,
        full_name: fullName.trim() || undefined,
      });
      setAuth(res.access_token, res.user);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to create account. Email may already be registered.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-base text-text-primary flex flex-col items-center justify-center p-4 relative">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[250px] bg-accent/10 blur-[100px] pointer-events-none rounded-full" />

      {/* Top logo link */}
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
            Create Account
          </h1>
          <p className="text-xs text-text-secondary mt-1">
            Deploy your personalized autonomous job application agent
          </p>
        </div>

        {error && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-semantic-red-dim border border-semantic-red/30 text-semantic-red text-xs mb-4">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSignup} className="flex flex-col gap-3.5">
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">
              Full Name (Optional)
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Alex Rivera"
              className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

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
            <label className="block text-xs font-medium text-text-secondary mb-1">
              Password
            </label>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Min 6 characters"
              className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">
              Confirm Password
            </label>
            <input
              type="password"
              required
              minLength={6}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter password"
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
              "Create Account"
            )}
          </Button>
        </form>

        <div className="mt-6 pt-4 border-t border-border text-center text-xs text-text-secondary">
          Already have an account?{" "}
          <Link href="/login" className="text-accent hover:underline font-medium">
            Sign in
          </Link>
        </div>
      </Card>
    </div>
  );
}
