/**
 * Mirrors backend/app/schemas/state.py. Keep in lockstep — the Python
 * schemas are authoritative. (Candidate for automated generation later.)
 */

export type ProjectPhase =
  | "created" | "inputs_uploaded" | "setup_complete" | "analysing"
  | "paper_edit_ready" | "in_review" | "revising" | "approved"
  | "rebuilding" | "validating" | "complete" | "failed";

export type FieldOrigin = "user" | "inferred" | "default";
export type ContributorStatus = "keep" | "optional" | "minimise" | "exclude";
export type BeatStatus = "draft" | "candidate" | "approved" | "locked" | "rejected";
export type CheckOutcome = "pass" | "warn" | "fail";

export type UncertaintyLabel =
  | "HIGH_CONFIDENCE" | "REVIEW_RECOMMENDED" | "IDENTITY_UNCERTAIN"
  | "MATCH_APPROXIMATE" | "SENTENCE_SEAM_RISK" | "BALANCE_RISK"
  | "CONTINUITY_RISK";

export interface SetupField { value: string | null; origin: FieldOrigin; }

export interface Contributor {
  cid: string; label: string; role?: string | null; source?: string | null;
  confidence?: string | null; status: ContributorStatus;
  value_note?: string | null; ambiguity_note?: string | null;
}

export interface Beat {
  bid: string; src: string; cid?: string | null; role?: string | null;
  func: string; quote_stub?: string | null; exact_quote?: string | null;
  est_duration?: number | null; boundary_status?: string | null;
  confidence?: string | null; include_reason?: string | null;
  representation_note?: string | null; graphics_note?: string | null;
  uncertainty_labels: UncertaintyLabel[]; status: BeatStatus;
  seg_ids: string[];
}

export interface PaperEdit { version: number; beats: Beat[]; created_at: string; }

export interface Blocker { check: string; why_it_blocks: string; what_is_needed: string; }

export interface ValidationCheck { name: string; outcome: CheckOutcome; detail?: string | null; }

export interface ValidationReport {
  checks: ValidationCheck[]; blockers: Blocker[]; overall: CheckOutcome;
  produced_at: string;
}

export interface ProjectMeta {
  id: string; name: string; created_at: string; updated_at: string;
  phase: ProjectPhase; schema_version: number;
  run_generation: number;
  /** Count of the 6 planning tasks completed in the current/last run (0-6). */
  planning_progress: number;
  /** Present only in admin/dev deployments; redacted in standard mode. */
  provider?: string;
  provider_history?: Record<string, string>[];
}

export interface Project {
  meta: ProjectMeta;
  inputs: unknown[];
  setup: Record<string, SetupField | string[]>;
  roster: Contributor[];
  structure: { mode?: string | null; cleanup_strategy: string; beat_order: string[]; rationale?: string | null };
  paper_edit?: PaperEdit | null;
  paper_edit_history: PaperEdit[];
  approval?: { approved_by: string; approved_at: string; accepted_risks: string[]; paper_edit_version: number } | null;
  validation?: ValidationReport | null;
  output?: { xml_path: string; checksum_sha256: string; produced_at: string } | null;
  // remaining backend aggregates (classification, groups, ledger, revisions,
  // rebuild, source_audit) are passed through untyped until the UI needs them
  [key: string]: unknown;
}
