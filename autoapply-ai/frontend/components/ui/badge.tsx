import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "amber" | "green" | "red" | "accent" | "outline";
}

export function Badge({
  className,
  variant = "default",
  ...props
}: BadgeProps) {
  const variants = {
    default: "bg-surface-2 text-text-secondary border-border",
    amber:
      "bg-semantic-amber-dim text-semantic-amber border-semantic-amber/30",
    green:
      "bg-semantic-green-dim text-semantic-green border-semantic-green/30",
    red: "bg-semantic-red-dim text-semantic-red border-semantic-red/30",
    accent: "bg-accent/15 text-accent border-accent/30",
    outline: "text-text-secondary border-border bg-transparent",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium border border-solid tracking-wide",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}
