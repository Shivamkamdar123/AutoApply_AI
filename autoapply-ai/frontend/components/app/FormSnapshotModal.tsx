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
import { Loader2, Shield } from "lucide-react";

interface FormSnapshotModalProps {
  jobId: string | null;
  jobTitle?: string;
  company?: string;
  open: boolean;
  onClose: () => void;
}

export function FormSnapshotModal({
  jobId,
  jobTitle,
  company,
  open,
  onClose,
}: FormSnapshotModalProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !jobId) {
      setImageUrl(null);
      setError(null);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);

    api
      .fetchScreenshotBlob(jobId)
      .then((url) => {
        if (isMounted) {
          setImageUrl(url);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(
            err.message ||
              "No live snapshot found on disk for this job. (A snapshot is created during the INSPECTING_FIELDS stage)."
          );
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [open, jobId]);

  return (
    <Dialog open={open} onOpenChange={(val) => !val && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col p-6">
        <DialogHeader>
          <div className="flex items-center gap-2 text-xs font-mono text-text-tertiary uppercase">
            <Shield className="w-3.5 h-3.5 text-accent" />
            <span>Browser Verification Snapshot</span>
          </div>
          <DialogTitle className="text-base font-semibold">
            {jobTitle ? `${jobTitle} @ ${company}` : "Form Verification"}
          </DialogTitle>
          <DialogDescription className="text-xs">
            Captured by Playwright during the INSPECTING_FIELDS phase before halting at AWAITING_REVIEW.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 min-h-[300px] max-h-[550px] overflow-auto rounded-lg border border-border bg-base p-2 flex items-center justify-center">
          {loading && (
            <div className="flex flex-col items-center gap-2 text-text-tertiary text-xs">
              <Loader2 className="w-5 h-5 animate-spin text-accent" />
              <span>Streaming verification snapshot from agent...</span>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center gap-1.5 text-text-tertiary text-xs text-center max-w-sm">
              <span className="text-semantic-amber font-mono font-medium">
                Notice
              </span>
              <span>{error}</span>
            </div>
          )}

          {imageUrl && !loading && (
            <img
              src={imageUrl}
              alt="Form Snapshot"
              className="w-full h-auto rounded border border-border"
            />
          )}
        </div>

        <DialogFooter className="flex justify-between items-center text-xs text-text-tertiary">
          <span>🛡️ Verified in Dry-Run mode. No live submission made.</span>
          <Button variant="secondary" size="sm" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
