from pathlib import Path
import subprocess
import sys


def test_sample_report_generates_expected_outputs():
    project_root = Path(__file__).resolve().parents[1]

    sample_input = project_root / "sample_data" / "sample_solaris_pm_report.txt"
    script_path = project_root / "src" / "solaris_pm.py"
    output_dir = project_root / "outputs"

    result = subprocess.run(
        [sys.executable, str(script_path), str(sample_input)],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    expected_files = [
        output_dir / "sample_solaris_pm_report_checklist.md",
        output_dir / "sample_solaris_pm_report_findings.json",
        output_dir / "sample_solaris_pm_report_explanation.md",
        output_dir / "sample_solaris_pm_report_dashboard.html",
        output_dir / "sample_solaris_pm_report_pm_report.pdf",
        output_dir / "summary.csv",
        output_dir / "index.html",
    ]

    for file_path in expected_files:
        assert file_path.exists(), f"Missing expected output: {file_path}"

    checklist_text = (output_dir / "sample_solaris_pm_report_checklist.md").read_text(
        encoding="utf-8"
    )

    assert "Solaris PM Checklist" in checklist_text
    assert "DEMO-SERVER01" in checklist_text
    assert "Overall Status" in checklist_text