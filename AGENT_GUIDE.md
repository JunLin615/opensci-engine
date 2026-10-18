# Agent guide

Start here; pick **one task row**, run it, then read only the linked section. This
public repository holds customer examples and reusable workflow scripts; the engine
installs from PyPI. Agent material is English; for a human walkthrough select
[English](docs/en/README.md) or [Simplified Chinese](docs/zh-CN/README.md), not both.

## Environment and baseline

Run commands from the repository root in an activated Python 3.11+ virtual
environment ([installation guide](docs/en/installation.md) if setup is needed). The
verified engine baseline is **0.8.0**, recorded in
[engine-baseline.json](engine-baseline.json) and shared with both READMEs:

```bash
python -m pip install "opensci-engine[protected]==0.8.0" -r requirements-examples.txt
python -m opensci_engine doctor
```

`requirements-examples.txt` adds matplotlib for plots. The `protected` extra supports
hardware previews; simulation alone needs `opensci-engine==0.8.0`. A newer installed
version is not automatically verified; the [alignment workflow](docs/engine-alignment.md)
checks another release without changing the baseline.

## Select a task

Every script prints one JSON document on stdout and keeps full data in files. Edit,
study and workflow scripts never overwrite: an existing output is refused unless
`--overwrite`. Details: [workflow recipes](docs/workflow-recipes.md).

| Task | Exact invocation | Output / next read |
| --- | --- | --- |
| First run, no catalog | `python examples/ideal_lens_focus.py --out run-ideal-focus` | Summary; request, result, rays in the directory |
| Catalog beam expander (editable native project) | `python examples/beam_expander.py --out run-example` | `run-example/project.json`, native run, arrivals CSV |
| Inspect a saved run | `python examples/result_summary.py run-example [--details]` | Verified summary; no simulation |
| Find IDs; one object's values, units, frames, ops | `python examples/edit_project.py run-example/project.json --describe [--ids L2]` | Object index / detail; [recipe](docs/workflow-recipes.md#find-objects) |
| Edit by ID, validate, run | `python examples/edit_project.py BASE.json --edits EDITS.json --out NEW.json --run NEW-run` | `NEW.json`, `NEW.changes.json`, run; [recipe](docs/workflow-recipes.md#edit-a-project-by-id) |
| Bounded sweep (1–2 parameters) | `python examples/sweep_parameters.py SPEC.json --base BASE.json --out STUDY` | `table.csv`, every sample's project and run; [recipe](docs/workflow-recipes.md#sweep) |
| Compare saved runs or a study (no rerun) | `python examples/compare_runs.py RUN_A RUN_B --project CURRENT.json --out CMP` | Aligned targets, input differences, freshness; [recipe](docs/workflow-recipes.md#compare-and-freshness) |
| Plot a study or a run | `python examples/plot_results.py sweep STUDY --y target:ID` / `power RUN` | PNG + SVG with units and outcome markers |
| Report | `python examples/build_report.py STUDY --project CURRENT.json --plots STUDY/plots` | `report.md`, `report.json` with artifact sha256 |
| Catalog candidates | `python examples/catalog_candidates.py --category LENS --wavelength-nm 780 --range focal_length_mm=95..105 --near focal_length_mm=100 --limit 5` | Bounded table; [recipe](docs/workflow-recipes.md#catalog-candidates) |
| Sensitivity | `python examples/sensitivity_analysis.py examples/specs/sensitivity_expander.json --out run-sensitivity` | Derivatives with units, step check, ranking; [recipe](docs/workflow-recipes.md#sensitivity) |
| Tolerance sampling | `python examples/tolerance_study.py examples/specs/tolerance_expander.json --out run-tolerance` | Seeded samples, outcome counts, distributions; [recipe](docs/workflow-recipes.md#tolerance) |
| Beam expansion and focusing | `python examples/beam_expansion_focus.py --out run-expansion` | Nominal + studies + closed-form check; [recipe](docs/workflow-recipes.md#design-workflows) |
| Polarization control | `python examples/polarization_control.py --out run-polarization` | Same layout |
| Alignment from two planes | `python examples/alignment_analysis.py --out run-alignment` | Same layout; `--synthetic-measurements` adds a labelled fit |
| Clean and fit detector CSV | `python examples/analyze_measurements.py examples/data/measurements/detector_response.csv --x input_power_mW --signal signal_V --background dark_V --x-unit mW --signal-unit V --out run-detector` | Fit, audit CSV, residual plot; [measurement guide](docs/en/measurements.md) |

Workflow scripts: `--list-parameters` gives inputs with units; set one with e.g.
`--gap-error-mm 250um`, study one with `--study NAME=V1,V2` or `NAME=START..STOP:COUNT`,
or skip studies with `--no-studies`. Spec files in `examples/specs/` are starting points.
Python-level editing without these scripts: [editing recipe](docs/agent-recipes.md).

## Read outcomes

Inspect `status`, every target's `id`, `value`, `unit`, `bounds`, `status`, plus `issues`,
`model_scope_issues`, `identity` and artifact paths. Never infer success from a value alone.

| Status / outcome / exit | Next action |
| --- | --- |
| `PASS` / 0 | Confirm all requested targets were checked |
| `WARNING` / 0 | Read issue context before accepting |
| `NOT_APPLICABLE` / 0 | Check that relevant targets were configured |
| `FAIL` / 1 | Inspect unmet bounds or diagnostics; revise and rerun |
| `UNKNOWN` / 2 | Supply missing inputs or choose a supported metric |
| `OUT_OF_MODEL_SCOPE`, `OUT_OF_MODEL` / 3 | Change the model or operating range |
| Error / 4 | Read the JSON error on stderr; [recipe](docs/workflow-recipes.md#recovery) |

- Any non-empty `model_scope_issues` means **out of model**, whatever the status, a
  target's status or a run script's exit code (a run can read `FAIL`, or targets `PASS`,
  outside its model). Studies, workflows and `edit_project.py --run` (`run.outcome`)
  report such cases as `OUT_OF_MODEL`.
- A run is current only for the project it was computed from. `compare_runs.py` /
  `build_report.py --project` mark others `HISTORICAL` (`HISTORICAL PASS` is not a pass of
  the current design).
- Study exits: sweep 0 completed / 1 no feasible sample; sensitivity 0 / 2 a derivative
  unavailable; tolerance 0 at least one PASS / 1 none; workflows the nominal outcome
  (unmet study samples are counted, not exit codes). Pass fractions divide by **all
  requested samples**; "among evaluable" (PASS + FAIL) is a separate, labelled figure. A
  tolerance pass fraction is a simulated-sample fraction, not a manufacturing yield.

Engine CLI exit codes differ (`python -m opensci_engine --help`). Do not retry an
unchanged invalid request; rerunning the same edit command is safe (`already_applied`).
Report the command, engine version, units, status and artifact paths.

## Inputs and units

Establish wavelength (nm), source power (W), Gaussian 1/e² waist **radius** and its
position (mm), component/observation IDs and poses, and target metrics with bounds;
clarify missing requirements before claiming a design meets them. Lengths mm, angles
degrees, power W in the right-handed design frame; poses use `quaternion_wxyz`. Script
specs also accept `{"value": x, "unit": "um"}`. Read `run-example/project.json` or
`--describe` output for the exact products, poses and targets rather than guessing.
The ideal focus uses 532 nm, 0.001 W, 1 mm waist radius, f = 100 mm, a plane 100 mm after
the lens and a 0.05 mm maximum radius (`--maximum-radius-mm`). Catalog commands may
download public data on first use; on a download failure check connectivity and the
[catalog guide](docs/en/catalog.md), and use the ideal focus as an installation check.

## External scientific tools

Install one topic's `requirements-<topic>.txt` into its own fresh Python 3.12+ virtual
environment, then read its section of the [external tools guide](docs/en/interop.md):

| Task | Entry point | Independent check |
| --- | --- | --- |
| Optimize or tolerance a Project with SciPy / Optuna / SALib | `examples/interop/optimization/optimize_expander.py` | ABCD optimum and per-design values |
| Diffraction at a declared stop (LightPipes, prysm, POPPY, Diffractio) | `examples/interop/diffraction/opensci_handoff.py`, then `external_focus.py` | Hankel integral, grid and window convergence |
| Photon statistics from the network export (Perceval, Piquasso) | `examples/interop/quantum/build_layouts.py`, then `run_quantum.py` with `quantum_inputs.json` | Closed-form two-photon interference |
| Metasurface response to a `TABULATED_THIN_LENS` model (grcwa) | `examples/interop/metasurface/step1_unit_cells.py` … `step4_engine_check.py`: seven commands incl. the convergence tables | Separate test wavelengths and settings, convergence spread, out-of-scope counterexamples |

Their `outcome` compares with the external tool or reference: `WITHIN_TOLERANCE` /
`COMPLETED` exit 0, `OUT_OF_TOLERANCE` exit 1, error exit 4; OpenSci's status is
`engine_status`. Quantum inputs come only from the user's input file. External results
never replace a run's status or Local Validation. Prompts:
[interop prompts](docs/en/interop-prompts.md).

The entry's token measurement and a representative task trial are recorded in
[guide validation](docs/agent-guide-validation.md).
