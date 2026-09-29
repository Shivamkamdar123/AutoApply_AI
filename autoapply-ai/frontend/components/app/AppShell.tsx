"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  User,
  LogOut,
  Shield,
  Search,
  Menu,
  X,
  Bot,
  Sparkles,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CommandPalette } from "./CommandPalette";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

interface AppShellProps {
  children: React.ReactNode;
  agentActive?: boolean;
}

export function AppShell({ children, agentActive = false }: AppShellProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const toggleAgentMutation = useMutation({
    mutationFn: () => api.toggleAgent(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["summary"] });
      toast(
        `Agent status: ${data.agent_active ? "ACTIVE (Supervised)" : "IDLE"}`,
        data.agent_active ? "success" : "info"
      );
    },
    onError: (err: any) => {
      toast(`Failed to toggle agent: ${err.message}`, "error");
    },
  });

  const navItems = [
    {
      name: "Dashboard",
      href: "/dashboard",
      icon: LayoutDashboard,
      active: pathname === "/dashboard",
    },
    {
      name: "Profile & Settings",
      href: "/profile",
      icon: User,
      active: pathname === "/profile",
    },
  ];

  return (
    <div className="min-h-screen bg-base text-text-primary flex flex-col md:flex-row">
      <CommandPalette
        open={commandPaletteOpen}
        onOpenChange={setCommandPaletteOpen}
      />

      {/* Desktop Left Sidebar */}
      <aside className="hidden md:flex w-64 flex-col border-r border-border bg-surface shrink-0 h-screen sticky top-0 justify-between p-4">
        <div className="flex flex-col gap-6">
          {/* Brand header */}
          <Link href="/dashboard" className="flex items-center gap-2.5 px-2 group">
            <span className="h-7 w-7 rounded-md bg-accent/20 border border-accent/40 flex items-center justify-center font-mono font-bold text-xs text-accent transition-transform group-hover:scale-105">
              AA
            </span>
            <span className="font-display font-bold text-base tracking-tight text-text-primary">
              AutoApply <span className="text-accent">AI</span>
            </span>
          </Link>

          {/* Navigation Links */}
          <nav className="flex flex-col gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors",
                    item.active
                      ? "bg-surface-3 text-text-primary font-semibold border-hairline shadow-sm"
                      : "text-text-secondary hover:text-text-primary hover:bg-surface-2"
                  )}
                >
                  <Icon
                    className={cn(
                      "w-4 h-4",
                      item.active ? "text-accent" : "text-text-tertiary"
                    )}
                  />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer: User & Quick Actions */}
        <div className="flex flex-col gap-3 pt-4 border-t border-border">
          {/* Quick Command Trigger */}
          <button
            onClick={() => setCommandPaletteOpen(true)}
            className="flex items-center justify-between px-2.5 py-1.5 rounded-md border border-border bg-surface-2 text-text-tertiary hover:text-text-secondary text-xs transition-colors w-full"
          >
            <span className="flex items-center gap-2">
              <Search className="w-3.5 h-3.5" />
              <span>Actions</span>
            </span>
            <kbd className="font-mono text-[10px] bg-surface-3 px-1.5 py-0.5 rounded border border-border">
              ⌘K
            </kbd>
          </button>

          {/* User profile row */}
          <div className="flex items-center justify-between px-2 py-1">
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-medium text-text-primary truncate">
                {user?.full_name || user?.email || "Candidate"}
              </span>
              <span className="text-[11px] text-text-tertiary truncate">
                {user?.email}
              </span>
            </div>
            <button
              onClick={logout}
              title="Log Out"
              className="text-text-tertiary hover:text-semantic-red p-1 rounded transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Body Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Sticky Glass Top Navigation Bar */}
        <header className="sticky top-0 z-40 nav-glass px-4 md:px-8 py-3 flex items-center justify-between">
          {/* Left: Mobile hamburger & breadcrumbs */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-1.5 text-text-secondary hover:text-text-primary rounded-md"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <div className="hidden sm:flex items-center gap-2 text-xs font-mono text-text-tertiary">
              <span className="text-text-secondary font-medium">autoapply-agent</span>
              <span>/</span>
              <span>{pathname.replace("/", "") || "overview"}</span>
            </div>
          </div>

          {/* Right: Controls & Status Badges */}
          <div className="flex items-center gap-3">
            {/* Safety Badge */}
            <Badge variant="amber" className="hidden sm:inline-flex" title="Submissions require manual human approval">
              <Shield className="w-3 h-3" />
              <span>SAFETY VALVE: DRY RUN</span>
            </Badge>

            {/* Agent Live Toggle */}
            <Button
              variant={agentActive ? "signature" : "secondary"}
              size="xs"
              onClick={() => toggleAgentMutation.mutate()}
              disabled={toggleAgentMutation.isPending}
              className="gap-1.5"
            >
              <span
                className={cn(
                  "w-1.5 h-1.5 rounded-full",
                  agentActive
                    ? "bg-white animate-pulse"
                    : "bg-text-tertiary"
                )}
              />
              <span>{agentActive ? "Agent Active" : "Agent Idle"}</span>
            </Button>
          </div>
        </header>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden border-b border-border bg-surface-2 p-4 flex flex-col gap-2">
            {navItems.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium",
                  item.active
                    ? "bg-surface-3 text-text-primary font-semibold"
                    : "text-text-secondary hover:text-text-primary"
                )}
              >
                <item.icon className="w-4 h-4" />
                <span>{item.name}</span>
              </Link>
            ))}
            <div className="pt-2 border-t border-border flex justify-between items-center text-xs">
              <span className="text-text-secondary">{user?.email}</span>
              <button
                onClick={logout}
                className="text-semantic-red flex items-center gap-1 font-medium"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Log Out</span>
              </button>
            </div>
          </div>
        )}

        {/* Page Content */}
        <main className="flex-1 p-4 md:p-8 max-w-7xl mx-auto w-full">
          {children}
        </main>
      </div>
    </div>
  );
}
