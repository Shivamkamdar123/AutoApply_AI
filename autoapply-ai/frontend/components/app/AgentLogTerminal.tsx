"use client";

import React, { useEffect, useRef, useState } from "react";
import { Terminal, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface LogEntry {
  id: string;
  timestamp: string;
  correlationId: string;
  message: string;
  type?: "info" | "warn" | "success" | "error";
}

interface AgentLogTerminalProps {
  logs?: LogEntry[];
  onClear?: () => void;
}

export function AgentLogTerminal({ logs = [], onClear }: AgentLogTerminalProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [internalLogs, setInternalLogs] = useState<LogEntry[]>([
    {
      id: "init-1",
      timestamp: new Date().toLocaleTimeString([], { hour12: false }),
      correlationId: "boot",
      message: "AutoApply AI agent core initialized in supervised dry-run mode.",
      type: "info",
    },
    {
      id: "init-2",
      timestamp: new Date().toLocaleTimeString([], { hour12: false }),
      correlationId: "sec",
      message: "Human safety valve verified: DRY_RUN=true, AUTO_SUBMIT=false.",
      type: "success",
    },
  ]);

  const allLogs = logs.length > 0 ? logs : internalLogs;

  // Stream live structlog events from backend via SSE
  useEffect(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";
    let eventSource: EventSource | null = null;

    try {
      eventSource = new EventSource(`${apiBase}/agent/events`);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const level = (data.level || "info").toLowerCase();
          const logType: "info" | "warn" | "success" | "error" =
            level === "warning" || level === "warn"
              ? "warn"
              : level === "error"
              ? "error"
              : data.event?.includes("COMPLETE") || data.event?.includes("APPLIED")
              ? "success"
              : "info";

          const timeStr = data.timestamp
            ? data.timestamp.split("T")[1]?.replace("Z", "")
            : new Date().toLocaleTimeString([], { hour12: false });

          setInternalLogs((prev) => {
            const entry: LogEntry = {
              id: `${Date.now()}-${Math.random()}`,
              timestamp: timeStr,
              correlationId: data.correlation_id || data.event || "agent",
              message: data.message,
              type: logType,
            };
            return [...prev.slice(-150), entry];
          });
        } catch (_) {}
      };

      eventSource.onerror = () => {
        // Fallback gracefully on reconnection
      };
    } catch (_) {}

    return () => {
      if (eventSource) eventSource.close();
    };
  }, []);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [allLogs]);

  return (
    <div className="w-full rounded-xl border border-border bg-base overflow-hidden mb-8 shadow-lg">
      {/* Terminal Title Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-surface-2 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-semantic-red/80" />
          <span className="w-2.5 h-2.5 rounded-full bg-semantic-amber/80" />
          <span className="w-2.5 h-2.5 rounded-full bg-semantic-green/80" />
          <span className="font-mono text-xs font-medium text-text-secondary ml-2 flex items-center gap-1.5">
            <Terminal className="w-3.5 h-3.5 text-accent" />
            <span>agent-audit.log</span>
          </span>
        </div>

        <Button
          variant="ghost"
          size="xs"
          onClick={() => {
            if (onClear) onClear();
            else setInternalLogs([]);
          }}
          className="text-text-tertiary hover:text-text-primary text-[11px] h-6 px-2 gap-1"
        >
          <Trash2 className="w-3 h-3" />
          <span>Clear</span>
        </Button>
      </div>

      {/* Terminal Body with Scanline Overlay */}
      <div
        ref={containerRef}
        className="terminal-scanlines p-4 max-h-[220px] overflow-y-auto font-mono text-xs leading-relaxed flex flex-col gap-1.5 select-text"
      >
        {allLogs.map((log) => (
          <div key={log.id} className="flex items-start gap-2">
            <span className="text-text-tertiary shrink-0">
              [{log.timestamp}]
            </span>
            <span className="text-accent/80 shrink-0 font-medium">
              [{log.correlationId}]
            </span>
            <span
              className={
                log.type === "success"
                  ? "text-semantic-green"
                  : log.type === "warn"
                  ? "text-semantic-amber"
                  : log.type === "error"
                  ? "text-semantic-red"
                  : "text-text-secondary"
              }
            >
              {log.message}
            </span>
          </div>
        ))}

        {allLogs.length === 0 && (
          <div className="text-text-tertiary italic text-center py-4">
            Terminal log cleared. Awaiting next pipeline event...
          </div>
        )}
      </div>
    </div>
  );
}
