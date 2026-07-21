/**
 * Step 4 — review the paper edit. A plain-language narrative is the primary
 * surface: what this cut will actually say, start to finish. The technical
 * detail (per-beat lock/reject, confidence, seg refs) is one level down,
 * for anyone who wants it — nothing is removed, just not first.
 *
 * Lock violations from a revision come back as explicit blockers, shown
 * verbatim; state stays untouched.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { approve, getProject, requestRevision, updateBeatStatus } from "../api/client";
import { ApprovalSummary } from "../components/ApprovalSummary";
import { NarrativeSummary } from "../components/NarrativeSummary";
import { PaperEditTable } from "../components/PaperEditTable";
import { RosterTable } from "../components/RosterTable";
import { Shell } from "../components/Shell";
import type { Project } from "../types/state";

export function ReviewPage() {
  const { id = "" } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [instruction, setInstruction] = useState("");
  const [approver, setApprover] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const nav = useNavigate();

  useEffect(() => { getProject(id).then(setProject).catch(e => setError(String(e))); }, [id]);

  const act = async (fn: () => Promise<Project>, after?: (p: Project) => void) => {
    setBusy(true); setError("");
    try { const p = await fn(); setProject(p); after?.(p); }
    catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  };

  if (!project) {
    return <Shell><div className="empty"><div className="mark">···</div>
      {error || "Loading project"}</div></Shell>;
  }
  const beats = project.paper_edit?.beats ?? [];
  const kept = beats.filter(b => b.status !== "rejected");
  const estSeconds = kept.reduce((s, b) => s + (b.est_duration ?? 0), 0);

  return (
    <Shell project={project}>
      <h1>Review the paper edit</h1>
      <p className="page-sub">
        Version {project.paper_edit?.version} · Locked beats survive revisions
        word-for-word, in order. Rejected beats never return. Reopening either
        is always your explicit call.
      </p>

      <div className="section">
        <h2>What this cut will say</h2>
        <div className="panel">
          <NarrativeSummary
            beats={beats}
            roster={project.roster}
            structure={project.structure}
            estSeconds={estSeconds}
          />
        </div>
      </div>

      <ApprovalSummary project={project} />

      <div className="section">
        <h2>Proceed or request changes</h2>
        <div className="panel">
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <input
              value={instruction}
              onChange={e => setInstruction(e.target.value)}
              placeholder='Request changes, e.g. "tighten the reflection beat"'
              style={{ flex: "1 1 320px", maxWidth: "none" }}
            />
            <button className="btn btn-secondary"
                    disabled={busy || !instruction.trim()}
                    onClick={() => act(() => requestRevision(id, instruction.trim()),
                                       () => setInstruction(""))}>
              Request changes
            </button>
          </div>
          <p className="small faint">
            Revisions touch only what you ask for. Locks are enforced before
            anything is accepted.
          </p>

          {error && <div className="alert danger">
            <h3>Change not applied</h3>
            <p style={{ whiteSpace: "pre-wrap" }}>{error}</p>
          </div>}

          <div className="actions" style={{ marginTop: 12 }}>
            <span className="push" />
            <input
              value={approver}
              onChange={e => setApprover(e.target.value)}
              placeholder="Approve as (your name)"
              aria-label="Approver name"
              style={{ maxWidth: 240 }}
            />
            <button className="btn btn-primary"
                    disabled={busy || !approver.trim()}
                    onClick={() => act(() => approve(id, approver.trim()),
                                       () => nav(`/projects/${id}/rebuild`))}>
              Proceed — approve paper edit
            </button>
          </div>
        </div>
      </div>

      <details className="section technical-detail">
        <summary>Show technical detail</summary>

        <div className="section">
          <h2>Contributors</h2>
          <RosterTable roster={project.roster} />
        </div>

        <div className="section">
          <h2>Paper edit</h2>
          <PaperEditTable
            beats={beats}
            onStatus={(bid, status) => act(() => updateBeatStatus(id, bid, status))}
          />
        </div>
      </details>
    </Shell>
  );
}
