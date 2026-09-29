"use client";

import React, { useState } from "react";
import { JobMatch } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfidenceRing } from "./ConfidenceRing";
import { CoverLetterModal } from "./CoverLetterModal";
import { Search, Sparkles, ExternalLink, Filter } from "lucide-react";

interface JobsTableProps {
  matches: JobMatch[];
  sourcesStatus?: Record<string, string>;
  isLoading?: boolean;
}

export function JobsTable({
  matches,
  sourcesStatus = {},
  isLoading = false,
}: JobsTableProps) {
  const [filterText, setFilterText] = useState("");
  const [selectedSource, setSelectedSource] = useState<string>("all");

  const [activeCover, setActiveCover] = useState<{
    jobId: string;
    title: string;
    company: string;
  } | null>(null);

  const sources = ["all", "greenhouse", "lever", "remotive", "remoteok", "sample"];

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
            Ranked by semantic match against your skills and career preferences.
          </p>
        </div>

        {/* Per-source live health chips */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {Object.entries(sourcesStatus).map(([source, status]) => {
            const isOk = status === "ok";
            return (
              <span
                key={source}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-surface-2 border border-border text-text-secondary"
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    isOk ? "bg-semantic-green" : "bg-semantic-amber"
                  }`}
                />
                <span className="capitalize">{source}:</span>
                <span className={isOk ? "text-semantic-green" : "text-semantic-amber"}>
                  {status}
                </span>
              </span>
            );
          })}
        </div>
      </div>

      {/* Search and Source Filter Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 text-text-tertiary absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter matched postings by title, company, or keyword..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            className="w-full bg-surface-2 border border-border rounded-lg pl-9 pr-3 py-1.5 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
          />
        </div>

        {/* Source Dropdown Filter */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {sources.map((src) => (
            <button
              key={src}
              onClick={() => setSelectedSource(src)}
              className={`px-2.5 py-1 rounded-md text-xs font-mono capitalize transition-colors shrink-0 ${
                selectedSource === src
                  ? "bg-accent/15 text-accent border border-accent/30 font-medium"
                  : "bg-surface-2 text-text-tertiary hover:text-text-secondary border border-border"
              }`}
            >
              {src}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <Card className="overflow-hidden bg-surface border-border">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border bg-surface-2/60 text-text-tertiary font-mono">
                <th className="py-2.5 px-4 font-normal">Job Title</th>
                <th className="py-2.5 px-4 font-normal">Company</th>
                <th className="py-2.5 px-4 font-normal">Fit Score</th>
                <th className="py-2.5 px-4 font-normal">Source</th>
                <th className="py-2.5 px-4 font-normal">Fit Tier</th>
                <th className="py-2.5 px-4 font-normal text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((m) => (
                <tr
                  key={m.job.id}
                  className="hover:bg-surface-2/50 transition-colors group"
                >
                  <td className="py-3 px-4 font-medium text-text-primary">
                    <div className="flex items-center gap-2">
                      <span>{m.job.title}</span>
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
                    {m.job.company}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-1.5">
                      <ConfidenceRing value={m.score} size="sm" strokeWidth={2.5} />
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-mono text-[11px] text-text-tertiary uppercase">
                      {m.job.source || "sample"}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    {m.recommended ? (
                      <Badge variant="accent">★ RECOMMENDED</Badge>
                    ) : (
                      <Badge variant="default">MATCHED</Badge>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
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
                      className="gap-1 text-text-tertiary hover:text-accent"
                    >
                      <Sparkles className="w-3 h-3" />
                      <span>Note</span>
                    </Button>
                  </td>
                </tr>
              ))}

              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="py-8 text-center text-text-tertiary italic text-xs"
                  >
                    No matched postings match the search criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
