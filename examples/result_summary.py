"""Summarize a saved local run without rerunning the simulation.

Usage: python examples/result_summary.py run-example [--details]
"""

import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys

from opensci_engine.results import ResultsError, load_run


EXIT_CODES = {
    "PASS": 0, "WARNING": 0, "NOT_APPLICABLE": 0,
    "FAIL": 1, "UNKNOWN": 2, "OUT_OF_MODEL_SCOPE": 3,
}
ERROR_EXIT = 4


class ArgumentParser(argparse.ArgumentParser):
    """Keep usage errors distinct from an UNKNOWN scientific result."""

    def error(self, message):
        raise ValueError(message)


def summarize_results(results, *, artifacts=None, details=False):
    """Return JSON-safe results using the public RunResults API; never simulate.

    All targets and diagnostics are retained. Only the power overview is reduced;
    complete power entries and rays remain in the supplied artifact files.
    """
    description = results.describe()
    integrity = description["integrity"]
    if integrity["checked"] and not integrity["consistent"]:
        raise ResultsError("RUN_INTEGRITY_FAILED", "; ".join(integrity["problems"]))
    statuses = description["status"]
    status = statuses.get("validation_status")
    if status is None:
        status = statuses["engine_status"]
    if status not in EXIT_CODES:
        raise ValueError(f"Unsupported result status: {status}")
    targets = []
    for target in results.result.targets:
        row = {
            "id": target.target_id, "metric": target.metric,
            "value": target.value, "unit": target.unit, "status": target.status.value,
            "bounds": {
                key: getattr(target, key)
                for key in ("minimum", "maximum", "target_value", "tolerance")
                if getattr(target, key) is not None
            },
        }
        for key in ("observation_id", "device_id", "message", "issue_codes"):
            value = getattr(target, key)
            if value:
                row[key] = list(value) if key == "issue_codes" else value
        targets.append(row)
    power = results.power_budget()
    summary = {
        "status": status,
        "engine_status": statuses["engine_status"],
        "validation_status": statuses.get("validation_status"),
        "targets": targets,
        "power_budget": {key: power[key] for key in (
            "available", "total_input_W", "total_sinks", "residual_W", "tolerance_W", "conserved"
        ) if key in power},
        "issues": [issue.model_dump(mode="json") for issue in results.result.issues],
        "model_scope_issues": statuses.get("model_scope_issues", []),
        "element_models": description["element_models"],
        "identity": results.identity(),
        "integrity": integrity,
        "artifacts": {key: str(path) for key, path in (artifacts or {}).items()},
    }
    if details:
        summary["power_budget_details"] = power
    return summary


def summarize_run(directory, *, details=False):
    """Read and verify a native local run; do not modify its files."""
    directory = Path(directory)
    results = load_run(directory)
    artifacts = {"run_directory": directory, "manifest": directory / "manifest.json"}
    artifacts.update({item["role"]: directory / item["name"]
                      for item in results.describe()["files"]})
    summary = summarize_results(results, artifacts=artifacts, details=details)
    summary["view_command"] = f'opensci-engine view "{directory}"'
    return summary


def emit_cli(workflow):
    """Keep one JSON summary on stdout and all diagnostics on stderr."""
    try:
        with redirect_stdout(sys.stderr):
            summary = workflow()
        code = EXIT_CODES[summary["status"]]
        output = json.dumps(summary, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    except Exception as exc:
        error = {"error": {"code": getattr(exc, "code", type(exc).__name__), "message": str(exc)}}
        print(json.dumps(error, ensure_ascii=True), file=sys.stderr)
        return ERROR_EXIT
    print(output)
    return code


def main(argv=None):
    def workflow():
        parser = ArgumentParser(description=__doc__)
        parser.add_argument("directory", type=Path, help="Saved local run directory")
        parser.add_argument("--details", action="store_true", help="Include the complete power ledger")
        args = parser.parse_args(argv)
        return summarize_run(args.directory, details=args.details)

    return emit_cli(workflow)


if __name__ == "__main__":
    raise SystemExit(main())
