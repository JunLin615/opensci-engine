# Initial alignment-check validation

Validated on 2026-10-13 using Windows AMD64 and Python 3.13.5. The verified
engine baseline remains `0.6.1`; this work does not advance it.

## Offline checks

The complete suite passed **45 tests** in an isolated environment installed by
the runner from PyPI:

```powershell
.\run-alignment-initial\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Coverage includes the existing 15 result-summary tests, 11 release-runner tests,
and 19 reporting tests. The new tests exercise public-release selection,
installation isolation, unchanged baseline files, expected nonzero scientific
exits, retained timeout evidence, documentation drift, catalog/API error
classification, blocked checks, and duplicate reporting across open and closed
issues. Reporter HTTP operations use a fake transport; tests do not publish
issues. The workflow also passed `actionlint` 1.7.12 and `git diff --check`.

## Isolated released-package checks

Two checks created separate virtual environments and catalog stores:

```bash
python scripts/check_alignment.py --out run-alignment-initial
python scripts/check_alignment.py --candidate latest --out run-alignment-candidate
```

Both installed `opensci-engine[protected]==0.6.1` from PyPI successfully. The
candidate check resolved `latest` to `0.6.1`; its recorded engine module path was
inside its own `.venv/Lib/site-packages/opensci_engine/`. Dependency consistency,
offline tests, ideal-lens passing/unmet-target cases, and invalid-input handling
passed. The candidate run additionally recorded the complete installed-package
list. These runs preceded the last beam-error classification regression test;
the final 45-test suite above includes that test.

**Both complete alignment runs reported `FAIL`**, because fresh catalog sync
returned `CATALOG_SERVICE_UNREACHABLE` for
`https://opensci-optic.com/api/v1/catalog`, with `WinError 10054` (connection reset
by the remote host). The reports classified this as `catalog_network` and marked
the beam and saved-summary checks `SKIPPED`. Complete diagnostics remained in
each output directory's `report.json` and `logs/`; failed scientific cases also
retained their generated artifacts. The Markdown reporter rendered the failed
report successfully. No baseline or documentation pins changed during either
check.

This establishes installation, offline/API checks and failure reporting on this
host, but does not establish fresh catalog availability or a complete passing
alignment run. Retry the fresh check after connectivity changes. CI uploads its
own evidence, including failed reports, rather than treating this limitation as
a passing result.

## Separate cached-catalog integration

Using the released package in the first runner-created environment, the beam
integration check passed with the previously cached catalog `2026-10-06.3`:

```powershell
.\run-alignment-initial\.venv\Scripts\python.exe -m tests.check_beam_summary --out run-alignment-cached-beam
```

The check confirmed that compact and detailed summaries preserve all expected
results, saved inspection does not rerun simulation, and saved artifact hashes
and modification times remain unchanged. For this run, compact output was
2,682 bytes versus 6,929 bytes for the original summary (4,691 bytes minified).
The result hash was
`6e3cda81604f7be4095a4e0458e6b7c440843d6ab91f79460883ea26f841e547`.
Byte counts depend on output-path length.

The cached check is independent evidence for the optical workflow; it does not
change the failed fresh-download reports. Generated `run-*` evidence is ignored
by Git. See [engine alignment](engine-alignment.md) for reproducible commands,
CI artifact retention, failure interpretation and baseline-update procedure.
