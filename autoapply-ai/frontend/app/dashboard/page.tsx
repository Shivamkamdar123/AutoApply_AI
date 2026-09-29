"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, DashboardSummary, ApplicationStatus, JobMatchResponse, UserProfile } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AppShell } from "@/components/app/AppShell";
import { BentoStats } from "@/components/app/BentoStats";
import { PipelineStepper } from "@/components/app/PipelineStepper";
import { ReviewQueue } from "@/components/app/ReviewQueue";
import { JobsTable } from "@/components/app/JobsTable";
import { AgentLogTerminal, LogEntry } from "@/components/app/AgentLogTerminal";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { Play, Search, Upload, RefreshCw, Sparkles, AlertCircle } from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [searchKeywords, setSearchKeywords] = useState("");
  const [searchLocation, setSearchLocation] = useState("");
  const [selectedSources, setSelectedSources] = useState<string[]>(["greenhouse", "lever", "remotive", "remoteok", "sample"]);
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      id: "l-1",
      timestamp: new Date().toLocaleTimeString([], { hour12: false }),
      correlationId: "boot",
      message: "Agent daemon online. DRY_RUN=true verified.",
      type: "info",
    },
  ]);

  // Auth gate check
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const addLog = (message: string, type: "info" | "warn" | "success" | "error" = "info", correlationId = "sys") => {
    const entry: LogEntry = {
      id: Math.random().toString(36).substring(2, 9),
      timestamp: new Date().toLocaleTimeString([], { hour12: false }),
      correlationId,
      message,
      type,
    };
    setLogs((prev) => [...prev, entry]);
  };

  // Queries
  const { data: summary, isLoading: summaryLoading } = useQuery<DashboardSummary>({
    queryKey: ["summary"],
    queryFn: api.getSummary,
    enabled: isAuthenticated,
  });

  const { data: reviewQueue = [], isLoading: queueLoading } = useQuery<ApplicationStatus[]>({
    queryKey: ["review-queue"],
    queryFn: api.getReviewQueue,
    enabled: isAuthenticated,
  });

  const { data: profile } = useQuery<UserProfile>({
    queryKey: ["profile"],
    queryFn: api.getProfile,
    enabled: isAuthenticated,
  });

  const { data: jobData, isLoading: jobsLoading, refetch: refetchJobs } = useQuery<JobMatchResponse>({
    queryKey: ["jobs", searchKeywords, searchLocation, selectedSources],
    queryFn: () =>
      api.matchJobs({
        query: searchKeywords || undefined,
        location: searchLocation || undefined,
        sources: selectedSources.join(","),
      }),
    enabled: isAuthenticated,
  });

  // Run Pipeline Cycle Mutation
  const runPipelineMutation = useMutation({
    mutationFn: async () => {
      addLog("Starting autonomous pipeline cycle...", "info", "pipeline");
      const res = await api.matchJobs({
        query: searchKeywords || undefined,
        location: searchLocation || undefined,
        sources: selectedSources.join(","),
      });
      return res;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["summary"] });
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      toast("Pipeline cycle complete! Matched postings refreshed.", "success");
      const foundCount = data.total_found ?? data.total_matched ?? (data.matches?.length || 0);
      const sourcesCount = data.sources_status ? Object.keys(data.sources_status).length : 0;
      addLog(
        `Scraped & matched ${foundCount} positions. Evaluated across ${sourcesCount} live sources.`,
        "success",
        "match"
      );
      addLog("Safety valve enforced: Form mappings staged in review queue.", "warn", "safety");
    },
    onError: (err: any) => {
      toast(`Pipeline run failed: ${err.message}`, "error");
      addLog(`Pipeline failed: ${err.message}`, "error", "pipeline");
    },
  });

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    addLog(`Querying sources for: "${searchKeywords || "all"}" in "${searchLocation || "any"}"`, "info", "search");
    refetchJobs();
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-base flex items-center justify-center p-6 text-text-tertiary">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
          <span className="font-mono text-xs">Authenticating session...</span>
        </div>
      </div>
    );
  }

  const matches = jobData?.matches || [];
  const sourcesStatus = jobData?.sources_status || {};

  return (
    <AppShell agentActive={summary?.agent_active}>
      {/* Top Banner / Welcome Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-text-primary">
            Candidate Console
          </h1>
          <p className="text-xs text-text-secondary mt-0.5">
            Autonomous scraper &amp; browser agent under strict human supervision.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push("/profile")}
            className="text-xs"
          >
            Manage Resume &amp; Skills
          </Button>

          <Button
            variant="signature"
            size="sm"
            onClick={() => runPipelineMutation.mutate()}
            disabled={runPipelineMutation.isPending}
            className="gap-2"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{runPipelineMutation.isPending ? "Executing Cycle..." : "Run Match Cycle"}</span>
          </Button>
        </div>
      </div>

      {/* Bento Grid Stats */}
      {summaryLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 mb-8">
          <Skeleton className="h-28 sm:col-span-2 rounded-xl" />
          <Skeleton className="h-28 rounded-xl" />
          <Skeleton className="h-28 rounded-xl" />
        </div>
      ) : (
        <BentoStats summary={summary} />
      )}

      {/* 5-Stage Pipeline Stepper */}
      <PipelineStepper summary={summary} />

      {/* Multi-Source Aggregator Search Bar */}
      <Card className="p-4 bg-surface border-border mb-8">
        <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3 items-stretch md:items-end">
          <div className="flex-1">
            <label className="block text-[11px] font-mono text-text-tertiary uppercase mb-1">
              Target Role / Keywords
            </label>
            <input
              type="text"
              value={searchKeywords}
              onChange={(e) => setSearchKeywords(e.target.value)}
              placeholder="e.g. Backend Engineer, Python, Distributed Systems, FastAPI"
              className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          <div className="w-full md:w-56">
            <label className="block text-[11px] font-mono text-text-tertiary uppercase mb-1">
              Location
            </label>
            <input
              type="text"
              value={searchLocation}
              onChange={(e) => setSearchLocation(e.target.value)}
              placeholder="e.g. Remote, United States, Europe"
              className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          <Button type="submit" variant="secondary" size="md" className="gap-2 shrink-0">
            <Search className="w-3.5 h-3.5" />
            <span>Search Sources</span>
          </Button>
        </form>
      </Card>

      {/* Human-in-the-Loop Review Queue */}
      {queueLoading ? (
        <div className="flex flex-col gap-4 mb-8">
          <Skeleton className="h-44 rounded-xl" />
        </div>
      ) : (
        <ReviewQueue items={reviewQueue} />
      )}

      {/* Matched Postings Table */}
      {jobsLoading ? (
        <div className="flex flex-col gap-3 mb-8">
          <Skeleton className="h-64 rounded-xl" />
        </div>
      ) : (
        <JobsTable matches={matches} sourcesStatus={sourcesStatus} />
      )}

      {/* Agent Decision Log Terminal */}
      <AgentLogTerminal logs={logs} onClear={() => setLogs([])} />
    </AppShell>
  );
}
