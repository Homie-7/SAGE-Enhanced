/**
 * Step 2 — quick setup, hybrid model.
 * Structured presets (canonical file 02 vocabulary) for the common choices,
 * with "Custom…" opening a free-text override on each. Everything defaults
 * to "Infer from material", and inferred values come back labelled at review.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, runPlanning, submitSetup } from "../api/client";
import { Shell } from "../components/Shell";
import type { Project } from "../types/state";

const CUSTOM = "__custom__";

/** Canonical preset vocabularies (file 02). "Infer" = empty value. */
const PRESETS: Record<string, { label: string; hint: string; options: string[] }> = {
  tone: {
    label: "Tone",
    hint: "How the finished cut should feel.",
    options: ["warm", "practical", "clear", "energetic", "restrained"],
  },
  cut_style: {
    label: "Cut style",
    hint: "How tightly speech gets trimmed. Natural is the usual choice.",
    options: ["conservative", "natural", "moderate", "punchy"],
  },
  opening: {
    label: "Opening",
    hint: "How the cut should begin.",
    options: ["context-first", "value-first", "strongest line"],
  },
  ending: {
    label: "Ending",
    hint: "How the cut should land.",
    options: ["resolved line", "takeaway", "uplifting"],
  },
  contributor_rule: {
    label: "Contributors",
    hint: "Who appears in the cut.",
    options: ["all meaningful", "strongest only"],
  },
  crew_interviewer: {
    label: "Crew & interviewer voices",
    hint: "Off-camera prompts and crew talk are excluded from the cut by default.",
    options: ["exclude", "consider"],
  },
};

type Choice = { preset: string; custom: string };
const infer: Choice = { preset: "", custom: "" };

function toField(c: Choice) {
  const value = c.preset === CUSTOM ? c.custom.trim() : c.preset;
  return value ? { value, origin: "user" } : { value: null, origin: "default" };
}

export function SetupPage() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [choices, setChoices] = useState<Record<string, Choice>>({
    tone: infer, cut_style: { preset: "natural", custom: "" },
    opening: infer, ending: infer, contributor_rule: infer,
    crew_interviewer: { preset: "exclude", custom: "" },
  });
  const [runtime, setRuntime] = useState("");
  const [mustKeep, setMustKeep] = useState("");
  const [avoid, setAvoid] = useState("");

  useEffect(() => { getProject(id).then(setProject).catch(e => setError(String(e))); }, [id]);

  const setChoice = (key: string, patch: Partial<Choice>) =>
    setChoices(c => ({ ...c, [key]: { ...c[key], ...patch } }));
  const list = (s: string) => s.split(",").map(x => x.trim()).filter(Boolean);

  const start = async () => {
    setBusy(true); setError("");
    try {
      await submitSetup(id, {
        runtime_target: runtime.trim()
          ? { value: runtime.trim(), origin: "user" }
          : { value: null, origin: "default" },
        tone: toField(choices.tone),
        cut_style: toField(choices.cut_style).value
          ? toField(choices.cut_style)
          : { value: "natural", origin: "default" },
        opening: toField(choices.opening),
        ending: toField(choices.ending),
        contributor_rule: toField(choices.contributor_rule),
        crew_interviewer: toField(choices.crew_interviewer).value
          ? toField(choices.crew_interviewer)
          : { value: "exclude", origin: "default" },
        must_keep: list(mustKeep),
        avoid: list(avoid),
      });
      runPlanning(id).catch(() => { /* surfaced on the processing page */ });
      nav(`/projects/${id}/processing`);
    } catch (e) { setError(String(e)); setBusy(false); }
  };

  const FIELD_DEFAULTS: Record<string, string> = { cut_style: "natural", crew_interviewer: "exclude" };

  const presetRow = (key: string) => {
    const p = PRESETS[key];
    const c = choices[key];
    const hasFieldDefault = key in FIELD_DEFAULTS;
    return (
      <div className="field-row" key={key}>
        <div className="field-label">{p.label}</div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <select
            value={c.preset}
            onChange={e => setChoice(key, { preset: e.target.value })}
            style={{ maxWidth: 240 }}
            aria-label={p.label}
          >
            <option value="">Infer from material{hasFieldDefault ? "" : " (default)"}</option>
            {p.options.map(o =>
              <option key={o} value={o}>
                {o}{FIELD_DEFAULTS[key] === o ? " (default)" : ""}
              </option>)}
            <option value={CUSTOM}>Custom…</option>
          </select>
          {c.preset === CUSTOM && (
            <input
              autoFocus
              value={c.custom}
              onChange={e => setChoice(key, { custom: e.target.value })}
              placeholder={`Describe the ${p.label.toLowerCase()} you want`}
              style={{ flex: "1 1 220px" }}
            />
          )}
        </div>
        <div className="field-hint">{p.hint}</div>
      </div>
    );
  };

  return (
    <Shell project={project}>
      <h1>Quick setup</h1>
      <p className="page-sub">Pick what you know; leave the rest on
        “Infer from material”. Every inference is labelled at review.</p>

      <div className="panel">
        <div className="field-row">
          <div className="field-label">Runtime target</div>
          <div><input value={runtime} onChange={e => setRuntime(e.target.value)}
                      placeholder="Leave blank to infer" style={{ maxWidth: 240 }} /></div>
          <div className="field-hint">e.g. 90s, 2 min.</div>
        </div>
        {presetRow("tone")}
        {presetRow("cut_style")}
        {presetRow("opening")}
        {presetRow("ending")}
        {presetRow("contributor_rule")}
        {presetRow("crew_interviewer")}
        <div className="field-row">
          <div className="field-label">Must keep</div>
          <div><input value={mustKeep} onChange={e => setMustKeep(e.target.value)}
                      placeholder="Comma-separated" style={{ maxWidth: "none" }} /></div>
          <div className="field-hint">Moments or topics that stay in, whatever else changes.</div>
        </div>
        <div className="field-row">
          <div className="field-label">Avoid</div>
          <div><input value={avoid} onChange={e => setAvoid(e.target.value)}
                      placeholder="Comma-separated" style={{ maxWidth: "none" }} /></div>
          <div className="field-hint">Topics to leave out.</div>
        </div>
      </div>

      {error && <div className="alert danger"><p>{error}</p></div>}

      <div className="actions">
        <button className="btn btn-ghost" onClick={() => nav(`/projects/${id}/upload`)}>
          Back to uploads
        </button>
        <span className="push" />
        <button className="btn btn-primary" onClick={start} disabled={busy}>
          Run planning
        </button>
      </div>
    </Shell>
  );
}
