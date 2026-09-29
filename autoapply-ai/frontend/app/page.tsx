"use client";

import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/lib/auth";
import {
  Shield,
  CheckCircle2,
  Lock,
  ArrowRight,
  Bot,
  FileSearch,
  Sparkles,
  Terminal,
  Cpu,
} from "lucide-react";

export default function LandingPage() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-base text-text-primary selection:bg-accent/30 selection:text-white flex flex-col justify-between">
      {/* Top Navigation */}
      <header className="sticky top-0 z-50 nav-glass px-6 md:px-12 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5 group">
          <span className="h-7 w-7 rounded-md bg-accent/20 border border-accent/40 flex items-center justify-center font-mono font-bold text-xs text-accent transition-transform group-hover:scale-105">
            AA
          </span>
          <span className="font-display font-bold text-lg tracking-tight text-text-primary">
            AutoApply <span className="text-accent">AI</span>
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-8 text-xs text-text-secondary">
          <a href="#safety" className="hover:text-text-primary transition-colors">
            Safety Model
          </a>
          <a href="#features" className="hover:text-text-primary transition-colors">
            Architecture
          </a>
          <a href="#workflow" className="hover:text-text-primary transition-colors">
            State Machine
          </a>
        </nav>

        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <Link href="/dashboard">
              <Button variant="signature" size="sm" className="gap-1.5">
                <span>Go to Dashboard</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </Link>
          ) : (
            <>
              <Link href="/login">
                <Button variant="ghost" size="sm">
                  Log In
                </Button>
              </Link>
              <Link href="/signup">
                <Button variant="signature" size="sm">
                  Get Started
                </Button>
              </Link>
            </>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-20 md:pt-32 pb-16 px-6 max-w-5xl mx-auto text-center flex flex-col items-center">
        {/* Subtle Signature Ambient Glow (Not full background) */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[300px] bg-gradient-signature opacity-15 blur-[120px] pointer-events-none rounded-full" />

        {/* Safety Badge Headline */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-border bg-surface-2 text-xs text-text-secondary mb-6 shadow-sm">
          <Shield className="w-3.5 h-3.5 text-semantic-amber" />
          <span className="font-mono text-[11px] font-medium tracking-wide">
            STRICT HUMAN-IN-THE-LOOP SAFETY VALVE
          </span>
        </div>

        {/* Main Pitch */}
        <h1 className="font-display text-4xl sm:text-6xl font-bold tracking-tight text-text-primary max-w-3xl leading-[1.1] mb-6">
          An AI agent that applies for you —{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#A78BFA] via-[#C084FC] to-[#F472B6]">
            and never submits without your approval.
          </span>
        </h1>

        <p className="text-base sm:text-lg text-text-secondary max-w-2xl mb-10 leading-relaxed">
          AutoApply AI aggregates real ATS boards, extracts your resume skills, maps form inputs, and halts at high-resolution inspection. You review the exact field decisions before any application proceeds.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center gap-3.5 w-full sm:w-auto justify-center mb-16">
          <Link href="/signup" className="w-full sm:w-auto">
            <Button variant="signature" size="lg" className="w-full sm:w-auto gap-2 px-7">
              <span>Deploy Candidate Agent</span>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
          <Link href="/login" className="w-full sm:w-auto">
            <Button variant="secondary" size="lg" className="w-full sm:w-auto px-7">
              Sign In to Console
            </Button>
          </Link>
        </div>

        {/* Trust & Safety Strip */}
        <div
          id="safety"
          className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-3xl p-3 rounded-xl border border-border bg-surface/70 backdrop-blur-sm"
        >
          <div className="flex items-center gap-2.5 px-3 py-2 text-left">
            <div className="w-7 h-7 rounded-md bg-semantic-amber/10 border border-semantic-amber/30 flex items-center justify-center shrink-0">
              <Shield className="w-4 h-4 text-semantic-amber" />
            </div>
            <div>
              <div className="text-xs font-semibold text-text-primary">
                Dry-Run by Default
              </div>
              <div className="text-[11px] text-text-tertiary">
                Forms mapped without auto-submission
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 px-3 py-2 text-left border-t sm:border-t-0 sm:border-l border-border">
            <div className="w-7 h-7 rounded-md bg-accent/10 border border-accent/30 flex items-center justify-center shrink-0">
              <CheckCircle2 className="w-4 h-4 text-accent" />
            </div>
            <div>
              <div className="text-xs font-semibold text-text-primary">
                Human Review Required
              </div>
              <div className="text-[11px] text-text-tertiary">
                Full snapshots &amp; confidence scores
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 px-3 py-2 text-left border-t sm:border-t-0 sm:border-l border-border">
            <div className="w-7 h-7 rounded-md bg-semantic-green/10 border border-semantic-green/30 flex items-center justify-center shrink-0">
              <Lock className="w-4 h-4 text-semantic-green" />
            </div>
            <div>
              <div className="text-xs font-semibold text-text-primary">
                Zero Silent Submissions
              </div>
              <div className="text-[11px] text-text-tertiary">
                Submissions require manual human click
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Bento Grid Architecture Features */}
      <section id="features" className="py-20 px-6 max-w-6xl mx-auto w-full">
        <div className="text-center mb-12">
          <h2 className="font-display text-2xl sm:text-3xl font-bold text-text-primary mb-3">
            Engineered for Precision, Not Blind Volume
          </h2>
          <p className="text-xs sm:text-sm text-text-secondary max-w-xl mx-auto">
            Traditional application bots flood companies with garbage. AutoApply AI delivers verified candidate fit.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Card 1: Resume Layout Parser */}
          <Card className="p-6 bg-surface border-border hover:border-border-strong transition-all flex flex-col justify-between">
            <div>
              <div className="w-9 h-9 rounded-lg bg-surface-2 border border-border flex items-center justify-center mb-4">
                <FileSearch className="w-4 h-4 text-accent" />
              </div>
              <h3 className="font-display text-base font-semibold text-text-primary mb-2">
                Hardened Resume Intelligence
              </h3>
              <p className="text-xs text-text-secondary leading-relaxed mb-4">
                Multi-column layout awareness via pdfplumber and python-docx. Detects scanned image PDFs, script anomalies, and extracts your skills with date-calculated experience.
              </p>
            </div>
            <div className="font-mono text-[11px] text-text-tertiary bg-base p-2.5 rounded border border-border">
              Parsed 24 core skills • 4.5 yrs exp
            </div>
          </Card>

          {/* Card 2: 7-State Finite State Machine */}
          <Card className="p-6 md:col-span-2 bg-surface border-border hover:border-border-strong transition-all flex flex-col justify-between relative overflow-hidden">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-9 h-9 rounded-lg bg-surface-2 border border-border flex items-center justify-center">
                  <Terminal className="w-4 h-4 text-semantic-amber" />
                </div>
                <Badge variant="amber">FINITE AUTOMATON</Badge>
              </div>
              <h3 className="font-display text-base font-semibold text-text-primary mb-2">
                Deterministic Browser State Machine
              </h3>
              <p className="text-xs text-text-secondary leading-relaxed max-w-xl mb-4">
                The Playwright agent operates as an explicit 7-state machine: LOCATING_FORM → INSPECTING_FIELDS → MAPPING_FIELDS → FILLING_FORM → CAPTURING_SCREENSHOT → AWAITING_REVIEW. It halts with per-field confidence rationales.
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[10px] text-text-secondary">
              <div className="p-2 rounded bg-base border border-border text-center">
                1. LOCATING
              </div>
              <div className="p-2 rounded bg-base border border-border text-center">
                2. INSPECTING
              </div>
              <div className="p-2 rounded bg-base border border-border text-center">
                3. MAPPING
              </div>
              <div className="p-2 rounded bg-semantic-amber/10 border border-semantic-amber/30 text-semantic-amber text-center font-bold">
                4. REVIEW HALT
              </div>
            </div>
          </Card>

          {/* Card 3: Multi-Source Scraping */}
          <Card className="p-6 md:col-span-2 bg-surface border-border hover:border-border-strong transition-all flex flex-col justify-between">
            <div>
              <div className="w-9 h-9 rounded-lg bg-surface-2 border border-border flex items-center justify-center mb-4">
                <Cpu className="w-4 h-4 text-semantic-green" />
              </div>
              <h3 className="font-display text-base font-semibold text-text-primary mb-2">
                Live ATS Adapters &amp; Content Hash Deduplication
              </h3>
              <p className="text-xs text-text-secondary leading-relaxed max-w-xl mb-4">
                Direct integration with Greenhouse, Lever, Remotive, and RemoteOK. Complies with robots.txt, respects crawl delays, deduplicates postings with SHA-256 signatures, and monitors per-source health telemetry.
              </p>
            </div>
            <div className="flex items-center gap-2 flex-wrap text-[11px] font-mono">
              <span className="px-2 py-0.5 rounded bg-surface-2 border border-border text-text-secondary">
                greenhouse: 200 OK
              </span>
              <span className="px-2 py-0.5 rounded bg-surface-2 border border-border text-text-secondary">
                lever: 200 OK
              </span>
              <span className="px-2 py-0.5 rounded bg-surface-2 border border-border text-text-secondary">
                remotive: 200 OK
              </span>
              <span className="px-2 py-0.5 rounded bg-surface-2 border border-border text-text-secondary">
                remoteok: 200 OK
              </span>
            </div>
          </Card>

          {/* Card 4: AI Tailored Notes */}
          <Card className="p-6 bg-surface border-border hover:border-border-strong transition-all flex flex-col justify-between">
            <div>
              <div className="w-9 h-9 rounded-lg bg-surface-2 border border-border flex items-center justify-center mb-4">
                <Sparkles className="w-4 h-4 text-accent" />
              </div>
              <h3 className="font-display text-base font-semibold text-text-primary mb-2">
                Contextual Application Notes
              </h3>
              <p className="text-xs text-text-secondary leading-relaxed mb-4">
                Personalized cover notes synthesized from your specific profile bio, skills, and the company&apos;s job description, with automatic rule-based fallback.
              </p>
            </div>
            <div className="font-mono text-[11px] text-accent/80 bg-accent/5 p-2.5 rounded border border-accent/20">
              Anthropic Claude 3 Haiku + Heuristic Fallback
            </div>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 px-6 text-center text-xs text-text-tertiary">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 font-mono">
            <span>AutoApply AI</span>
            <span>•</span>
            <span>Human-Supervised Autonomous Agent</span>
          </div>
          <div>Strict Dry-Run Default • Zero Unverified Submissions</div>
        </div>
      </footer>
    </div>
  );
}
