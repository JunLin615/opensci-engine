# Agent guide

Start here; read **one relevant workflow**, then follow its result. This public
repository contains customer examples and helpers. Install the engine from PyPI;
private source access is unnecessary. Agent instructions stay in English. For a
human walkthrough, select [English](docs/en/README.md) or
[Simplified Chinese](docs/zh-CN/README.md), not both.

## Environment and baseline

Run commands from the repository root in an activated Python 3.11+ virtual
environment. Use the [installation guide](docs/en/installation.md) only if setup
is needed. The verified engine baseline is **0.6.1**, shared with both READMEs;
[validation evidence](docs/result-summary-validation.md) records the environment
and catalog used. To reproduce it:

```bash
python -m pip install "opensci-engine[protected]==0.6.1"
python -c "from importlib.metadata import version; print(version('opensci-engine'))"
python -m opensci_engine doctor
```

The `protected` extra supports hardware previews; optical simulation alone needs
only `opensci-engine==0.6.1`. A newer installed version is not automatically a
verified baseline. Examples follow released engine APIs; implement engine changes
in `opensci`, then update this repository against the published package.

## Select a task

| Task / input | Exact invocation | Output / next read |
| --- | --- | --- |
| First run; no catalog needed | `python examples/ideal_lens_focus.py --out run-ideal-focus` | JSON summary; full request, result, rays and arrivals CSV in that directory |
| Catalog beam expander; default project | `python examples/beam_expander.py --out run-example` | JSON summary, native run directory, sibling `run-example-arrivals.csv`, viewer command |
| Inspect a saved native run | `python examples/result_summary.py run-example` | Verified summary; no simulation or file changes |
| Inspect full power ledger | `python examples/result_summary.py run-example --details` | Summary plus complete power entries and rows |
| Find catalog lenses at 780 nm | `python -m opensci_engine catalog list --category LENS --wavelength-nm 780 --limit 5` | Bounded candidate list; [catalog guide](docs/en/catalog.md) for filters and releases |
| Change wavelength, positions or targets | Follow [editing recipe](docs/agent-recipes.md) after creating `run-example` | New validated project and run, preserving the original |
| Clean and fit detector CSV | `python examples/analyze_measurements.py examples/data/measurements/detector_response.csv --x input_power_mW --signal signal_V --background dark_V --x-unit mW --signal-unit V --out run-detector` | Fit/row summary, original input, audit CSV, provenance and residual plot; [measurement guide](docs/en/measurements.md) for reference normalization |

Measurement analysis runs independently of the engine; install its plotting
dependency with `python -m pip install -r requirements-examples.txt`. Set
`--maximum-rmse` in response units when an acceptance bound is required. Review
excluded rows and residuals; successful fitting alone does not validate a detector.

The catalog example may download public data on first use. A saved project pins
its catalog release. On a download failure, check connectivity and the catalog
guide; use the ideal-lens route for an independent installation check. Generic
sweeps are not yet delivered; do not invent commands for them.

## Inputs and units

For a customer design, establish wavelength (nm), source power (W), Gaussian waist
radius and its position (mm), component/observation IDs and poses, and target
metric plus bounds or value/tolerance. Clarify missing requirements before claiming
that a design meets the customer's needs. Demonstration defaults are explicit:

- Ideal focus: 532 nm, 0.001 W, 1 mm source waist radius, 100 mm focal length, observation
  100 mm after the lens, maximum beam radius **0.05 mm**. Change its target with
  `python examples/ideal_lens_focus.py --out run-focus-strict --maximum-radius-mm 0.001`.
- Beam expander: 780 nm, 0.001 W, 1 mm waist radius; the generated catalog design
  supplies component poses and an expanded-waist target. Read `run-example/project.json`
  for the exact selected products, positions and target, rather than guessing them.

Lengths are mm, wavelength nm, angles degrees, and power W. Gaussian size means
**1/e² intensity radius**, not diameter. Positions use the right-handed design
frame; poses use `quaternion_wxyz` orientation. Keep coordinate frames explicit.

## Inspect before iterating

Prefer the ideal focus for a first run: no customer inputs or catalog are needed
to check the installation. Read its single JSON document on stdout. At minimum
inspect `status`, every target's `id`, `value`, `unit`, `bounds`, and `status`, plus
`issues` and `model_scope_issues`. Check `identity` for engine/catalog provenance,
`integrity` for verification, and `artifacts` / `exports` for complete data.
The low-level ideal bundle has no native manifest or 3D scene; saved-run inspection
expects a native run such as the beam expander. See [results](docs/en/results.md)
only when more detail is needed. Preserve run directories and write revisions to
new paths. Never infer success from a numeric value alone.

| Summary status / example exit | Next action |
| --- | --- |
| `PASS` / 0 | Confirm all requested targets were actually checked |
| `WARNING` / 0 | Read issue context and suggested actions before accepting |
| `NOT_APPLICABLE` / 0 | Determine whether relevant checks were configured |
| `FAIL` / 1 | Inspect unmet bounds or diagnostics; revise and rerun |
| `UNKNOWN` / 2 | Supply missing inputs or choose a supported metric |
| `OUT_OF_MODEL_SCOPE` / 3 | Read model-scope issues; change the model or operating range |
| Error / 4 | Read JSON error on stderr; fix input, usage, artifact integrity or runtime problem |

These exits apply to repository scripts. Engine CLI usage/input/integrity errors
use separate codes documented by `python -m opensci_engine --help`. Do not retry
an unchanged invalid design or hide unsuccessful outcomes. For reports, include
the command, engine version, target units, error/status, and relevant artifact paths.

Keep discovery bounded: use the task table, one recipe, and only the necessary
result fields. The entry's token measurement and a representative task's reading,
calls, retries and outcome are recorded in [guide validation](docs/agent-guide-validation.md).
