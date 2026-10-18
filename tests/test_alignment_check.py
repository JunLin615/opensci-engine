"""Offline checks of the release runner; no package installation or network use."""

import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import check_alignment as alignment


class ReleaseSelectionTests(unittest.TestCase):
    def test_only_exact_public_versions_are_accepted(self):
        for version in ("0.6.1", "1.0", "1.2.3rc1", "1.2.3.post2", "1.2.3.dev1"):
            with self.subTest(version=version):
                self.assertEqual(alignment.release_version(version), version)
        for value in (None, "", "latest", "0.6.*", ">=0.6.1", "0.6.1 --extra-index-url x",
                      "https://example.com/engine.whl", "../local", "0.6.1+private", "0.6.1\n"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                alignment.release_version(value)

    def test_latest_resolves_from_pypi_and_revalidates_the_response(self):
        with patch.object(alignment.urllib.request, "urlopen", return_value=io.StringIO(
            json.dumps({"info": {"version": "0.7.0"}})
        )) as request:
            self.assertEqual(alignment.latest_version(), "0.7.0")
        self.assertEqual(request.call_args.args[0].full_url, "https://pypi.org/pypi/opensci-engine/json")
        self.assertEqual(request.call_args.kwargs["timeout"], 30)
        with patch.object(alignment.urllib.request, "urlopen", return_value=io.StringIO(
            json.dumps({"info": {"version": "https://example.com/engine.whl"}})
        )), self.assertRaises(ValueError):
            alignment.latest_version()

    def test_catalog_classification_distinguishes_service_data_and_api_failures(self):
        for code, expected in (
            ("CATALOG_SERVICE_UNREACHABLE", "catalog_network"),
            ("CATALOG_NOT_AVAILABLE", "catalog_network"),
            ("CATALOG_HASH_MISMATCH", "catalog_data"),
            ("ENGINE_UPGRADE_REQUIRED", "catalog_data"),
            ("INVALID_INPUT", "package_api"), (None, "package_api"),
        ):
            with self.subTest(code=code):
                self.assertEqual(alignment.catalog_failure_category(json.dumps({"error": {"code": code}})), expected)
        for output in ("Traceback: incompatible API", "[]", "null", '{"error":null}'):
            with self.subTest(output=output):
                self.assertEqual(alignment.catalog_failure_category(output), "package_api")


class AlignmentRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repository"
        self.root.mkdir()
        self.out = Path(self.temporary.name) / "evidence"
        self.baseline = {"version": "0.6.1", "documentation": ["README.md", "installation.md"]}
        (self.root / "engine-baseline.json").write_text(json.dumps(self.baseline), encoding="utf-8")
        (self.root / "README.md").write_text(
            'Baseline **0.6.1**; see engine-baseline.json.\n', encoding="utf-8")
        (self.root / "installation.md").write_text(
            'pip install "opensci-engine[protected]==0.6.1"\nSee engine-baseline.json.\n', encoding="utf-8")

    def fake_processes(self, *, version="0.6.1", sync_error=None, beam_error=None):
        def run(command, **kwargs):
            code, stdout, stderr = 0, "", ""
            if "-c" in command and "engine_version" in command[-1]:
                stdout = json.dumps({"engine_version": version, "python": "test", "platform": "test",
                                     "executable": command[0], "module_path": str(
                                         Path(command[0]).parent.parent / "Lib" / "site-packages" /
                                         "opensci_engine" / "__init__.py")})
            elif command[-2:] == ["catalog", "sync"] and sync_error:
                code, stdout = 1, json.dumps({"error": {"code": sync_error, "message": "Catalog unavailable"}})
            elif "examples/ideal_lens_focus.py" in command:
                if "nan" in command:
                    code, stderr = 4, json.dumps({"error": {"code": "ValueError", "message": "Invalid bound"}})
                elif "0.001" in command:
                    code, stdout = 1, json.dumps({"status": "FAIL"})
                else:
                    stdout = json.dumps({"status": "PASS"})
            elif "tests.check_beam_summary" in command and beam_error:
                code, stderr = 1, beam_error
            elif "tests.check_beam_summary" in command or "examples/result_summary.py" in command:
                stdout = json.dumps({"status": "PASS"})
            return subprocess.CompletedProcess(command, code, stdout, stderr)
        return run

    def test_documentation_drift_is_a_failure_even_if_commands_succeed(self):
        (self.root / "README.md").write_text("Baseline **0.5.0**\n", encoding="utf-8")
        runner = alignment.AlignmentCheck(self.root, self.out)
        with patch.object(alignment.subprocess, "run", side_effect=self.fake_processes()):
            report = runner.run()
        check = next(row for row in report["checks"] if row["name"] == "baseline-documentation")
        self.assertEqual((report["status"], check["status"]), ("FAIL", "FAIL"))
        self.assertIn("0.5.0", check["error"])
        self.assertIn("missing reference", check["error"])
        self.assertTrue((self.out / "report.json").is_file())

    def test_candidate_uses_isolated_public_install_without_mutating_baseline(self):
        originals = {path.name: path.read_bytes() for path in self.root.iterdir()}
        with patch.dict(alignment.os.environ, {"PYTHONPATH": "private-engine", "PYTHONHOME": "private-runtime"}):
            runner = alignment.AlignmentCheck(self.root, self.out, "latest")
        with patch.object(alignment, "latest_version", return_value="0.7.0") as latest, \
             patch.object(alignment.subprocess, "run", side_effect=self.fake_processes(version="0.7.0")) as commands:
            report = runner.run()
        latest.assert_called_once_with()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual((report["baseline_version"], report["candidate_version"], report["installed_version"]),
                         ("0.6.1", "0.7.0", "0.7.0"))
        self.assertEqual(originals, {path.name: path.read_bytes() for path in self.root.iterdir()})
        install = next(call for call in commands.call_args_list if "install" in call.args[0])
        self.assertEqual(install.args[0][1:], ["-m", "pip", "--isolated", "install", "--no-compile",
                                             "--index-url", "https://pypi.org/simple", "opensci-engine[protected]==0.7.0"])
        self.assertTrue(Path(install.args[0][0]).is_relative_to(self.out / ".venv"))
        for call in commands.call_args_list:
            self.assertNotIn("PYTHONPATH", call.kwargs["env"])
            self.assertNotIn("PYTHONHOME", call.kwargs["env"])
            self.assertEqual(call.kwargs["env"]["PYTHONNOUSERSITE"], "1")
            self.assertNotIn("import opensci_engine._", " ".join(call.args[0]))
            self.assertNotIn("from opensci_engine._", " ".join(call.args[0]))
        scientific_failure = next(row for row in report["checks"] if row["name"] == "ideal-unmet-target")
        self.assertEqual((scientific_failure["status"], scientific_failure["exit_code"]), ("PASS", 1))
        self.assertEqual(json.loads(Path(scientific_failure["stdout"]).read_text())["status"], "FAIL")

    def test_catalog_failures_retain_evidence_and_skip_dependent_checks(self):
        for code, category in (("CATALOG_SERVICE_UNREACHABLE", "catalog_network"),
                               ("CATALOG_HASH_MISMATCH", "catalog_data"),
                               ("INVALID_INPUT", "package_api")):
            with self.subTest(code=code):
                runner = alignment.AlignmentCheck(self.root, self.out / code)
                with patch.object(alignment.subprocess, "run", side_effect=self.fake_processes(sync_error=code)) as commands:
                    report = runner.run()
                self.assertEqual(report["status"], "FAIL")
                checks = {row["name"]: row for row in report["checks"]}
                self.assertEqual(checks["catalog-sync"]["category"], category)
                self.assertEqual(checks["catalog-sync"]["exit_code"], 1)
                self.assertIn(code, Path(checks["catalog-sync"]["stdout"]).read_text())
                self.assertEqual(checks["beam-summary"]["status"], "SKIPPED")
                self.assertEqual(checks["saved-run-summary"]["status"], "SKIPPED")
                self.assertFalse(any("tests.check_beam_summary" in call.args[0] for call in commands.call_args_list))
                self.assertFalse(any("examples/result_summary.py" in call.args[0] for call in commands.call_args_list))
                self.assertEqual(json.loads((runner.out / "report.json").read_text())["status"], "FAIL")

    def test_beam_failure_after_successful_sync_preserves_catalog_or_api_category(self):
        for index, (diagnostic, category) in enumerate((
            (json.dumps({"code": "EXAMPLE_UNAVAILABLE", "message": "No compatible lens"}), "catalog_data"),
            (json.dumps({"problems": [{"code": "EXAMPLE_UNAVAILABLE", "message": "No compatible lens"}]}), "catalog_data"),
            ("Traceback (most recent call last):\nAssertionError: result fields changed", "package_api"),
        )):
            with self.subTest(category=category, diagnostic=diagnostic):
                runner = alignment.AlignmentCheck(self.root, self.out / f"beam-{index}")
                with patch.object(alignment.subprocess, "run", side_effect=self.fake_processes(beam_error=diagnostic)) as commands:
                    report = runner.run()
                checks = {row["name"]: row for row in report["checks"]}
                self.assertEqual(report["status"], "FAIL")
                self.assertEqual(checks["catalog-sync"]["status"], "PASS")
                self.assertEqual(checks["beam-summary"]["status"], "FAIL")
                self.assertEqual(checks["beam-summary"]["category"], category)
                self.assertEqual(Path(checks["beam-summary"]["stderr"]).read_text(), diagnostic)
                self.assertEqual(checks["saved-run-summary"]["status"], "SKIPPED")
                self.assertFalse(any("examples/result_summary.py" in call.args[0] for call in commands.call_args_list))

    def test_timeout_retains_partial_output_and_failure_report(self):
        runner = alignment.AlignmentCheck(self.root, self.out)
        timeout = subprocess.TimeoutExpired(["fake", "command"], 7, output=b"partial stdout", stderr=b"partial error")
        for name, catalog, category in (("slow-command", False, "package_api"),
                                        ("catalog-sync", True, "catalog_network"),
                                        ("beam-summary", True, "package_api")):
            with self.subTest(name=name), patch.object(alignment.subprocess, "run", side_effect=timeout):
                check = runner.command(name, category, ["fake", "command"], timeout=7, catalog=catalog)
                self.assertEqual(check["status"], "FAIL")
                self.assertEqual(check["category"], category)
                self.assertIsNone(check["exit_code"])
                self.assertIn("7s timeout", check["error"])
                self.assertEqual(Path(check["stdout"]).read_text(), "partial stdout")
                self.assertEqual(Path(check["stderr"]).read_text(), "partial error")
        runner.finish()
        self.assertEqual(json.loads((self.out / "report.json").read_text())["status"], "FAIL")

    def test_invalid_release_still_writes_report_without_running_commands(self):
        runner = alignment.AlignmentCheck(self.root, self.out, "../local-package")
        with patch.object(alignment.subprocess, "run") as command:
            report = runner.run()
        command.assert_not_called()
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["checks"][-1]["name"], "release-selection")
        self.assertEqual(json.loads((self.out / "report.json").read_text()), report)

    def test_wrong_installed_version_stops_before_running_examples(self):
        runner = alignment.AlignmentCheck(self.root, self.out, "0.7.0")
        with patch.object(alignment.subprocess, "run", side_effect=self.fake_processes(version="0.6.1")) as commands:
            report = runner.run()
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["checks"][-1]["name"], "installed-version-match")
        self.assertFalse(any("unittest" in call.args[0] for call in commands.call_args_list))

    def test_existing_output_is_rejected_without_touching_prior_evidence(self):
        self.out.mkdir()
        previous = self.out / "report.json"
        previous.write_text('{"status":"PASS","candidate":"older"}', encoding="utf-8")
        original = previous.read_bytes()
        with self.assertRaises(FileExistsError):
            alignment.AlignmentCheck(self.root, self.out)
        self.assertEqual(previous.read_bytes(), original)
        self.assertEqual(list(self.out.iterdir()), [previous])


if __name__ == "__main__":
    unittest.main()
