"use client";

import React, { useState } from "react";
import { ApplicationStatus } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ConfidenceRing } from "./ConfidenceRing";
import { FormSnapshotModal } from "./FormSnapshotModal";
import { CoverLetterModal } from "./CoverLetterModal";
import {
  ShieldAlert,
  Camera,
  FileText,
  Check,
  X,
  Sparkles,
  Building,
  CheckCircle2,
} from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/toast";

interface ReviewQueueProps {
  items: ApplicationStatus[];
  isLoading?: boolean;
}

export function ReviewQueue({ items, isLoading = false }: ReviewQueueProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [activeSnapshot, setActiveSnapshot] = useState<{
    jobId: string;
    title: string;
    company: string;
  } | null>(null);

  const [activeCover, setActiveCover] = useState<{
    jobId: string;
    title: string;
    company: string;
  } | null>(null);

  const actionMutation = useMutation({
    mutationFn: ({
      jobId,
      action,
    }: {
      jobId: string;
      action: "approve" | "reject";
    }) => api.submitReviewAction(jobId, action, false),
    onSuccess: (data, variables) => {
      // Invalidate review queue and summary queries to update counts automatically
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      queryClient.invalidateQueries({ queryKey: ["summary"] });
      toast(
        `Application for ${data.company} ${variables.action === "approve" ? "approved (Dry Run verified)" : "rejected"}.`,
        "success"
      );
    },
    onError: (err: any) => {
      toast(`Action failed: ${err.message}`, "error");
    },
  });

  const pendingItems = items.filter((i) => i.stage === "needs_review");

  return (
    <div className="mb-8">
      {/* Modals */}
      <FormSnapshotModal
        open={Boolean(activeSnapshot)}
        jobId={activeSnapshot?.jobId || null}
        jobTitle={activeSnapshot?.title}
        company={activeSnapshot?.company}
        onClose={() => setActiveSnapshot(null)}
      />

      <CoverLetterModal
        open={Boolean(activeCover)}
        jobId={activeCover?.jobId || null}
        jobTitle={activeCover?.title}
        company={activeCover?.company}
        onClose={() => setActiveCover(null)}
      />

      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <h3 className="font-display text-base font-semibold text-text-primary">
            Human-in-the-Loop Review Queue
          </h3>
          <Badge variant="amber">
            {pendingItems.length} PENDING APPROVAL
          </Badge>
        </div>
        <span className="text-xs text-text-tertiary hidden sm:inline-block font-mono">
          Stage: AWAITING_REVIEW
        </span>
      </div>

      {pendingItems.length === 0 ? (
        <Card className="p-8 text-center bg-surface border-border flex flex-col items-center justify-center gap-2">
          <CheckCircle2 className="w-8 h-8 text-semantic-green/60 mb-1" />
          <h4 className="font-display text-sm font-semibold text-text-primary">
            Review Queue Clear
          </h4>
          <p className="text-xs text-text-secondary max-w-sm">
            All drafted applications have been reviewed or no recommended matches exceed threshold. Trigger a new search or match cycle to populate candidates.
          </p>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          {pendingItems.map((item) => (
            <Card
              key={item.job_id}
              className="p-5 bg-surface border-border hover:border-border-strong transition-all flex flex-col gap-4"
            >
              {/* Card Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
                <div className="flex flex-col">
                  <span className="font-display font-bold text-base text-text-primary">
                    {item.title}
                  </span>
                  <div className="flex items-center gap-2 text-xs text-text-secondary mt-0.5">
                    <span className="flex items-center gap-1">
                      <Building className="w-3.5 h-3.5 text-text-tertiary" />
                      <strong>{item.company}</strong>
                    </span>
                    <span>•</span>
                    <span className="font-mono text-text-tertiary">
                      ID: {item.job_id}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-surface-2 border border-border">
                    <ConfidenceRing value={item.match_score} size="sm" />
                    <span className="text-xs font-mono font-medium text-text-secondary">
                      Profile Match
                    </span>
                  </div>
                </div>
              </div>

              {/* Field Mappings Table with Radial Meters */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="text-text-tertiary font-mono border-b border-border pb-2">
                      <th className="pb-2 font-normal">Application Field</th>
                      <th className="pb-2 font-normal">Proposed Value</th>
                      <th className="pb-2 font-normal">Confidence</th>
                      <th className="pb-2 font-normal hidden md:table-cell">
                        Source / Rationale
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {(item.field_mappings || []).map((f) => (
                      <tr key={f.field_name} className="hover:bg-surface-2/40">
                        <td className="py-2.5 font-medium text-text-primary">
                          {f.field_name}
                        </td>
                        <td className="py-2.5 font-mono text-text-secondary">
                          {f.value_filled || "--"}
                        </td>
                        <td className="py-2.5">
                          <div className="flex items-center gap-1.5">
                            <ConfidenceRing value={f.confidence} size="sm" strokeWidth={2.5} />
                            <span className="text-[11px] font-mono text-text-tertiary hidden sm:inline">
                              {Math.round(f.confidence * 100)}%
                            </span>
                          </div>
                        </td>
                        <td className="py-2.5 text-text-tertiary text-[11px] hidden md:table-cell">
                          {f.rationale}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Safety Valve Notice & Actions */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-border bg-surface-2/30 -mx-5 -mb-5 p-4 rounded-b-lg">
                <div className="flex items-center gap-2 text-xs text-text-tertiary">
                  <ShieldAlert className="w-4 h-4 text-semantic-amber shrink-0" />
                  <span>
                    <strong>Safety Valve:</strong> Approving verifies form entries in Dry Run mode. Never submits live.
                  </span>
                </div>

                <div className="flex items-center gap-2 shrink-0 flex-wrap">
                  <Button
                    variant="outline"
                    size="xs"
                    onClick={() =>
                      setActiveSnapshot({
                        jobId: item.job_id,
                        title: item.title,
                        company: item.company,
                      })
                    }
                    className="gap-1.5"
                  >
                    <Camera className="w-3.5 h-3.5" />
                    <span>Snapshot</span>
                  </Button>

                  <Button
                    variant="outline"
                    size="xs"
                    onClick={() =>
                      setActiveCover({
                        jobId: item.job_id,
                        title: item.title,
                        company: item.company,
                      })
                    }
                    className="gap-1.5"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-accent" />
                    <span>Cover Note</span>
                  </Button>

                  <Button
                    variant="danger"
                    size="xs"
                    onClick={() =>
                      actionMutation.mutate({
                        jobId: item.job_id,
                        action: "reject",
                      })
                    }
                    disabled={actionMutation.isPending}
                    className="gap-1"
                  >
                    <X className="w-3.5 h-3.5" />
                    <span>Reject</span>
                  </Button>

                  <Button
                    variant="primary"
                    size="xs"
                    onClick={() =>
                      actionMutation.mutate({
                        jobId: item.job_id,
                        action: "approve",
                      })
                    }
                    disabled={actionMutation.isPending}
                    className="gap-1"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Approve (Dry Run)</span>
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
