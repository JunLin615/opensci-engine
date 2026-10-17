# External-tool examples validation

Evidence for the four examples in [examples/interop](../examples/interop/) and the
[external tools guide](en/interop.md). These examples require **opensci-engine 0.8.0**
or newer; the 0.6.1 baseline of the other examples is unchanged.

Recorded on 2026-10-15 with opensci-engine 0.8.0, engine build
`0.8.0+444e44652013a822`. Every engine-side number below comes from that build.
Each script's `outcome` compares OpenSci with an external tool or an independent
reference (`WITHIN_TOLERANCE` / `OUT_OF_TOLERANCE`, or `COMPLETED` for a step that only
produces data); OpenSci's own run statuses are quoted separately.

## Reproduce

From the repository root, one fresh virtual environment per topic:

```bash
python -m pip install -r examples/interop/<topic>/requirements-<topic>.txt
python -m unittest tests.test_interop -v
```

Then run the commands of each section below. The offline tests cover the reference
formulas, the field-construction convention, quantum-input parsing, network loading,
group delay from declared glass, unitary dilation and the metasurface fitting
helpers; they need numpy (and scipy for the diffraction reference) and skip cleanly
without them. Two further tests run the Engine (network export with group delays,
`TABULATED_THIN_LENS` scope) and are skipped on engines older than 0.8.0; with the
build above all 24 tests ran and passed. Run outputs are written under `run-interop-*` directories and are not
committed.

Environment of the recorded runs: Windows 10 (AMD64), CPython 3.12.14, numpy 2.5.4,
scipy 1.18.1, matplotlib 3.11.2. All Projects are catalog-free (declared and native
components), so no catalog release is involved.

## Optimization and tolerance

`python examples/interop/optimization/optimize_expander.py --out run-interop-optimization`
with SciPy 1.18.1, Optuna 5.0.0, SALib 1.6.0. Outcome `WITHIN_TOLERANCE`, 709 Engine
evaluations (run status 686 `PASS`, 23 `FAIL` where the divergence target bound is not
met; no infeasible run: a run with any other status would be logged with
`feasible: false` and given a penalty instead of its value), about 0.2 s each.

| Quantity | Result | Reference / tolerance |
| --- | --- | --- |
| Optimum L1–L2 separation, SciPy bounded (9 evaluations) | 200.05728727493042 mm | ABCD 200.05728727493047 mm; error 5.7e-14 mm (tolerance 1e-4) |
| Optimum, Optuna TPE seed 1 (60 trials) | 199.9687 mm; divergence 1.1298e-4 rad | ABCD minimum 1.12829e-4 rad; excess 0.14 % (tolerance 1 %) |
| Engine vs ABCD over all 709 evaluated designs | max relative difference 2.3e-14 | tolerance 1e-9 |
| Sobol total indices (Saltelli N = 128, 640 designs) | L1 0.536, L2 0.524, waist 0.389 (±0.17, ±0.15, ±0.11) | Engine vs ABCD indices differ by 7.5e-15 (tolerance 1e-6) |

Every evaluation line in `evaluations.jsonl` carries `project_hash`, `input_hash`,
`result_hash` and `engine_build_id`. The wide Sobol confidence intervals are the
sampling uncertainty of N = 128; the large total and small first-order indices of the
two lens positions show that the divergence depends on their separation.

## Diffraction at a declared stop

`opensci_handoff.py --out run-interop-diffraction` (beam at the stop from the Engine's
transverse-plane handoff, `RunResults.handoff("stop_plane", element="STOP")`, equal to
the pupil-plane state propagated 1 mm by ABCD to the last digit), then
`external_focus.py` in the same
environment (LightPipes 2.1.5, prysm 0.21.1, POPPY 1.2.0 with astropy 8.0.1,
setuptools 80.10.2) and again in a separate environment with numpy 1.26.4, scipy
1.17.1 and Diffractio 1.0.0 that reads only the handoff files. Outcome
`WITHIN_TOLERANCE` for all three cases in both environments, including the 0.5 mm case
whose Engine run is `OUT_OF_MODEL_SCOPE`. 532 nm, 1 mW, 1 mm waist radius at the source, stop
100 mm downstream, ideal lens f = 200 mm 1 mm after the stop, focal plane 200 mm behind
the lens; encircled power radius 50 µm.

| Stop radius | Engine status | Transmitted fraction (Engine = analytic) | Reference peak (W/mm²) | Engine peak vs reference | Reference / Engine encircled fraction |
| --- | --- | --- | --- | --- | --- |
| 3 mm | `PASS` | 0.99999998 | 0.55487 | +0.024 % | 0.98720 / 0.98721 |
| 1.2 mm | `WARNING` `GAUSSIAN_TRUNCATION` | 0.94382 | 0.32316 | +62.1 % | 0.94821 / 0.98721 |
| 0.5 mm | `OUT_OF_MODEL_SCOPE` `GAUSSIAN_SEVERE_TRUNCATION` | 0.39338 | 0.027150 | withheld | 0.41942 / withheld |

The Engine's transmitted power matched `1 − exp(−2a²/w²)` to 9e-16 in every case.
LightPipes `Forvard` peak irradiance (computed in absolute W/mm²), as relative error
against the reference:

| Grid (samples, window) | 3 mm | 1.2 mm | 0.5 mm |
| --- | --- | --- | --- |
| 512, 6 mm | −5.0e-7 | +6.6e-5 | −4.0e-4 |
| 1024, 6 mm | +2.6e-7 | +2.0e-4 | +7.9e-4 |
| 2048, 6 mm | +1.8e-9 | −2.3e-4 | −2.2e-4 |
| 4096, 6 mm | +1.1e-7 | −2.8e-4 | +2.4e-3 |
| 2048, 9 mm | −3.4e-8 | −1.5e-4 | +7.2e-4 |
| 4096, 9 mm | +3.2e-8 | −1.0e-4 | +8.6e-4 |
| Spread of the last three | 1.5e-7 | 1.7e-4 | 1.7e-3 |

Encircled-fraction errors of the finest grid were 3.3e-4, 8.4e-4 and 1.9e-3 (tolerance
5e-3). Normalized radial profiles (0–100 µm, 5 µm steps): prysm and POPPY 1.2e-8, 1.9e-7
and 3.9e-7 from the reference (tolerance 1e-3); LightPipes 1.4e-3, 8.3e-4 and 1.9e-3,
dominated by linear interpolation of its 2.2 µm grid (tolerance 5e-3). Diffractio
absolute peak: −2.6e-5, −2.7e-5 and −6.0e-6 (tolerance 1e-3).

Observed tool behaviour: prysm 0.21.1 needs setuptools < 81 (`pkg_resources`);
`focus_fixed_sampling` takes the focal-plane step in micrometres and returns an
arbitrary overall scale, and POPPY's `normalize="first"` normalizes at its entrance
plane, so both are compared as normalized profiles. Diffractio 1.0.0's `CZT` returned
the focal maximum one output sample from the requested centre and spaced its samples by
(x_end − x_start)/N, so only its located peak is compared. A pixelated hard stop gave
non-monotonic LightPipes convergence; edge pixels are weighted by their covered area.

## Quantum photonics

`build_layouts.py --out run-interop-quantum` exported 19 networks through
`opensci-engine project network` (exit 0) and refused the thin-lens layout (exit 65,
`PHASE_UNDEFINED_IDEAL_LENS`). `run_quantum.py` with `quantum_inputs.json`, Perceval
(`perceval-quandela`) 1.3.1 with exqalibur 1.4.2, Piquasso 8.0.1 with numba 0.68.0.
Outcome `WITHIN_TOLERANCE`. Quantum inputs: one photon per source in V; Gaussian wavepackets with
rms intensity duration 0.25 ps (HOM) or 1000 ps (MZI), zero-delay indistinguishability
0.95; threshold detectors with efficiency 0.8 and dark-count probability 0 (0.01 in
`hom_dark_counts` and in the lossy `mzi_t1_dark_counts`).

| Case | Lossless | Relative group delay (ps) | p | Perceval P_cc | Piquasso P_cc | Reference P_cc |
| --- | --- | --- | --- | --- | --- | --- |
| hom | yes | 0 | 0.95 | 0.0160000000 | 0.0160000000 | 0.016 |
| hom_delay −0.3 mm | yes | +1.000692 | 0.017304 | 0.3144628079 | 0.3144628079 | 0.3144628081 |
| hom_delay −0.05 mm | yes | +0.166782 | 0.849967 | 0.0480107087 | 0.0480107087 | 0.0480107086 |
| hom_window_group (3 mm N-BK7) | no (column 0.918842) | −0.0000008 | 0.95 | 0.0147014644 | 0.0147014644 | 0.0147014644 |
| hom_window_phase | no | +0.163032 | 0.854182 | 0.0428747563 | 0.0428747563 | 0.0428747564 |
| mzi_t0 | yes | 0 | 0.95 | 0.6400000004 | 0.6400000004 | 0.64 |
| mzi_t1 (1 mm window) | no (0.958392) | 0 | 0.95 | 0.5378015355 | 0.5378014972 | 0.5378014954 |
| mzi_t1p0003 | no | 0 | 0.95 | 0.0162778350 | 0.0162778338 | 0.0162778342 |
| hom_dark_counts | yes | 0 | 0.95 | 0.0254440000 | 0.0254440000 | 0.025444 |
| mzi_t1_dark_counts | no (0.958392) | 0 | 0.95 | 0.5418743177 | 0.5418742791 | 0.5418742773 |
| mzi_t1_broadband (0.25 ps photons) | refused `SINGLE_FREQUENCY_MODEL_INVALID`: group-delay spread 1.83 ps between the arms | | | | | |

Over all 21 evaluated cases: Perceval vs reference 4.0e-8, Piquasso vs reference 1.8e-9
(tolerance 1e-6), relative delay vs reference 4e-10 ps (tolerance 1e-4 ps). Every path
carried the exported `group_delay_ps`; it agreed with the group delay computed from the
Project's declared Sellmeier glass to 1.3e-9 ps (tolerance 1e-4 ps). The
13-point delay scan (−1.0 … +1.0 ps) gave a dip visibility of 0.94912 with Perceval
and 0.94912 for the reference (0.95 at unlimited delay range). The export's phase delay
of the `hom_window_phase` case is 0 while its pair group delay is 0.163032 ps, which
lowers p from 0.95 to 0.854; in `hom_window_group` the phase delay is −0.163 ps and the
exported pair group delay −8.3e-7 ps, so the photons stay at p = 0.95. Perceval took about 1 ms per case; Piquasso's first case included
38 s of just-in-time compilation.

The closed-form photon-number distribution is checked in `tests/test_interop.py` against an
explicit unitary completion of each lossy matrix (agreement 1e-12, probabilities sum to 1).

Licenses as reported upstream (package metadata, 2026-10-15): perceval-quandela MIT;
exqalibur CC BY-NC-ND 4.0; piquasso Apache-2.0.

## Metasurface lens as a virtual focusing component

`step1_unit_cells.py` (grcwa 0.1.2; 855 solves at 101 orders in 214 s for 19
wavelengths, 225 solves at 201 orders in 393 s for 490/515/532/545/580 nm, one BLAS
thread per process; |R + T − 1| ≤ 9e-13), `step2_focusing.py` (1024 and 2048 samples,
0.325 µm cells, 333 µm and 666 µm windows), `step3_fit_model.py` (with Engine runs for
the field-angle calibration), `step4_engine_check.py` (tabulated model) and
`step4_engine_check.py --model per-wavelength-ideal`. Outcome `WITHIN_TOLERANCE` for both
step-4 modes. The unit-cell library SHA-256 recorded as `source_data_sha256` was
`374ca765da99f17ee30babd1f1b4dba476cdca86e9e13649313c98940b861a5f`; it changes with
the platform's floating-point results, so each run records its own.

The external results are split into a table set (model rows), a calibration set (error
bounds and domain) and a test set (only the final check). External focus (101 orders,
1024 samples) and the Engine's deviation with the tabulated model:

| Case | Set | External focus (µm) | Engine focus error (µm) | External spot radius (µm) | Engine spot error | External efficiency | Engine power error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 490 nm | table | 216.868 | 0.000 | 1.217 | −7.3 % | 0.676 | 0.0 % |
| 495 nm | calibration | 214.792 | −0.216 | 1.189 | −5.1 % | 0.693 | −5.4 % |
| 505 nm | test | 210.458 | −0.094 | 1.169 | −3.5 % | 0.644 | +7.3 % |
| 515 nm | calibration | 206.086 | +0.168 | 1.163 | −3.0 % | 0.710 | +9.7 % |
| 525 nm | calibration | 201.966 | +0.102 | 1.177 | −4.3 % | 0.897 | −3.0 % |
| 532 nm | table | 199.263 | 0.000 | 1.174 | −4.1 % | 0.952 | 0.0 % |
| 535 nm | test | 198.224 | −0.179 | 1.172 | −4.0 % | 0.906 | +0.8 % |
| 545 nm | calibration | 194.630 | −0.119 | 1.174 | −4.1 % | 0.701 | +15.9 % |
| 555 nm | test | 191.019 | −0.042 | 1.175 | −4.2 % | 0.747 | +4.8 % |
| 565 nm | calibration | 187.190 | +0.296 | 1.175 | −4.3 % | 0.814 | −3.8 % |
| 575 nm | test | 184.329 | +0.315 | 1.178 | −4.3 % | 0.834 | −3.6 % |
| 580 nm | table | 183.315 | 0.000 | 1.189 | −5.0 % | 0.831 | 0.0 % |
| 532 nm, 20 µm beam | calibration | 198.212 | −0.083 | 1.694 | −0.6 % | 0.955 | 0.0 % |
| 545 nm, 25 µm beam | test | 193.991 | +0.226 | 1.372 | −1.6 % | 0.705 | +15.7 % |

External numerical spread over 101/201 orders and 1024/2048 samples (490, 515, 532,
545, 580 nm and the angle and beam-size cases): focus position 0.50 % (largest at
580 nm), spot radius 0.71 %, efficiency 0.015. Error bounds from the calibration set
plus that spread: focus position ±1.4 µm, spot radius ±8.1 %, delivered power ±19 %.
All test cases stay inside them (largest: focus 0.32 µm, spot −5.8 % at 1.5°, power
+15.7 %). Validated domain: 490–580 nm, field angle ≤ 2°, input beam radius ≤ 30 µm
(calibrated at 20 and 30 µm, tested at 25 µm), x polarization.

Field angles at 532 nm, Engine (tabulated model) against external; the angle domain was
set from these calibration runs, and 1.5° at 555 nm is the test case:

| Field angle | External axial / lateral focus (µm) | Engine axial / lateral (µm) | Engine spot error | Inside the bounds |
| --- | --- | --- | --- | --- |
| 1.5° (555 nm, test) | 191.030 / 5.20 | 190.977 / 5.00 | −5.8 % | yes |
| 2° | 199.496 / 7.15 | 199.262 / 6.96 | −5.2 % | yes |
| 5° | 197.702 / 17.55 | 199.260 / 17.43 | −7.5 % | no (axial 1.56 µm) |
| 8° | 195.887 / 27.95 | 199.257 / 28.00 | −13.4 % | no |
| 20° | 183.669 / 66.95 | 199.225 / 72.51 | −40.6 % | no |

Engine runs with the `TABULATED_THIN_LENS` model: every in-domain run (table,
calibration and test cases, 2° and 1.5°) was `WARNING`: `GAUSSIAN_TRUNCATION` for the 30 µm beam
(the 100 µm aperture clips 0.4 % of it), and the waist target's Gaussian state for the 20 µm and 25 µm beam cases, and the Engine reproduced the model's
thin-lens prediction to 5e-16. One Project with all 19 wavelengths as spectral lines of
one source, with one waist-radius target per line, ran with `WARNING` and gave the same
per-line results (5e-16). The power not delivered into the
focus appears in the power budget as the `UNMODELLED_RESPONSE` sink of the element (for
example 0.184 mW of 1 mW at 545 nm). Counterexamples, all `OUT_OF_MODEL_SCOPE`: 450 nm
with `MODEL_WAVELENGTH_OUTSIDE_BAND`; 5°, 8° and 20° with `MODEL_FIELD_ANGLE_EXCEEDED`;
a `peak_irradiance_W_per_mm2` target through the element with
`METRIC_NOT_VALIDATED_FOR_ELEMENT` and no value.

With one `IDEAL_THIN_LENS` per wavelength (`--model per-wavelength-ideal`) the in-domain
numbers are the same within 3.8e-7 (decimal rounding of the per-line focal lengths),
450 nm is out of scope through the lens's valid band, and the 5°, 8° and 20° inputs
return `WARNING`: that model kind cannot state a field-angle domain.

The model states `max_beam_radius_mm` 0.03, the validated 30 µm radius itself. The
Engine compares beam radius and field angle with their limits with a rounding tolerance,
so the 30 µm beam, which reaches the element with a computed radius of
0.030000000000000002 mm at some wavelengths, stays inside the domain at every
wavelength.

## Scope of these checks

The references are independent of the exported data they check: an ABCD calculation,
a Hankel integral, closed-form two-photon interference with catalogue Sellmeier
coefficients, and external electromagnetic results at wavelengths, angles and beam
sizes the model was not built from. Agreement within the stated tolerances shows that
the exports and conventions are read correctly and that the Engine reproduces the
declared model; it does not extend the Engine's physics (diffraction, photon
statistics, metasurface full-wave response) beyond what the documentation states.
