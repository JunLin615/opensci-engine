# Your first optical design

[User guide](README.md) · English · [简体中文](../zh-CN/getting-started.md)

This walkthrough builds a two-lens beam expander, runs it locally, and opens its optical scene. Complete the [installation](installation.md) first.

## 1. Load the catalog

```bash
opensci-engine catalog sync
opensci-engine catalog list --category LENS --wavelength-nm 780 --limit 20
```

The catalog lists OpenSci optical components with their design specifications and simulation models. Copy a returned `optical_sku` into `opensci-engine catalog show OPTICAL_SKU` to inspect a component.

## 2. Create a project

```bash
opensci-engine project example --kind beam_expander > project.json
```

In Windows PowerShell 5.1, use:

```powershell
opensci-engine project example --kind beam_expander | Out-File -Encoding utf8 project.json
```

The generated JSON includes optical components, poses, sources, observation planes, and targets. Each catalog component carries the catalog version used by the design.

Other starting points:

| Example kind | Optical system |
| --- | --- |
| `focus` | A single focusing lens |
| `folded` | A fold mirror and a lens |
| `beam_expander` | A two-lens telescope |
| `relay_4f` | A 4f relay |
| `folded_expander` | A folded beam expander |
| `dichroic_routing` | Two wavelengths routed by a dichroic mirror |
| `polarization` | A waveplate and polarizer |
| `two_beam_interference` | Two arms from one laser crossing at an observation plane |
| `two_color_dichroic` | A two-line source routed to two detectors |
| `dichroic_combiner` | Two lasers combined onto one beam |

## 3. Simulate

```bash
opensci-engine project run project.json --out-dir run
opensci-engine project verify run
```

The run command writes the result and its supporting artifacts into `run`. Start with `manifest.json` for the overall status and target outcomes. See the [results guide](results.md) for individual files and status meanings.

## 4. Explore the scene

```bash
opensci-engine view run
```

Use the camera presets, select an optical element to see its properties, and toggle beam paths. The viewer supports English and Chinese. Stop the local viewer with Ctrl+C in the terminal.

For a standalone HTML view or image snapshots:

```bash
opensci-engine view run --write-html view.html
opensci-engine view run --snapshot shots
```

## 5. Inspect, change, repeat

```bash
opensci-engine results describe run
opensci-engine export arrivals run --format csv --out arrivals.csv
opensci-engine schema project
```

Edit `project.json` to change component positions, source parameters, or design targets, then write the next run to a new directory:

```bash
opensci-engine project run project.json --out-dir run-revised
```

Keep the original run to compare target values and beam data. A typical design loop is **define targets → simulate → inspect results → adjust geometry → simulate again**.

## Working with your agent

Give your coding agent a concrete task:

> Use OpenSci Engine to create a beam-expander example. Run it locally, inspect the target outcomes and power budget, and export the beam-arrival table as CSV. Show me the 3D view and explain the beam sizes and component spacing.

The CLI returns structured output, and the Python API lets an agent read the same project and scientific results. The [example script](../../examples/beam_expander.py) demonstrates the complete local workflow.

Next: [Read and export results](results.md) or [continue to hardware](hardware.md).
