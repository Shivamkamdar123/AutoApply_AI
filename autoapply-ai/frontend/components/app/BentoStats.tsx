import React from "react";
import { Card } from "@/components/ui/card";
import { ConfidenceRing } from "./ConfidenceRing";
import { DashboardSummary } from "@/lib/api";
import { ShieldAlert, CheckCircle, Search, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface BentoStatsProps {
  summary?: DashboardSummary | null;
  isLoading?: boolean;
}

export function BentoStats({ summary, isLoading = false }: BentoStatsProps) {
  const avgScore = summary?.average_match_score || 0;
  const pendingReview = summary?.total_needs_review || 0;
  const applied = summary?.total_applied || 0;
  const matched = summary?.total_matched || 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 mb-8">
      {/* 1. Large Feature Bento: Avg Match Score with Radial Ring */}
      <Card className="p-4 sm:col-span-2 flex items-center justify-between bg-surface border-border hover:border-border-strong transition-all relative overflow-hidden group">
        <div className="flex flex-col gap-1 z-10">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono uppercase tracking-wider text-text-tertiary">
              Aggregate Semantic Fit
            </span>
            <span className="flex h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
          </div>
          <h4 className="text-xl font-display font-bold text-text-primary">
            Average Profile Match
          </h4>
          <p className="text-xs text-text-secondary max-w-xs leading-relaxed">
            TF-IDF cosine similarity across target skills, verified against real postings.
          </p>
        </div>

        <div className="z-10 flex flex-col items-center">
          <ConfidenceRing value={avgScore} size="lg" strokeWidth={4} />
          <span className="text-[10px] font-mono text-text-tertiary mt-1.5">
            Cosine Score
          </span>
        </div>

        {/* Ambient subtle glow background */}
        <div className="absolute right-0 top-0 bottom-0 w-1/2 bg-accent/5 blur-3xl pointer-events-none group-hover:bg-accent/10 transition-colors" />
      </Card>

      {/* 2. Pending Human Review Card (Safety Valve focus) */}
      <Card
        className={cn(
          "p-4 flex flex-col justify-between transition-all",
          pendingReview > 0
            ? "border-semantic-amber/40 bg-surface relative overflow-hidden"
            : "border-border bg-surface"
        )}
      >
        <div className="flex items-center justify-between text-text-tertiary text-xs">
          <span className="font-mono uppercase tracking-wider text-[11px]">
            Review Queue
          </span>
          <ShieldAlert className="w-4 h-4 text-semantic-amber" />
        </div>
        <div className="my-2">
          <div className="text-3xl font-display font-bold text-semantic-amber">
            {isLoading ? "--" : pendingReview}
          </div>
          <span className="text-xs text-text-secondary">
            Halted at AWAITING_REVIEW
          </span>
        </div>
        <div className="text-[11px] text-text-tertiary font-mono">
          Strict Dry-Run enforced
        </div>
      </Card>

      {/* 3. Verified & Dry-Run Applied */}
      <Card className="p-4 flex flex-col justify-between border-border bg-surface hover:border-border-strong transition-all">
        <div className="flex items-center justify-between text-text-tertiary text-xs">
          <span className="font-mono uppercase tracking-wider text-[11px]">
            Verified Form Staged
          </span>
          <CheckCircle className="w-4 h-4 text-semantic-green" />
        </div>
        <div className="my-2">
          <div className="text-3xl font-display font-bold text-semantic-green">
            {isLoading ? "--" : applied}
          </div>
          <span className="text-xs text-text-secondary">
            Mappable & Verified
          </span>
        </div>
        <div className="text-[11px] text-text-tertiary font-mono">
          Ready for manual submission
        </div>
      </Card>
    </div>
  );
}
