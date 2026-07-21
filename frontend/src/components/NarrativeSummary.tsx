/**
 * A plain-language walkthrough of the proposed edit — "it starts with X,
 * then Y says this, then it closes with Z" — built entirely from data SAGE
 * already computed (paper_edit beats, roster, structure). No new AI call:
 * deterministic templating, so it's free, instant, and can never drift from
 * the technical beat table underneath it.
 */
import type { Beat, Contributor } from "../types/state";

const FUNC_PHRASE: Record<string, (label: string) => string> = {
  hook: label => `${label} opens with`,
  context: label => `${label} sets the scene`,
  definition: label => `${label} explains`,
  problem: label => `${label} raises`,
  process: label => `${label} walks through`,
  example: label => `${label} gives an example`,
  evidence: label => `${label} backs it up`,
  reflection: label => `${label} reflects`,
  outcome: label => `${label} points to the outcome`,
  transition: label => `${label} moves things on`,
  closing: label => `${label} closes with`,
};

function speakerLabel(cid: string | null | undefined, roster: Contributor[]): string {
  const c = roster.find(r => r.cid === cid);
  return c?.label ?? "An unidentified speaker";
}

function connector(index: number, total: number): string {
  if (index === 0) return "It begins with";
  if (index === total - 1) return "It closes with";
  return index % 2 === 0 ? "From there," : "Next,";
}

export function NarrativeSummary({ beats, roster, structure, estSeconds }: {
  beats: Beat[];
  roster: Contributor[];
  structure: { mode?: string | null; rationale?: string | null };
  estSeconds: number;
}) {
  const kept = beats.filter(b => b.status !== "rejected");
  if (!kept.length) {
    return <p className="dim">No beats proposed yet.</p>;
  }

  // Flagged once per speaker, not once per beat — a recording where one
  // speaker's identity is uncertain would otherwise repeat the same caveat
  // after nearly every line, recreating in prose the exact "too technical
  // to actually read" problem this view exists to solve.
  const uncertainAlreadyNoted = new Set<string>();

  const lines = kept.map((b, i) => {
    const label = speakerLabel(b.cid, roster);
    const phrase = FUNC_PHRASE[b.func]?.(label) ?? `${label} says`;
    // Labels are names/role titles (often acronyms, e.g. "LND Specialist") —
    // never lowercase them. The connector reads as its own clause instead.
    const lead = i === 0 || i === kept.length - 1
      ? phrase
      : `${connector(i, kept.length)} ${phrase}`;
    const quote = b.exact_quote ?? b.quote_stub ?? "";
    // The per-beat flag is the actual signal shown elsewhere (the technical
    // table's "Flags" column) — a contributor-level confidence check alone
    // would miss beats tied to a contributor whose own record reads fine
    // but whose speaker-boundary is flagged at the segment/beat level.
    const flaggedHere = b.uncertainty_labels.includes("IDENTITY_UNCERTAIN")
      && b.cid != null && !uncertainAlreadyNoted.has(b.cid);
    if (flaggedHere && b.cid) uncertainAlreadyNoted.add(b.cid);
    return (
      <p key={b.bid}>
        {lead}
        {quote && <>: <span className="quote">&ldquo;{quote}&rdquo;</span></>}
        {flaggedHere && (
          <span className="dim small">
            {" "}(this speaker's identity is uncertain in the source recording)
          </span>
        )}
      </p>
    );
  });

  const minutes = Math.round(estSeconds / 60 * 10) / 10;
  // structure.rationale is LLM-authored prose and already ends in its own
  // punctuation — strip a trailing "." before appending the runtime
  // sentence, or it reads "...arc.. Estimated runtime...".
  const rationale = structure.rationale?.trim().replace(/\.+$/, "");

  return (
    <div className="narrative">
      {lines}
      <p className="dim" style={{ marginTop: 16 }}>
        {structure.mode
          ? `Overall, this builds a ${structure.mode} cut`
          : "Overall, this builds the cut"}
        {rationale ? ` — ${rationale}.` : "."}
        {estSeconds > 0 ? ` Estimated runtime: ~${minutes} minute${minutes === 1 ? "" : "s"}.` : ""}
      </p>
    </div>
  );
}
