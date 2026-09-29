import React from "react";
import { cn } from "@/lib/utils";

interface ConfidenceRingProps {
  value: number; // 0.0 to 1.0 or 0 to 100
  size?: "sm" | "md" | "lg";
  strokeWidth?: number;
  className?: string;
  showText?: boolean;
}

export function ConfidenceRing({
  value,
  size = "md",
  strokeWidth = 3,
  className,
  showText = true,
}: ConfidenceRingProps) {
  // Normalize value to 0-100
  const normalized = value > 1 ? Math.min(100, Math.max(0, value)) : Math.min(100, Math.max(0, value * 100));

  const dimensions = {
    sm: { diameter: 26, fontSize: "text-[9px]" },
    md: { diameter: 42, fontSize: "text-[11px]" },
    lg: { diameter: 64, fontSize: "text-sm" },
  };

  const { diameter, fontSize } = dimensions[size];
  const radius = (diameter - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (normalized / 100) * circumference;

  // Determine semantic color based on score thresholds
  let strokeColor = "#8B7CF7"; // default accent indigo
  if (normalized >= 75) {
    strokeColor = "#34D399"; // green
  } else if (normalized >= 45) {
    strokeColor = "#F5A623"; // amber
  } else {
    strokeColor = "#F0596B"; // red
  }

  return (
    <div
      className={cn("relative inline-flex items-center justify-center shrink-0", className)}
      style={{ width: diameter, height: diameter }}
    >
      <svg
        width={diameter}
        height={diameter}
        className="-rotate-90 transform"
        aria-hidden="true"
      >
        {/* Background track */}
        <circle
          cx={diameter / 2}
          cy={diameter / 2}
          r={radius}
          stroke="#24272E"
          strokeWidth={strokeWidth}
          fill="transparent"
        />
        {/* Foreground progress */}
        <circle
          cx={diameter / 2}
          cy={diameter / 2}
          r={radius}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="transparent"
          className="transition-all duration-500 ease-out"
        />
      </svg>
      {showText && (
        <span
          className={cn(
            "absolute font-mono font-semibold tracking-tighter text-text-primary",
            fontSize
          )}
        >
          {Math.round(normalized)}%
        </span>
      )}
    </div>
  );
}
