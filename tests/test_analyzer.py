from pathlib import Path
import subprocess
import sys

from src.solaris_pm import (
    detect_enclosure_status,
    detect_filesystem_status,
    detect_fma_status,
    detect_hba_status,
    detect_syslog_status,
    extract_sections,
    extract_statuses,
    generate_findings,
    get_finding_remark,
    get_row_value,
    process_file,
)


def make_section(name, output, command="test command"):
    return f"""
Section : {name}
Command : {command}
Output  :
{output}

---------------------------------------------------------------------
"""


def make_report(*sections):
    return "Solaris / SPARC Preventive Maintenance Report\n" + "\n".join(sections)


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


def test_filesystem_threshold_detects_not_ok_and_ok():
    not_ok_sections = extract_sections(
        make_report(make_section("Filesystem Status", "/var :Needs Cleaning (85%)"))
    )
    ok_sections = extract_sections(
        make_report(make_section("Filesystem Status", "/export/home 72%"))
    )

    assert detect_filesystem_status(not_ok_sections) == "Not OK"
    assert detect_filesystem_status(ok_sections) == "OK"


def test_fault_warning_and_not_applicable_rules():
    syslog_sections = extract_sections(
        make_report(make_section("System status from syslog", "daemon.error Disk warning"))
    )
    fma_sections = extract_sections(
        make_report(make_section("FMA (Hardware Status)", "Problem Status : open"))
    )
    hba_sections = extract_sections(
        make_report(make_section("HBA Port Link Status", "No HBA adapter found"))
    )
    enclosure_sections = extract_sections(
        make_report(make_section("Enclosure/Disk Status", "Not OK\nDevice: c0t0d0"))
    )

    assert detect_syslog_status(syslog_sections) == "Not OK"
    assert detect_fma_status(fma_sections) == "Not OK"
    assert detect_hba_status(hba_sections) == "Not Applicable"
    assert detect_enclosure_status(enclosure_sections) == "Not OK"


def test_overall_status_counts_failed_checks():
    text = make_report(
        make_section("Hostname", "DEMO-SERVER01"),
        make_section("OS Information", "Oracle Solaris 11.4"),
        make_section("Disk Management", "all pools are healthy"),
        make_section("Filesystem Status", "/var :Needs Cleaning (88%)"),
        make_section("System status from syslog", "Healthy"),
        make_section("FMA (Hardware Status)", "Problem Status : open"),
        make_section("Services", "Healthy"),
        make_section("Hardware diagnostic", "System Configuration: Oracle Corporation sun4v SPARC T4-2"),
        make_section("Hard disk device statistics", "All OK"),
        make_section("HBA Port Link Status", "All OK"),
        make_section("Enclosure/Disk Status", "All OK"),
        make_section("Virtualization Check", "Not Applicable"),
    )

    row = extract_statuses(text, Path("demo.txt"))

    assert row["Overall Status"] == "Not OK"
    assert row["Failed Check Count"] == 2
    assert row["Failed Checks"] == "Filesystem Status; FMA Hardware Status"


def test_findings_include_actionable_evidence():
    text = make_report(
        make_section("System status from syslog", "daemon.error Disk reported unexpected SCSI SENSE data")
    )

    findings = generate_findings(text)

    assert findings == [
        {
            "section": "System Status from Syslog",
            "status": "Not OK",
            "line": None,
            "evidence": "daemon.error Disk reported unexpected SCSI SENSE data",
        }
    ]


def test_finding_remarks_match_normalized_check_names():
    findings = [
        {
            "section": "System Status from Syslog",
            "status": "Not OK",
            "line": None,
            "evidence": "daemon.error Disk warning",
        }
    ]

    assert get_finding_remark(findings, "Syslog") == "daemon.error Disk warning"


def test_process_file_can_write_to_custom_output_directory(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    sample_input = project_root / "sample_data" / "sample_solaris_pm_report.txt"
    output_dir = tmp_path / "session" / "run"

    row = process_file(sample_input, output_dir=output_dir)

    assert (output_dir / "sample_solaris_pm_report_checklist.md").exists()
    assert (output_dir / "sample_solaris_pm_report_findings.json").exists()
    assert (output_dir / "sample_solaris_pm_report_explanation.md").exists()
    assert (output_dir / "sample_solaris_pm_report_dashboard.html").exists()
    assert (output_dir / "sample_solaris_pm_report_pm_report.pdf").exists()
    assert get_row_value(row, ["OS Information", "OS Version", "OS"]) == "Oracle Solaris 11.4.93.221.2"
    assert get_row_value(row, ["Enclosure/Disk Status", "Enclosure", "Enclosure Status"]) == "OK"
