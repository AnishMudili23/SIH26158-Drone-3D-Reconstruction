"""
Unit tests for src/pipeline.py — Unified End-to-End Reconstruction Pipeline.
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pipeline import run_pipeline


def test_pipeline_raises_on_invalid_input(tmp_path):
    invalid_path = tmp_path / "nonexistent.mp4"
    out_dir = tmp_path / "out"

    with pytest.raises(ValueError, match="Need at least 3 frames"):
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()
        run_pipeline(input_path=empty_dir, output_dir=out_dir)


def test_pipeline_raises_on_unsupported_file_format(tmp_path):
    bad_file = tmp_path / "file.txt"
    bad_file.write_text("not a video")
    out_dir = tmp_path / "out"

    with pytest.raises(ValueError, match="Unsupported input"):
        run_pipeline(input_path=bad_file, output_dir=out_dir)
