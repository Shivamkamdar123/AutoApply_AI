"use client";

import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { Loader2, Copy, Check, Sparkles } from "lucide-react";

interface CoverLetterModalProps {
  jobId: string | null;
  jobTitle?: string;
  company?: string;
  open: boolean;
  onClose: () => void;
}

export function CoverLetterModal({
  jobId,
  jobTitle = "",
  company = "",
  open,
  onClose,
}: CoverLetterModalProps) {
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [provider, setProvider] = useState<string>("heuristic");
  const { toast } = useToast();

  useEffect(() => {
    if (!open || !jobId) {
      setContent("");
      setCopied(false);
      return;
    }

    setLoading(true);
    api
      .generateCoverLetter({
        job_id: jobId,
        job_title: jobTitle,
        company: company,
      })
      .then((res) => {
        setContent(res.cover_letter);
        setProvider(res.provider);
        setLoading(false);
      })
      .catch((err) => {
        setContent(`Could not generate cover letter: ${err.message}`);
        setLoading(false);
      });
  }, [open, jobId, jobTitle, company]);

  const handleCopy = () => {
    if (!content) return;
    navigator.clipboard.writeText(content);
    setCopied(true);
    toast("Cover letter copied to clipboard!", "success");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Dialog open={open} onOpenChange={(val) => !val && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col p-6">
        <DialogHeader>
          <div className="flex items-center gap-1.5 text-xs font-mono text-accent">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Tailored Note ({provider})</span>
          </div>
          <DialogTitle className="text-base font-semibold">
            Application Note: {company} — {jobTitle}
          </DialogTitle>
          <DialogDescription className="text-xs">
            Synthesized dynamically from candidate profile skills and target role requirements.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 min-h-[260px] relative">
          {loading ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-text-tertiary text-xs bg-surface-2">
              <Loader2 className="w-5 h-5 animate-spin text-accent" />
              <span>Generating tailored application note...</span>
            </div>
          ) : (
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={12}
              className="w-full h-full rounded-md border border-border bg-base p-3 text-xs font-mono text-text-primary leading-relaxed focus:outline-none focus:ring-1 focus:ring-accent resize-none"
            />
          )}
        </div>

        <DialogFooter className="flex justify-between items-center">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            disabled={loading || !content}
            className="gap-1.5"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-semantic-green" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy Note</span>
              </>
            )}
          </Button>

          <Button variant="secondary" size="sm" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
