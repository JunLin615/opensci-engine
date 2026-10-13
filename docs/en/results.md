# Results, visualization, and export

[User guide](README.md) · English · [简体中文](../zh-CN/results.md)

One run produces a complete record of the design and its simulation. The results API reads that record directly, so inspecting or exporting data does not rerun the simulation.

## Read the run directory

| File | Contents |
| --- | --- |
| `manifest.json` | Overall status, target outcomes, identities, and file hashes |
| `project.json` | The optical project that was run |
| `engine_request.json` | The input passed to the physics engine |
| `simulation_result.json` | Target values, beams, observations, paths, power budget, and issues |
| `ray_data.json` | Traced chief and pupil rays, including surface crossings and optical path lengths |
| `local_validation.json` | Local Validation record with project, catalog, engine, and result identities |
| `optical_scene.json` | Structured optical scene |
| `optical_scene.glb` | 3D scene in glTF binary format |

```bash
opensci-engine results describe run
opensci-engine results monitor run output
opensci-engine project verify run
```

`output` is the observation-plane identifier in the beam-expander example. Use `results describe` to discover the planes available in your own run.

## Interpret the status

| Status | Meaning | Design action |
| --- | --- | --- |
| `PASS` | Evaluated targets are met | Inspect the values and continue the design |
| `WARNING` | Results include reported issues | Read the issue list and its context |
| `FAIL` | A requirement or validation check failed | Inspect the failing target or issue and revise the project |
| `UNKNOWN` | Available information does not determine the result | Supply the missing input or inspect the metric's requirements |
| `OUT_OF_MODEL_SCOPE` | A requested calculation is outside the selected model's domain | Read the affected model and parameter information |
| `NOT_APPLICABLE` | A check does not apply to this configuration | Continue with the relevant checks |

For scripting, design-command exit codes are `0` for PASS/WARNING/NOT_APPLICABLE, `1` for FAIL, `2` for UNKNOWN, and `3` for OUT_OF_MODEL_SCOPE. File and usage errors have separate codes in the CLI reference.

## Compact summaries from the examples

Run the examples from the repository root:

```bash
python examples/beam_expander.py --out run-example
python examples/ideal_lens_focus.py --out run-ideal-focus
```

Each example writes one JSON summary to standard output. Structured keys remain in English; diagnostics go to standard error. The default output includes the overall `status`, `engine_status`, nullable `validation_status`, and target identifiers, metrics, actual values, units, applicable bounds, outcomes, and available messages or issue codes. It also preserves actionable `issues`, `model_scope_issues`, and `element_models`, along with `identity` and `integrity` information. The compact `power_budget`, when available, contains scalar totals and `total_sinks`; the full ledger is available with `--details`.

The `artifacts` and `exports` fields point to complete data on disk. The beam-expander example saves a native local run and an arrivals CSV, and provides a `view_command` for its 3D scene. The ideal-lens example runs without a catalog download and saves its request, simulation result, rays, and arrivals under `--out`. Its low-level result does not include a native local-run manifest or a 3D viewer command. The default output directories are `run-example` and `run-ideal-focus`, respectively.

Read a previously saved native local run without repeating the simulation:

```bash
python examples/result_summary.py run-example
python examples/result_summary.py run-example --details
```

The helper verifies the saved run before summarizing it through the public results API. This command expects the native local-run artifacts produced by the beam-expander example or `opensci-engine project run`; the ideal-lens output is a low-level result bundle. The reusable Python functions in [result_summary.py](../../examples/result_summary.py) are `summarize_results(results, *, artifacts=None, details=False)` and `summarize_run(directory, *, details=False)`. Both return a dictionary suitable for JSON output.

The example scripts and saved-run summary command use these exit codes:

| Exit code | Reported result |
| --- | --- |
| `0` | `PASS`, `WARNING`, or `NOT_APPLICABLE` |
| `1` | `FAIL` |
| `2` | `UNKNOWN` |
| `3` | `OUT_OF_MODEL_SCOPE` |
| `4` | Input, artifact-integrity, runtime, or command-usage error |

Design outcomes, including a non-passing result, still produce a JSON summary and preserve complete data. Exit code `4` produces a JSON error on standard error and leaves standard output empty. These example error codes are separate from the engine CLI's file and usage error codes.

The ideal-lens target can be changed with `--maximum-radius-mm` (default `0.05`). These commands exercise the default target, a stricter target intended to fail, and invalid input:

```bash
python examples/ideal_lens_focus.py --out run-focus-default
python examples/ideal_lens_focus.py --out run-focus-strict --maximum-radius-mm 0.001
python examples/ideal_lens_focus.py --maximum-radius-mm -1
```

The radius bound must be finite and nonnegative; `nan` is also invalid. Inspect `$LASTEXITCODE` in PowerShell or `$?` in a POSIX shell immediately after each command. Use `--details` with either example to include the full power ledger in its summary; full ray data remains available through the saved artifact paths.

## View and share

```bash
opensci-engine view run
opensci-engine view run --write-html view.html
opensci-engine view run --snapshot shots
```

The browser viewer includes camera presets, selectable components, beam visibility controls, and English/Chinese labels. Snapshots include orthographic PNG views, `scene_summary.json`, and a legend.

## Export tables

```bash
opensci-engine export arrivals run --format csv --out arrivals.csv
opensci-engine export rays run --format jsonl --out rays.jsonl
opensci-engine results columns arrivals
opensci-engine results metrics --name waist_distance_x_mm
```

Exports include monitors, arrivals, rays, paths, segments, power budgets, superpositions, wavefronts, irradiance, and metric definitions. Use `export --help` for formats and selectors. Wavefront exports use traced optical-path differences; irradiance maps use the paraxial Gaussian superposition model.

From Python:

```python
from pathlib import Path
from opensci_engine.results import load_run

results = load_run("run")
print(results.describe())
print(results.power_budget())
Path("arrivals.csv").write_bytes(results.export("arrivals", "csv"))
```

## Units and conventions

The API uses millimetres for length, nanometres for vacuum wavelength, degrees for angles, and watts for power. Gaussian beam size `w` is the **1/e² intensity radius**. Coordinates are right-handed; an element's local `+z` is its optical axis. Export column names and metric descriptors identify the relevant units.

Next: [Continue from design to hardware](hardware.md).
