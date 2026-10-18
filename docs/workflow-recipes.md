# Workflow recipes for agents

[Agent guide](../AGENT_GUIDE.md). English-only reference for the workflow scripts in
`examples/`; read only the section the task needs. Each script's `--help` holds its
complete specification. Verified with opensci-engine **0.8.0** and catalog release
`2026-10-15.1`. Human walkthrough: [English](en/workflows.md) ·
[简体中文](zh-CN/workflows.md).

## Conventions

- Run from the repository root. Stdout is one compact JSON document; diagnostics go to
  stderr. A refusal prints `{"error": {"code", "message", ...}}` on stderr, nothing on
  stdout, and exits 4; nothing is run or written. One exception: when `edit_project.py
  --run` writes a valid edit and the Engine refuses the run, stdout reports
  `run.status` `RUN_REFUSED` with its `problems` (exit 4).
- Inputs are never modified. Edit, study and workflow scripts refuse an existing output
  (`OUTPUT_EXISTS`) unless `--overwrite`.
- Numbers keep their schema unit (`_mm`, `_nm`, `_w`/`_W`, `_deg`, `_rad`; target bounds
  in the target's `unit`) or are written `{"value": 250, "unit": "um"}` with `nm`, `um`,
  `mm`, `m`, `deg`, `rad`, `mrad`, `urad`, `W`, `mW`, `uW`. Quaternions `[w, x, y, z]`
  are unitless; rotation angles are degrees unless given as a quantity.
- Paths in stdout are as given on the command line; paths recorded inside a study are
  relative to its study directory.

| Script | Exit 0 | 1 | 2 | 3 | 4 |
| --- | --- | --- | --- | --- | --- |
| `edit_project.py` | `EDITED`, `ALREADY_APPLIED`, `DESCRIBED`; with `--run` outcome `PASS` (run `PASS` / `WARNING`) | outcome `FAIL` | outcome `UNKNOWN` | outcome `OUT_OF_MODEL` | refused, `RUN_REFUSED` |
| `sweep_parameters.py` | `COMPLETED` | `NO_FEASIBLE` (constraints given, none met) | | | refused |
| `sensitivity_analysis.py` | `COMPLETED` | | `INCOMPLETE` (a derivative unavailable) | | refused |
| `tolerance_study.py` | `COMPLETED` (at least one PASS), `DRAWN`, `REPRODUCED` | `NO_FEASIBLE` (no PASS), `MISMATCH` | | | refused |
| `compare_runs.py`, `plot_results.py`, `build_report.py` | `COMPLETED` | | | | invalid input |
| `catalog_candidates.py` | `COMPLETED` | `NO_MATCH` | | | invalid input, no catalog |
| three design workflows | nominal `PASS` | nominal `FAIL` | `UNKNOWN` | `OUT_OF_MODEL` | `ERROR`, refused |

`edit_project.py --run` exits with the run's outcome class (below): a run with any
model-scope issue exits 3 even when its Engine status is `FAIL`. `run.status` keeps the
Engine status and `run.model_scope_issues` the reasons.

## Outcome classes

Studies, comparisons and workflows classify every sample or run, in this precedence:

1. `ERROR`: the edit, load or run was refused, or the sample was not run.
2. `OUT_OF_MODEL`: completed with any `model_scope_issues` or status `OUT_OF_MODEL_SCOPE`,
   whatever the target statuses.
3. `UNKNOWN`: a selected target has no value or status `UNKNOWN` (also a selected target
   id that the run does not contain, or a run with no target to evaluate).
4. `FAIL`: a selected target failed.
5. `PASS`: every selected target is `PASS`, or `WARNING` with a value (warning codes are
   listed).

No sample is dropped. `pass_fraction` is PASS / **all requested samples**;
`pass_fraction_among_evaluable` is PASS / (PASS + FAIL) and is labelled as such.

## Find objects

```bash
python examples/edit_project.py run-example/project.json --describe
python examples/edit_project.py run-example/project.json --describe --ids SRC,L2,expanded_waist
```

The first prints every component, observation and target with `id`, `kind`, `role`,
`binding` and position (686 bytes for the catalog beam expander). `--ids` adds, per
object, the current values with units, pose with `local_axes` in design axes, retained
DOFs, the allowed ops, target bounds with `bounds_unit`, and the model and catalog
wavelength bands, plus one `conventions` block (transform frames and pivots, pose
formula, component origin, plane axes). Read `local_axes` before moving along a local
axis: in the catalog beam expander L2's local +Z is design −X.

## Edit a project by ID

```bash
python examples/edit_project.py BASE.json --edits EDITS.json --out NEW.json [--run RUN_DIR] \
    [--changes FILE] [--expect-base-hash HASH] [--overwrite]
```

`EDITS.json` is a list of operations (or `{"ops": [...]}`) in the Designer
`updateProject` vocabulary, applied in order to a copy of BASE. `changes` objects merge;
`null` removes a field.

| Op | Arguments |
| --- | --- |
| `set_component_pose` | `instance_id`, `position_mm?`, `quaternion_wxyz?` (absolute, design frame) |
| `set_source_model` | `instance_id`, `changes` (e.g. `wavelength_nm`, `power_w`, `waist_radius_mm`) |
| `set_observation_pose`, `set_observation` | `observation_id`, pose fields or `changes` |
| `set_target` | `target_id`, `changes` (bounds in the target's unit) |
| `set_component_product` | `instance_id`, `optical_sku`, `catalog_version?` |
| `set_component_model` | `instance_id`, `optical_model_id`, `custom_part_key?`, `description?` |
| `set_retained_dof(s)`, `set_design_intent` | as in `--help` |
| `add_/remove_component`, `add_/remove_observation`, `add_/remove_target` | object or id |
| model ops | `add_/update_/remove_optical_model`, `add_/update_/remove_model_material`, `add_/remove_model_coating` |
| `transform` | `selector {ids \| groups \| instances \| kinds}`, `translation_mm?`, `rotation? {axis, angle_deg} \| {quaternion_wxyz}`, `frame "design" \| {"component": ID}`, `pivot "frame_origin" \| "selection_centroid" \| {"point_mm": [...]} \| {"component": ID}` |

`transform` is a rigid move computed by the Engine; translation and rotation axis are in
the frame's axes, so `"frame": {"component": "L2"}` with `"translation_mm": [0, 0, 0.25]`
moves L2 0.25 mm along its own optical axis. Observation ids in the selector move too.

Example on the catalog beam expander (`python examples/beam_expander.py --out run-example`):
change the wavelength, move L2 and the output plane 1 mm along design +X, and replace the
waist target by an interval. Save as `edits.json`:

```json
[
  {"op": "set_source_model", "instance_id": "SRC", "changes": {"wavelength_nm": 785}},
  {"op": "transform", "selector": {"ids": ["L2", "output"]}, "frame": "design", "translation_mm": [1, 0, 0]},
  {"op": "set_target", "target_id": "expanded_waist",
   "changes": {"target_value": null, "tolerance_rel": null, "minimum": 1.8, "maximum": 2.2}}
]
```

```bash
python examples/edit_project.py run-example/project.json --edits edits.json --out run-edit/project.json --run run-edit/run
```

Result on catalog `2026-10-15.1`: exit 1, `run.outcome` `FAIL`, `expanded_waist`
1.1148985411200965 mm outside 1.8–2.2 mm (a completed run of a design that misses its
target). The output is `run-edit/project.json` (the Engine-normalized Project),
`run-edit/project.changes.json` (every op as given and normalized, before/after of each
affected field, project hashes before and after, output sha256) and the run directory.

Retry and concurrency:

- Running the same command again prints `"already_applied": true`, writes nothing and
  reuses the run when it is still current (`run.reused: true`).
- The same `--out` with different ops or a changed base is refused: `OUTPUT_EXISTS` with
  `mismatch` `OPS_CHANGED`, `BASE_CHANGED`, `RECORD_MISSING` or `OUTPUT_MODIFIED`. Choose a
  new `--out`, or `--overwrite` deliberately.
- `--expect-base-hash HASH` (the `base_project_hash` of a previous result) refuses with
  `BASE_CHANGED` and the `current_hash` when BASE has changed since that result.

## Sweep

```bash
python examples/sweep_parameters.py SPEC.json [--base BASE.json] --out STUDY_DIR
```

| Key | Meaning |
| --- | --- |
| `base_project` | Project file relative to the spec; `--base` overrides |
| `parameters` | 1 or 2 entries `{name, unit?, values \| range {start, stop, count}, ops}`; two give the full grid, first outermost |
| `max_evaluations` | required; refused with `BUDGET_EXCEEDED` before any run when the sample count exceeds it |
| `targets` | ids deciding each sample's outcome (default all); an id not in the Project is refused with `TARGET_UNKNOWN` |
| `constraints` | all must hold: `{"outcome": [...]}`, `{"target": ID, "status": [...]}`, `{"column": C, "min"?, "max"?}` (quantities convert to the column unit) |
| `objective` | `{"column": C, "sense": "minimize" \| "maximize"}` over feasible samples (in model, not `ERROR` or `UNKNOWN`, every constraint met) |
| `derived` | `{"name", "op": add \| sub \| mul \| div \| abs \| abs_diff, "a", "b"}` |
| `stop_on` | outcome classes that stop the sweep; remaining samples become `ERROR` (default none) |

Placeholders in `ops`: `"$value"` becomes `{"value": v, "unit": <parameter unit>}`;
`{"$value": {"scale": s, "offset": o}}` becomes `o + s·v`. Each sample applies its ops to
the unchanged base. Columns: `param:<name>`, `target:<id>` (target unit),
`derived:<name>`. Examples: `examples/specs/beam_expander_l2_sweep.json` (one parameter,
constraint and objective) and `examples/specs/polarization_hwp_wavelength_sweep.json`
(2-parameter grid with out-of-model samples).

Writes `study.json` (spec as given and normalized, base hash, identities, budget),
`samples/<id>/{project.json, run/, sample.json}`, `table.csv` (every sample: parameters
with units, outcome, status, `model_scope_issues`, per-target value/unit/status, error
codes, hashes, run path, seconds) and `summary.json`. Stdout lists counts with
denominators, the best sample or `no_feasible` with the failed constraints, and at most
five rows.

## Compare and freshness

```bash
python examples/compare_runs.py RUN_A RUN_B RUN_C --project CURRENT.json --out CMP
python examples/compare_runs.py STUDY_DIR --project CURRENT.json
```

Reads saved runs only. Targets and observation planes are aligned by ID (absent ones are
`"missing": true`); `delta` is against the first run or `--reference`. Only differing
inputs are listed (source fields, poses, products and declared models, target
definitions, catalog release, Engine build). With `--project`, each run is `CURRENT`
when its project hash, Engine input hash and Engine build match the current project and
installation, otherwise `HISTORICAL` with reasons `PROJECT_CHANGED`, `ENGINE_CHANGED` or
`RUN_UNVERIFIED`; outcomes then read e.g. `HISTORICAL PASS`. A historical result never
counts as a check of the current project: rerun it. Files: `CMP/compare.json`,
`CMP/compare.csv` (long format).

## Plots and reports

```bash
python examples/plot_results.py sweep STUDY_DIR --y target:expanded_waist
python examples/plot_results.py power RUN_DIR
python examples/build_report.py STUDY_DIR --project CURRENT.json --plots STUDY_DIR/plots --changes NEW.changes.json
python examples/build_report.py RUN_A RUN_B --project CURRENT.json --out REPORT_DIR
```

`sweep` draws a curve (one parameter) or heatmap (two) with axis units, the target band
and every sample's outcome marker; samples without a value stay visible at the axis edge
or in their cell. `power` plots received power per plane and the power-ledger sinks.
`bars` and `histogram` take a small JSON file (`--help`). PNG + SVG go to
`STUDY_DIR/plots/` or, for a run, `plots/` next to the run directory; the caption names
the data file (sha256 prefix), Engine build and catalog release. Reports write
`report.md` + `report.json` (default `STUDY_DIR/report/` or `./report/`) with inputs,
the edit record, outcomes with units, diagnostics, freshness, plot links and every
artifact's relative path and sha256.

## Catalog candidates

```bash
python examples/catalog_candidates.py --category LENS --form PLANO_CONVEX_LENS --wavelength-nm 780 \
    --range focal_length_mm=95..105 --range outer_diameter_mm=12.7..12.7 --near focal_length_mm=100 \
    --limit 8 --columns optical_sku,focal_length_mm,outer_diameter_mm,working_band_nm --out candidates.csv
```

`--category`, `--form`, `--readiness`, `--mounting` and `--wavelength-nm` (a published
model is valid there) are Engine filters; `--range FIELD=MIN..MAX[UNIT]` compares the
catalog's decimal strings exactly (either side may be empty); `--near FIELD=VALUE` or
`--sort FIELD [--descending]` order the rows; `--limit` ≤ 100. The output states
`catalog_version`, `engine_matches`, `matched`, products excluded for a missing field,
`shown` and `omitted`; `--out` writes every matched row. The command above returns 8 of
471 plano-convex lenses valid at 780 nm. Use a returned `optical_sku` in
`set_component_product`.

## Sensitivity

```bash
python examples/sensitivity_analysis.py SPEC.json --out STUDY_DIR [--base BASE.json] [--no-plots] [--no-report]
```

| Key | Meaning |
| --- | --- |
| `base_project` or `design` | Project file, or `{"builder": NAME, "arguments": {...}}` from `examples/optical_designs.py` (catalog-free) |
| `targets` | target ids to differentiate (unknown ids refused: `TARGET_UNKNOWN`) |
| `parameters` | `{name, unit, ops, nominal = 0, steps (≥ 2; numbers, quantities or {"relative": r}), scale?}` |
| `consistency_threshold` | relative difference of two step estimates that is flagged (default 0.01) |
| `resolution` | per-target change treated as none, e.g. `{"far_position_u": {"value": 1, "unit": "nm"}}` |
| `max_evaluations` | required; 1 + 2·(total steps) must fit |

`"$value"` is nominal + perturbation. For a `transform` translation or rotation keep
`nominal` 0 (the ops move by the step); for a `set_*` op give the field's base value as
`nominal`, otherwise `NOMINAL_MISMATCH`. Default steps: 0.01 and 0.1 mm, 0.01° and 0.1°,
relative 1e-3 and 1e-2. Method: central difference at each step, forward or backward
(labelled, with the reason) when one side is ERROR, out of model or without value;
second difference reported; flags `STEP_DEPENDENT`, `NEAR_EXTREMUM` (use the second
difference there), `NO_CHANGE`, `ONE_SIDED`, `METHOD_DIFFERS`, `UNAVAILABLE`. Units are
target unit per parameter unit. With `scale`, `scaled` = D·s and the ranking uses
|D|·s + |f″|·s²/2. Files add `sensitivity.csv` and `plots/sensitivity_<target>`,
`plots/tornado_<target>`. Specs: `examples/specs/sensitivity_*.json`;
`sensitivity_expander_band_edge.json` shows a one-sided estimate next to the band edge.

## Tolerance

```bash
python examples/tolerance_study.py SPEC.json --out STUDY_DIR [--seed N] [--samples N] [--zero-tolerance] [--draw-only]
python examples/tolerance_study.py --verify-seed STUDY_DIR
```

| Key | Meaning |
| --- | --- |
| `base_project` or `design` | as for sensitivity |
| `targets` | all must PASS for a sample to PASS |
| `samples`, `seed`, `max_evaluations` | sample count (nominal run extra), integer seed, budget ≥ samples + 1 |
| `parameters` | `{name, unit, ops, nominal = 0, distribution}`, sampled independently in this order |
| `distribution` | `{"kind": "uniform", "low", "high"}` or `{"kind": "normal", "sigma", "mean_offset" = 0, "truncate_sigma" \| "bounds": [low, high]}` (offsets in the parameter unit) |

Offsets come from `numpy.random.Generator(PCG64(seed))`, one uniform number per sample
and parameter, row by row; `samples.csv` and `sampling.json` are written before any run.
The same seed and spec give byte-identical `samples.csv`, and the first n samples of a
larger run are the same; `--verify-seed` redraws and compares. `--zero-tolerance`
reproduces the nominal project and result hashes exactly. Stdout: counts per outcome
class with denominators, target-value statistics over samples completed in model scope
(count stated), sampling assumptions. Specs: `examples/specs/tolerance_*.json`.

## Design workflows

```bash
python examples/beam_expansion_focus.py --out run-expansion-gap --gap-error-mm 250um --study f3_mm=75..125:5
python examples/polarization_control.py --out run-pol-1064 --wavelength-nm 1064 --no-studies
python examples/alignment_analysis.py --out run-alignment-tilt --study mirror_tilt_local_y_mrad=-1..1:5
```

Each builds a catalog-free design from `examples/optical_designs.py`, runs it, runs its
studies, compares each study with the nominal run, plots changing targets, compares the
Engine values with an independent closed-form reference and writes reports.
`--list-parameters` prints every input with unit, default, meaning and role. Inputs take
a bare number in the option's unit or a unit suffix (`--gap-error-mm 250um`,
`--min-power-w 0.85mW`). `--study NAME=V1,V2` or `NAME=START..STOP:COUNT` (repeatable)
replaces the default studies; `--max-evaluations` (default 40) bounds nominal plus all
samples before anything runs. Output: `DIR/workflow.json`, `DIR/nominal/`,
`DIR/studies/<NAME>/` (sweep study, `compare/`, `plots/`, `closed_form.json`, `report/`),
`DIR/report/report.md`. Exit follows the nominal outcome; study samples are counted in
`studies[].counts` and `pass_fraction` ("n/N"). `alignment_analysis.py
--synthetic-measurements` adds a fit of rows labelled `SYNTHETIC` (not measurements).

## Recovery

| Error code | Cause | Next step |
| --- | --- | --- |
| `OUTPUT_EXISTS` | output file or directory already holds other results | new `--out`; `--overwrite` only to replace it |
| `BASE_CHANGED` | `--expect-base-hash` differs from the base | re-read the base (`--describe`) and rebuild the edit |
| `PROJECT_OP_INVALID` | `op_code` `UNKNOWN_OP`, `NOT_FOUND`, `DUPLICATE_ID`, `BAD_ARGUMENT`, `IN_USE`, `UNIT_UNKNOWN`, `UNIT_INCOMPATIBLE` at `op_index` | fix that op; check ids with `--describe` |
| `WORKSPACE_OPERATION_REFUSED` | a `transform` result is invalid, e.g. `OPTICAL_BODIES_OVERLAP` in `problems` | smaller move or other pivot/frame |
| `PROJECT_REJECTED` | the Engine check refuses the edited Project; `problems` list codes and locations | change the offending values |
| `RUN_REFUSED` (`run.status`) | the edit was written but the Engine refused the run | read `run.problems`; adjust geometry or models |
| `BUDGET_EXCEEDED` | more evaluations than `max_evaluations` | fewer values or a deliberate larger budget |
| `SPEC_INVALID`, `TARGET_UNKNOWN`, `NOMINAL_MISMATCH`, `STEP_REQUIRED` | spec structure, unknown target, `set_*` parameter without its base `nominal`, relative step at nominal 0 | fix the spec as the message states |
| `INPUT_INVALID` | a workflow input cannot build a design | change the named input |
| `CATALOG_NOT_AVAILABLE` | no catalog release installed | `opensci-engine catalog sync` (or `catalog import FILE`) |

An `ERROR` sample inside a study is recorded with its stage and code in `table.csv`; the
other samples still run.
