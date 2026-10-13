"""Check examples against an isolated installation of a released PyPI engine.

python scripts/check_alignment.py --out run-alignment
python scripts/check_alignment.py --candidate latest --out run-candidate
"""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
VERSION = re.compile(r"\d+(?:\.\d+)+(?:a\d+|b\d+|rc\d+|\.post\d+|\.dev\d+)?")
NETWORK_CODES = {
    "CATALOG_SERVICE_UNREACHABLE", "CATALOG_NOT_AVAILABLE",
    "CATALOG_RELEASE_NOT_FOUND", "CATALOG_SYNC_UNAVAILABLE",
}
MODEL_CODES = {
    "OPTICAL_SKU_NOT_PUBLISHED", "SIMULATION_MODEL_AMBIGUOUS", "SIMULATION_MODEL_UNSUPPORTED",
    "PRODUCT_ROLE_MISMATCH", "SURFACE_COATING_REQUIRED", "EXAMPLE_UNAVAILABLE", "ENGINE_UPGRADE_REQUIRED",
}


def release_version(value):
    """Accept an exact public release number, never a URL or pip option."""
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise ValueError(f"Expected an exact PyPI version, got {value!r}")
    return value


def latest_version():
    request = urllib.request.Request(
        "https://pypi.org/pypi/opensci-engine/json", headers={"User-Agent": "opensci-engine-alignment"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return release_version(json.load(response)["info"]["version"])


def documentation_problems(root, baseline):
    """Check current entry/install pins; historical evidence keeps its original version."""
    problems = []
    expected = baseline["version"]
    for name in baseline["documentation"]:
        text = (root / name).read_text(encoding="utf-8")
        pins = re.findall(r"opensci-engine(?:\[protected\])?==([0-9][a-zA-Z0-9.]*)", text)
        pins += re.findall(r"\*\*(\d+\.\d+\.\d+)\*\*", text)
        if not pins or any(pin != expected for pin in pins):
            problems.append(f"{name}: version pins {pins!r} differ from baseline {expected}")
        if "engine-baseline.json" not in text:
            problems.append(f"{name}: missing reference to engine-baseline.json")
    return problems


def catalog_failure_category(stdout):
    """Classify explicit service/model errors; unknown CLI failures remain API failures."""
    try:
        document = json.loads(stdout)
        errors = [document.get("error", document), *document.get("problems", [])]
        codes = [error.get("code") for error in errors if isinstance(error, dict)]
    except (ValueError, AttributeError, TypeError):
        return "package_api"
    codes = [code for code in codes if isinstance(code, str)]
    if any(code in NETWORK_CODES for code in codes):
        return "catalog_network"
    if any(code.startswith("CATALOG_") or code in MODEL_CODES for code in codes):
        return "catalog_data"
    return "package_api"


class AlignmentCheck:
    def __init__(self, root, out, candidate=None):
        self.root = Path(root).resolve()
        self.out = Path(out).resolve()
        # Never overwrite a prior candidate's evidence or environment.
        self.out.mkdir(parents=True, exist_ok=False)
        (self.out / "logs").mkdir()
        self.env = dict(os.environ)
        for key in ("PYTHONPATH", "PYTHONHOME"):
            self.env.pop(key, None)
        self.env.update(PYTHONNOUSERSITE="1", PYTHONIOENCODING="utf-8",
                        PIP_DISABLE_PIP_VERSION_CHECK="1", MPLBACKEND="Agg",
                        OPENSCI_CATALOG_DIR=str(self.out / ".catalog"))
        self.report = {
            "schema_version": 1, "baseline_version": None,
            "requested_version": candidate or "baseline", "candidate_version": None,
            "installed_version": None, "status": "FAIL", "checks": [],
            "artifact_directory": str(self.out),
        }

    def record(self, name, category, status, command, *, error=None, **extra):
        entry = {"name": name, "category": category, "status": status,
                 "command": list(command), "exit_code": None,
                 "stdout": None, "stderr": None, "error": error, **extra}
        self.report["checks"].append(entry)
        return entry

    def command(self, name, category, command, *, expected_exit=0, result_status=None,
                json_error=False, timeout=180, catalog=False):
        stdout = self.out / "logs" / f"{name}.stdout.txt"
        stderr = self.out / "logs" / f"{name}.stderr.txt"
        code, error, output, diagnostic = None, None, "", ""
        timed_out = False
        try:
            process = subprocess.run(command, cwd=self.root, env=self.env, capture_output=True,
                                     text=True, encoding="utf-8", errors="replace", timeout=timeout)
            code, output, diagnostic = process.returncode, process.stdout, process.stderr
            if code != expected_exit:
                error = f"Expected exit {expected_exit}, received {code}"
            elif result_status is not None:
                document = json.loads(output)
                if document.get("status") != result_status:
                    error = f"Expected result {result_status}, received {document.get('status')!r}"
            elif json_error:
                if output.strip() or not json.loads(diagnostic).get("error"):
                    error = "Expected JSON error on stderr and empty stdout"
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            output = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            diagnostic = (exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            error = f"Command exceeded {timeout}s timeout"
        except (OSError, ValueError, AttributeError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        stdout.write_text(output, encoding="utf-8")
        stderr.write_text(diagnostic, encoding="utf-8")
        if catalog and error and not timed_out:
            category = catalog_failure_category(output)
            if category == "package_api":
                category = catalog_failure_category(diagnostic)
        if error:
            excerpt = (diagnostic.strip() or output.strip())[-1500:]
            if excerpt:
                error += f"\n{excerpt}"
        return self.record(name, category, "FAIL" if error else "PASS", command,
                           exit_code=code, expected_exit_code=expected_exit, error=error,
                           stdout=str(stdout), stderr=str(stderr), result_status=result_status)

    def finish(self):
        self.report["status"] = "FAIL" if any(c["status"] == "FAIL" for c in self.report["checks"]) else "PASS"
        (self.out / "report.json").write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        return self.report

    def run(self):
        try:
            self._run()
        except Exception as exc:
            self.record("alignment-runner", "setup", "FAIL", [], error=f"{type(exc).__name__}: {exc}")
        return self.finish()

    def _run(self):
        baseline = json.loads((self.root / "engine-baseline.json").read_text(encoding="utf-8"))
        baseline_version = release_version(baseline["version"])
        self.report["baseline_version"] = baseline_version
        problems = documentation_problems(self.root, baseline)
        self.record("baseline-documentation", "documentation", "FAIL" if problems else "PASS", [],
                    error="; ".join(problems) or None)
        requested = self.report["requested_version"]
        try:
            target = latest_version() if requested == "latest" else release_version(
                baseline_version if requested == "baseline" else requested)
            self.report["candidate_version"] = target
            self.record("release-selection", "setup", "PASS", [], resolved_version=target)
        except Exception as exc:
            self.record("release-selection", "setup", "FAIL", [], error=f"{type(exc).__name__}: {exc}")
            return
        venv = self.out / ".venv"
        if self.command("create-environment", "setup", [sys.executable, "-m", "venv", str(venv)], timeout=180)["status"] == "FAIL":
            return
        python = str(venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
        install = [python, "-m", "pip", "--isolated", "install", "--no-compile", "--index-url",
                   "https://pypi.org/simple", f"opensci-engine[protected]=={target}"]
        if self.command("install-engine", "package_api", install, timeout=600)["status"] == "FAIL":
            return
        requirements = self.root / "requirements-examples.txt"
        if requirements.exists():
            dependencies = [python, "-m", "pip", "--isolated", "install", "--no-compile", "--index-url",
                            "https://pypi.org/simple", "-r", str(requirements)]
            if self.command("install-example-dependencies", "package_api", dependencies, timeout=600)["status"] == "FAIL":
                return
        identity = self.command("installed-environment", "package_api", [python, "-c",
            "import json,platform,sys,opensci_engine; from importlib.metadata import version; "
            "print(json.dumps({'engine_version':version('opensci-engine'),'python':sys.version,"
            "'platform':platform.platform(),'executable':sys.executable,'module_path':opensci_engine.__file__}))"])
        if identity["status"] == "FAIL":
            return
        info = json.loads(Path(identity["stdout"]).read_text(encoding="utf-8"))
        self.report["installed_version"] = info["engine_version"]
        (self.out / "environment.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
        if info["engine_version"] != target:
            self.record("installed-version-match", "package_api", "FAIL", [],
                        error=f"Expected {target}, installed {info['engine_version']}")
            return
        if not Path(info["module_path"]).resolve().is_relative_to(venv.resolve()):
            self.record("installed-package-location", "package_api", "FAIL", [],
                        error=f"Engine loaded outside isolated environment: {info['module_path']}")
            return
        self.command("installed-packages", "package_api", [python, "-m", "pip", "freeze", "--all"])
        self.command("dependency-consistency", "package_api", [python, "-m", "pip", "check"])
        self.command("offline-tests", "package_api", [python, "-m", "unittest", "discover", "-s", "tests", "-v"], timeout=300)
        runs = self.out / "runs"
        self.command("ideal-pass", "package_api", [python, "examples/ideal_lens_focus.py", "--out", str(runs / "ideal-pass")],
                     result_status="PASS")
        self.command("ideal-unmet-target", "package_api", [python, "examples/ideal_lens_focus.py", "--out", str(runs / "ideal-fail"),
                     "--maximum-radius-mm", "0.001"], expected_exit=1, result_status="FAIL")
        self.command("ideal-invalid-input", "package_api", [python, "examples/ideal_lens_focus.py", "--maximum-radius-mm", "nan"],
                     expected_exit=4, json_error=True)
        sync = self.command("catalog-sync", "catalog_network", [python, "-m", "opensci_engine", "catalog", "sync"],
                            catalog=True, timeout=180)
        if sync["status"] == "FAIL":
            for name in ("beam-summary", "saved-run-summary"):
                self.record(name, "catalog_data", "SKIPPED", [], error="Blocked by catalog-sync; see its error and category")
            return
        self.command("catalog-identity", "catalog_data", [python, "-m", "opensci_engine", "catalog", "status"])
        beam = self.command("beam-summary", "package_api", [python, "-m", "tests.check_beam_summary", "--out", str(runs / "beam")],
                            result_status="PASS", catalog=True)
        if beam["status"] == "PASS":
            self.command("saved-run-summary", "package_api", [python, "examples/result_summary.py", str(runs / "beam")],
                         result_status="PASS")
        else:
            self.record("saved-run-summary", "package_api", "SKIPPED", [], error="Blocked by beam-summary")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", help="Exact PyPI version or latest; never updates the verified baseline")
    parser.add_argument("--out", type=Path, default=Path("run-alignment"), help="New directory for reports, logs and runs")
    args = parser.parse_args(argv)
    try:
        report = AlignmentCheck(ROOT, args.out, args.candidate).run()
    except OSError as exc:
        parser.exit(1, f"Cannot create a fresh output directory: {exc}\n")
    print(json.dumps({"status": report["status"], "baseline_version": report["baseline_version"],
                      "installed_version": report["installed_version"],
                      "report": str(args.out / "report.json")}, separators=(",", ":")))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
