/** Typed API client for the core loop. Shapes come from types/state.
 *
 * Managed-service note: provider selection is NOT part of this client's
 * standard surface. Projects are created with the centrally configured
 * provider; admin/dev tooling talks to the admin endpoints directly.
 */
import type { Project, ValidationReport } from "../types/state";

// In dev, Vite proxies "/api" to the local backend (vite.config.ts). In a
// hosted build, the frontend and backend are separate deployments, so the
// full backend URL must be supplied at build time via VITE_API_BASE_URL
// (a public URL, not a secret — set in the hosting dashboard).
const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

async function checkOk(res: Response): Promise<void> {
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* keep status */ }
    throw new Error(detail);
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  await checkOk(res);
  return res.json() as Promise<T>;
}

/** For endpoints with no response body (e.g. DELETE -> 204). */
async function reqVoid(path: string, init?: RequestInit): Promise<void> {
  const res = await fetch(`${BASE}${path}`, init);
  await checkOk(res);
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export interface AppMeta {
  admin_mode: boolean;
  default_provider?: string;
  available_providers?: string[];
}

export const getMeta = () => req<AppMeta>("/meta");

export interface AdminStatus {
  ok: boolean;
  default_provider: string;
  providers: Record<string, { ready: boolean; detail: string; is_default: boolean }>;
  database: { writable: boolean; detail: string };
  artefacts: { writable: boolean; path: string };
  canonical_prompts: { present: boolean; path: string };
}
/** Admin/dev deployments only; 403 otherwise. */
export const getAdminStatus = () => req<AdminStatus>("/admin/status");
export const listProjects = () => req<Project[]>("/projects");
export const getProject = (id: string) => req<Project>(`/projects/${id}`);
export const createProject = (name: string, provider?: string) =>
  req<Project>("/projects", json(provider ? { name, provider } : { name }));

export async function uploadInput(id: string, kind: "xml" | "transcript" | "notes", file: File) {
  const form = new FormData();
  form.append("file", file);
  return req<Project>(`/projects/${id}/uploads?kind=${kind}`, { method: "POST", body: form });
}

export const submitSetup = (id: string, setup: Record<string, unknown>) =>
  req<Project>(`/projects/${id}/setup`, json(setup));
/** Discards the current plan (or in-progress analysis) and goes back to
 * Setup. Refused (409) once the project has been approved. */
export const reopenSetup = (id: string) =>
  req<Project>(`/projects/${id}/reopen-setup`, { method: "POST" });
export const deleteProject = (id: string) =>
  reqVoid(`/projects/${id}`, { method: "DELETE" });
export const runPlanning = (id: string) =>
  req<Project>(`/projects/${id}/analyse`, { method: "POST" });
export const updateBeatStatus = (id: string, bid: string, status: string) =>
  req<Project>(`/projects/${id}/beats/status`, json({ bid, status }));
export const requestRevision = (id: string, instruction: string, reopened_bids: string[] = []) =>
  req<Project>(`/projects/${id}/revise`, json({ instruction, reopened_bids }));
export const approve = (id: string, approved_by: string, accepted_risks: string[] = []) =>
  req<Project>(`/projects/${id}/approve`, json({ approved_by, accepted_risks }));
export const triggerRebuild = (id: string) =>
  req<Project>(`/projects/${id}/rebuild`, { method: "POST" });
export const getValidation = (id: string) =>
  req<ValidationReport>(`/projects/${id}/validation`);
export const downloadUrl = (id: string) => `${BASE}/projects/${id}/download`;

/** Route for a project given its phase — keeps navigation on the core loop rail. */
export function phaseRoute(p: Project): string {
  const id = p.meta.id;
  switch (p.meta.phase) {
    case "created": return `/projects/${id}/upload`;
    case "inputs_uploaded": return `/projects/${id}/setup`;
    case "setup_complete":
    case "analysing": return `/projects/${id}/processing`;
    case "paper_edit_ready":
    case "in_review":
    case "revising": return `/projects/${id}/review`;
    case "approved":
    case "rebuilding":
    case "validating": return `/projects/${id}/rebuild`;
    case "complete":
    case "failed": return `/projects/${id}/download`;
  }
}
