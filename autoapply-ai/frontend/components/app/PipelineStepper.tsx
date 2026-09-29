import React from "react";
import { cn } from "@/lib/utils";
import { DashboardSummary } from "@/lib/api";

interface PipelineStepperProps {
  summary?: DashboardSummary | null;
}

export function PipelineStepper({ summary }: PipelineStepperProps) {
  const needsReview = summary?.total_needs_review || 0;
  const applied = summary?.total_applied || 0;
  const matched = summary?.total_matched || 0;

  const totalResumes = summary?.total_resumes ?? 0;
  const hasResume = summary?.has_active_resume ?? (totalResumes > 0);

  // Active step is 1 if no resume, 3 if pending review, 4 if applied, 2 if matched
  const activeStep = !hasResume ? 1 : needsReview > 0 ? 3 : applied > 0 ? 4 : matched > 0 ? 2 : 1;

  const steps = [
    {
      step: 1,
      name: "Resume Parsed",
      desc: hasResume ? "Skills & history extracted" : "Upload resume in Profile",
      count: totalResumes,
    },
    {
      step: 2,
      name: "Jobs Matched",
      desc: "Scraped & deduplicated",
      count: matched,
    },
    {
      step: 3,
      name: "Awaiting Review",
      desc: "Halted at Safety Valve",
      count: needsReview,
      highlight: true,
    },
    {
      step: 4,
      name: "Verified (Dry Run)",
      desc: "Fields mapped & checked",
      count: applied,
    },
    {
      step: 5,
      name: "Live Submitted",
      desc: "Human override required",
      count: summary?.total_submitted || 0,
    },
  ];

  return (
    <div className="w-full bg-surface border border-border rounded-xl p-5 mb-8">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-display text-sm font-semibold text-text-primary">
            Agent State Machine Pipeline
          </h3>
          <p className="text-xs text-text-secondary">
            Deterministic application lifecycle guaranteeing zero silent submissions.
          </p>
        </div>
        <span className="font-mono text-[11px] text-text-tertiary">
          State: {needsReview > 0 ? "AWAITING_REVIEW" : "IDLE"}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3 relative">
        {steps.map((s, idx) => {
          const isActive = s.step === activeStep;
          const isPassed = s.step < activeStep;

          return (
            <div
              key={s.name}
              className={cn(
                "flex flex-col p-3 rounded-lg border transition-all relative",
                isActive
                  ? "border-accent bg-surface-2 shadow-glow"
                  : isPassed
                  ? "border-border-strong bg-surface-2/60"
                  : "border-border bg-surface-2/30 opacity-70"
              )}
            >
              {/* Connector line for desktop */}
              {idx < steps.length - 1 && (
                <div className="hidden md:block absolute -right-2 top-1/2 w-4 h-[1px] bg-border-strong z-10" />
              )}

              <div className="flex items-center justify-between mb-2">
                <span
                  className={cn(
                    "w-5 h-5 rounded-full flex items-center justify-center font-mono text-[10px] font-bold",
                    isActive
                      ? "bg-accent text-white shadow-sm"
                      : isPassed
                      ? "bg-semantic-green/20 text-semantic-green border border-semantic-green/40"
                      : "bg-surface-3 text-text-tertiary"
                  )}
                >
                  {s.step}
                </span>
                <span className="font-mono text-xs font-semibold text-text-primary">
                  {s.count}
                </span>
              </div>

              <div className="font-medium text-xs text-text-primary mb-0.5 truncate">
                {s.name}
              </div>
              <div className="text-[11px] text-text-tertiary leading-tight">
                {s.desc}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
