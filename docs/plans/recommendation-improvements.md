# Recommendation and curation improvements

## Approach

Keep the existing Spotify client, Textual screens, and JSON history. Implement
and commit each batch separately after its checks pass.
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

Each batch is complete when its behavioral tests pass and its interface changes
work through the existing discovery screen. API availability and subjective
music quality require separate live validation.

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

Batch 2 is implemented. Exact genre matches take priority across both candidate
pools and replacements; the requested familiar/discovery mix applies within a
genre tier. Related matches and unverified/broadened filtering are disclosed.
Per-track source details survive replacement and update with the cursor. Mood
fit is shown only for measured mean deviation at or below 0.2. Playlist counts
reflect distinct fetched playlists, not duplicate entries within a playlist.
Validation: 98 tests and 4 subtests pass, including cross-pool genre preference,
missing metadata, explanation provenance, and headless detail-panel updates.

Batch 3 is implemented. Discovery reports profile loading, familiar tracks,
search, related artists, public playlists, genre validation, ranking, and
completion. A thread-safe memory cache expires entries after ten minutes and
evicts the least recently used entries above 512. Metadata gathered from top and
followed artists is reused for genre checks. Successful empty responses can be
cached; failures cannot. The client exposes endpoint status separately from data.
403/410 responses disable optional catalog endpoints for the session, while
transient errors and playlist-specific access errors remain retryable.

Validation: 113 tests and 4 subtests pass. Tests cover expiry, eviction, mutation
isolation, request reuse, endpoint access/transient/empty responses, and threaded
progress callbacks through the real Mood and Recommendations screens.
In a controlled one-track run with 10 ms of simulated latency per metadata call,
cold/warm discovery used 3/0 metadata requests and took 37.90/0.12 ms. This is a
synthetic measurement, not a live speed claim. A read-only capability check using
the existing cached login stopped at Spotify OAuth; endpoint availability and
live recommendation quality remain unverified. No new login was opened.
