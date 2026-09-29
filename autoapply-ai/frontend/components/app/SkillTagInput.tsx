"use client";

import React, { useState } from "react";
import { X, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SkillTagInputProps {
  skills: string[];
  onChange: (skills: string[]) => void;
}

export function SkillTagInput({ skills, onChange }: SkillTagInputProps) {
  const [inputValue, setInputValue] = useState("");

  const handleAdd = () => {
    const trimmed = inputValue.trim().toLowerCase();
    if (trimmed && !skills.includes(trimmed)) {
      onChange([...skills, trimmed]);
      setInputValue("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  const handleRemove = (skillToRemove: string) => {
    onChange(skills.filter((s) => s !== skillToRemove));
  };

  return (
    <div className="flex flex-col gap-2.5">
      {/* Existing tags list */}
      <div className="flex flex-wrap gap-1.5 p-3 rounded-lg border border-border bg-base min-h-[44px]">
        {skills.map((skill) => (
          <span
            key={skill}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-2 border border-border text-text-primary font-mono text-xs"
          >
            <span>{skill}</span>
            <button
              type="button"
              onClick={() => handleRemove(skill)}
              className="text-text-tertiary hover:text-semantic-red transition-colors"
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}

        {skills.length === 0 && (
          <span className="text-xs text-text-tertiary italic self-center">
            No skills specified. Add your core frameworks, languages, and technical tools below.
          </span>
        )}
      </div>

      {/* Input row */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. Python, FastAPI, Docker, PostgreSQL, Kubernetes (Press Enter to add)"
          className="flex-1 rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
        />
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={handleAdd}
          disabled={!inputValue.trim()}
          className="gap-1 shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add Skill</span>
        </Button>
      </div>
    </div>
  );
}
