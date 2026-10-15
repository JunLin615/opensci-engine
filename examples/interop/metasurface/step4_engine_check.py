"""Step 4: use the fitted metalens model in OpenSci and check it (requires opensci-engine 0.8.0).

The step-3 ``TABULATED_THIN_LENS`` model is declared in a catalog-free Project and
traced with the same 30 um Gaussian input as the external calculation (waist at the
metasurface, x polarization). For every table and hold-out wavelength the Engine's
waist position, waist radius and delivered power are compared with

* the step-3 thin-lens prediction (the Engine must reproduce the model it was given),
* the external focus (the deviation must stay inside the model's stated errors).

One Project with a multi-line source shows the chromatic focus of the whole table in
one run. Outside the model's domain the Engine must not return a result as valid:

* a 450 nm source (outside the 490-580 nm rows): ``OUT_OF_MODEL_SCOPE``;
* a 20 deg field angle (beyond ``max_field_angle_deg``): ``OUT_OF_MODEL_SCOPE``;
* a target asking for a metric the model was not validated for: ``OUT_OF_MODEL_SCOPE``.

``--model per-wavelength-ideal`` runs the same comparison with one IDEAL_THIN_LENS per
wavelength (focal length and transmittance interpolated from the same rows), the
single-line equivalent of the tabulated model; that model kind cannot state a field-
angle domain, so its 20 deg result is reported, not judged.

Usage: python examples/interop/metasurface/step4_engine_check.py run-interop-metasurface [--model tabulated]
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import sys

if __package__:
    from ..common import ArgumentParser, decimal_text, emit, environment, pose, require_engine, run_identity, write_json
    from .step1_unit_cells import HOLDOUT_NM, TABLE_NM
    from .step3_fit_model import aperture_fraction, interpolate, thin_lens_focus
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import ArgumentParser, decimal_text, emit, environment, pose, require_engine, run_identity, write_json
    from step1_unit_cells import HOLDOUT_NM, TABLE_NM
    from step3_fit_model import aperture_fraction, interpolate, thin_lens_focus

LENS_X_MM, HEIGHT_MM, PLANE_X_MM = 0.0, 50.0, 0.3
SOURCE_DISTANCE_MM = 1.0
MODEL_AGREEMENT_REL = 1e-6  # Engine vs the thin-lens prediction of the same model


def model_rows(model):
    return [{"wavelength_nm": float(r["wavelength_nm"]), "focal_length_um": float(r["focal_length_mm"]) * 1000,
             "transmittance": float(r["transmittance"])} for r in model["model"]["rows"]]


def project(model, mode, *, wavelengths_nm, waist_um, tilt_deg=0.0, target_metric="waist_radius_x_mm",
            band_override=None):
    """Catalog-free Project: Gaussian source -> metalens at the origin plane -> observation plane 0.3 mm behind."""
    rows = model_rows(model)
    if mode == "tabulated":
        models = [copy.deepcopy(model)]
    else:
        wavelength = wavelengths_nm[0]
        f_um, transmittance = interpolate(rows, min(max(wavelength, rows[0]["wavelength_nm"]), rows[-1]["wavelength_nm"]))
        band = band_override or (wavelength, wavelength)
        ideal = model["model"]
        models = [{"model_id": model["model_id"], "model": {
            "model_kind": "IDEAL_THIN_LENS", "model_version": "1", "focal_length_mm": decimal_text(f_um / 1000, 9),
            "transmittance": decimal_text(transmittance, 6), "clear_radius_mm": ideal["clear_radius_mm"],
            "edge_radius_mm": ideal["edge_radius_mm"], "status": "SPECIFIED",
            "valid_band_nm": {"min_nm": decimal_text(band[0]), "max_nm": decimal_text(band[1]), "status": "SPECIFIED"}}}]
    theta = math.radians(tilt_deg)
    direction = (math.cos(theta), 0.0, math.sin(theta))
    start = [LENS_X_MM - SOURCE_DISTANCE_MM * direction[0], 0.0, HEIGHT_MM - SOURCE_DISTANCE_MM * direction[2]]
    source = {"model_kind": "GAUSSIAN_BEAM", "waist_radius_mm": waist_um / 1000, "waist_position_mm": SOURCE_DISTANCE_MM,
              "m2": 1.0, "polarization": {"kind": "LINEAR", "angle_deg": 0.0}}
    if len(wavelengths_nm) == 1:
        source.update(wavelength_nm=float(wavelengths_nm[0]), power_w=0.001)
    else:
        source["spectral_lines"] = [{"wavelength_nm": float(w), "power_w": 0.001} for w in wavelengths_nm]
    return {
        "schema": "opensci.project", "project_schema_version": "2.0", "design_intent": "OPTICAL_SYSTEM",
        "optical_models": models,
        "components": [
            {"instance_id": "SRC", "optical_role": "source", "nominal_pose": pose(start, direction),
             "custom_part": {"custom_part_key": "user-laser", "description": "tunable laser"}, "source_model": source},
            {"instance_id": "META", "optical_role": "lens", "optical_model_id": model["model_id"],
             "custom_part": {"custom_part_key": "own-metalens", "description": "customer metalens"},
             "nominal_pose": pose((LENS_X_MM, 0.0, HEIGHT_MM), (1, 0, 0))},
        ],
        "observations": [{"observation_id": "after", "aperture": {"shape": "circle", "radius_mm": 1},
                          "pose": pose((PLANE_X_MM, 0.0, HEIGHT_MM), (1, 0, 0))}],
        "targets": [{"target_id": "spot", "metric": target_metric, "observation_id": "after", "maximum": 0.01,
                     "unit": "mm" if target_metric.endswith("_mm") else "W/mm^2"}],
    }


def run(document):
    from opensci_engine.local import load_project, run_optical_project
    from opensci_engine.results import load_run

    results = load_run(run_optical_project(load_project(document)))
    statuses = results.describe()["status"]
    outcome = {"status": statuses.get("validation_status") or statuses["engine_status"],
               "engine_status": statuses["engine_status"],
               "issues": sorted({issue.code for issue in results.result.issues}),
               "model_scope_issues": [i.get("code") if isinstance(i, dict) else str(i)
                                      for i in statuses.get("model_scope_issues", [])],
               "target_issue_codes": sorted({str(getattr(code, "value", code)) for target in results.result.targets
                                             for code in (target.issue_codes or ())}),
               "identity": run_identity(results), "beams": []}
    for arrival in results.monitor("after")["arrivals"]:
        beam = arrival["beam"]
        gaussian = beam["gaussian"]
        entry = {"wavelength_nm": beam["wavelength_nm"], "power_W": beam["power_W"], "gaussian_valid": gaussian["valid"]}
        if gaussian["valid"]:
            waist = [p - gaussian["waist_distance_x_mm"] * d for p, d in zip(beam["position_mm"], beam["direction"])]
            entry.update({"waist_axial_um": (waist[0] - LENS_X_MM) * 1000, "waist_lateral_um": (waist[2] - HEIGHT_MM) * 1000,
                          "waist_radius_um": gaussian["waist_radius_x_mm"] * 1000})
        outcome["beams"].append(entry)
    return outcome


def compare(beam, external, model, waist_um, clear_um, f_um, transmittance):
    z_model, w_model = thin_lens_focus(f_um, waist_um, beam["wavelength_nm"])
    power_model = 0.001 * transmittance * aperture_fraction(waist_um, clear_um)
    return {
        "engine": {k: beam.get(k) for k in ("waist_axial_um", "waist_radius_um", "power_W")},
        "external": {"z_focus_um": external["z_focus_um"], "w_focus_um": external["w_focus_um"],
                     "power_W": 0.001 * external["focusing_efficiency"]},
        "engine_vs_model_rel": max(abs(beam["waist_axial_um"] / z_model - 1), abs(beam["waist_radius_um"] / w_model - 1),
                                   abs(beam["power_W"] / power_model - 1)),
        "engine_vs_external": {"z_abs_err_um": beam["waist_axial_um"] - external["z_focus_um"],
                               "z_rel_err": beam["waist_axial_um"] / external["z_focus_um"] - 1,
                               "w_rel_err": beam["waist_radius_um"] / external["w_focus_um"] - 1,
                               "power_rel_err": beam["power_W"] / (0.001 * external["focusing_efficiency"]) - 1},
    }


def bounds_of(model):
    metrics = {m["metric"]: m for m in model["model"]["supported_metrics"]}
    return {"z_abs_um": float(metrics["waist_distance_x_mm"]["abs_error"]) * 1000,
            "w_rel": float(metrics["waist_radius_x_mm"]["rel_error"]), "power_rel": float(metrics["power_W"]["rel_error"])}


def within(errors, bounds):
    return (abs(errors["z_abs_err_um"]) <= bounds["z_abs_um"] and abs(errors["w_rel_err"]) <= bounds["w_rel"]
            and abs(errors["power_rel_err"]) <= bounds["power_rel"])


def run_example(directory, mode):
    installed = require_engine()
    directory = Path(directory)
    model = json.loads((directory / "metalens_model.json").read_text(encoding="utf-8"))
    step3 = json.loads((directory / "step3_report.json").read_text(encoding="utf-8"))
    table = json.loads(Path(step3["focus_table"]).read_text(encoding="utf-8"))
    design = table["design"]
    waist_um, clear_um = design["input_waist_radius_um"], design["diameter_um"] / 2
    rows = model_rows(model)
    bounds = bounds_of(model)
    external = {(r["wavelength_nm"], r["tilt_deg"], r["input_waist_radius_um"]): r for r in table["rows"]}

    cases = {}
    for lam in TABLE_NM + HOLDOUT_NM:
        outcome = run(project(model, mode, wavelengths_nm=[lam], waist_um=waist_um))
        f_um, transmittance = interpolate(rows, lam)
        entry = {"role": "table row" if lam in TABLE_NM else "hold-out", "status": outcome["status"],
                 "issues": outcome["issues"], "identity": outcome["identity"]}
        entry.update(compare(outcome["beams"][0], external[(lam, 0.0, waist_um)], model, waist_um, clear_um, f_um,
                             transmittance))
        entry["within_stated_errors"] = within(entry["engine_vs_external"], bounds)
        cases[f"{lam}nm"] = entry
    for (lam, tilt, waist), row in external.items():
        if tilt == 0.0 and waist != waist_um:
            outcome = run(project(model, mode, wavelengths_nm=[lam], waist_um=waist))
            f_um, transmittance = interpolate(rows, lam)
            entry = {"role": "beam-size check", "status": outcome["status"], "issues": outcome["issues"]}
            entry.update(compare(outcome["beams"][0], row, model, waist, clear_um, f_um, transmittance))
            entry["within_stated_errors"] = within(entry["engine_vs_external"], bounds)
            cases[f"{lam}nm_input_{waist:g}um"] = entry

    max_angle = float(model["model"]["max_field_angle_deg"])
    field = {}
    for (lam, tilt, waist), row in sorted(external.items()):
        if tilt == 0.0:
            continue
        outcome = run(project(model, mode, wavelengths_nm=[lam], waist_um=waist, tilt_deg=tilt))
        beam = outcome["beams"][0] if outcome["beams"] else {}
        entry = {"tilt_deg": tilt, "inside_model_domain": tilt <= max_angle, "status": outcome["status"],
                 "issues": outcome["issues"], "model_scope_issues": outcome["model_scope_issues"],
                 "target_issue_codes": outcome["target_issue_codes"],
                 "engine": {k: beam.get(k) for k in ("waist_axial_um", "waist_lateral_um", "waist_radius_um", "power_W")},
                 "external": {"z_focus_um": row["z_focus_um"], "lateral_um": row["focus_xy_um"][0], "w_focus_um": row["w_focus_um"],
                              "power_W": 0.001 * row["focusing_efficiency"]}}
        if beam.get("waist_axial_um") is not None:
            entry["engine_vs_external"] = {
                "z_abs_err_um": beam["waist_axial_um"] - row["z_focus_um"],
                "lateral_abs_err_um": beam["waist_lateral_um"] - row["focus_xy_um"][0],
                "w_rel_err": beam["waist_radius_um"] / row["w_focus_um"] - 1,
                "power_rel_err": beam["power_W"] / (0.001 * row["focusing_efficiency"]) - 1}
        field[f"{tilt:g}deg"] = entry

    counter = {"450nm": run(project(model, mode, wavelengths_nm=[450.0], waist_um=waist_um,
                                    band_override=(rows[0]["wavelength_nm"], rows[-1]["wavelength_nm"])))}
    counter["450nm"]["expected"] = "OUT_OF_MODEL_SCOPE"
    counter["450nm"]["expected_code"] = "MODEL_WAVELENGTH_OUTSIDE_BAND"
    counter["20deg"] = {k: field["20deg"][k] for k in ("status", "issues", "model_scope_issues", "target_issue_codes",
                                                        "engine", "external")}
    counter["20deg"]["expected"] = "OUT_OF_MODEL_SCOPE" if mode == "tabulated" else "not stated by IDEAL_THIN_LENS"
    counter["20deg"]["expected_code"] = "MODEL_FIELD_ANGLE_EXCEEDED" if mode == "tabulated" else None
    if mode == "tabulated":
        counter["unsupported_metric"] = run(project(model, mode, wavelengths_nm=[532], waist_um=waist_um,
                                                    target_metric="peak_irradiance_W_per_mm2"))
        counter["unsupported_metric"]["expected"] = "OUT_OF_MODEL_SCOPE"
        counter["unsupported_metric"]["expected_code"] = "METRIC_NOT_VALIDATED_FOR_ELEMENT"
        multi = run(project(model, mode, wavelengths_nm=list(TABLE_NM + HOLDOUT_NM), waist_um=waist_um))
        lines = {round(b["wavelength_nm"]): b for b in multi["beams"]}
        multi_line = {"status": multi["status"], "issues": multi["issues"], "identity": multi["identity"], "lines": {}}
        for lam in TABLE_NM + HOLDOUT_NM:
            f_um, transmittance = interpolate(rows, lam)
            multi_line["lines"][f"{lam}nm"] = compare(lines[lam], external[(lam, 0.0, waist_um)], model, waist_um, clear_um,
                                                      f_um, transmittance)
    else:
        multi_line = None
    for outcome in counter.values():
        codes = set(outcome["issues"]) | set(outcome.get("target_issue_codes", [])) | set(outcome["model_scope_issues"])
        outcome["as_expected"] = ((outcome["status"] == outcome["expected"] and outcome["expected_code"] in codes)
                                  if outcome["expected"].isupper() else None)

    in_domain = list(cases.values()) + [f for f in field.values() if f["inside_model_domain"]]
    checks = {
        "engine_vs_model_rel": {"value": max(c["engine_vs_model_rel"] for c in cases.values()), "tolerance": MODEL_AGREEMENT_REL},
        "in_domain_cases_within_stated_errors": {"value": sum(1 for c in cases.values() if not c["within_stated_errors"])
                                                 + sum(1 for f in field.values() if f["inside_model_domain"]
                                                       and not within_field(f, bounds)), "tolerance": 0},
        "in_domain_runs_out_of_scope": {"value": sum(1 for c in in_domain if c["status"] == "OUT_OF_MODEL_SCOPE")
                                        + (1 if multi_line and multi_line["status"] == "OUT_OF_MODEL_SCOPE" else 0),
                                        "tolerance": 0},
        "counterexamples_not_as_expected": {"value": sum(1 for c in counter.values() if c["as_expected"] is False),
                                            "tolerance": 0},
    }
    if multi_line:
        checks["multi_line_engine_vs_model_rel"] = {"value": max(l["engine_vs_model_rel"] for l in multi_line["lines"].values()),
                                                    "tolerance": MODEL_AGREEMENT_REL}
    status = "PASS" if all(c["value"] <= c["tolerance"] for c in checks.values()) else "FAIL"
    holdouts = [c for c in cases.values() if c["role"] == "hold-out"]
    report = {"example": "interop/metasurface step 4", "status": status, "model_mode": mode, "engine_version": installed,
              "environment": environment("numpy"), "stated_errors": bounds, "max_field_angle_deg": max_angle,
              "checks": checks, "cases": cases, "field_angles": field, "counterexamples": counter,
              "multi_line": multi_line, "in_domain_count": len(in_domain)}
    write_json(directory / f"step4_report_{mode}.json", report)
    return {"example": report["example"], "status": status, "model_mode": mode, "checks": checks,
            "stated_errors": bounds,
            "holdout_max_abs": {k: max(abs(c["engine_vs_external"][k]) for c in holdouts)
                                for k in ("z_rel_err", "w_rel_err", "power_rel_err")},
            "counterexamples": {k: {"status": v["status"], "expected": v["expected"], "as_expected": v["as_expected"],
                                    "issues": v["issues"] + v["model_scope_issues"],
                                    "target_issue_codes": v.get("target_issue_codes", [])}
                                for k, v in counter.items()},
            "report": str(directory / f"step4_report_{mode}.json")}


def within_field(entry, bounds):
    errors = entry.get("engine_vs_external")
    if not errors:
        return False
    return (abs(errors["z_abs_err_um"]) <= bounds["z_abs_um"] and abs(errors["lateral_abs_err_um"]) <= bounds["z_abs_um"]
            and abs(errors["w_rel_err"]) <= bounds["w_rel"] and abs(errors["power_rel_err"]) <= bounds["power_rel"])


def main(argv=None):
    def workflow():
        parser = ArgumentParser(description=__doc__.split("\n\n")[0])
        parser.add_argument("directory", type=Path, help="directory with metalens_model.json and step3_report.json")
        parser.add_argument("--model", choices=("tabulated", "per-wavelength-ideal"), default="tabulated",
                            help="model kind to declare (default: the TABULATED_THIN_LENS model itself)")
        args = parser.parse_args(argv)
        return run_example(args.directory, args.model)

    return emit(workflow)


if __name__ == "__main__":
    raise SystemExit(main())
