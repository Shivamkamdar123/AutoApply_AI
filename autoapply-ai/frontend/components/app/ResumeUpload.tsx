"use client";

import React, { useRef, useState } from "react";
import { ResumeItem } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Upload, FileText, Trash2, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { formatDate } from "@/lib/utils";

interface ResumeUploadProps {
  resumes: ResumeItem[];
  onUpload: (file: File, autoPopulate: boolean) => Promise<any>;
  onDelete: (id: string) => Promise<any>;
  isUploading?: boolean;
}

export function ResumeUpload({
  resumes,
  onUpload,
  onDelete,
  isUploading = false,
}: ResumeUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [autoPopulate, setAutoPopulate] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const validateAndUpload = async (file: File) => {
    setErrorMessage(null);

    // Validate size (max 15MB)
    if (file.size > 15 * 1024 * 1024) {
      setErrorMessage("File exceeds 15MB limit. Please upload a smaller resume.");
      return;
    }

    // Validate extension
    const allowed = [".pdf", ".docx", ".txt"];
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    if (!allowed.includes(ext)) {
      setErrorMessage("Unsupported file type. Please upload a .pdf, .docx, or .txt file.");
      return;
    }

    try {
      await onUpload(file, autoPopulate);
    } catch (err: any) {
      const msg = err.message || "";
      if (msg.includes("ScannedImageResumeError") || msg.includes("scanned")) {
        setErrorMessage("Scanned image PDF detected. Please upload a text-selectable PDF or DOCX.");
      } else if (msg.includes("EmptyResumeError") || msg.includes("empty")) {
        setErrorMessage("Uploaded resume appears to be empty. Please check the file contents.");
      } else if (msg.includes("UnsupportedScriptError") || msg.includes("script")) {
        setErrorMessage("Unsupported non-English character script detected.");
      } else {
        setErrorMessage(msg || "Failed to parse resume file.");
      }
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      {/* Drag & Drop Upload Container */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-3 ${
          isDragOver
            ? "border-accent bg-accent/5 shadow-glow"
            : "border-border bg-surface-2 hover:border-border-strong hover:bg-surface-2/80"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              validateAndUpload(e.target.files[0]);
            }
          }}
        />

        {isUploading ? (
          <div className="flex flex-col items-center gap-2 text-accent">
            <Loader2 className="w-8 h-8 animate-spin" />
            <span className="text-xs font-mono">
              Parsing resume layout & extracting skills...
            </span>
          </div>
        ) : (
          <>
            <div className="w-10 h-10 rounded-full bg-surface-3 flex items-center justify-center text-text-secondary border border-border">
              <Upload className="w-5 h-5 text-accent" />
            </div>
            <div>
              <p className="text-sm font-medium text-text-primary mb-1">
                Drag and drop your resume file here, or click to browse
              </p>
              <p className="text-xs text-text-tertiary font-mono">
                Supports PDF (layout-aware), DOCX, and TXT up to 15MB
              </p>
            </div>
          </>
        )}
      </div>

      {/* Auto-populate switch */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="chkAutoPopulate"
          checked={autoPopulate}
          onChange={(e) => setAutoPopulate(e.target.checked)}
          className="rounded border-border bg-surface-2 text-accent focus:ring-accent"
        />
        <label htmlFor="chkAutoPopulate" className="text-xs text-text-secondary cursor-pointer">
          Auto-populate profile suggestions (skills & experience years) from newly uploaded resume
        </label>
      </div>

      {/* Error alert if any */}
      {errorMessage && (
        <div className="flex items-center gap-2.5 p-3 rounded-lg bg-semantic-red-dim border border-semantic-red/30 text-semantic-red text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Resumes Version History Table */}
      <div className="mt-2">
        <h4 className="text-xs font-mono uppercase tracking-wider text-text-tertiary mb-3">
          Resume Document History ({resumes.length})
        </h4>

        {resumes.length === 0 ? (
          <div className="p-4 rounded-lg border border-border bg-base text-center text-xs text-text-tertiary italic">
            No resume uploaded yet. Upload your resume above to seed your profile and begin matching.
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-border bg-surface">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-surface-2/60 text-text-tertiary font-mono">
                  <th className="py-2.5 px-4 font-normal">Filename</th>
                  <th className="py-2.5 px-4 font-normal">Uploaded Date</th>
                  <th className="py-2.5 px-4 font-normal">Status</th>
                  <th className="py-2.5 px-4 font-normal text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {resumes.map((r) => (
                  <tr key={r.id} className="hover:bg-surface-2/50 transition-colors">
                    <td className="py-2.5 px-4 font-medium text-text-primary flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 text-accent" />
                      <span>{r.filename}</span>
                    </td>
                    <td className="py-2.5 px-4 text-text-secondary font-mono">
                      {formatDate(r.uploaded_at)}
                    </td>
                    <td className="py-2.5 px-4">
                      {r.is_active ? (
                        <Badge variant="green">ACTIVE</Badge>
                      ) : (
                        <Badge variant="default">ARCHIVED</Badge>
                      )}
                    </td>
                    <td className="py-2.5 px-4 text-right">
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={() => onDelete(r.id)}
                        className="text-text-tertiary hover:text-semantic-red"
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
