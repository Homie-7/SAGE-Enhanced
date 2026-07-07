/**
 * Project list + create.
 *
 * Managed service: standard users never see provider choice — projects run
 * on the centrally hosted provider (VAL in production). When the backend is
 * deployed in admin/dev mode (/api/meta), a clearly labelled admin selector
 * appears; the backend enforces this server-side regardless.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createProject, getMeta, listProjects, phaseRoute } from "../api/client";
import type { AppMeta } from "../api/client";
import type { Project } from "../types/state";

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [meta, setMeta] = useState<AppMeta>({ admin_mode: false });
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("");
  const [error, setError] = useState("");
  const nav = useNavigate();

  useEffect(() => {
    listProjects().then(setProjects).catch(e => setError(String(e)));
    getMeta().then(setMeta).catch(() => { /* standard mode */ });
  }, []);

  const create = async () => {
    if (!name.trim()) return;
    try {
      const p = await createProject(name.trim(), provider || undefined);
      nav(phaseRoute(p));
    } catch (e) { setError(String(e)); }
  };

  return (
    <main>
      <h1>SAGE — Projects</h1>
      <p>
        <input value={name} onChange={e => setName(e.target.value)}
               placeholder="Project name"
               onKeyDown={e => e.key === "Enter" && create()} />
        {" "}
        {meta.admin_mode && (
          <label>
            <strong>[admin]</strong> provider:{" "}
            <select value={provider} onChange={e => setProvider(e.target.value)}>
              <option value="">default ({meta.default_provider})</option>
              {meta.available_providers?.map(v => <option key={v} value={v}>{v}</option>)}
            </select>{" "}
          </label>
        )}
        <button onClick={create}>Create project</button>
      </p>
      {error && <p role="alert">{error}</p>}
      <table>
        <thead><tr><th>Name</th><th>Phase</th>{meta.admin_mode && <th>Provider</th>}<th>Updated</th></tr></thead>
        <tbody>
          {projects.map(p => (
            <tr key={p.meta.id} onClick={() => nav(phaseRoute(p))} style={{ cursor: "pointer" }}>
              <td>{p.meta.name}</td>
              <td>{p.meta.phase}</td>
              {meta.admin_mode && <td>{p.meta.provider}</td>}
              <td>{new Date(p.meta.updated_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
