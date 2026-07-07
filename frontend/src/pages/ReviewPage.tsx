/**
 * Step 4 — review the paper edit. Lock what must survive, reject what goes,
 * ask for targeted changes, then approve. Lock violations from a revision
 * come back as explicit blockers, shown verbatim; state stays untouched.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { approve, getProject, requestRevision, updateBeatStatus } from "../api/client";
import { ApprovalSummary } from "../components/ApprovalSummary";
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

  return (
    <Shell project={project}>
      <h1>Review the paper edit</h1>
      <p className="page-sub">
        Version {project.paper_edit?.version} · Locked beats survive revisions
        word-for-word, in order. Rejected beats never return. Reopening either
        is always your explicit call.
      </p>

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

      <div className="section">
        <h2>Request changes</h2>
        <div className="panel">
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <input
              value={instruction}
              onChange={e => setInstruction(e.target.value)}
              placeholder='Describe the change, e.g. "tighten the reflection beat"'
              style={{ flex: "1 1 320px", maxWidth: "none" }}
            />
            <button className="btn btn-secondary"
                    disabled={busy || !instruction.trim()}
                    onClick={() => act(() => requestRevision(id, instruction.trim()),
                                       () => setInstruction(""))}>
              Revise
            </button>
          </div>
          <p className="small faint" style={{ marginBottom: 0 }}>
            Revisions touch only what you ask for. Locks are enforced before
            anything is accepted.
          </p>
        </div>
      </div>

      <ApprovalSummary project={project} />

      {error && <div className="alert danger">
        <h3>Change not applied</h3>
        <p style={{ whiteSpace: "pre-wrap" }}>{error}</p>
      </div>}

      <div className="actions">
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
          Approve paper edit
        </button>
      </div>
    </Shell>
  );
}
