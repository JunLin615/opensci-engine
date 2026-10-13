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
