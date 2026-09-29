"use client";

import React, { useState } from "react";
import { JobMatch, SourceStatusItem, api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfidenceRing } from "./ConfidenceRing";
import { CoverLetterModal } from "./CoverLetterModal";
import {
  Search,
  Sparkles,
  ExternalLink,
  SlidersHorizontal,
  LayoutGrid,
  List,
  DollarSign,
  ArrowRight,
  CheckCircle2,
  BookmarkPlus,
  Send,
} from "lucide-react";

interface JobsTableProps {
  matches: JobMatch[];
  sourcesStatus?: Record<string, SourceStatusItem | string>;
  isLoading?: boolean;
  onRefresh?: () => void;
}

const ALL_SOURCES = [
  "all",
  "arbeitnow",
  "adzuna",
  "jsearch",
  "usajobs",
  "greenhouse",
  "lever",
  "remotive",
  "remoteok",
  "sample",
];

const KANBAN_STAGES = [
  { id: "saved", label: "Saved", color: "border-sky-500/30 text-sky-400" },
  { id: "needs_review", label: "Needs Review", color: "border-amber-500/30 text-amber-400" },
  { id: "applied", label: "Applied", color: "border-emerald-500/30 text-emerald-400" },
  { id: "interview", label: "Interview", color: "border-purple-500/30 text-purple-400" },
  { id: "offer", label: "Offer", color: "border-green-400/40 text-green-300" },
  { id: "rejected", label: "Rejected", color: "border-rose-500/30 text-rose-400" },
];

export function JobsTable({
  matches,
  sourcesStatus = {},
  isLoading = false,
  onRefresh,
}: JobsTableProps) {
  const [filterText, setFilterText] = useState("");
  const [selectedSource, setSelectedSource] = useState<string>("all");
  const [threshold, setThreshold] = useState<number>(30); // 30% default threshold
  const [viewMode, setViewMode] = useState<"table" | "kanban">("table");
  const [stagedJobs, setStagedJobs] = useState<Record<string, string>>({}); // jobId -> stage

  const [activeCover, setActiveCover] = useState<{
    jobId: string;
    title: string;
    company: string;
  } | null>(null);

  const filtered = matches.filter((m) => {
    const textMatch =
      m.job.title.toLowerCase().includes(filterText.toLowerCase()) ||
      m.job.company.toLowerCase().includes(filterText.toLowerCase()) ||
      (m.job.description || "").toLowerCase().includes(filterText.toLowerCase());

    const sourceMatch =
      selectedSource === "all" ||
      (m.job.source || "sample").toLowerCase() === selectedSource.toLowerCase();

    return textMatch && sourceMatch;
  });

  const handleStageJob = async (jobId: string, stage: string) => {
    try {
      setStagedJobs((prev) => ({ ...prev, [jobId]: stage }));
      await api.updateApplicationStage(jobId, stage);
      if (onRefresh) onRefresh();
    } catch (_) {
      // Fallback
    }
  };

  return (
    <div className="mb-8">
      <CoverLetterModal
        open={Boolean(activeCover)}
        jobId={activeCover?.jobId || null}
        jobTitle={activeCover?.title}
        company={activeCover?.company}
        onClose={() => setActiveCover(null)}
      />

      {/* Header and Source Status Chips */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4">
        <div>
          <h3 className="font-display text-base font-semibold text-text-primary">
            Aggregated Postings &amp; Candidate Fit
          </h3>
          <p className="text-xs text-text-secondary">
            Live aggregator feed ranked by semantic match. Transparent fit tiers &amp; adjustable threshold.
          </p>
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-surface-2 border border-border rounded-lg p-0.5">
            <button
              onClick={() => setViewMode("table")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono transition-colors ${
                viewMode === "table"
                  ? "bg-accent/20 text-accent font-semibold"
                  : "text-text-tertiary hover:text-text-secondary"
              }`}
            >
              <List className="w-3.5 h-3.5" />
              <span>Table</span>
            </button>
            <button
              onClick={() => setViewMode("kanban")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono transition-colors ${
                viewMode === "kanban"
                  ? "bg-accent/20 text-accent font-semibold"
                  : "text-text-tertiary hover:text-text-secondary"
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>Kanban</span>
            </button>
          </div>
        </div>
      </div>

      {/* Per-source live health chips */}
      <div className="flex items-center gap-1.5 flex-wrap mb-4">
        {Object.entries(sourcesStatus).map(([source, info]) => {
          const isObj = typeof info === "object" && info !== null;
          const statusStr = isObj ? (info as SourceStatusItem).status : String(info);
          const count = isObj ? ((info as SourceStatusItem).count ?? (info as SourceStatusItem).accepted) : null;
          const error = isObj ? (info as SourceStatusItem).error : null;

          const isOk = statusStr === "ok";
          const isNoKey = statusStr === "no_key";
          const isRateLimited = statusStr === "rate_limited";
          const isNoResults = statusStr === "no_results";
          const isFallback = statusStr === "fallback";

          let label = statusStr;
          let colorClass = "text-semantic-red";
          let dotClass = "bg-semantic-red";

          if (isOk) {
            label = `${count ?? 0} found`;
            colorClass = "text-semantic-green";
            dotClass = "bg-semantic-green";
          } else if (isNoKey) {
            label = "no key";
            colorClass = "text-amber-400";
            dotClass = "bg-amber-400";
          } else if (isRateLimited) {
            label = "rate limited";
            colorClass = "text-amber-400";
            dotClass = "bg-amber-400";
          } else if (isNoResults) {
            label = "0 found";
            colorClass = "text-text-tertiary";
            dotClass = "bg-text-tertiary";
          } else if (isFallback) {
            label = "fallback";
            colorClass = "text-semantic-amber";
            dotClass = "bg-semantic-amber";
          } else if (error) {
            label = "error";
          }

          return (
            <span
              key={source}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-surface-2 border border-border text-text-secondary"
            >
              <span className={`w-1.5 h-1.5 rounded-full ${dotClass}`} />
              <span className="capitalize">{source}:</span>
              <span className={colorClass}>{label}</span>
            </span>
          );
        })}
      </div>

      {/* Control Bar: Search + Source Filter + Threshold Slider */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 mb-4 items-center">
        {/* Search Input */}
        <div className="lg:col-span-4 relative">
          <Search className="w-3.5 h-3.5 text-text-tertiary absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter by title, company, skills..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            className="w-full bg-surface-2 border border-border rounded-lg pl-9 pr-3 py-1.5 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
          />
        </div>

        {/* Source Filter Tags */}
        <div className="lg:col-span-5 flex items-center gap-1 overflow-x-auto pb-1 lg:pb-0">
          {ALL_SOURCES.map((src) => (
            <button
              key={src}
              onClick={() => setSelectedSource(src)}
              className={`px-2 py-1 rounded text-[11px] font-mono capitalize transition-colors shrink-0 ${
                selectedSource === src
                  ? "bg-accent/20 text-accent border border-accent/40 font-semibold"
                  : "bg-surface-2 text-text-tertiary hover:text-text-secondary border border-border"
              }`}
            >
              {src}
            </button>
          ))}
        </div>

        {/* Adjustable Threshold Slider */}
        <div className="lg:col-span-3 flex items-center gap-2 bg-surface-2 border border-border rounded-lg px-3 py-1.5">
          <SlidersHorizontal className="w-3.5 h-3.5 text-text-tertiary shrink-0" />
          <span className="text-[11px] font-mono text-text-secondary shrink-0">
            Min Fit: <strong className="text-accent">{threshold}%</strong>
          </span>
          <input
            type="range"
            min="10"
            max="80"
            step="5"
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="w-full h-1 bg-border rounded-lg appearance-none cursor-pointer accent-accent"
          />
        </div>
      </div>

      {/* TABLE VIEW */}
      {viewMode === "table" && (
        <Card className="overflow-hidden bg-surface border-border shadow-md">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-surface-2/60 text-text-tertiary font-mono">
                  <th className="py-2.5 px-4 font-normal">Job Title</th>
                  <th className="py-2.5 px-4 font-normal">Company &amp; Location</th>
                  <th className="py-2.5 px-4 font-normal">Fit Score</th>
                  <th className="py-2.5 px-4 font-normal">Salary</th>
                  <th className="py-2.5 px-4 font-normal">Source</th>
                  <th className="py-2.5 px-4 font-normal">Fit Tier</th>
                  <th className="py-2.5 px-4 font-normal text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.map((m) => {
                  const scorePct = Math.round(m.score * 100);
                  const isRec = scorePct >= threshold;
                  const isGoodFit = !isRec && scorePct >= 25;
                  const currentStage = stagedJobs[m.job.id];

                  return (
                    <tr
                      key={m.job.id}
                      className="hover:bg-surface-2/50 transition-colors group"
                    >
                      <td className="py-3 px-4 font-medium text-text-primary">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{m.job.title}</span>
                          {m.job.url && (
                            <a
                              href={m.job.url}
                              target="_blank"
                              rel="noreferrer"
                              className="opacity-0 group-hover:opacity-100 text-text-tertiary hover:text-accent transition-opacity"
                            >
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>
                      </td>

                      <td className="py-3 px-4 text-text-secondary">
                        <div>{m.job.company}</div>
                        <div className="text-[11px] text-text-tertiary">
                          {m.job.location || "Remote"}
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <ConfidenceRing value={m.score} size="sm" strokeWidth={2.5} />
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        {m.job.salary_range ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                            <DollarSign className="w-3 h-3" />
                            {m.job.salary_range}
                          </span>
                        ) : (
                          <span className="text-[11px] text-text-tertiary font-mono">--</span>
                        )}
                      </td>

                      <td className="py-3 px-4">
                        <span className="font-mono text-[11px] text-text-tertiary uppercase">
                          {m.job.source || "sample"}
                        </span>
                      </td>

                      <td className="py-3 px-4">
                        {isRec ? (
                          <Badge variant="accent" className="bg-emerald-500/20 text-emerald-300 border-emerald-500/30">
                            ★ RECOMMENDED
                          </Badge>
                        ) : isGoodFit ? (
                          <Badge variant="default" className="bg-sky-500/15 text-sky-300 border-sky-500/30">
                            GOOD FIT
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-text-tertiary border-border">
                            NEAR MATCH
                          </Badge>
                        )}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {currentStage ? (
                            <span className="inline-flex items-center gap-1 text-[11px] text-semantic-green font-mono font-medium">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              {currentStage.toUpperCase()}
                            </span>
                          ) : (
                            <Button
                              variant="secondary"
                              size="xs"
                              onClick={() => handleStageJob(m.job.id, "needs_review")}
                              className="text-[11px] gap-1 text-accent border border-accent/30 hover:bg-accent/15"
                            >
                              <BookmarkPlus className="w-3 h-3" />
                              <span>Stage</span>
                            </Button>
                          )}

                          <Button
                            variant="ghost"
                            size="xs"
                            onClick={() =>
                              setActiveCover({
                                jobId: m.job.id,
                                title: m.job.title,
                                company: m.job.company,
                              })
                            }
                            className="text-text-tertiary hover:text-accent gap-1"
                          >
                            <Sparkles className="w-3 h-3" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}

                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-text-tertiary italic text-xs">
                      No jobs match the current filters. Adjust search query or source filters above.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* KANBAN BOARD VIEW */}
      {viewMode === "kanban" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
          {KANBAN_STAGES.map((col) => {
            // Find jobs assigned to this stage or matched if col.id === "saved"
            const colJobs = filtered.filter((m) => {
              const assigned = stagedJobs[m.job.id];
              if (assigned) return assigned === col.id;
              if (col.id === "needs_review") return m.recommended;
              if (col.id === "saved") return !m.recommended;
              return false;
            });

            return (
              <div
                key={col.id}
                className="bg-surface border border-border rounded-xl p-3 flex flex-col min-h-[360px]"
              >
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-border">
                  <span className={`text-xs font-mono font-semibold ${col.color}`}>
                    {col.label}
                  </span>
                  <span className="text-[11px] font-mono text-text-tertiary px-1.5 py-0.5 rounded bg-surface-2 border border-border">
                    {colJobs.length}
                  </span>
                </div>

                <div className="flex flex-col gap-2 overflow-y-auto flex-1 max-h-[500px]">
                  {colJobs.map((m) => (
                    <div
                      key={m.job.id}
                      className="bg-surface-2 border border-border hover:border-accent/40 rounded-lg p-2.5 transition-all text-xs flex flex-col gap-1.5 shadow-sm"
                    >
                      <div className="font-semibold text-text-primary leading-tight">
                        {m.job.title}
                      </div>
                      <div className="text-[11px] text-text-secondary flex items-center justify-between">
                        <span>{m.job.company}</span>
                        <span className="font-mono text-accent font-medium">
                          {Math.round(m.score * 100)}%
                        </span>
                      </div>

                      {m.job.salary_range && (
                        <div className="text-[10px] text-emerald-400 font-mono">
                          {m.job.salary_range}
                        </div>
                      )}

                      <div className="flex items-center justify-between pt-1 border-t border-border/50 text-[10px]">
                        <span className="font-mono text-text-tertiary uppercase">
                          {m.job.source}
                        </span>

                        <div className="flex items-center gap-1">
                          {col.id !== "applied" && (
                            <button
                              onClick={() => handleStageJob(m.job.id, "applied")}
                              className="text-text-tertiary hover:text-emerald-400 font-mono text-[10px] flex items-center gap-0.5"
                              title="Mark Applied"
                            >
                              <Send className="w-2.5 h-2.5" />
                              Apply
                            </button>
                          )}
                          {col.id !== "needs_review" && (
                            <button
                              onClick={() => handleStageJob(m.job.id, "needs_review")}
                              className="text-text-tertiary hover:text-amber-400 font-mono text-[10px] flex items-center gap-0.5"
                              title="Move to Needs Review"
                            >
                              <ArrowRight className="w-2.5 h-2.5" />
                              Review
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}

                  {colJobs.length === 0 && (
                    <div className="text-center py-8 text-text-tertiary italic text-[11px]">
                      No items
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
