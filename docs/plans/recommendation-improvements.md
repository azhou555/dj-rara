# Recommendation and curation improvements

## Approach

Keep the existing Spotify client, Textual screens, and JSON history. Implement
the first batch below, then evaluate the remaining improvements separately.
No release or package version change is required for this implementation.

## Batch 1: selection and curation

1. **Explicit curation and safe export**
   - Add keep (`k`), skip (`x`), and undo (`u`); retain Space as a shortcut.
   - Export kept tracks when any exist; otherwise export undecided tracks.
     Skipped tracks never enter an export. Block an empty export.
   - Show the exact export count and prevent duplicate submissions while saving.
2. **Diverse selection**
   - Limit each artist to two tracks across both familiar and discovery pools.
   - Deduplicate recordings by ISRC where available, with normalized title and
     artist names as a conservative fallback. Preserve live/remix distinctions.
   - Preserve the requested pool ratio where candidates permit. Return fewer
     results rather than silently defeating the cap.
3. **Ranking with incomplete data**
   - Use a neutral mood score when measurements are missing, rather than the
     worst possible score. Disable the mood contribution if no candidate has it.
   - Use playlist ranking when available; randomize tied candidates before
     selection so unavailable signals do not turn fetch order into ranking.
   - Count a track at most once per playlist.
4. **Replacement and skip memory**
   - Retain unused ranked candidates from discovery in a session reserve.
   - `r` replaces skipped tracks; `Shift+r` replaces all unkept tracks.
     Kept tracks stay in place. Use the same diversity rules and pool ratio.
   - Never reintroduce previously displayed tracks in that session. Keep rows
     unchanged when no replacement exists and report partial/exhausted reserves.
   - Persist explicit skips for seven days in existing JSON history. Undoing a
     skip or keeping that track clears its cooldown.

### Validation

Test export semantics, undo, repeated submission, replacement exhaustion,
preservation of kept tracks, cross-pool diversity, recording duplicates, missing
signals, playlist occurrence counts, and cooldown expiry. Use Textual's headless
pilot to exercise keyboard interactions. Run the complete existing suite.

## Batch 2: genre precision and explanations

- Separate exact genre matches from related tags; rank exact matches first.
- Report when genre constraints are broadened or no genre metadata is available.
- Attach factual provenance to candidates and display it in a selected-track
  detail panel. Only claim mood fit when audio measurements exist.
- Validate exact/related ordering, missing tags, and explanation provenance.

## Batch 3: responsiveness

- Add progress callbacks for profile loading, candidate retrieval, and ranking.
- Cache artist metadata and top tracks per session with bounded size and expiry.
- Remember unsupported optional endpoints for the session; distinguish failures
  from empty results. Verify capabilities with the user's app before relying on
  API-dependent ranking behavior.
- Validate cache expiry and error recovery; compare request counts and elapsed
  discovery time on the same inputs before and after.

## Acceptance

Batch 1 is complete when its tests pass and all four behaviors work through the
existing discovery screen. Batches 2 and 3 remain planned follow-up work.

## Implementation status

Batch 1 is implemented. The complete suite passes: 92 tests and 4 subtests,
including six headless Textual cases covering keyboard controls, partial and
exhausted replacement reserves, and successful/failed playlist creation.
`git diff --check` passes. Spotify calls were mocked; live endpoint availability
and subjective recommendation quality have not been verified in this pass.

The reserve keeps ranked familiar and discovery pools in memory. Replacement
uses the requested mix where available and checks artist limits against every
other visible row, so partially filled replacements remain within the cap.
Undo applies to keep/skip decisions on tracks still displayed. Replaced skips
retain their cooldown.
