# dd-l2-bangkok-multicrs-audit

## Story

Krit Suwannarat, a deliverables auditor at Thailand's Ministry of
Interior, has just received a multi-layer GPKG of ward-level
infrastructure from a contractor consortium. He suspects the
consortium silently merged sources with disagreeing CRSes inside a
single container, and that an in-house tool mangled the Thai-script
labels via the classic UTF-8→Latin-1→UTF-8 double-decode bug. He needs
a one-row-per-layer audit table with the declared CRS, geometry type,
feature count, a sample coordinate in the layer's *own* CRS, and the
detected text encoding so he can reject the deliverable with each
defect cited row by row.

## What this task probes

Multi-layer GPKG enumeration plus per-layer schema + content
introspection plus encoding-defect detection plus tabular CSV
assembly:

* List every layer in the container (don't treat the GPKG as
  single-layer).
* Read each layer's *declared* CRS without reprojecting (the audit's
  point is to capture what the contractor declared, not what the
  agent thinks they should have declared).
* Pull a sample coordinate in the layer's own CRS so the auditor can
  spot-check that the coordinate magnitudes match the declared CRS.
* Heuristically detect Latin-1 mojibake on a non-ASCII text column —
  the canonical signature is "UTF-8 bytes interpreted as Latin-1, then
  re-encoded as UTF-8", which leaves visible chars in the Latin-1
  Supplement block (e.g. `à¸ª`) where Thai-block characters belong.
* Assemble the result as a clean CSV table.

## Why this difficulty

L2: chains schema introspection, attribute decoding, and tabular
assembly across multiple layers — strictly more than L1's single
operation, but bounded to bundled data so there's no fetching or
discovery component (which would push it to L3). The encoding
heuristic is the operation that lifts the task above L1: the agent
must reason that bytes-as-Latin-1-redecoded-as-UTF-8 yielding a
non-ASCII string is a positive signal, while ASCII strings are
inconclusive. No spatial computation, no reprojection, no joins.

## Input / output formats

### Input

`inputs/bangkok_contractor_delivery.gpkg` — single GPKG with three
layers, each in a different CRS:

| Layer | Geometry | Features | Declared CRS | Encoding |
|---|---|---|---|---|
| `parcels` | Polygon | 4000 | `EPSG:24047` | latin1-mojibake on `name_th` |
| `roads` | LineString | 5000 | `EPSG:32647` | latin1-mojibake on `name` |
| `markets` | Point | 1000 | `EPSG:4326` | utf-8 (clean) |

### Output

`crs_audit.csv` — CSV with header row and one row per layer:

```csv
layer_name,declared_crs,geometry_type,feature_count,sample_x,sample_y,encoding_detected
markets,EPSG:4326,Point,1000,100.45,13.66,utf-8
parcels,EPSG:24047,Polygon,4000,657706.46,1509274.7,latin1-mojibake
roads,EPSG:32647,LineString,5000,657156.99,1509488.92,latin1-mojibake
```

`sample_x` / `sample_y` are in the layer's own declared CRS. Order of
rows is not graded — the grader indexes by `layer_name`. The
reference's choice of "first feature, by sorted id, representative
point" is one valid implementation; agents that sample any feature
are graded identically as long as the coordinate values fall in the
plausibility window for their declared CRS.

## Failure modes

1. **Agent treated the GPKG as single-layer** and only opened the
   default first layer, writing one audit row instead of three.
   *Detection:* `layers_complete` fails plus the two missing layers'
   10 subchecks fail. Covered by `broken_partial_layers`
   (score 0.2941 under the 2026-06-14 severity weighting).
2. **Agent skipped the Latin-1 mojibake heuristic** and reported
   every layer as `utf-8`. *Detection:* both
   `parcels_encoding_correct` and `roads_encoding_correct` flip while
   the rest pass. Covered by `broken_wrong_encoding` (score 0.8824
   under the 2026-06-14 severity weighting).
3. **Agent emitted the audit in the wrong format** (JSON, GeoPackage,
   plain text). *Detection:* Gate 1 rejects on the required-columns
   header check. Covered by `broken_wrong_format` (score 0.000).
4. **Agent silently reprojected every layer to EPSG:4326** before
   reading sample coordinates. *Detection:* `parcels_declared_crs_correct`
   and `roads_declared_crs_correct` flip; the sample-coord check also
   fails for those layers because lon/lat values fall outside the
   metric plausibility window. Not covered by a broken solution;
   principled detector is the per-layer `declared_crs_correct` and
   `sample_coords_plausible` subchecks.
5. **Agent reported sample coordinates from the wrong CRS** (e.g.
   declared `EPSG:24047` but reported lon/lat ~100/13). *Detection:*
   `<layer>_sample_coords_plausible` fails for the affected layers
   because (100, 13) is far below the EPSG:24047 metric window
   (~6×10⁵ off). Not covered by a broken solution; principled
   detector is the per-layer `sample_coords_plausible` subcheck.
6. **Agent overzealously flagged the clean layer as mojibake**
   because its Thai labels look "non-ASCII" — the agent didn't check
   that re-decoding actually produces a *different* string.
   *Detection:* `markets_encoding_correct` fails (markets is genuinely
   UTF-8). Not covered by a broken solution; principled detector is
   the markets-layer encoding subcheck.
7. **Agent invented its own CRS string format** like `"24047"` or
   `"Indian 1975 UTM 47N"` rather than the canonical `"EPSG:24047"`.
   *Detection:* every `declared_crs_correct` subcheck fails. Not
   covered by a broken solution; principled detector is the per-layer
   `declared_crs_correct` subcheck (case-insensitive exact match on
   the canonical `EPSG:NNNN` form).
8. **Agent off-by-one on feature counts** — e.g. counted features but
   subtracted 1 for a header row, or summed `len()` over geometry
   types and produced a wrong total. *Detection:* the affected
   layer's `feature_count_correct` subcheck fails. Not covered by a
   broken solution; principled detector is the count subcheck.

## Expected weak-agent failure mode

The most likely weak-agent failure is **#1 — single-layer
enumeration**. A weak agent that opens the GPKG as if it were a
single-layer GeoJSON-like file (no `pyogrio.list_layers` /
`fiona.listlayers` / `ogrinfo` call, no SQLite-style multi-table
inspection) sees only the first layer and writes a one-row audit
table. That produces a structurally perfect output that scores
0.2941, clearly distinguishable from a wrong-format solution
(0.000), an encoding-skipping solution (0.8824), and a fully correct
solution (1.000).
