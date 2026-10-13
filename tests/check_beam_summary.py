"""Catalog integration check and same-run output comparison.

Run from the repository root: python -m tests.check_beam_summary
Requires the published package and an available (or cached) optical catalog.
"""

import hashlib
from importlib.metadata import version
import json
from pathlib import Path
from unittest.mock import patch

from opensci_engine.results import load_run

from examples.beam_expander import run_example
from examples.result_summary import summarize_run


def snapshot(directory):
    return {path.name: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
            for path in directory.iterdir() if path.is_file()}


def main():
    directory = Path("run-summary-check")
    summary = run_example(directory)
    results = load_run(directory)
    # Reproduce the original example's JSON layout using this exact saved result.
    legacy = {
        "status": summary["status"],
        "targets": [{"id": t.target_id, "status": t.status.value, "value": t.value}
                    for t in results.result.targets],
        "power_budget": results.power_budget(),
        "run_directory": str(directory),
        "arrivals_csv": summary["exports"]["arrivals_csv"],
        "view_command": summary["view_command"],
    }
    before = snapshot(directory)
    forbidden = AssertionError("Saved-result inspection must not simulate")
    with patch("opensci_engine.validate", side_effect=forbidden), \
         patch("opensci_engine.validate_with_ray_paths", side_effect=forbidden), \
         patch("opensci_engine.local.run_optical_project", side_effect=forbidden):
        compact = summarize_run(directory)
        detailed = summarize_run(directory, details=True)
    assert before == snapshot(directory), "Inspection modified saved artifacts"
    assert compact["targets"] == summary["targets"]
    assert detailed["power_budget_details"] == results.power_budget()
    assert compact["integrity"]["consistent"] is True
    assert all(Path(p).exists() for p in summary["artifacts"].values())
    assert all(Path(p).exists() for p in summary["exports"].values())
    old_bytes = len((json.dumps(legacy, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    new_bytes = len((json.dumps(summary, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8"))
    # Also compare identical formatting to isolate content reduction from minification.
    old_compact_bytes = len((json.dumps(legacy, separators=(",", ":")) + "\n").encode("utf-8"))
    assert new_bytes < old_compact_bytes, "Default summary did not reduce content"
    report = {
        "engine_version": version("opensci-engine"),
        "catalog_version": summary["identity"]["catalog_version"],
        "result_hash": summary["identity"]["result_hash"],
        "status": summary["status"],
        "legacy_stdout_utf8_bytes_lf": old_bytes,
        "legacy_minified_utf8_bytes_lf": old_compact_bytes,
        "summary_stdout_utf8_bytes_lf": new_bytes,
        "saved_inspection_unchanged": True,
        "details_match_full_power_budget": True,
    }
    (directory / "summary-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
