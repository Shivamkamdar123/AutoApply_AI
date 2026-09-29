import { getAccessToken, clearAuth } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export interface UserProfile {
  user_id: string;
  full_name?: string | null;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  linkedin_url?: string | null;
  github_url?: string | null;
  portfolio_url?: string | null;
  desired_role?: string | null;
  desired_location?: string | null;
  remote_preference?: "remote" | "hybrid" | "onsite" | "any";
  years_experience?: number | null;
  skills: string[];
  bio?: string | null;
  active_resume_id?: string | null;
  resumes: ResumeItem[];
  created_at: string;
  updated_at: string;
}

export interface ResumeItem {
  id: string;
  user_id: string;
  filename: string;
  uploaded_at: string;
  is_active: boolean;
}

export interface JobPosting {
  id: string;
  title: string;
  company: string;
  location?: string | null;
  url?: string | null;
  description: string;
  source: string;
}

export interface JobMatch {
  job: JobPosting;
  score: number;
  matched_skills: string[];
  recommended: boolean;
}

export interface SourceStatusItem {
  status: "ok" | "error" | "fallback" | string;
  count?: number;
  accepted?: number;
  error?: string | null;
}

export interface JobMatchResponse {
  matches: JobMatch[];
  total_found?: number;
  total_matched?: number;
  sources_status: Record<string, SourceStatusItem | string>;
}

export interface FieldMappingDecision {
  field_name: string;
  selector: string;
  value_filled: string;
  confidence: number;
  source_field: string;
  rationale: string;
}

export interface ApplicationStatus {
  job_id: string;
  user_id: string;
  company: string;
  title: string;
  stage: "located" | "mapped" | "needs_review" | "applied" | "submitted" | "rejected" | "failed";
  match_score: number;
  updated_at: string;
  notes?: string | null;
  error_details?: string | null;
  dry_run: boolean;
  field_mappings: FieldMappingDecision[];
}

export interface DashboardSummary {
  user_id: string;
  total_matched: number;
  total_applied: number;
  total_submitted: number;
  total_needs_review: number;
  total_rejected: number;
  average_match_score: number;
  agent_active: boolean;
  dry_run_mode: boolean;
  auto_submit_enabled: boolean;
  top_recommended_jobs: JobMatch[];
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(options.headers || {});

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // Set default JSON Content-Type only if not sending FormData
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const url = `${API_BASE}${endpoint}`;
  let response: Response;

  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err: any) {
    throw new ApiError(
      err?.message || "Network request failed. Is the backend server running?",
      0
    );
  }

  if (response.status === 401) {
    // Session expired or invalid
    if (typeof window !== "undefined") {
      const isAuthPage =
        window.location.pathname === "/login" ||
        window.location.pathname === "/signup" ||
        window.location.pathname === "/";
      if (!isAuthPage) {
        clearAuth();
        window.location.href = "/login?expired=true";
      }
    }
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    const message =
      errorBody.detail ||
      errorBody.message ||
      `HTTP Error ${response.status}: ${response.statusText}`;
    throw new ApiError(message, response.status);
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }
  return response as unknown as T;
}

export const api = {
  // Auth
  signup: (data: { email: string; password: string; full_name?: string }) =>
    apiRequest<{ access_token: string; token_type: string; user: any }>(
      "/auth/signup",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    ),

  login: (data: { email: string; password: string }) =>
    apiRequest<{ access_token: string; token_type: string; user: any }>(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    ),

  getMe: () => apiRequest<any>("/auth/me"),

  forgotPassword: (email: string) =>
    apiRequest<{ message: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  resetPassword: (token: string, new_password: string) =>
    apiRequest<{ message: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password }),
    }),

  // Profile
  getProfile: () => apiRequest<UserProfile>("/profile"),

  updateProfile: (data: Partial<UserProfile>) =>
    apiRequest<UserProfile>("/profile", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  uploadResume: (file: File, autoPopulate: boolean = true) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiRequest<UserProfile>(
      `/profile/resume?auto_populate_suggestions=${autoPopulate}`,
      {
        method: "POST",
        body: formData,
      }
    );
  },

  deleteResume: (resumeId: string) =>
    apiRequest<{ status: string; message: string }>(
      `/profile/resume/${resumeId}`,
      {
        method: "DELETE",
      }
    ),

  // Jobs
  matchJobs: (params?: { query?: string; location?: string; sources?: string }) => {
    const queryParts = [];
    if (params?.query) queryParts.push(`query=${encodeURIComponent(params.query)}`);
    if (params?.location) queryParts.push(`location=${encodeURIComponent(params.location)}`);
    if (params?.sources) queryParts.push(`sources=${encodeURIComponent(params.sources)}`);
    const qs = queryParts.length ? `?${queryParts.join("&")}` : "";
    return apiRequest<JobMatchResponse>(`/jobs/match${qs}`);
  },

  // Review Queue
  getReviewQueue: () => apiRequest<ApplicationStatus[]>("/review-queue"),

  submitReviewAction: (
    jobId: string,
    action: "approve" | "reject",
    autoSubmitOverride: boolean = false
  ) =>
    apiRequest<ApplicationStatus>(`/review-queue/${jobId}/action`, {
      method: "POST",
      body: JSON.stringify({
        job_id: jobId,
        action,
        auto_submit_override: autoSubmitOverride,
      }),
    }),

  // Dashboard Summary & Agent Toggle
  getSummary: () => apiRequest<DashboardSummary>("/dashboard/summary"),

  toggleAgent: () =>
    apiRequest<{ agent_active: boolean; message: string }>("/agent/toggle", {
      method: "POST",
    }),

  // Cover Letter Generator
  generateCoverLetter: (data: {
    job_id: string;
    job_title: string;
    company: string;
    job_description?: string;
  }) =>
    apiRequest<{ cover_letter: string; provider: string; generated_at: string }>(
      "/cover-letter/generate",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    ),

  // Form Snapshot Screenshot
  getScreenshotUrl: (jobId: string) => `${API_BASE}/screenshots/${jobId}`,

  fetchScreenshotBlob: async (jobId: string): Promise<string> => {
    const token = getAccessToken();
    const res = await fetch(`${API_BASE}/screenshots/${jobId}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new ApiError("Failed to fetch screenshot", res.status);
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },
};
