# Real Premiere export — round-trip checklist (Stage 4)

The single unproven boundary is Premiere itself. Everything up to and
including the edited XML is now verified by code; import acceptance can only
be proven by a real export → SAGE → re-import cycle in Premiere Pro.

## 1. Producing the export (editor's machine)

1. In Premiere, open the project containing a **synced interview sequence**
   (single camera, external or camera audio synced — V1 scope).
2. If the sequence contains multicam or nested sequences: flatten first
   (SAGE V1 blocks multicam explicitly).
3. Select the sequence → **File → Export → Final Cut Pro XML**.
4. Keep the media online; note the drive/path — `pathurl` values in the XML
   must remain valid for the re-import test.
5. Export or locate the matching **timecoded transcript** (same recording).

## 2. Pre-flight (no Premiere needed)

```
cd backend
python scripts/audit_real_export.py /path/to/export.xml --rebuild-probe
```

Outcome must be `Readiness: OK`. Every warning it prints is a real property
of the export (transitions/titles dropped by Style B, etc.) — record them.

## 3. Running the loop

Run the normal core loop (upload XML + transcript → setup → planning →
review → approve → rebuild → download). For a code-only structural test the
mock provider is insufficient on new material — a live provider (admin/dev
mode) or hand-written plan fixture is required for the planning stage.

## 4. Re-import test in Premiere (the actual proof)

Import the downloaded XML into the same Premiere project and check,
in this order (canonical file 05 post-import checklist):

| # | Check | Pass condition | Result | Notes |
|---|-------|----------------|--------|-------|
| 1 | Import completes | No error dialog; sequence appears | | |
| 2 | Media relinks | No offline clips (same drive/paths) | | |
| 3 | Frame rate | Sequence settings match source (e.g. 25fps) | | |
| 4 | Clip order | Beats appear in approved paper-edit order | | |
| 5 | No gaps/overlaps | Timeline is contiguous from 00:00 | | |
| 6 | AV sync | Audio matches lips on every beat boundary | | |
| 7 | Linking | Selecting video selects its audio (and only its audio) | | |
| 8 | Channel integrity | Both stereo channels present per beat | | |
| 9 | In/out accuracy | First/last words of each beat match the paper edit | | |

## 5. Documenting issues

For every failed row, record **precisely**:

- Premiere version and OS,
- the exact dialog text or symptom,
- the clipitem id(s) involved (from the downloaded XML),
- the corresponding beat (BID) and its transcript span,
- whether the source export re-imports cleanly on its own (isolates whether
  the problem is SAGE's output or the export/media environment).

File findings against `backend/tests/fixtures/benchmarks/teacher_success_story/`
so the synthetic fixture can be replaced by the real export
(`inputs/source.xml`, `inputs/transcript.txt`, regenerate mock spans with
`generate_teacher_fixtures.py` against the real transcript).

## Status

- [ ] Real export obtained
- [ ] Pre-flight audit OK
- [ ] Loop run on real material
- [ ] Re-import checklist completed in Premiere
- [ ] Issues documented / fixes applied
- [ ] Synthetic benchmark XML replaced with the real export
