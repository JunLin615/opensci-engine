# External scientific tools

[User guide](README.md) · English · [简体中文](../zh-CN/interop.md)

OpenSci computes ray paths, Gaussian beams, polarization, power and a linear optical
network of your design. Optimizers, diffraction codes, quantum-optics simulators and
electromagnetic solvers run in your own Python environment and read what OpenSci
exports. The four worked examples below were executed against independent references;
the [validation record](../interop-validation.md) lists versions, inputs, outputs and
deviations.

**These examples require opensci-engine 0.8.0 or newer.** They use the linear optical
network with per-path group delays, native components and the `TABULATED_THIN_LENS`
model kind; the guides for the 0.6.1 package do not cover them. Each script checks the
installed version and stops with a clear message on an older engine.

| Topic | OpenSci provides | External tool computes | Example |
| --- | --- | --- | --- |
| [Optimization and tolerance](#optimization-and-tolerance) | Each design's run, target metrics, run identity | Next design values (SciPy, Optuna), sensitivity indices (SALib) | `examples/interop/optimization/` |
| [Diffraction at a declared stop](#diffraction-at-a-declared-stop) | Gaussian beam state, power, stop and lens parameters, plane frames | Diffracted focal field (LightPipes; prysm, POPPY, Diffractio as cross-checks) | `examples/interop/diffraction/` |
| [Quantum photonics](#quantum-photonics-from-the-network-export) | Linear optical network: modes, lossy transfer matrix, path delays, conventions | Photon statistics (Perceval; Piquasso as cross-check) | `examples/interop/quantum/` |
| [Metasurface lens as a virtual component](#metasurface-lens-as-a-virtual-focusing-component) | Runs with a tabulated thin focusing element inside its validated domain | Unit-cell responses (grcwa) and focusing (angular spectrum) | `examples/interop/metasurface/` |

External results stay in their own files next to the OpenSci run they used, with that
run's identity. They do not change the run, its hashes or its Local Validation, and a
virtual component made from them is a simulation model, not an orderable product.

Prompts for your own agent: [English](interop-prompts.md) · [简体中文](../zh-CN/interop-prompts.md).

## Before you start

Use one fresh virtual environment per topic (Python 3.11 or newer; the examples were
verified with Python 3.12) and run the commands from the repository root:

```bash
python -m venv .venv-optimization
.venv-optimization/bin/python -m pip install -r examples/interop/optimization/requirements-optimization.txt
```

On Windows use `.venv-optimization\Scripts\python`. The requirements files pin the
verified versions; the third-party packages are never dependencies of
`opensci-engine` itself. Every script prints one JSON summary on stdout and exits with
0 when all its comparisons are inside their stated tolerances, 1 when one is not, and
4 on an error (a JSON error on stderr).

## Optimization and tolerance

`optimize_expander.py` collimates a catalog-free Keplerian expander (two declared ideal
thin lenses, f = 50 mm and 150 mm, 532 nm, 0.5 mm waist) by moving lens `L2`:

```bash
python examples/interop/optimization/optimize_expander.py --out run-interop-optimization
```

Each evaluation copies the Project, sets `L2`'s position by `instance_id`, runs the
Engine in memory and reads the target metric `divergence_half_angle_x_rad` from the
run's results. SciPy (`minimize_scalar`, bounded) and Optuna (TPE, seed 1, 60 trials)
search the separation; SALib then estimates first-order and total Sobol indices of
the divergence for uniform mounting errors of ±0.5 mm on both lenses and ±5 % on the
source waist. An independent ABCD calculation (numpy only) supplies the reference
optimum and the reference value of every evaluated design.

Outputs in the `--out` directory: `evaluations.jsonl` (one line per Engine run with its
inputs, metric value, status and `project_hash`, `input_hash`, `result_hash`,
`engine_build_id`), `project-baseline.json` and `report.json`. In the validated run
SciPy reached the reference optimum (200.0573 mm separation) to 6e-14 mm in 9
evaluations, every Engine value matched the ABCD reference to 2e-14 relative, and the
Sobol indices of Engine and reference agreed to 1e-14. The optimizer chooses the
values, OpenSci computes each design; a run whose status is `OUT_OF_MODEL_SCOPE` or
`UNKNOWN` should be treated as a failed evaluation rather than a number.

## Diffraction at a declared stop

A 532 nm TEM00 beam (1 mm waist radius, 1 mW) passes a declared circular
`APERTURE_STOP` and an `IDEAL_THIN_LENS` (f = 200 mm); the question is the irradiance
in the back focal plane. Run both sides, possibly in two environments:

```bash
python examples/interop/diffraction/opensci_handoff.py --out run-interop-diffraction
python examples/interop/diffraction/external_focus.py run-interop-diffraction
```

`opensci_handoff.py` runs the Project for stop radii 3, 1.2 and 0.5 mm and writes a
`handoff.json` per case: the Gaussian state at the stop (radii, wavefront radii, M²,
power, wavelength, medium, beam axes), the stop and lens parameters from the Project,
the Engine's own focal-plane result, and the run identity. `external_focus.py` reads
only these files. It constructs the sampled field under a stated convention
(`tem00_field.py`):

* field `E ~ exp[i(k·r − ωt)]`; `U = sqrt(2P/(π w_x w_y)) exp(−x²/w_x² − y²/w_y²) exp(+ik(x²/2R_x + y²/2R_y))`
  in the beam axes, `R > 0` for a diverging beam; Gouy phase and piston omitted;
  `|U|²` integrates to the beam power;
* only valid for M² = 1 on both axes (the script refuses otherwise); M² > 1 alone
  does not determine a mode content or coherence;
* hard, infinitely thin stop with area-weighted edge pixels; ideal lens as a
  quadratic phase (the Engine does not model the ideal lens's phase).

LightPipes propagates the field with absolute units on six grids and windows (the
convergence study); prysm and POPPY recompute the normalized radial profile, Diffractio
the absolute peak; a Hankel integral (`hankel_reference.py`) is the independent
reference. Results of the validated run:

| Stop radius | Engine status | Engine focal peak vs reference | LightPipes finest vs reference (convergence spread) |
| --- | --- | --- | --- |
| 3 mm | `PASS` | +0.024 % | 3e-8 (1e-7) |
| 1.2 mm (5.6 % of the power blocked) | `WARNING` `GAUSSIAN_TRUNCATION` | **+62 %** | −1.0e-4 (1.7e-4) |
| 0.5 mm | `OUT_OF_MODEL_SCOPE` `GAUSSIAN_SEVERE_TRUNCATION` | Gaussian withheld | 8.6e-4 (1.7e-3) |

The Engine's transmitted power equals `1 − exp(−2a²/w²)` in every case. Its focal
irradiance is a paraxial Gaussian quantity: exact for the open stop, but after a
`GAUSSIAN_TRUNCATION` warning only the power is reliable and the focal irradiance needs
a diffraction calculation like this one. prysm and POPPY agree with the reference
profile to 4e-7, Diffractio's absolute peak to 3e-5.

Diffractio 1.0.0 requires numpy < 2 and cannot share an environment with
opensci-engine. Install `requirements-diffractio.txt` in a second environment and run
the same `external_focus.py` there: it reads only the handoff files. The script also
writes `focus_profiles.png` (Engine Gaussian and diffraction reference per case).

## Quantum photonics from the network export

`build_layouts.py` builds small catalog-free Projects from native components (a thin
50:50 plate splitter, flat mirrors, uncoated windows of a declared N-BK7 Sellmeier
glass) and exports each with the public command:

```bash
python examples/interop/quantum/build_layouts.py --out run-interop-quantum
python examples/interop/quantum/run_quantum.py run-interop-quantum --inputs examples/interop/quantum/quantum_inputs.json
```

Cases: Hong-Ou-Mandel interference at 780 nm; a delay scan from 13 exports with source
B moved by −0.3 … +0.3 mm; a 3 mm window in one arm with the other source moved back by
the window's group-delay length or by its phase-delay length only; a two-input
Mach-Zehnder at 532 nm with 0, 1 and 1.0003 mm windows; an ideal thin lens on the path,
which the export refuses (`PHASE_UNDEFINED_IDEAL_LENS`).

The Project's lasers only define the network's modes, wavelength and polarization.
Every quantum quantity comes from `quantum_inputs.json`: one photon per source in the
V mode; Gaussian wavepackets (rms intensity duration 0.25 ps for the HOM cases, 1000 ps
for the MZI) with zero-delay indistinguishability 0.95; one threshold detector per output
plane with efficiency 0.8 and a dark-count probability (0, and 0.01 in one case).
`run_quantum.py` never imports opensci-engine:

* it reads `T[output, input]` (Perceval `Unitary(Matrix(U))` and Piquasso
  `Interferometer(U)` read matrices the same way) and multiplies by `sqrt(η)` for the
  detector efficiency;
* a lossy T is embedded in a unitary twice its size (unitary dilation), and the extra
  modes are traced out;
* each path's group delay is taken from the export's `group_delay_ps` and checked
  against the value computed from the Project's declared glass; the photons'
  mutual indistinguishability is `p0 exp(−Δτ²/4σ²)` with Δτ their relative group delay;
* a single-wavelength T is used only when one photon's paths to one output differ in
  group delay by at most 5 % of its duration; otherwise the case is refused
  (`SINGLE_FREQUENCY_MODEL_INVALID`, shown with 0.25 ps photons in the 1 mm MZI).

Perceval (SLOS) simulates the partially distinguishable photons with noise tags;
Piquasso recomputes the same distribution as the p-weighted mixture of
indistinguishable and distinguishable photons. The closed-form reference
(`reference.py`) uses no exported data: 2 × 2 splitter algebra, the SCHOTT N-BK7
Sellmeier formula, Fresnel loss of the uncoated faces and the Gaussian wavepacket
overlap. In the validated run Perceval matched the reference to 4e-8 and Piquasso to
2e-9 over all cases; the HOM dip visibility over the scan was 0.9491 (reference
0.9491; analytic 0.95 at infinite delay range). Compensating the 3 mm window by its
phase delay leaves a 0.163 ps group-delay mismatch and lowers the photons'
indistinguishability from 0.95 to 0.854; the export's group delay makes this visible.

Licenses as reported upstream: Perceval (`perceval-quandela`) MIT; its required
dependency `exqalibur` declares CC BY-NC-ND 4.0 in its package metadata; Piquasso
Apache-2.0. Piquasso 8.0.1 with numba 0.68 can fail to reload its own compiled cache;
the script gives each run a fresh `NUMBA_CACHE_DIR`.

## Metasurface lens as a virtual focusing component

A TiO2 nanopillar metalens (f = 200 µm at 532 nm, 100 µm diameter) is characterized
externally and turned into an OpenSci `TABULATED_THIN_LENS` model:

```bash
python examples/interop/metasurface/step1_unit_cells.py --out run-interop-metasurface
python examples/interop/metasurface/step2_focusing.py run-interop-metasurface
python examples/interop/metasurface/step3_fit_model.py run-interop-metasurface
python examples/interop/metasurface/step4_engine_check.py run-interop-metasurface
```

1. **Unit cells** (grcwa): zeroth-order complex transmission of pillars 40–150 nm in
   radius (period 325 nm, height 600 nm, constant indices TiO2 2.43 / SiO2 1.46, normal
   incidence, x polarization) at the ten table wavelengths 490–580 nm and five hold-out
   wavelengths. The flux-normalized amplitude `t·sqrt(T/|t|²)` is used, because `|t|²`
   alone is not a power fraction across media of different index.
2. **Focusing** (numpy): local periodic approximation and scalar angular-spectrum
   propagation of a 30 µm Gaussian beam; focus position, second-moment radius and
   focusing efficiency per wavelength, at field angles 2, 5, 8 and 20° and for a 20 µm
   beam.
3. **Model**: one row per table wavelength (equivalent thin-lens focal length from the
   Gaussian focusing law; transmittance = focusing efficiency / Gaussian power inside the
   clear aperture), optical power and transmittance interpolated linearly in
   wavelength, error bounds per supported metric from the hold-out comparison plus the
   external numerical spread (RCWA orders 101/201, propagation windows 1024/2048
   samples), the largest field angle whose deviations stay inside those bounds as
   `max_field_angle_deg`, the validated beam radius as `max_beam_radius_mm`, `LINEAR_X`
   as validated polarization, and the tool versions plus the SHA-256 of the unit-cell
   library as evidence. The result is `metalens_model.json`.
4. **OpenSci check**: the model is declared in a catalog-free Project and traced for
   every table and hold-out wavelength, in one multi-line run, at small field angles,
   and for the counterexamples.

Results of the validated run (unit cells with 101 RCWA orders, 1024 × 1024 propagation
grid; external spread from 201 orders and a 2048-sample grid: 0.50 % in focus position,
0.71 % in spot radius, 0.015 in efficiency):

| Quantity | Table rows (10) | Hold-out wavelengths (5) | 20 µm input beam | Stated model error |
| --- | --- | --- | --- | --- |
| Focus position | exact by construction | ≤ 0.30 µm (0.16 %) | 0.08 µm | `waist_distance_*_mm` ± 0.0014 mm |
| Spot radius (Engine Gaussian vs external second moment) | −3.0 … −7.3 % | −3.0 … −5.1 % | −0.6 % | `waist_radius_*_mm` ± 8.1 % |
| Delivered power | exact by construction | −5.4 … +15.9 % | +0.03 % | `power_W` ± 19 % |

The focal position follows the external result closely across the band; the ideal
Gaussian focus is 3–7 % smaller than the external spot (phase discretization of the
cells), which the stated radius error carries. The focusing efficiency changes from
0.64 to 0.95 within 10 nm, so linear interpolation between rows predicts the power of
a hold-out wavelength only to 16 %; denser rows or `transmittance_interpolation:
POINTS_ONLY` give a tighter power model. At 2° field angle the external focus stays
within the stated errors; at 5° its axial position moves by 1.56 µm, more than the
1.4 µm bound, so `max_field_angle_deg` is 2. The Engine reproduced the thin-lens
prediction of the model to 4e-7 in every in-domain case.

Counterexamples: a 450 nm source is outside the 490–580 nm rows and the run is
`OUT_OF_MODEL_SCOPE` (`MODEL_WAVELENGTH_OUTSIDE_BAND`). At 20° the external focus lies
15.6 µm closer to the lens and 5.6 µm closer to the axis than the thin-lens prediction,
with a 68 % larger spot and 13 % less power: the model's `max_field_angle_deg` puts
this input outside its scope. `step4_engine_check.py` also checks that a target asking
for an unsupported metric (`peak_irradiance_W_per_mm2`) through the element is
`OUT_OF_MODEL_SCOPE`, and traces all 15 wavelengths as one multi-line source.
`--model per-wavelength-ideal` runs the same comparison with one `IDEAL_THIN_LENS` per
wavelength; that kind cannot state a field-angle domain and returns `WARNING` at 20°.
All runs report `GAUSSIAN_TRUNCATION` because the 100 µm aperture clips 0.4 % of the
30 µm beam; the Engine counts that power loss itself.

Other unit-cell solvers fit the same pipeline as long as step 1 writes the same library
fields: meent (MIT) and torcwa (LGPL) install with pip; DFlat (`dflat-opt`) and metabox
depend on gdspy, which needs a C compiler on Windows, and metabox runs on Python 3.8 with
TensorFlow 2.11, so it belongs in its own environment exchanging files. Only grcwa
(GPLv3, as declared in its package metadata) was executed for this example.

A single external focus does not define a general component. The model is valid only
for its wavelength rows, field angles up to `max_field_angle_deg`, input beam radii up
to `max_beam_radius_mm` (validated at 20 and 30 µm), x polarization and the listed
metrics; a target asking for another metric through the element is outside the model's
scope. It states no phase, so the network export and wavefront results refuse paths
through it. Its accuracy is bounded by the external reference itself: the local
periodic approximation and scalar propagation neglect cell coupling and vector effects.
