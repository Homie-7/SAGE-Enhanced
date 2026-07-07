/**
 * Review the paper edit: lock / reject / reopen beats, request a targeted
 * revision (Targeted Revision Mode, file 03), or approve. Lock violations
 * from a revision come back as explicit blockers and are shown verbatim.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { approve, getProject, requestRevision, updateBeatStatus } from "../api/client";
import { ApprovalSummary } from "../components/ApprovalSummary";
import { PaperEditTable } from "../components/PaperEditTable";
import { RosterTable } from "../components/RosterTable";
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

  if (!project) return <main><p>{error || "Loading…"}</p></main>;
  const beats = project.paper_edit?.beats ?? [];

  return (
    <main>
      <h1>Review paper edit — {project.meta.name}</h1>
      <p>Version {project.paper_edit?.version} · phase {project.meta.phase}</p>

      <h2>Contributor roster</h2>
      <RosterTable roster={project.roster} />

      <h2>Paper edit</h2>
      <PaperEditTable beats={beats}
        onStatus={(bid, status) => act(() => updateBeatStatus(id, bid, status))} />
      <p><em>Locked beats survive revisions verbatim, in order. Rejected beats
        never reappear. Reopening either is an explicit action here.</em></p>

      <h2>Request changes (targeted revision)</h2>
      <p>
        <input style={{ width: "34em" }} value={instruction}
               onChange={e => setInstruction(e.target.value)}
               placeholder='e.g. "tighten the reflection beat"' />
        {" "}
        <button disabled={busy || !instruction.trim()}
                onClick={() => act(() => requestRevision(id, instruction.trim()),
                                   () => setInstruction(""))}>
          Revise
        </button>
      </p>

      <ApprovalSummary project={project} />
      <p>
        Approve as: <input value={approver} onChange={e => setApprover(e.target.value)}
                           placeholder="your name" />
        {" "}
        <button disabled={busy || !approver.trim()}
                onClick={() => act(() => approve(id, approver.trim()),
                                   () => nav(`/projects/${id}/rebuild`))}>
          Approve paper edit
        </button>
      </p>
      {error && <p role="alert" style={{ whiteSpace: "pre-wrap" }}>{error}</p>}
    </main>
  );
}
