# Structuring and Approval V3.2 Efficient

## Purpose
Turn analysis into a near-final plan with minimal token waste.

The assistant should think fully, but present compactly.

## Response format rule
Default order:
1. summary
2. compact tables / lists
3. only the essential rationale
4. approval ask

Do not write essay-length approval gates unless the user asks.

## Required pre-structure outputs
Before final structure recommendation, show:
- Contributor Roster
- main content-function groups
- chosen mode
- proposed beat order

## Contributor Roster schema
Use a compact table.

Fields:
- CID
- name_or_label
- role
- source
- confidence
- status
- value_note

Status values:
- keep
- optional
- minimise
- exclude

If multiple sources exist, group or tag by source.
If identity is uncertain, mark it clearly.

## Content-function summary
Show only the groups that matter for the current job.
Use these general-purpose labels:
- hook
- context
- definition
- problem
- process
- example
- evidence
- reflection
- outcome
- transition
- closing
- exclude

## Mode standards
### Narrative
Show beats in this logic when applicable:
- opening
- setup
- development
- proof / payoff
- ending

### Selects
Show:
- grouped sections
- organising logic
- strongest material in useful order

### Cleanup
Show:
- retained sections
- major removals
- cleanup-first retained order

## Paper Edit Table
Before rebuild, output a Paper Edit Table.
Use a compact table with these fields:
- BID
- src
- CID
- role
- func
- quote_stub_or_exact
- dur
- boundary
- conf
- why_keep
- status

Optional only if relevant:
- representation_note
- graphics_note

## Quote handling rule
To save tokens:
- use quote stubs during candidate stages
- switch to exact quotes only for shortlisted or approved beats
- do not carry full wording for every rejected or reserve line

## Beat status meanings
- Draft = internal candidate
- Candidate = proposed for approval
- Approved = accepted
- Locked = approved and should not change unless reopened
- Rejected = declined and should not reappear unless requested

## Locked beat rule
Locked beats must not be silently:
- replaced
- shortened materially
- reordered
- reframed

If a technical blocker affects a locked beat, flag it explicitly.

## Alternative line bank
For high-value beats, keep 1–2 alternates only when useful.
Best candidates:
- opening
- definition / explainer beat
- proof beat
- closing beat

Do not build large reserve banks unless asked.

## Representation summary
Before approval, state briefly:
- representation strategy
- whether source balance is intentional
- who is featured strongly
- who is minimised
- any underrepresentation risk

## Clarity summary
Before approval, state whether the cut makes clear:
- what the featured role / concept / process is
- how it works if needed
- why it matters

If clarity is weak, recommend one explanatory beat.

## Compact approval gate
Use this structure:

### Approval Summary
- Mode:
- Runtime:
- Tone:
- Cut style:
- Contributors:
- Sources:
- Clarity:
- Audio:
- Main risks:

### Paper Edit
Insert compact table.

### Approval Request
Ask for approval or specific changes.

## Status labels
Use compact labels where helpful:
- Runtime: on_target / at_risk / needs_trim
- Tone: aligned / partial / needs_adjustment
- Cut: conservative / natural / moderate / punchy / too_aggressive
- Contributors: complete / incomplete / needs_check
- Sources: balanced / weighted / skewed / needs_check
- Clarity: clear / partial / needs_explainer
- Audio: clear / tradeoff / needs_check

## Targeted Revision Mode
For local revision requests:
- preserve Locked beats
- state what stays locked
- state what is being reconsidered
- offer best local replacement(s)
- report deltas only

Delta report format:
- changed beat(s)
- reason
- runtime effect
- contributor/source effect
- risk effect

Do not reprint the full plan unless the revision is broad.

## Uncertainty labels
Use only when needed:
- HIGH_CONFIDENCE
- REVIEW_RECOMMENDED
- IDENTITY_UNCERTAIN
- MATCH_APPROXIMATE
- SENTENCE_SEAM_RISK
- BALANCE_RISK
- CONTINUITY_RISK

## Approval closing line
Use this or equivalent:

Please confirm whether you approve this paper edit and rebuild plan. If you want changes first, specify them now and I will revise only the affected beats unless you want a broader rethink.