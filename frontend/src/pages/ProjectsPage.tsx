/**
 * Home: project list + create. Standard users see no provider machinery;
 * the admin selector appears only when /api/meta reports admin mode and
 * stays visually secondary. Backend enforces regardless.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createProject, deleteProject, getAdminStatus, getMeta, listProjects, phaseRoute,
} from "../api/client";
import type { AdminStatus, AppMeta } from "../api/client";
import { ConfirmAction } from "../components/ConfirmAction";
import { Shell } from "../components/Shell";
import { WelcomeModal } from "../components/WelcomeModal";
import type { Project } from "../types/state";

const PHASE_LABEL: Record<string, string> = {
  created: "Awaiting upload", inputs_uploaded: "Awaiting setup",
  setup_complete: "Ready to plan", analysing: "Planning",
  paper_edit_ready: "Ready for review", in_review: "In review",
  revising: "Revising", approved: "Approved",
  rebuilding: "Rebuilding", validating: "Validating",
  complete: "Complete", failed: "Needs attention",
};

// Display only — the stored identifier (provider: "val", VAL_API_KEY, the
// registry key, prompts/configs/val.json) stays lowercase; this just fixes
// how the name reads for a human, the same way PHASE_LABEL does for phases.
const PROVIDER_LABEL: Record<string, string> = { val: "VAL", claude: "Claude", mock: "Mock" };
const providerLabel = (p: string) => PROVIDER_LABEL[p] ?? p;

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [meta, setMeta] = useState<AppMeta>({ admin_mode: false });
  const [status, setStatus] = useState<AdminStatus | null>(null);
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("");
  const [error, setError] = useState("");
  const nav = useNavigate();

  useEffect(() => {
    listProjects().then(setProjects).catch(e => { setProjects([]); setError(String(e)); });
    getMeta().then(m => {
      setMeta(m);
      if (m.admin_mode) getAdminStatus().then(setStatus).catch(() => {});
    }).catch(() => { /* standard mode */ });
  }, []);

  const create = async () => {
    if (!name.trim()) return;
    try {
      const p = await createProject(name.trim(), provider || undefined);
      nav(phaseRoute(p));
    } catch (e) { setError(String(e)); }
  };

  return (
    <Shell adminMode={meta.admin_mode}>
      <WelcomeModal />
      <h1>Projects</h1>
      <p className="page-sub">Each project takes one recorded interview from
        source timeline to an edited sequence, with your approval in the middle.</p>

      <div className="panel">
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={e => e.key === "Enter" && create()}
            placeholder="New project name"
            aria-label="New project name"
            style={{ flex: "1 1 260px" }}
          />
          <button className="btn btn-primary" onClick={create} disabled={!name.trim()}>
            Create project
          </button>
        </div>
      </div>

      {meta.admin_mode && (
        <section className="admin-panel" aria-label="Provider testing (admin)">
          <h2>Provider testing — admin only</h2>
          {status && Object.entries(status.providers).map(([name, p]) => (
            <div key={name} className="provider-row">
              <span className="name">{providerLabel(name)}</span>
              <span className={"pill " + (p.ready ? "ok" : "warn")}>
                {p.ready ? "ready" : "not configured"}
              </span>
              {p.is_default && <span className="pill">default</span>}
              <span className="detail" title={p.detail}>{p.detail}</span>
            </div>
          ))}
          <div className="provider-row" style={{ marginTop: 8 }}>
            <span className="name">new</span>
            <span className="small dim">Run new projects on</span>
            <select value={provider} onChange={e => setProvider(e.target.value)}
                    style={{ maxWidth: 220 }} aria-label="Provider for new projects">
              <option value="">default ({providerLabel(meta.default_provider ?? "")})</option>
              {meta.available_providers?.map(v => <option key={v} value={v}>{providerLabel(v)}</option>)}
            </select>
          </div>
          <p className="small faint" style={{ margin: "10px 0 0" }}>
            Recorded per project. Standard deployments never show this panel;
            the server refuses provider selection outside admin mode.
          </p>
        </section>
      )}

      {error && <div className="alert danger"><p>{error}</p></div>}

      <div className="section">
        {projects === null ? (
          <div className="empty"><div className="mark">···</div>Loading projects</div>
        ) : projects.length === 0 ? (
          <div className="empty">
            <div className="mark">SAGE</div>
            No projects yet. Create one above to start a cut.
          </div>
        ) : (
          <div className="table-wrap">
            <table className="sys">
              <thead>
                <tr><th>Name</th><th>Status</th>
                    {meta.admin_mode && <th>Provider</th>}
                    <th>Updated</th><th /></tr>
              </thead>
              <tbody>
                {projects.map(p => (
                  <tr key={p.meta.id} className="row-link"
                      onClick={() => nav(phaseRoute(p))}>
                    <td>{p.meta.name}</td>
                    <td>
                      <span className={"pill " +
                        (p.meta.phase === "complete" ? "ok"
                         : p.meta.phase === "failed" ? "danger"
                         : ["analysing", "rebuilding", "validating"].includes(p.meta.phase)
                           ? "active" : "")}>
                        {PHASE_LABEL[p.meta.phase] ?? p.meta.phase}
                      </span>
                    </td>
                    {meta.admin_mode && <td className="mono dim">{providerLabel(p.meta.provider ?? "")}</td>}
                    <td className="dim small">
                      {new Date(p.meta.updated_at).toLocaleString()}
                    </td>
                    <td onClick={e => e.stopPropagation()}>
                      <ConfirmAction
                        className="btn-quiet-danger small"
                        label="Delete"
                        confirmLabel="Delete for good"
                        message={`Delete "${p.meta.name}"? This can't be undone.`}
                        onConfirm={async () => {
                          try {
                            await deleteProject(p.meta.id);
                            setProjects(prev => (prev ?? []).filter(x => x.meta.id !== p.meta.id));
                          } catch (e) { setError(String(e)); }
                        }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Shell>
  );
}
