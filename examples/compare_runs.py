"""Compare saved runs, or the samples of a sweep study, without rerunning anything.

Usage:
  python examples/compare_runs.py RUN_DIR RUN_DIR ... [--project CURRENT.json] [--labels a,b,...]
                                  [--reference LABEL] [--out DIR]
  python examples/compare_runs.py STUDY_DIR [--project CURRENT.json] [--out DIR]

Each argument is a run directory (it holds manifest.json) or a study directory written by sweep_parameters.py (its
samples become the compared runs, labelled by sample id; a sample that was refused or not run stays in the
comparison as an ERROR entry with missing data). A run directory named "run" is labelled by its parent directory.

What is compared, by ID:
* targets: value, unit and status per run, the difference to the reference run (first run, or --reference) when
  both have a value in the same unit; a target absent from a run is listed with "missing": true;
* observation planes: received power (W) and number of arriving beams per run, missing planes listed;
* inputs read from each run's project.json: source wavelength(s), power, waist and polarization; component and
  observation poses; catalog products / declared models; target definitions and bounds; plus each run's catalog
  release and Engine build. Only inputs that differ between runs are listed;
* outcome class per run (ERROR, OUT_OF_MODEL, UNKNOWN, FAIL, PASS) and its model-scope issues;
* freshness, when --project is given: CURRENT or HISTORICAL (reasons PROJECT_CHANGED, ENGINE_CHANGED,
  RUN_UNVERIFIED) for every run; the outcome of a historical run is labelled e.g. "HISTORICAL PASS".

Writes DIR/compare.json (everything) and DIR/compare.csv (long format: section, id, field, unit, run, value,
status, delta, reference) when --out is given. Stdout: one compact JSON document (at most eight runs and ten input
differences in full; the files hold everything). Exit 0 compared, 4 invalid input.
"""

from __future__ import annotations

import argparse
from pathlib import Path

if __package__:
    from . import workflow_common as wc
else:
    import workflow_common as wc

MAX_RUNS_SHOWN = 8
MAX_DIFFERENCES_SHOWN = 10


def expand_inputs(paths, labels=None):
    """``[(label, run_dir or None, sample record or None)]`` for run directories and study directories."""
    entries = []
    for path in [Path(p) for p in paths]:
        if (path / "manifest.json").is_file() or (path / "local_validation.json").is_file():
            name = path.resolve().parent.name if path.name == "run" else path.name  # samples/<id>/run -> <id>
            entries.append((name, path, None))
        elif (path / "summary.json").is_file() and (path / "samples").is_dir():
            for sample_dir in sorted(p for p in (path / "samples").iterdir() if p.is_dir()):
                record = wc.read_json(sample_dir / "sample.json") if (sample_dir / "sample.json").is_file() else None
                run_dir = sample_dir / "run"
                entries.append((sample_dir.name, run_dir if (run_dir / "manifest.json").is_file() else None, record))
        else:
            raise wc.WorkflowError("RUN_NOT_READABLE", f"{path} is neither a run directory nor a study directory",
                                   path=path.as_posix())
    if labels:
        if len(labels) != len(entries):
            raise wc.WorkflowError("BAD_ARGUMENT", f"{len(labels)} labels for {len(entries)} runs")
        entries = [(label, run_dir, record) for label, (_old, run_dir, record) in zip(labels, entries)]
    seen = set()
    for label, _run_dir, _record in entries:
        if label in seen:
            raise wc.WorkflowError("BAD_ARGUMENT", f"duplicate run label {label!r}; use --labels")
        seen.add(label)
    return entries


def project_inputs(project):
    """Flat ``{key: value}`` of the inputs worth comparing (module docstring)."""
    out = {}
    for c in project.get("components") or []:
        ident = c.get("instance_id")
        pose = c.get("nominal_pose") or {}
        out[f"pose:{ident}.position_mm"] = pose.get("position_mm")
        out[f"pose:{ident}.quaternion_wxyz"] = pose.get("quaternion_wxyz")
        if c.get("product"):
            out[f"binding:{ident}.optical_sku"] = c["product"].get("optical_sku")
        if c.get("optical_model_id"):
            out[f"binding:{ident}.optical_model_id"] = c["optical_model_id"]
        source = c.get("source_model")
        if source:
            for key in ("wavelength_nm", "spectral_lines", "power_w", "waist_radius_mm", "waist_position_mm", "m2",
                        "polarization", "linewidth_nm", "coherence_length_mm"):
                if key in source:
                    out[f"source:{ident}.{key}"] = source[key]
    for o in project.get("observations") or []:
        pose = o.get("pose") or {}
        out[f"observation:{o.get('observation_id')}.position_mm"] = pose.get("position_mm")
        out[f"observation:{o.get('observation_id')}.quaternion_wxyz"] = pose.get("quaternion_wxyz")
    for t in project.get("targets") or []:
        for key in ("metric", "observation_id", "unit", "minimum", "maximum", "target_value", "tolerance_abs",
                    "tolerance_rel"):
            if t.get(key) is not None:
                out[f"target:{t.get('target_id')}.{key}"] = t[key]
    models = {m.get("model_id"): m for m in project.get("optical_models") or []}
    for model_id, model in models.items():
        out[f"model:{model_id}"] = wc.canonical_digest(model)[:16]
    return out


def _key_unit(key):
    return wc.field_unit(key.split(".")[-1])


def load_entry(label, run_dir, record, selected=None):
    entry = {"label": label, "run_dir": None if run_dir is None else Path(run_dir).as_posix()}
    if run_dir is None:
        entry.update({"outcome": "ERROR", "status": None, "targets": [], "observations": {}, "inputs": {},
                      "model_scope_issues": [], "identity": (record or {}).get("identity") or {},
                      "error": (record or {}).get("error") or {"code": "RUN_MISSING"}, "power_budget": None})
        return entry
    from opensci_engine.results import load_run

    summary, fields = wc.read_saved_run(run_dir, selected)
    results = load_run(run_dir, verify=False)
    entry.update({"outcome": fields["outcome"], "status": fields["status"], "targets": fields["targets"],
                  "model_scope_issues": fields["model_scope_issues"], "warnings": fields["warnings"],
                  "identity": fields["identity"], "power_budget": summary.get("power_budget"),
                  "observations": {m["observation_id"]: {"total_power_W": m["total_power_W"],
                                                         "arrival_count": m["arrival_count"], "status": m["status"]}
                                   for m in results.monitors()},
                  "inputs": project_inputs(wc.read_json(Path(run_dir) / "project.json"))})
    entry["inputs"]["run.catalog_version"] = entry["identity"].get("catalog_version")
    entry["inputs"]["run.engine_build_id"] = entry["identity"].get("engine_build_id")
    return entry


def _ordered_union(lists):
    out = []
    for items in lists:
        for item in items:
            if item not in out:
                out.append(item)
    return out


def compare(paths, *, labels=None, reference=None, project=None, targets=None):
    """Comparison document (module docstring). ``project``: current Project document or path for freshness."""
    entries = [load_entry(label, run_dir, record, targets) for label, run_dir, record in expand_inputs(paths, labels)]
    if not entries:
        raise wc.WorkflowError("BAD_ARGUMENT", "nothing to compare")
    names = [e["label"] for e in entries]
    ref = reference or names[0]
    if ref not in names:
        raise wc.WorkflowError("BAD_ARGUMENT", f"reference {ref!r} is not one of the runs {names}")
    ref_entry = entries[names.index(ref)]
    if project is not None:
        for entry in entries:
            if entry["run_dir"] is None:
                entry["freshness"] = {"freshness": "HISTORICAL", "reasons": ["RUN_UNVERIFIED"]}
            else:
                entry["freshness"] = wc.freshness(project, entry["run_dir"])
            entry["outcome_label"] = entry["outcome"] if entry["freshness"]["freshness"] == "CURRENT" else \
                f"HISTORICAL {entry['outcome']}"
    target_rows = []
    for target_id in _ordered_union([[t["id"] for t in e["targets"]] for e in entries]):
        row = {"id": target_id, "runs": {}}
        ref_target = next((t for t in ref_entry["targets"] if t["id"] == target_id), None)
        for entry in entries:
            target = next((t for t in entry["targets"] if t["id"] == target_id), None)
            if target is None:
                row["runs"][entry["label"]] = {"missing": True}
                continue
            row.setdefault("metric", target["metric"])
            row.setdefault("unit", target["unit"])
            cell = {"value": target["value"], "unit": target["unit"], "status": target["status"]}
            if ref_target is not None and isinstance(target["value"], (int, float)) and \
                    isinstance(ref_target["value"], (int, float)) and target["unit"] == ref_target["unit"]:
                cell["delta"] = target["value"] - ref_target["value"]
            row["runs"][entry["label"]] = cell
        target_rows.append(row)
    observation_rows = []
    for obs_id in _ordered_union([list(e["observations"]) for e in entries]):
        observation_rows.append({"id": obs_id, "unit": "W", "runs": {
            e["label"]: e["observations"].get(obs_id) or {"missing": True} for e in entries}})
    differences = []
    for key in _ordered_union([list(e["inputs"]) for e in entries]):
        values = {e["label"]: e["inputs"].get(key, "<missing>" if e["run_dir"] else None) for e in entries}
        present = [wc.canonical_json(v) for label, v in values.items()
                   if next(x for x in entries if x["label"] == label)["run_dir"] is not None]
        if len(set(present)) > 1:
            differences.append({"input": key, "unit": _key_unit(key), "values": values})
    runs = []
    for entry in entries:
        item = {"label": entry["label"], "outcome": entry["outcome"], "status": entry["status"],
                "model_scope_issues": sorted({i.get("code") for i in entry["model_scope_issues"]}),
                "run_dir": entry["run_dir"], "identity": entry["identity"]}
        for key in ("freshness", "outcome_label", "error", "power_budget"):
            if entry.get(key) is not None:
                item[key] = entry[key]
        runs.append(item)
    return {"status": "COMPLETED", "kind": "opensci-example.run-comparison", "reference": ref, "runs": runs,
            "targets": target_rows, "observations": observation_rows, "input_differences": differences}


def csv_rows(document):
    rows = []
    for row in document["targets"]:
        for label, cell in row["runs"].items():
            rows.append({"section": "target", "id": row["id"], "field": row.get("metric"), "unit": row.get("unit"),
                         "run": label, "value": cell.get("value"), "status": cell.get("status") or (
                             "MISSING" if cell.get("missing") else None),
                         "delta": cell.get("delta"), "reference": document["reference"]})
    for row in document["observations"]:
        for label, cell in row["runs"].items():
            rows.append({"section": "observation", "id": row["id"], "field": "total_power_W", "unit": "W",
                         "run": label, "value": cell.get("total_power_W"),
                         "status": "MISSING" if cell.get("missing") else cell.get("status")})
    for diff in document["input_differences"]:
        for label, value in diff["values"].items():
            rows.append({"section": "input", "id": diff["input"], "field": diff["input"].split(".")[-1],
                         "unit": diff["unit"], "run": label, "value": value})
    for run in document["runs"]:
        rows.append({"section": "outcome", "id": run["label"], "field": "outcome", "run": run["label"],
                     "value": run.get("outcome_label", run["outcome"]), "status": run["status"]})
    return rows


CSV_COLUMNS = ["section", "id", "field", "unit", "run", "value", "status", "delta", "reference"]


def write_outputs(document, out_dir):
    out_dir = Path(out_dir)
    json_path = wc.write_json(out_dir / "compare.json", document)
    csv_path = wc.write_csv(out_dir / "compare.csv", csv_rows(document), CSV_COLUMNS)
    return {"json": json_path.as_posix(), "csv": csv_path.as_posix()}


def compact(document, paths=None):
    runs = document["runs"]
    shown = runs[:MAX_RUNS_SHOWN]
    labels = [r["label"] for r in shown]
    return {
        "status": document["status"], "reference": document["reference"], "run_count": len(runs),
        "runs": [{key: r.get(key) for key in ("label", "outcome", "outcome_label", "status", "model_scope_issues")
                  if r.get(key) is not None} | ({"freshness": r["freshness"]["freshness"],
                                                "reasons": r["freshness"]["reasons"]} if r.get("freshness") else {})
                 for r in shown],
        "runs_omitted": max(0, len(runs) - MAX_RUNS_SHOWN),
        "targets": [{"id": t["id"], "unit": t.get("unit"),
                     "runs": {label: t["runs"][label] for label in labels}} for t in document["targets"]],
        "observations_W": [{"id": o["id"], "runs": {label: o["runs"][label].get("total_power_W", "missing")
                                                    if not o["runs"][label].get("missing") else "missing"
                                                    for label in labels}} for o in document["observations"]],
        "input_differences": document["input_differences"][:MAX_DIFFERENCES_SHOWN],
        "input_differences_omitted": max(0, len(document["input_differences"]) - MAX_DIFFERENCES_SHOWN),
        "paths": paths,
    }


def main(argv=None):
    def workflow():
        parser = wc.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        parser.add_argument("paths", nargs="+", type=Path, help="Run directories or one/more study directories")
        parser.add_argument("--project", type=Path, help="Current Project JSON: report each run's freshness")
        parser.add_argument("--labels", help="Comma-separated run labels (default: directory / sample names)")
        parser.add_argument("--reference", help="Label of the reference run for deltas (default: the first)")
        parser.add_argument("--targets", help="Comma-separated target ids deciding the outcome (default: all)")
        parser.add_argument("--out", type=Path, help="Directory for compare.json and compare.csv")
        args = parser.parse_args(argv)
        document = compare(args.paths, labels=args.labels.split(",") if args.labels else None,
                           reference=args.reference, project=args.project,
                           targets=args.targets.split(",") if args.targets else None)
        paths = write_outputs(document, args.out) if args.out else None
        return compact(document, paths)

    return wc.emit(workflow)


if __name__ == "__main__":
    raise SystemExit(main())
