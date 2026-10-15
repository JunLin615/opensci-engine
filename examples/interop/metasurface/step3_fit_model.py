"""Step 3: fit the external focusing response to an OpenSci TABULATED_THIN_LENS model (no OpenSci import).

From the step-2 focus table (normal incidence, 30 um input beam) each table
wavelength becomes one model row:

* focal length: the equivalent thin lens that puts a Gaussian waist at the external
  focus, from inverting z' = f / (1 + (f / z_R)^2) for an input waist at the lens;
* transmittance: focusing efficiency / Gaussian power inside the clear aperture, so the
  aperture loss the Engine applies itself is not counted twice.

Between rows the model interpolates optical power (1/f) and transmittance linearly in
wavelength. The model is then validated against external results it was not built
from: hold-out wavelengths, the input-beam-size check and small field angles. Each
supported metric gets an error bound = largest model-vs-external deviation + the
external reference's own numerical spread (RCWA orders, propagation window). The
largest field angle whose deviations stay inside those bounds becomes
``max_field_angle_deg``; the validated beam radius (rounded up to 0.1 um) becomes ``max_beam_radius_mm``.

A single external focus does not define a general component: the model holds only
inside the stated wavelength span, field angle, beam size and polarization, for the
listed metrics.

Usage: python examples/interop/metasurface/step3_fit_model.py run-interop-metasurface
"""

from __future__ import annotations

from datetime import date
import hashlib
import json
import math
from pathlib import Path
import sys

if __package__:
    from ..common import ArgumentParser, decimal_text, emit, sha256_file, write_json
    from .step1_unit_cells import HOLDOUT_NM, TABLE_NM
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import ArgumentParser, decimal_text, emit, sha256_file, write_json
    from step1_unit_cells import HOLDOUT_NM, TABLE_NM

MODEL_ID = "metalens_tio2_f200um"
CANDIDATE_FIELD_ANGLES_DEG = (2.0, 5.0, 8.0, 20.0)
# The validated input radius (30 um) is stated rounded up to 0.1 um, so a beam of exactly that radius, which a trace
# reproduces only to the last floating-point digit, stays inside the domain.
BEAM_RADIUS_MARGIN_UM = 0.1


def rayleigh_um(waist_um, wavelength_nm):
    return math.pi * waist_um ** 2 / (wavelength_nm * 1e-3)


def equivalent_focal_length_um(z_focus_um, waist_um, wavelength_nm):
    """Invert z' = f / (1 + (f / z_R)^2) (input waist at the lens) for the converging root f."""
    z_r = rayleigh_um(waist_um, wavelength_nm)
    a = z_focus_um / z_r ** 2
    return (1.0 - math.sqrt(1.0 - 4.0 * a * z_focus_um)) / (2.0 * a)


def thin_lens_focus(f_um, waist_um, wavelength_nm):
    """Waist position after the lens and waist radius (um) of a Gaussian with its waist at an ideal thin lens."""
    z_r = rayleigh_um(waist_um, wavelength_nm)
    ratio = f_um / z_r
    return f_um / (1.0 + ratio ** 2), waist_um * ratio / math.sqrt(1.0 + ratio ** 2)


def aperture_fraction(waist_um, clear_radius_um):
    return 1.0 - math.exp(-2.0 * clear_radius_um ** 2 / waist_um ** 2)


def interpolate(rows, wavelength_nm):
    """LINEAR_IN_OPTICAL_POWER focal length and LINEAR transmittance between rows (no extrapolation)."""
    lams = [r["wavelength_nm"] for r in rows]
    if not lams[0] <= wavelength_nm <= lams[-1]:
        raise ValueError(f"{wavelength_nm} nm lies outside the table {lams[0]}-{lams[-1]} nm")
    for lo, hi in zip(rows, rows[1:]):
        if lo["wavelength_nm"] <= wavelength_nm <= hi["wavelength_nm"]:
            u = (wavelength_nm - lo["wavelength_nm"]) / (hi["wavelength_nm"] - lo["wavelength_nm"])
            power = (1 - u) / lo["focal_length_um"] + u / hi["focal_length_um"]
            return 1.0 / power, (1 - u) * lo["transmittance"] + u * hi["transmittance"]
    return rows[0]["focal_length_um"], rows[0]["transmittance"]


def ceil_sig(value, digits=2):
    """Round a positive bound up to ``digits`` significant digits."""
    if value <= 0:
        return 0.0
    exponent = math.floor(math.log10(value)) - digits + 1
    scale = 10.0 ** exponent
    return round(math.ceil(value / scale - 1e-9) * scale, max(0, -exponent))


def canonical_sha256(document):
    return hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def spreads(directory, main):
    """External numerical spread per (wavelength, tilt, waist) across the available convergence tables."""
    others = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(directory).glob("focus_nG*_N*.json"))
              if p.name != main.name]
    key = lambda r: (r["wavelength_nm"], r["tilt_deg"], r["input_waist_radius_um"])  # noqa: E731
    base = {key(r): r for r in json.loads(main.read_text(encoding="utf-8"))["rows"]}
    result = {}
    for table in others:
        for row in table["rows"]:
            ref = base.get(key(row))
            if ref is None:
                continue
            entry = result.setdefault(key(row), {"z_rel": 0.0, "w_rel": 0.0, "eff_abs": 0.0, "settings": []})
            entry["z_rel"] = max(entry["z_rel"], abs(row["z_focus_um"] / ref["z_focus_um"] - 1.0))
            entry["w_rel"] = max(entry["w_rel"], abs(row["w_focus_um"] / ref["w_focus_um"] - 1.0))
            entry["eff_abs"] = max(entry["eff_abs"], abs(row["focusing_efficiency"] - ref["focusing_efficiency"]))
            entry["settings"].append(table["library"] + f" N{table['grid']['samples']}")
    return [p.name for p in Path(directory).glob("focus_nG*_N*.json") if p.name != main.name], result


def run_example(directory, n_g, samples, transmittance_interpolation):
    directory = Path(directory)
    table_path = directory / f"focus_nG{n_g}_N{samples}.json"
    table = json.loads(table_path.read_text(encoding="utf-8"))
    library_path = directory / table["library"]
    library = json.loads(library_path.read_text(encoding="utf-8"))
    design = table["design"]
    waist, clear_um = design["input_waist_radius_um"], design["diameter_um"] / 2
    normal = {r["wavelength_nm"]: r for r in table["rows"]
              if r["tilt_deg"] == 0 and r["input_waist_radius_um"] == waist}
    fraction = aperture_fraction(waist, clear_um)
    rows = []
    for lam in TABLE_NM:
        ext = normal[lam]
        rows.append({"wavelength_nm": lam, "focal_length_um": equivalent_focal_length_um(ext["z_focus_um"], waist, lam),
                     "transmittance": min(1.0, ext["focusing_efficiency"] / fraction)})

    convergence_tables, spread = spreads(directory, table_path)
    max_spread = {k: max([s[k] for s in spread.values()] or [0.0]) for k in ("z_rel", "w_rel", "eff_abs")}

    def deviation(ext, f_um, transmittance, waist_um, label, role):
        z, w = thin_lens_focus(f_um, waist_um, ext["wavelength_nm"])
        efficiency = transmittance * aperture_fraction(waist_um, clear_um)
        return {"case": label, "role": role, "wavelength_nm": ext["wavelength_nm"],
                "external": {"z_focus_um": ext["z_focus_um"], "w_focus_um": ext["w_focus_um"],
                             "focusing_efficiency": ext["focusing_efficiency"], "focus_xy_um": ext["focus_xy_um"]},
                "model": {"z_focus_um": z, "w_focus_um": w, "focusing_efficiency": efficiency},
                "z_abs_err_um": z - ext["z_focus_um"], "z_rel_err": z / ext["z_focus_um"] - 1.0,
                "w_rel_err": w / ext["w_focus_um"] - 1.0, "efficiency_abs_err": efficiency - ext["focusing_efficiency"],
                "power_rel_err": efficiency / ext["focusing_efficiency"] - 1.0}

    validation = []
    for lam in TABLE_NM + HOLDOUT_NM:
        f_um, transmittance = interpolate(rows, lam)
        validation.append(deviation(normal[lam], f_um, transmittance, waist, f"{lam} nm",
                                    "table row" if lam in TABLE_NM else "hold-out"))
    for row in table["rows"]:
        if row["tilt_deg"] == 0 and row["input_waist_radius_um"] != waist:
            f_um, transmittance = interpolate(rows, row["wavelength_nm"])
            validation.append(deviation(row, f_um, transmittance, row["input_waist_radius_um"],
                                        f"{row['wavelength_nm']} nm, input radius {row['input_waist_radius_um']:g} um",
                                        "beam-size check"))
    in_domain = validation
    bounds = {
        "z_abs_um": ceil_sig(max(abs(v["z_abs_err_um"]) for v in in_domain)
                             + max_spread["z_rel"] * max(v["external"]["z_focus_um"] for v in in_domain)),
        "w_rel": ceil_sig(max(abs(v["w_rel_err"]) for v in in_domain) + max_spread["w_rel"]),
        "power_rel": ceil_sig(max(abs(v["power_rel_err"]) for v in in_domain)
                              + max_spread["eff_abs"] / min(v["external"]["focusing_efficiency"] for v in in_domain)),
    }

    # Field angle: the thin-lens equivalent predicts the 0 deg focus displaced to f tan(theta) on a flat focal plane.
    reference = normal[532]
    field = []
    max_angle = None
    for angle in CANDIDATE_FIELD_ANGLES_DEG:
        tilted = next((r for r in table["rows"] if r["wavelength_nm"] == 532 and r["tilt_deg"] == angle), None)
        if tilted is None:
            continue
        lateral_model = reference["z_focus_um"] * math.tan(math.radians(angle))
        entry = {"tilt_deg": angle, "external_z_um": tilted["z_focus_um"], "external_lateral_um": tilted["focus_xy_um"][0],
                 "model_z_um": reference["z_focus_um"], "model_lateral_um": lateral_model,
                 "z_abs_err_um": reference["z_focus_um"] - tilted["z_focus_um"],
                 "lateral_abs_err_um": lateral_model - tilted["focus_xy_um"][0],
                 "w_rel_err": reference["w_focus_um"] / tilted["w_focus_um"] - 1.0,
                 "power_rel_err": reference["focusing_efficiency"] / tilted["focusing_efficiency"] - 1.0}
        entry["within_bounds"] = (abs(entry["z_abs_err_um"]) <= bounds["z_abs_um"]
                                  and abs(entry["lateral_abs_err_um"]) <= bounds["z_abs_um"]
                                  and abs(entry["w_rel_err"]) <= bounds["w_rel"]
                                  and abs(entry["power_rel_err"]) <= bounds["power_rel"])
        field.append(entry)
    for entry in field:  # accepted from the smallest angle upward until the first one outside the bounds
        if not entry["within_bounds"]:
            break
        max_angle = entry["tilt_deg"]
    if max_angle is None:
        raise ValueError("no field angle validated: the model would have no field-angle domain")

    tools = [{"name": "grcwa", "version": library["solver"].get("version") or "unknown"}]
    tools += [{"name": name, "version": version} for name, version in (table.get("environment", {}).get("packages") or {}).items()
              if version and name in ("numpy", "scipy")]
    configuration = {"unit_cells": {k: library[k] for k in ("assumptions", "solver", "radii_um")},
                     "focusing": {k: table[k] for k in ("design", "grid", "method")}}
    lam_lo, lam_hi = TABLE_NM[0], TABLE_NM[-1]
    model = {
        "model_kind": "TABULATED_THIN_LENS", "model_version": "1",
        "rows": [{"wavelength_nm": decimal_text(r["wavelength_nm"]), "focal_length_mm": decimal_text(r["focal_length_um"] / 1000, 7),
                  "transmittance": decimal_text(r["transmittance"], 4)} for r in rows],
        "focal_interpolation": "LINEAR_IN_OPTICAL_POWER", "transmittance_interpolation": transmittance_interpolation,
        "clear_radius_mm": decimal_text(clear_um / 1000), "edge_radius_mm": decimal_text(clear_um / 1000 + 0.01),
        "max_field_angle_deg": decimal_text(max_angle), "max_beam_radius_mm": decimal_text((waist + BEAM_RADIUS_MARGIN_UM) / 1000),
        "validated_polarizations": ["LINEAR_X"],
        "supported_metrics": [
            *({"metric": f"waist_distance_{axis}_mm", "abs_error": decimal_text(bounds["z_abs_um"] / 1000, 6),
               "basis": "largest deviation from the external focus over table rows, hold-out wavelengths and the "
                        "beam-size check, plus the external reference's numerical spread"} for axis in ("x", "y")),
            *({"metric": f"waist_radius_{axis}_mm", "rel_error": decimal_text(bounds["w_rel"], 4),
               "basis": "largest relative deviation from the external second-moment focal radius, plus the external "
                        "numerical spread"} for axis in ("x", "y")),
            {"metric": "power_W", "rel_error": decimal_text(bounds["power_rel"], 4),
             "basis": "largest relative deviation of the delivered power from the external focusing efficiency, plus "
                      "the external numerical spread"},
        ],
        "evidence": {
            "method": "RCWA unit-cell library (TiO2 pillars on SiO2, constant indices, normal incidence, x polarization), "
                      "local periodic approximation and scalar angular-spectrum focusing of a 30 um Gaussian beam",
            "tools": tools, "source_data_sha256": sha256_file(library_path),
            "configuration_sha256": canonical_sha256(configuration),
            "fit_model": "rows: equivalent thin-lens focal length from the Gaussian focusing law at each row's external "
                         "focus; transmittance = focusing efficiency / Gaussian power inside the clear aperture; "
                         f"interpolation linear in optical power and {transmittance_interpolation.lower()} in transmittance",
            "validation_summary": f"rows {lam_lo}-{lam_hi} nm; hold-out wavelengths {', '.join(str(w) for w in HOLDOUT_NM)} nm; "
                                  f"input radius 20 and 30 um (bound stated as 30.1 um); field angles up to {decimal_text(max_angle)} deg within "
                                  "the stated errors; external spread from RCWA orders 101/201 and propagation windows "
                                  "1024/2048 samples",
            "date": date.today().isoformat(),
        },
        "plane_z_mm": "0", "status": "DECLARED",
    }
    optical_model = {"model_id": MODEL_ID, "display_name": "TiO2 metalens f 200 um (tabulated response)", "model": model}
    write_json(directory / "metalens_model.json", optical_model)
    report = {"example": "interop/metasurface step 3", "status": "PASS", "model": str(directory / "metalens_model.json"),
              "rows": rows, "aperture_fraction": fraction, "error_bounds": bounds, "external_spread": max_spread,
              "convergence_tables": convergence_tables, "validation": validation, "field_angles": field,
              "max_field_angle_deg": max_angle, "focus_table": str(table_path), "library": str(library_path)}
    write_json(directory / "step3_report.json", report)
    holdouts = [v for v in validation if v["role"] == "hold-out"]
    return {"example": report["example"], "status": "PASS", "model": report["model"], "error_bounds": bounds,
            "max_field_angle_deg": max_angle, "external_spread": max_spread,
            "holdout_max": {"z_rel_err": max(abs(v["z_rel_err"]) for v in holdouts),
                            "w_rel_err": max(abs(v["w_rel_err"]) for v in holdouts),
                            "efficiency_abs_err": max(abs(v["efficiency_abs_err"]) for v in holdouts)},
            "report": str(directory / "step3_report.json")}


def main(argv=None):
    def workflow():
        parser = ArgumentParser(description=__doc__.split("\n\n")[0])
        parser.add_argument("directory", type=Path, help="directory with the step-1 library and step-2 focus tables")
        parser.add_argument("--nG", type=int, default=101, help="library of the model (default 101)")
        parser.add_argument("--samples", type=int, default=1024, help="focus table of the model (default 1024 samples)")
        parser.add_argument("--transmittance-interpolation", choices=("LINEAR", "POINTS_ONLY"), default="LINEAR")
        args = parser.parse_args(argv)
        return run_example(args.directory, args.nG, args.samples, args.transmittance_interpolation)

    return emit(workflow)


if __name__ == "__main__":
    raise SystemExit(main())
