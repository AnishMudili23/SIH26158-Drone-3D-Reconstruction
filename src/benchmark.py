"""
Top-level Benchmark CLI module.

Usage:
    python -m src.benchmark --dataset zurich_mav --output-dir reports/benchmark
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add src to sys.path
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from evaluation.benchmark_runner import BenchmarkRunner


def main():
    parser = argparse.ArgumentParser(description="AeroMesh Independent Benchmark & Ablation CLI")
    parser.add_argument("--dataset", default="real_mission_01", help="Dataset name or path")
    parser.add_argument("--ground-truth", default=None, help="Path to ground truth trajectory or checkpoints")
    parser.add_argument("--output-dir", default="reports/benchmark", help="Directory to save benchmark reports")
    args = parser.parse_args()

    print("\n========================================================")
    print("  AeroMesh Independent Benchmark & Metric Validation    ")
    print(f"  Dataset: {args.dataset}")
    print("========================================================\n")

    runner = BenchmarkRunner(output_dir=args.output_dir)
    results = runner.run_ablations()
    paths = runner.export_reports(results)

    print(f"  [Output] Benchmark JSON: {paths['json']}")
    print(f"  [Output] Benchmark CSV:  {paths['csv']}")
    print(f"  [Output] Summary Table:  {paths['md']}\n")

    # Print summary table directly to console
    print(paths["md"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
