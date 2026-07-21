# Workflow navigation, reopening, project management, welcome modal

Date: 2026-07-21. Scope: frontend UX + a real backend capability (reopening
setup, including safely superseding an in-flight background analysis), plus
project deletion and a cosmetic display-casing fix. No workflow redesign,
no change to the approval gate, no change to canonical editorial logic.

## 1. Rail navigation
Every `WorkflowRail` node becomes a link to that phase's route, for any
phase index `<= current`. Pure frontend — each page already fetches live
project state on mount via `getProject(id)`, so visiting an already-reached
step is safe by construction and requires no backend change.

## 2. Reopening setup
**Trigger:** a "Back to setup" action, available on the Processing page
(while `analysing`) and on the Download page when `phase === "failed"` and
`project.approval` is still null (i.e. the failure happened during planning,
not during rebuild/validation — those happen only after approval, which
stays a one-way gate).

**Legal transitions added** (`schemas/state.py: PHASE_TRANSITIONS`):
`SETUP_COMPLETE -> INPUTS_UPLOADED`, `ANALYSING -> INPUTS_UPLOADED`,
`FAILED -> INPUTS_UPLOADED`. The graph alone doesn't know *why* a project is
`FAILED` (planning crash vs. rebuild/validation crash both land there), so
the new `reopen_setup()` engine method adds the extra business rule the
graph can't express: refuse (raise, surfaced as 409) unless
`project.approval is None`.

**What reopening does:** bumps `ProjectMeta.run_generation` (new int field,
default 0), resets the planning-derived fields to their defaults
(`source_audit`, `roster`, `classification`, `groups`, `structure`,
`paper_edit`, `paper_edit_history`, `ledger`), and transitions to
`INPUTS_UPLOADED`. Deliberately **not** cleared: `setup` and `inputs` — the
Setup page reopens pre-filled with prior answers, and previously uploaded
files remain (re-uploading is optional, matching the existing upload
endpoint's accepted phases).

**The race condition this must not create:** `run_planning`'s loop
(`engine.py`) saves after every one of the 6 planning tasks, using an
in-memory `project` object. If setup is reopened mid-loop, that background
task must not keep saving over the fresh state. Fix: capture
`started_generation = project.meta.run_generation` before the loop; after
each task's save, re-fetch the stored project and check a shared
**supersession** condition — `fresh is None` (deleted) **or**
`fresh.meta.run_generation != started_generation` (reopened). On
supersession, stop immediately: no further saves, not marked failed (this
isn't a failure, it's an intentional, explicit user action).

**Frontend confirmation:** reopening discards a real in-progress or
completed plan, so it sits behind an inline confirm ("This stops the
current analysis and discards this plan — continue?"), not a bare button
click. Built as one small reusable component (`ConfirmAction`), not a
one-off, since delete needs the identical pattern (see §3).

## 3. Delete / manage projects
**Backend:** `DELETE /api/projects/{id}`. `SQLiteProjectStore.delete()`
already removes the DB row; adding `DiskArtefactStore.delete_project()`
(recursive removal of the project's artefact directory, ignore-missing) so
deletion actually frees disk, not just hides the row. No phase restriction
— deletable at any point, including mid-analysis, because the same
supersession check from §2 covers it: `save()` currently does
`INSERT ... ON CONFLICT DO UPDATE`, so an in-flight background task would
otherwise resurrect a deleted row on its next save. The supersession check
already treats "project no longer exists" as superseded, so this is
covered by the same mechanism, not a second one.

**Frontend:** a delete action per row on the Projects page, `stopPropagation`
so it doesn't trigger the row's existing navigate-on-click, behind the same
`ConfirmAction` component as §2.

## 4. Welcome modal
Shown once (localStorage flag `sage_welcome_seen`), on the Projects page.
3-4 sentences: what SAGE is, and its core principle (human-led, AI assists
structuring, never replaces the editor's judgement). Styled to the existing
dark/red design system. Dismissed with one button. No backend involvement.

## 5. Display casing: VAL not val
Cosmetic only — the stored identifier (`provider: "val"`, `VAL_API_KEY`,
`prompts/configs/val.json`, the registry key) is unchanged; only
user-facing display text changes. New `PROVIDER_LABEL` map in
`ProjectsPage.tsx` (`val` → `VAL`, `claude` → `Claude`, `mock` → `Mock`),
following the file's existing `PHASE_LABEL` pattern, applied to the admin
provider-status rows, the projects table's provider column, and the
provider-select dropdown. Doc prose (`README.md`) using lowercase "val" as
the system name gets the same fix.

## Testing
- Backend: new tests for `reopen_setup` (legal from `setup_complete`/
  `analysing`/pre-approval `failed`; 409 from any phase where
  `approval is not None`), for the supersession check aborting a stale
  `run_planning` loop after a reopen and after a delete, and for
  `DELETE /projects/{id}` removing both the DB row and the artefact
  directory. Existing 49 tests must stay green.
- Frontend: manual verification (no frontend test harness in this repo) —
  rail navigation across phases, reopen-then-resubmit-setup round trip,
  delete with confirm, welcome modal first-load/dismiss/no-repeat, VAL
  casing in the admin panel.
