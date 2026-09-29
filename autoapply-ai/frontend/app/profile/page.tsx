"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, UserProfile } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AppShell } from "@/components/app/AppShell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SkillTagInput } from "@/components/app/SkillTagInput";
import { ResumeUpload } from "@/components/app/ResumeUpload";
import { useToast } from "@/components/ui/toast";
import { formatDate } from "@/lib/utils";
import { Save, RotateCcw, Check, Sparkles } from "lucide-react";

export default function ProfilePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [formData, setFormData] = useState<Partial<UserProfile>>({
    full_name: "",
    email: "",
    phone: "",
    location: "",
    linkedin_url: "",
    github_url: "",
    portfolio_url: "",
    desired_role: "",
    desired_location: "",
    remote_preference: "any",
    years_experience: null,
    skills: [],
    bio: "",
  });

  const [isDirty, setIsDirty] = useState(false);

  // Auth gate
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  // Fetch full profile
  const { data: profile, isLoading } = useQuery<UserProfile>({
    queryKey: ["profile"],
    queryFn: api.getProfile,
    enabled: isAuthenticated,
  });

  // Populate form when data arrives
  useEffect(() => {
    if (profile) {
      setFormData({
        full_name: profile.full_name || "",
        email: profile.email || "",
        phone: profile.phone || "",
        location: profile.location || "",
        linkedin_url: profile.linkedin_url || "",
        github_url: profile.github_url || "",
        portfolio_url: profile.portfolio_url || "",
        desired_role: profile.desired_role || "",
        desired_location: profile.desired_location || "",
        remote_preference: profile.remote_preference || "any",
        years_experience: profile.years_experience,
        skills: profile.skills || [],
        bio: profile.bio || "",
      });
      setIsDirty(false);
    }
  }, [profile]);

  const updateField = (field: keyof UserProfile, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setIsDirty(true);
  };

  // Save profile mutation
  const saveMutation = useMutation({
    mutationFn: () => api.updateProfile(formData),
    onSuccess: (updated) => {
      queryClient.setQueryData(["profile"], updated);
      queryClient.invalidateQueries({ queryKey: ["summary"] });
      setIsDirty(false);
      toast("Profile preferences saved successfully!", "success");
    },
    onError: (err: any) => {
      toast(`Save failed: ${err.message}`, "error");
    },
  });

  // Resume upload mutation
  const uploadResumeMutation = useMutation({
    mutationFn: ({ file, autoPopulate }: { file: File; autoPopulate: boolean }) =>
      api.uploadResume(file, autoPopulate),
    onSuccess: (updatedProfile) => {
      queryClient.setQueryData(["profile"], updatedProfile);
      queryClient.invalidateQueries({ queryKey: ["summary"] });
      toast("Resume uploaded and parsed successfully!", "success");
    },
  });

  // Delete resume mutation
  const deleteResumeMutation = useMutation({
    mutationFn: (id: string) => api.deleteResume(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] });
      toast("Resume version deleted.", "info");
    },
    onError: (err: any) => {
      toast(`Failed to delete resume: ${err.message}`, "error");
    },
  });

  if (authLoading || isLoading) {
    return (
      <AppShell>
        <div className="max-w-4xl flex flex-col gap-6">
          <Skeleton className="h-10 w-48 rounded-md" />
          <Skeleton className="h-64 rounded-xl" />
          <Skeleton className="h-64 rounded-xl" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto pb-12">
        {/* Header Strip */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 pb-4 border-b border-border">
          <div>
            <h1 className="font-display text-2xl font-bold tracking-tight text-text-primary">
              Candidate Profile &amp; Settings
            </h1>
            <p className="text-xs text-text-secondary mt-0.5">
              All fields are optional. Changes update your TF-IDF matching and browser agent mappings in real-time.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-[11px] font-mono text-text-tertiary">
              Last saved: {formatDate(profile?.updated_at)}
            </span>
            <Button
              variant={isDirty ? "signature" : "secondary"}
              size="sm"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending || !isDirty}
              className="gap-1.5"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{saveMutation.isPending ? "Saving..." : isDirty ? "Save Changes *" : "Saved"}</span>
            </Button>
          </div>
        </div>

        <div className="flex flex-col gap-6">
          {/* Section 1: Basic Information */}
          <Card className="p-6 bg-surface border-border">
            <h3 className="font-display text-sm font-semibold text-text-primary mb-1">
              1. Basic Information
            </h3>
            <p className="text-xs text-text-secondary mb-4">
              Contact coordinates auto-filled by the browser agent during form mapping.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  value={formData.full_name || ""}
                  onChange={(e) => updateField("full_name", e.target.value)}
                  placeholder="e.g. Alex Rivera"
                  className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  Contact Email (Application submissions)
                </label>
                <input
                  type="email"
                  value={formData.email || ""}
                  onChange={(e) => updateField("email", e.target.value)}
                  placeholder="e.g. alex.rivera@example.com"
                  className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  Phone Number
                </label>
                <input
                  type="tel"
                  value={formData.phone || ""}
                  onChange={(e) => updateField("phone", e.target.value)}
                  placeholder="e.g. +1 (555) 789-0123"
                  className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  Current Location
                </label>
                <input
                  type="text"
                  value={formData.location || ""}
                  onChange={(e) => updateField("location", e.target.value)}
                  placeholder="e.g. San Francisco, CA / Bengaluru, IN"
                  className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>
            </div>
          </Card>

          {/* Section 2: Professional Links */}
          <Card className="p-6 bg-surface border-border">
            <h3 className="font-display text-sm font-semibold text-text-primary mb-1">
              2. Professional Links &amp; Profiles
            </h3>
            <p className="text-xs text-text-secondary mb-4">
              URLs populated into standard job application inputs.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  LinkedIn URL
                </label>
                <input
                  type="url"
                  value={formData.linkedin_url || ""}
                  onChange={(e) => updateField("linkedin_url", e.target.value)}
                  placeholder="https://linkedin.com/in/username"
                  className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  GitHub Profile
                </label>
                <input
                  type="url"
                  value={formData.github_url || ""}
                  onChange={(e) => updateField("github_url", e.target.value)}
                  placeholder="https://github.com/username"
                  className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  Portfolio / Website
                </label>
                <input
                  type="url"
                  value={formData.portfolio_url || ""}
                  onChange={(e) => updateField("portfolio_url", e.target.value)}
                  placeholder="https://portfolio.dev"
                  className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>
            </div>
          </Card>

          {/* Section 3: Target Role, Preferences & Skills Tag Editor */}
          <Card className="p-6 bg-surface border-border">
            <h3 className="font-display text-sm font-semibold text-text-primary mb-1">
              3. Target Roles &amp; Matching Preferences
            </h3>
            <p className="text-xs text-text-secondary mb-4">
              Drives the TF-IDF cosine-similarity scoring and n-gram overlap algorithms.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  Desired Role Title
                </label>
                <input
                  type="text"
                  value={formData.desired_role || ""}
                  onChange={(e) => updateField("desired_role", e.target.value)}
                  placeholder="e.g. Senior Backend Engineer"
                  className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  Desired Location
                </label>
                <input
                  type="text"
                  value={formData.desired_location || ""}
                  onChange={(e) => updateField("desired_location", e.target.value)}
                  placeholder="e.g. Remote / United States"
                  className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  Workplace Preference
                </label>
                <select
                  value={formData.remote_preference || "any"}
                  onChange={(e) => updateField("remote_preference", e.target.value)}
                  className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
                >
                  <option value="any">Any (Remote, Hybrid, Onsite)</option>
                  <option value="remote">Remote Only</option>
                  <option value="hybrid">Hybrid</option>
                  <option value="onsite">On-site</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  Total Years of Experience
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  max="50"
                  value={formData.years_experience !== null ? formData.years_experience : ""}
                  onChange={(e) =>
                    updateField(
                      "years_experience",
                      e.target.value ? parseFloat(e.target.value) : null
                    )
                  }
                  placeholder="e.g. 4.5"
                  className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>
            </div>

            {/* Interactive Skills Tag Input */}
            <div className="mb-4">
              <label className="block text-xs font-medium text-text-secondary mb-1">
                Core Skills &amp; Tech Stack
              </label>
              <SkillTagInput
                skills={formData.skills || []}
                onChange={(newSkills) => updateField("skills", newSkills)}
              />
            </div>

            {/* Candidate Bio / Summary */}
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">
                Candidate Bio / Summary (Used for AI cover note generation)
              </label>
              <textarea
                rows={4}
                value={formData.bio || ""}
                onChange={(e) => updateField("bio", e.target.value)}
                placeholder="Senior backend engineer specializing in high-throughput Python services, distributed systems, and browser automation..."
                className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent leading-relaxed"
              />
            </div>
          </Card>

          {/* Section 4: Resume Management */}
          <Card id="resume" className="p-6 bg-surface border-border">
            <h3 className="font-display text-sm font-semibold text-text-primary mb-1">
              4. Resume Documents &amp; Version History
            </h3>
            <p className="text-xs text-text-secondary mb-4">
              Uploaded resumes are securely stored and parsed with layout awareness to extract verified skills.
            </p>

            <ResumeUpload
              resumes={profile?.resumes || []}
              onUpload={async (file, autoPopulate) => {
                await uploadResumeMutation.mutateAsync({ file, autoPopulate });
              }}
              onDelete={async (id) => {
                await deleteResumeMutation.mutateAsync(id);
              }}
              isUploading={uploadResumeMutation.isPending}
            />
          </Card>

          {/* Bottom Save Bar */}
          <div className="flex justify-end gap-3 pt-4">
            <Button
              variant="outline"
              size="md"
              onClick={() => {
                if (profile) {
                  setFormData({
                    full_name: profile.full_name || "",
                    email: profile.email || "",
                    phone: profile.phone || "",
                    location: profile.location || "",
                    linkedin_url: profile.linkedin_url || "",
                    github_url: profile.github_url || "",
                    portfolio_url: profile.portfolio_url || "",
                    desired_role: profile.desired_role || "",
                    desired_location: profile.desired_location || "",
                    remote_preference: profile.remote_preference || "any",
                    years_experience: profile.years_experience,
                    skills: profile.skills || [],
                    bio: profile.bio || "",
                  });
                  setIsDirty(false);
                }
              }}
              disabled={!isDirty}
            >
              Reset Changes
            </Button>

            <Button
              variant="signature"
              size="md"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending || !isDirty}
              className="gap-2"
            >
              <Save className="w-4 h-4" />
              <span>{saveMutation.isPending ? "Saving..." : "Save Profile Changes"}</span>
            </Button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
