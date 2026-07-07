/** Step 1 — upload the source timeline export and its transcript. */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, uploadInput } from "../api/client";
import { Shell } from "../components/Shell";
import type { Project } from "../types/state";

export function UploadPage() {
  const { id = "" } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const nav = useNavigate();

  useEffect(() => { getProject(id).then(setProject).catch(e => setError(String(e))); }, [id]);

  const ACCEPT: Record<string, { exts: string[]; explain: string }> = {
    xml: { exts: [".xml"],
      explain: "The sequence field takes a Premiere Final Cut Pro XML export (.xml)." },
    transcript: { exts: [".txt", ".json", ".text"],
      explain: "The transcript field takes timecoded text (.txt) or word-timed JSON (.json) — not the sequence XML." },
    notes: { exts: [".txt", ".md", ".text"],
      explain: "Notes must be a text file (.txt, .md)." },
  };

  const upload = (kind: "xml" | "transcript" | "notes") =>
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      e.target.value = "";
      if (!file) return;
      const ext = "." + (file.name.split(".").pop() ?? "").toLowerCase();
      if (!ACCEPT[kind].exts.includes(ext)) {
        setError(`'${file.name}' isn't accepted here. ${ACCEPT[kind].explain}`);
        return;
      }
      try { setProject(await uploadInput(id, kind, file)); setError(""); }
      catch (err) { setError(String(err)); }
    };

  const has = (kind: string) =>
    (project?.inputs as { kind: string; filename: string }[] | undefined)
      ?.find(f => f.kind === kind);

  const done = (kind: string) => {
    const f = has(kind) as { filename: string; ingest_note?: string | null } | undefined;
    if (!f) return null;
    return (
      <span className="small" style={{ color: "var(--ok)" }}>
        ✓ {f.filename}
        {f.ingest_note &&
          <span className="dim" style={{ display: "block", color: "var(--text-dim)" }}>
            {f.ingest_note}
          </span>}
      </span>
    );
  };

  return (
    <Shell project={project}>
      <h1>Upload sources</h1>
      <p className="page-sub">Two files start a project: the sequence exported
        from Premiere and its transcript. Notes are optional.</p>

      <div className="panel">
        <div className="field-row">
          <div className="field-label">Sequence XML</div>
          <div><input type="file" accept=".xml" onChange={upload("xml")} /> {done("xml")}</div>
          <div className="field-hint">Premiere: File → Export → Final Cut Pro XML,
            from the synced interview sequence. One source sequence per project
            in this version — for multi-sequence work, run one project per
            sequence.</div>
        </div>
        <div className="field-row">
          <div className="field-label">Transcript</div>
          <div><input type="file" accept=".txt,.json,.text" onChange={upload("transcript")} /> {done("transcript")}</div>
          <div className="field-hint">Timecoded text (.txt) or word-timed JSON
            (.json) of the same recording. JSON is converted to timecoded text
            automatically.</div>
        </div>
        <div className="field-row">
          <div className="field-label">Notes <span className="faint">(optional)</span></div>
          <div><input type="file" accept=".txt,.md,.text" onChange={upload("notes")} /> {done("notes")}</div>
        </div>
      </div>

      {error && <div className="alert danger"><p>{error}</p></div>}

      <div className="actions">
        <span className="push" />
        <button className="btn btn-primary"
                disabled={project?.meta.phase !== "inputs_uploaded"}
                onClick={() => nav(`/projects/${id}/setup`)}>
          Continue to setup
        </button>
      </div>
    </Shell>
  );
}
