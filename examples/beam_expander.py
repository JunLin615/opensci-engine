"""Run a catalog-based beam expander and export its results.

运行目录中的扩束系统示例，并导出结果。
Usage / 用法: python examples/beam_expander.py --out run-example
"""

import argparse
import json
from pathlib import Path

from opensci_engine.local import (
    example_project_of_kind,
    run_optical_project,
    verify_run_artifacts,
)
from opensci_engine.results import load_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("run-example"))
    args = parser.parse_args()

    project = example_project_of_kind("beam_expander")
    run = run_optical_project(project, output_dir=args.out)
    problems = verify_run_artifacts(run.artifacts.directory)
    if problems:
        raise RuntimeError(f"Run verification: {problems}")

    results = load_run(args.out)
    csv_path = args.out.parent / f"{args.out.name}-arrivals.csv"
    csv_path.write_bytes(results.export("arrivals", "csv"))
    print(json.dumps({
        "status": run.status.value,
        "targets": [
            {"id": target.target_id, "status": target.status.value, "value": target.value}
            for target in run.result.targets
        ],
        "power_budget": results.power_budget(),
        "run_directory": str(args.out),
        "arrivals_csv": str(csv_path),
        "view_command": f'opensci-engine view "{args.out}"',
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
