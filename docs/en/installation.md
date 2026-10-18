# Installation

[User guide](README.md) · English · [简体中文](../zh-CN/installation.md)

OpenSci Engine runs on Windows, macOS, and Linux with **Python 3.11 or newer**. Choose pip for Python scripts and notebooks, or uv for a standalone command-line tool.

## Python environment

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install and check the engine:

```bash
python -m pip install "opensci-engine[protected]"
opensci-engine doctor
```

You can also run the CLI as `python -m opensci_engine`. If PowerShell activation is unavailable, use `.venv\Scripts\python.exe -m pip install "opensci-engine[protected]"` and `.venv\Scripts\python.exe -m opensci_engine doctor` directly.

The `protected` extra adds support for opening assembly previews and assembly details in the hardware workflow. For optical design and simulation alone, `python -m pip install opensci-engine` is sufficient.

## Standalone CLI with uv

With [uv](https://docs.astral.sh/uv/) installed:

```bash
uv tool install "opensci-engine[protected]"
opensci-engine doctor
```

If the command is not on your PATH, run `uv tool update-shell` and open a new terminal. To run a command without a persistent tool installation:

```bash
uvx --from "opensci-engine[protected]" opensci-engine doctor
```

## Prepare the catalog

```bash
opensci-engine catalog sync
opensci-engine catalog status
```

The catalog downloads into a local store. Later simulations use stored releases, including when working offline. `doctor` checks local installation readiness; `catalog sync` retrieves the current catalog from OpenSci.

## Upgrade

For a pip installation:

```bash
python -m pip install --upgrade "opensci-engine[protected]"
```

For a uv tool installation:

```bash
uv tool upgrade opensci-engine
```

Run `opensci-engine doctor` to see the installed version. To reproduce the version used by this guide, install `"opensci-engine[protected]==0.8.0"`.

[engine-baseline.json](../../engine-baseline.json) records the verified release and test environment. Maintainers can check another released version with the [alignment workflow](../engine-alignment.md); a successful candidate check does not automatically change this baseline.

## Common setup questions

| Symptom | Next step |
| --- | --- |
| Python version error during installation | Check `python --version`; use Python 3.11+ or the uv route |
| `opensci-engine` command not found | Activate the environment or use `python -m opensci_engine` |
| `DOWNLOAD_ON_FIRST_USE` in doctor | Run `opensci-engine catalog sync` or start a catalog-based design |
| Catalog download fails | Check connectivity with `opensci-engine catalog check`; offline catalog import is described in the [catalog guide](catalog.md) |
| Service requests a newer engine | Upgrade, update the project's catalog, and rerun the design before submitting it |

Next: [Run your first optical design](getting-started.md).
