# User guide

[Home](../../README.md) · English · [简体中文](../zh-CN/README.md)

Start with a working optical design, then explore its results and adapt it to your experiment.

1. [Install OpenSci Engine](installation.md) — Python, virtual environments, uv, and upgrades.
2. [Run your first design](getting-started.md) — generate a project, simulate it, and open the 3D view.
3. [Work with the catalog](catalog.md) — find optics, manage releases, and reproduce a project.
4. [Read and export results](results.md) — validation, beam data, visualization, and CSV exports.
5. [Continue to hardware](hardware.md) — component selection, assembly preview, and ordering.

## Examples

| Example | Run from the repository root | Uses the optical catalog |
| --- | --- | --- |
| [Beam expander](../../examples/beam_expander.py) | `python examples/beam_expander.py --out run-example` | Yes; downloads on first use |
| [Ideal-lens focus](../../examples/ideal_lens_focus.py) | `python examples/ideal_lens_focus.py` | No; uses mathematical elements |

Install the package into your Python environment before running these scripts. `uv tool install` provides an isolated CLI; use the [pip installation](installation.md) for Python imports.

Guides are checked against **opensci-engine 0.6.1**. Commands expose their options through `--help`; Python APIs are documented in the installed package and the [PyPI reference](https://pypi.org/project/opensci-engine/).

[OpenSci website](https://opensci-optic.com/) · [Package releases](https://pypi.org/project/opensci-engine/#history) · [Ask a question](https://github.com/JunLin615/opensci-engine/issues/new/choose)
