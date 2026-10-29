<p align="center">
  <a href="https://opensci-optics.com/"><img src="assets/logo.svg" alt="OpenSci" width="88"></a>
</p>

# OS Optics

**Optical design, simulation, and a path to real hardware.**

English · [简体中文](README.zh-CN.md)

[![PyPI](https://img.shields.io/pypi/v/os-optics.svg)](https://pypi.org/project/os-optics/)
[![Python](https://img.shields.io/pypi/pyversions/os-optics.svg)](https://pypi.org/project/os-optics/)
[![Website](https://img.shields.io/badge/website-opensci--optics.com-167D8D)](https://opensci-optics.com/)

Build optical systems, simulate light propagation, and explore the results on your own computer. OS Optics combines a catalog of optical components, deterministic physics, structured scientific results, and an interactive 3D view in one Python package. Use it directly or through your own coding agent.

When a design is ready, continue to [OpenSci](https://opensci-optics.com/) for optical components, assembly configurations, and hardware orders.

**[Agent guide](AGENT_GUIDE.md) · [Get started](docs/en/getting-started.md) · [User guide](docs/en/README.md) · [PyPI](https://pypi.org/project/os-optics/) · [Website](https://opensci-optics.com/) · [Feedback](https://github.com/JunLin615/os-optics/issues)**

**OS Optics 0.10.0:** these examples and workflow helpers run on the published
os-optics **0.10.0** release. [engine-baseline.json](engine-baseline.json) records
the verified version, its wheel and source hashes, and the tested environment.

## What you can do

| Design | Simulate | Explore | Build |
| --- | --- | --- | --- |
| Find optics and define positions, sources, and targets | Trace rays, propagate Gaussian beams, and evaluate polarization and interference | Inspect a 3D scene, compare target values, and export scientific data | Select components and request a hardware configuration and order |

- **Local computation:** run on Windows, macOS, or Linux with Python 3.11+.
- **Reproducible projects:** preserve engine identity, catalog versions, numerical settings, and result hashes.
- **Scientific outputs:** examine observation planes, beam states, ray paths, power budgets, and wavefront data.
- **Python and CLI:** integrate into notebooks, scripts, parameter studies, and agent workflows.
- **Connected hardware workflow:** continue from local design to purchasing and assembly through OpenSci.

## Install

```bash
python -m pip install "os-optics[protected]"
os-optics doctor
```

Prefer an isolated command-line tool? Use `uv tool install "os-optics[protected]"`.
See the [installation guide](docs/en/installation.md) for virtual environments and upgrades.
Up to 0.9.0 the package was published as `opensci-engine`; an installation under that name
takes the same `python -m pip install --upgrade "os-optics[protected]"`, then uses the
`os-optics` command and `import os_optics`.

## Run your first design

```bash
os-optics catalog sync
os-optics project example --kind beam_expander > project.json
os-optics project run project.json --out-dir run
os-optics view run
```

The first command downloads the current optical catalog. The example creates a two-lens beam expander; the run produces simulation results, a Local Validation record, and a 3D scene. The viewer opens locally in your browser.

For Windows PowerShell 5.1, create the JSON file with `os-optics project example --kind beam_expander | Out-File -Encoding utf8 project.json`.

Inspect and export the same run:

```bash
os-optics results describe run
os-optics export arrivals run --format csv --out arrivals.csv
os-optics project verify run
```

## Use Python

```python
from os_optics.local import example_project_of_kind, run_optical_project
from os_optics.results import load_run

project = example_project_of_kind("beam_expander")
run = run_optical_project(project, output_dir="run-python")
print(run.status.value)

results = load_run("run-python")
print(results.power_budget())
```

Try the runnable [beam expander](examples/beam_expander.py) and [ideal-lens focus](examples/ideal_lens_focus.py) examples.

## Documentation

| Guide | English | 简体中文 |
| --- | --- | --- |
| Installation and upgrades | [Read](docs/en/installation.md) | [阅读](docs/zh-CN/installation.md) |
| Your first optical design | [Read](docs/en/getting-started.md) | [阅读](docs/zh-CN/getting-started.md) |
| Catalog and reproducible projects | [Read](docs/en/catalog.md) | [阅读](docs/zh-CN/catalog.md) |
| Results, visualization, and export | [Read](docs/en/results.md) | [阅读](docs/zh-CN/results.md) |
| Design studies: edits, sweeps, comparisons, sensitivity, tolerance, and three optical workflows | [Read](docs/en/workflows.md) | [阅读](docs/zh-CN/workflows.md) |
| Measurement cleaning, fitting, and reference normalization | [Read](docs/en/measurements.md) | [阅读](docs/zh-CN/measurements.md) |
| From design to hardware | [Read](docs/en/hardware.md) | [阅读](docs/zh-CN/hardware.md) |
| External scientific tools | [Read](docs/en/interop.md) | [阅读](docs/zh-CN/interop.md) |

The examples and guides use the published **0.10.0** package. External-tool examples cover optimization, diffraction, quantum photonics and metasurface components. Find available package versions in the [PyPI release history](https://pypi.org/project/os-optics/#history).

The verified version and test environment are recorded in [engine-baseline.json](engine-baseline.json). [Release-alignment checks](docs/engine-alignment.md) validate this baseline and candidate PyPI releases; only a reviewed update advances the baseline.

## Get involved

Questions, example designs, bug reports, and documentation improvements are welcome in English or Chinese. [Open an issue](https://github.com/JunLin615/os-optics/issues/new/choose) or send a documentation or example pull request.

This repository brings together the user documentation, examples, and community feedback for OS Optics. Install the engine from [PyPI](https://pypi.org/project/os-optics/) and explore the full platform at [opensci-optics.com](https://opensci-optics.com/).
