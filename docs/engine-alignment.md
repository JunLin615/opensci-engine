# Maintaining alignment with released engines

[engine-baseline.json](../engine-baseline.json) is the machine-readable record of
the verified PyPI engine release, test environment, catalog identity, CI Python
version and current documentation entry points. Current entry/install guides
reference it; historical validation reports retain their original versions.

These checks belong to this customer examples repository. They do not run in the
engine's private development repository, gate engine releases, or require the
engine to preserve obsolete example interfaces. Update examples and helpers when
released engine contracts change.

## Run a check

Use Python 3.11+ from the repository root. The runner needs only the standard
library; it creates its own virtual environment and installs the exact released
distribution from PyPI, even if another engine is already installed:

```bash
python scripts/check_alignment.py --out run-alignment
python scripts/check_alignment.py --candidate 0.6.1 --out run-candidate-061
python scripts/check_alignment.py --candidate latest --out run-candidate-latest
```

The first command uses the verified baseline. `latest` resolves the current
release from PyPI metadata and records the exact selected version. Every output
directory must be new, so repeated checks cannot overwrite earlier evidence.
Candidate checks never write `engine-baseline.json` or advance documentation pins.

The runner installs `opensci-engine[protected]` into `OUTPUT/.venv`, strips
`PYTHONPATH`/`PYTHONHOME`, disables user-site imports, and verifies the imported
engine is inside that environment. If `requirements-examples.txt` exists, it also
installs those workflow dependencies. Installed package versions, Python/platform
identity, installation logs and the engine module path remain in the evidence.

Checks cover documentation consistency, dependency consistency, offline unittest
discovery, ideal-lens passing/unmet/invalid cases, a fresh public catalog download,
the beam-summary integration check, and saved-result inspection. The integration
check accepts `--out` to keep generated files inside the check's output directory.
New helpers should add offline tests and, when needed, an explicit integration
command to the runner.

## Read the result

The command emits a compact JSON status and report path; exit `0` means all checks
passed and exit `1` means at least one check failed. An expected non-passing design
is a successful **check**: the strict ideal-lens case must report `FAIL` and exit
`1`, while invalid input must exit `4` with an error on stderr.

| Evidence | Contents |
| --- | --- |
| `report.json` | Requested/resolved/installed versions; each check's category, status, command, actual/expected exit code, diagnostic and log paths |
| `environment.json` | Installed engine version/location, Python executable/version and platform |
| `logs/` | Complete stdout/stderr for installation and every executed command, including dependency versions |
| `runs/` | Complete successful or non-passing example outputs and the beam comparison report |
| `.venv/`, `.catalog/` | Local execution environment and isolated catalog store; omitted from uploaded artifacts |

Produce a Markdown report without contacting GitHub:

```bash
python scripts/report_alignment.py run-alignment/report.json --summary run-alignment/summary.md
```

Failures are separated by cause:

- `package_api`: installation/import/dependency failures, changed APIs or output
  contracts, unit-test failures, or unexpected example outcomes. Inspect the
  command and stderr before changing the helper or expected result.
- `catalog_network`: explicit catalog availability/service-connectivity errors
  or a catalog-sync timeout. Catalog-dependent checks are marked `SKIPPED`;
  offline checks still run. This does not establish an engine regression.
- `catalog_data`: catalog schema/integrity/store errors or an engine upgrade
  requirement. Check the recorded catalog response and its release identity.
- `documentation`: current entry/install version pins or baseline references
  disagree with the machine record.
- `setup`: version discovery, environment creation or runner setup could not
  complete. Full report availability depends on the output directory being writable.

Unknown catalog command errors remain `package_api` until diagnosed; the report
does not infer connectivity failures from arbitrary error text. Catalog downloads
use an isolated store to expose availability failures. The previously cached
catalog may still support a separate local optical check, but that does not make
the fresh-download check pass. Retry after connectivity changes, using a new output
directory, and retain the failed report.

## CI and periodic reporting

The [Engine alignment workflow](../.github/workflows/engine-alignment.yml) checks
the verified baseline on repository pushes and pull requests. In Actions, choose
**Run workflow** to supply a candidate version or `latest`; a blank input checks
the baseline. A weekly Monday check at 05:23 UTC checks `latest`.

Each run writes a job summary and uploads `engine-alignment` artifacts for 30
days, including logs and generated example files even on failure. It excludes
virtual environments and catalog caches. Actions logs retain setup failures that
occur before the runner can create a report. Download evidence needed beyond the
artifact retention window before it expires.

Only the scheduled reporting job receives issue-write permission. It reads the
report with code from the scheduled default-branch commit, and creates an issue
for a new unverified release or a new failure pattern. The fingerprint combines
the resolved version, overall status and failed check names/categories. It ignores
temporary paths, timestamps and error wording, and searches open **and closed**
reports; unchanged observations create no comments or duplicate issues. A new
failed workflow/category on the same version creates a new report. Recovery to a
passing but still unverified version can also produce a distinct observation.
Manual/PR checks produce summaries and artifacts without posting issues.

## Complete an alignment update

1. Select an exact candidate and retain its report. Resolve package/API or data
   failures; investigate connectivity separately. Keep unsuccessful outcomes in
   the evidence rather than treating skipped checks as passed.
2. Update examples, helpers, documentation and expected results for the published
   API. Rerun the candidate check until the complete relevant workflow passes.
3. In one reviewed PR, update `engine-baseline.json` version and verified
   environment/evidence, all listed entry/install pins, and affected walkthroughs
   or expected outputs. The consistency check enforces the current pins together.
4. Run the baseline check from that revision, inspect the artifacts, then accept
   the new baseline. Close the corresponding version-specific observation issues
   when their work is accepted. Keep standing issues #1 and #2 open.

When retaining a prior reproducible snapshot is useful, tag its verified commit
and record its catalog identity/evidence before moving the default baseline. Keep
one supported baseline on the default branch; do not add historical compatibility
branches solely to avoid updating examples.

Initial validation evidence is recorded in [alignment validation](engine-alignment-validation.md).
