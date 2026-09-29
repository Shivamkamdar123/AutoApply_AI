"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import {
  LayoutDashboard,
  User,
  Play,
  Upload,
  LogOut,
  Search,
  CheckCircle,
  Shield,
  FileText,
} from "lucide-react";
import { useAuth } from "@/lib/auth";

interface CommandPaletteProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  onTriggerPipeline?: () => void;
  onTriggerUpload?: () => void;
}

export function CommandPalette({
  open: controlledOpen,
  onOpenChange,
  onTriggerPipeline,
  onTriggerUpload,
}: CommandPaletteProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const router = useRouter();
  const { logout, isAuthenticated } = useAuth();

  const isControlled = controlledOpen !== undefined;
  const isOpen = isControlled ? controlledOpen : internalOpen;
  const setOpen = isControlled ? onOpenChange! : setInternalOpen;

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen(!isOpen);
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [isOpen, setOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4 bg-black/75 backdrop-blur-sm animate-in fade-in-0 duration-150">
      <div
        className="fixed inset-0"
        onClick={() => setOpen(false)}
        aria-hidden="true"
      />
      <Command
        className="relative w-full max-w-xl rounded-xl border border-border bg-surface-2 text-text-primary shadow-2xl overflow-hidden focus:outline-none"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center border-b border-border px-3">
          <Search className="mr-2.5 h-4 w-4 shrink-0 text-text-tertiary" />
          <Command.Input
            placeholder="Type a command, page, or action..."
            className="flex h-12 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-text-tertiary disabled:cursor-not-allowed disabled:opacity-50 text-text-primary"
            autoFocus
          />
          <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border border-border bg-surface px-1.5 font-mono text-[10px] font-medium text-text-tertiary">
            ESC
          </kbd>
        </div>

        <Command.List className="max-h-[300px] overflow-y-auto p-2 text-xs">
          <Command.Empty className="py-6 text-center text-text-tertiary">
            No matching actions found.
          </Command.Empty>

          <Command.Group heading="Navigation" className="text-text-tertiary font-medium px-2 py-1.5 text-[11px]">
            <Command.Item
              onSelect={() => {
                setOpen(false);
                router.push("/dashboard");
              }}
              className="flex items-center gap-2.5 px-2.5 py-2 rounded-md cursor-pointer select-none text-text-primary hover:bg-surface-3 transition-colors data-[selected=true]:bg-surface-3"
            >
              <LayoutDashboard className="h-4 w-4 text-accent" />
              <span>Go to Dashboard</span>
            </Command.Item>
            <Command.Item
              onSelect={() => {
                setOpen(false);
                router.push("/profile");
              }}
              className="flex items-center gap-2.5 px-2.5 py-2 rounded-md cursor-pointer select-none text-text-primary hover:bg-surface-3 transition-colors data-[selected=true]:bg-surface-3"
            >
              <User className="h-4 w-4 text-accent" />
              <span>Candidate Profile & Settings</span>
            </Command.Item>
          </Command.Group>

          <Command.Group heading="Agent Actions" className="text-text-tertiary font-medium px-2 py-1.5 text-[11px] mt-2">
            <Command.Item
              onSelect={() => {
                setOpen(false);
                if (onTriggerPipeline) {
                  onTriggerPipeline();
                } else {
                  router.push("/dashboard?run=true");
                }
              }}
              className="flex items-center gap-2.5 px-2.5 py-2 rounded-md cursor-pointer select-none text-text-primary hover:bg-surface-3 transition-colors data-[selected=true]:bg-surface-3"
            >
              <Play className="h-4 w-4 text-semantic-green" />
              <span>Run Pipeline Match Cycle</span>
            </Command.Item>
            <Command.Item
              onSelect={() => {
                setOpen(false);
                if (onTriggerUpload) {
                  onTriggerUpload();
                } else {
                  router.push("/profile#resume");
                }
              }}
              className="flex items-center gap-2.5 px-2.5 py-2 rounded-md cursor-pointer select-none text-text-primary hover:bg-surface-3 transition-colors data-[selected=true]:bg-surface-3"
            >
              <Upload className="h-4 w-4 text-text-secondary" />
              <span>Upload New Resume File</span>
            </Command.Item>
          </Command.Group>

          {isAuthenticated && (
            <Command.Group heading="Account" className="text-text-tertiary font-medium px-2 py-1.5 text-[11px] mt-2">
              <Command.Item
                onSelect={() => {
                  setOpen(false);
                  logout();
                }}
                className="flex items-center gap-2.5 px-2.5 py-2 rounded-md cursor-pointer select-none text-semantic-red hover:bg-surface-3 transition-colors data-[selected=true]:bg-surface-3"
              >
                <LogOut className="h-4 w-4 text-semantic-red" />
                <span>Log Out of AutoApply AI</span>
              </Command.Item>
            </Command.Group>
          )}
        </Command.List>
      </Command>
    </div>
  );
}
