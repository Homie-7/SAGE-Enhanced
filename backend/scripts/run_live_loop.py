#!/usr/bin/env python3
"""Run the full SAGE core loop from the command line — the operator tool for
the first real Premiere validation run.

Usage:
  python scripts/run_live_loop.py --xml export.xml --transcript t.txt \\
      --provider val --name "Real validation run 1"

Rules preserved exactly as in the app:
  - the approval gate is HUMAN: the paper edit is printed and the operator
    must review it and type an approver name to proceed — there is no
    --auto-approve flag, deliberately;
  - the provider is recorded at creation and never switched silently;
  - all state persists to the configured SAGE_DB_PATH, so the run is
    inspectable in the UI afterwards.

Pre-flight the export first:  python scripts/audit_real_export.py <xml> --rebuild-probe
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.api.deps import get_artefacts, get_engine, get_registry, get_store  # noqa: E402
from app.orchestration.engine import ApprovalGateError, TaskFailure  # noqa: E402
from app.schemas.state import InputFile, Project, ProjectMeta, ProjectPhase  # noqa: E402


def _print_paper_edit(project: Project) -> None:
    pe = project.paper_edit
    print(f"\n== Paper edit v{pe.version} — {len(pe.beats)} beats ==")
    for b in pe.beats:
        flags = ",".join(b.uncertainty_labels) or "-"
        quote = (b.exact_quote or b.quote_stub or "")[:70]
        print(f"  {b.bid:<4} {b.func:<12} ~{b.est_duration or '?':>4}s "
              f"[{b.status:<9}] {flags:<24} | {quote}")
    audit = project.source_audit.track_structure or {}
    for w in audit.get("warnings", []):
        print(f"  ⚠ {w}")


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True, type=Path)
    ap.add_argument("--transcript", required=True, type=Path)
    ap.add_argument("--provider", default=config.DEFAULT_PROVIDER)
    ap.add_argument("--name", default="Live validation run")
    args = ap.parse_args()

    for f in (args.xml, args.transcript):
        if not f.exists():
            print(f"BLOCKER: {f} does not exist."); return 2

    store, artefacts, engine, registry = (
        get_store(), get_artefacts(), get_engine(), get_registry())

    adapter = registry.get(args.provider)
    ready, detail = adapter.readiness()
    print(f"provider {args.provider}: {detail}")
    if not ready:
        return 2

    # create + ingest (same checksum/store/register path as the API)
    project = Project(meta=ProjectMeta(name=args.name, provider=args.provider))
    project.meta.provider_history.append(
        {"provider": args.provider, "reason": "live_loop_cli"})
    project = await store.create(project)
    print(f"project {project.meta.id} created (provider {args.provider})")

    for kind, path in (("xml", args.xml), ("transcript", args.transcript)):
        data = path.read_bytes()
        stored = await artefacts.write(project.meta.id, f"{kind}_{path.name}", data)
        project.inputs.append(InputFile(
            kind=kind, filename=path.name, stored_path=stored,
            checksum_sha256=hashlib.sha256(data).hexdigest()))
    project = await engine.transition(project, ProjectPhase.INPUTS_UPLOADED)

    # quick setup, all inferred (canonical inference defaults)
    project = await engine.transition(project, ProjectPhase.SETUP_COMPLETE)

    print("running planning pipeline…")
    try:
        project = await engine.run_planning(project)
    except TaskFailure as exc:
        print(f"PLANNING FAILED: {exc.blocker.why_it_blocks}")
        print(f"  needed: {exc.blocker.what_is_needed}")
        return 2
    if project.meta.phase == ProjectPhase.FAILED:
        for b in (project.validation.blockers if project.validation else []):
            print(f"BLOCKER [{b.check}]: {b.why_it_blocks} → {b.what_is_needed}")
        return 2

    _print_paper_edit(project)

    # HUMAN approval gate — review the table above before answering.
    print("\nApproval locks every beat above and resolves exact quotes.")
    approver = input("Type your name to approve (empty = abort): ").strip()
    if not approver:
        print("Not approved. Project remains reviewable in the UI "
              f"(id {project.meta.id}).")
        return 1
    project = await engine.ensure_in_review(project)
    project = await engine.approve(project, approver, accepted_risks=[])
    print(f"approved by {approver}; rebuilding…")

    try:
        project = await engine.run_rebuild(project)
    except (ApprovalGateError, TaskFailure) as exc:
        print(f"REBUILD FAILED: {exc}")
        return 2

    if project.validation:
        print(f"\nvalidation overall: {project.validation.overall.value}")
        for c in project.validation.checks:
            print(f"  [{c.outcome.value}] {c.name}: {c.detail or ''}")
        for b in project.validation.blockers:
            print(f"  ✗ {b.check}: {b.why_it_blocks} → {b.what_is_needed}")
    if project.meta.phase == ProjectPhase.COMPLETE and project.output:
        print(f"\nOUTPUT: {project.output.xml_path}")
        print(f"sha256 {project.output.checksum_sha256}")
        print("Next: import this XML in Premiere and complete "
              "docs/real-export-checklist.md section 4.")
        return 0
    print(f"\nfinal phase: {project.meta.phase.value} — not complete.")
    return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
