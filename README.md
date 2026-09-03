# Solaris PM Automation

![Python Test](https://github.com/hritheqal/solaris-pm-automation/actions/workflows/test.yml/badge.svg)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://solaris-pm-automation-v9s4i3yborzyggpzjihs7z.streamlit.app/)

A Python and Bash-based automation tool for analyzing Solaris / SPARC Preventive Maintenance (PM) reports.

This project uses a Bash collector script to collect read-only Solaris PM command outputs, then analyzes the generated TXT report using Python. The analyzer produces a Markdown checklist, JSON findings evidence, human-readable explanation report, per-server HTML dashboard, multi-server HTML index dashboard, CSV summary, and PDF PM checklist report.

The project also includes a Streamlit web upload interface for browser-based PM report analysis.

## Live Demo

Try the public Streamlit demo:

https://solaris-pm-automation-v9s4i3yborzyggpzjihs7z.streamlit.app/

Use the bundled sample report or sanitized PM output only. Do not upload real customer PM data, server serial numbers, or production logs.

## Project Purpose

The goal of this project is to reduce manual effort when reviewing Solaris / SPARC PM outputs.

Instead of manually checking long command outputs one by one, this tool helps generate structured reports showing:

- Server inventory details
- PM health checklist
- Failed checks
- Evidence from raw command output
- Human-readable explanation
- Per-server HTML dashboard
- Multi-server HTML index dashboard
- Summary CSV for multiple servers
- PDF PM checklist report

## Features

- Bash collector for Solaris / SPARC PM checks
- Section-based Python parser for structured PM TXT reports
- Generates Markdown checklist per server
- Generates JSON findings with evidence
- Generates human-readable explanation report
- Generates per-server HTML dashboard report
- Generates multi-server HTML index dashboard
- Generates summary CSV for single or multiple servers
- Generates PDF PM checklist report
- Streamlit web upload interface
- Download buttons for generated reports
- Supports one-file or folder-based analysis
- Uses safe sample input and output for portfolio demonstration
- Excludes real client/server PM data through `.gitignore`
- Automated testing using pytest and GitHub Actions

## PM Checks Covered

The analyzer currently supports the following checks:

- Hostname
- Date
- Uptime
- Serial Number
- Model
- Firmware Version
- OS Information
- Disk Management / ZFS pool status
- System status from syslog / dmesg
- Filesystem usage
- FMA hardware status
- Solaris services status
- Hardware diagnostic
- Hard disk device statistics
- HBA port link status
- Enclosure / disk status
- Virtualization status
- VM health status
- Overall status

## Folder Structure

```text
solaris-pm-automation/
├── README.md
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
├── app.py
├── scripts/
│   └── Solaris_PM.sh
├── src/
│   ├── solaris_pm.py
│   └── debug_sections.py
├── tests/
│   └── test_analyzer.py
├── sample_data/
│   └── sample_solaris_pm_report.txt
├── sample_output/
│   ├── index.html
│   ├── summary.csv
│   ├── sample_solaris_pm_report_checklist.md
│   ├── sample_solaris_pm_report_findings.json
│   ├── sample_solaris_pm_report_explanation.md
│   ├── sample_solaris_pm_report_dashboard.html
│   └── sample_solaris_pm_report_pm_report.pdf
├── inputs/
├── outputs/
├── web_uploads/
└── backups/
```

## Public Demo Readiness

The Streamlit app is suitable for public demo deployment with sanitized data.

- Visitors can run the bundled safe sample report without uploading anything.
- Uploaded or pasted files are isolated by browser session and run folder.
- Real customer PM reports, serial numbers, and production logs should not be uploaded to the public demo.
- `inputs/`, `outputs/`, `web_uploads/`, and `backups/` remain ignored by Git.

## Installation

Install runtime dependencies:

```bash
python -m pip install -r requirements.txt
```

Install development and test dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

## How It Works

### 1. Collect PM Output on Solaris Server

Run the Bash collector script on the Solaris / SPARC server:

```bash
chmod +x scripts/Solaris_PM.sh
./scripts/Solaris_PM.sh
```

The script generates:

```text
<HOSTNAME>_PM_Report_<TIMESTAMP>.txt
<HOSTNAME>_PM_Report_<TIMESTAMP>.csv
```

Example:

```text
CTC-CD01_PM_Report_20260828_090231.txt
CTC-CD01_PM_Report_20260828_090231.csv
```

### 2. Copy TXT Report to Analyzer Machine

Copy the generated .txt file into the local inputs/ folder:

```text
inputs/CTC-CD01_PM_Report_20260828_090231.txt
```

### 3. Run Python Analyzer

Analyze one PM report:

```bash
python src\solaris_pm.py inputs\CTC-CD01_PM_Report_20260828_090231.txt
```

Analyze all TXT reports inside inputs/:

```bash
python src\solaris_pm.py inputs
```

Analyze the safe sample data:

```bash
python src\solaris_pm.py sample_data
```

## Streamlit Web Upload Interface

This project includes a Streamlit web interface for uploading and analyzing Solaris PM TXT reports.

Run the web app:

```bash
streamlit run app.py
```

Then try the safe sample report, upload a sanitized Solaris PM .txt report, or paste sanitized raw PM output generated by:

```text
scripts/Solaris_PM.sh
```

The web interface generates downloadable outputs:

- Markdown checklist
- JSON findings
- Explanation report
- Server HTML dashboard
- Index HTML dashboard
- CSV summary
- PDF PM report

The Streamlit interface is useful for users who prefer browser-based upload instead of running the analyzer from the command line.

## Output Files

For each input file, the analyzer generates:

```text
outputs/<input_filename>_checklist.md
outputs/<input_filename>_findings.json
outputs/<input_filename>_explanation.md
outputs/<input_filename>_dashboard.html
outputs/<input_filename>_pm_report.pdf
```

It also generates:

```text
outputs/summary.csv
outputs/index.html
```

## Output Description

### Markdown Checklist

The checklist provides a clean PM status table.

Example:

```text
Hostname                       CTC-CD01
Serial Number                  1204BDY8E0
Model                          SPARC T4-2
Disk Management Status         OK
System Status from Syslog      Not OK
Filesystem Status              OK
FMA Hardware Status            OK
Overall Status                 Not OK
```

### Findings JSON

The JSON file stores raw evidence for abnormal findings.

Example:

```json
[
  {
    "section": "System Status from Syslog",
    "status": "Not OK",
    "line": null,
    "evidence": "Disk reported unexpected SCSI SENSE data to controller"
  }
]
```

### Explanation Report

The explanation report converts findings into a human-readable format.

It includes:

- Finding section
- Evidence
- Possible meaning
- Recommended action

### Per-Server HTML Dashboard

The analyzer generates an HTML dashboard for each PM report. It can be opened directly in a browser.

Example:

```powershell
start outputs\sample_solaris_pm_report_dashboard.html
```

The per-server dashboard shows:

- Server summary
- Overall status
- Health checklist
- Failed checks
- Findings evidence

### Multi-Server Index Dashboard

When multiple PM reports are analyzed together, the analyzer also generates a multi-server index dashboard:

```text
outputs/index.html
```

Example:

```powershell
start outputs\index.html
```

The multi-server dashboard shows:

- Total servers analyzed
- OK servers
- Not OK servers
- Hostname
- Serial number
- Model
- OS version
- Overall status
- Failed check count
- Failed checks
- Link to each individual server dashboard

### PDF PM Checklist Report

The analyzer generates a PDF PM checklist report:

```text
outputs/<input_filename>_pm_report.pdf
```

The PDF report includes:

- Server information
- Physical activities
- System health check
- Virtualization check
- Overall PM result

This is useful for PM submission, ticket attachment, or internal handover.

### Summary CSV

The summary CSV gives a high-level overview of all processed servers.

This is useful when multiple PM reports are analyzed together.

```text
outputs/summary.csv
```

## Sample Data

Safe sample data is provided for testing and portfolio demonstration:

```text
sample_data/sample_solaris_pm_report.txt
```

To test using sample data:

```bash
python src\solaris_pm.py sample_data
```

Then open the generated multi-server dashboard:

```powershell
start outputs\index.html
```

Or open the generated per-server dashboard:

```powershell
start outputs\sample_solaris_pm_report_dashboard.html
```

Or open the generated PDF report:

```powershell
start outputs\sample_solaris_pm_report_pm_report.pdf
```

## Testing

Run automated tests locally:

```bash
python -m pytest tests
```

GitHub Actions automatically runs the test workflow on push and pull request.

## Important Security Note

Real client or server PM reports should not be committed to GitHub.

The following folders are ignored by .gitignore:

```text
inputs/
outputs/
web_uploads/
backups/
```

This prevents accidental upload of real server data, serial numbers, logs, or customer information.

## GitHub Releases

Current release milestones:

- v1.0.0 - Initial Solaris PM collector and analyzer baseline
- v1.1.0 - Added per-server HTML dashboard report
- v1.1.1 - README documentation update
- v1.2.0 - Added multi-server HTML index dashboard
- v1.3.0 - Added automated analyzer test and GitHub Actions CI
- v1.3.1 - Added CI badge and development requirements
- v1.4.0 - Added PDF PM checklist report export
- v1.4.1 - Updated README for PDF export
- v1.4.2 - Updated sample output demo with PDF report
- v2.0.0 - Added Streamlit web upload interface
- v2.0.1 - Updated README for Streamlit web interface
- v2.1.0 - Prepared public demo workflow with sample run, isolated web outputs, and stronger analyzer tests

## Current Version

v2.1.0

## Technologies Used

- Python 3
- Bash
- Streamlit
- ReportLab
- pytest
- GitHub Actions
- Solaris / SPARC command outputs
- Markdown
- JSON
- CSV
- HTML / CSS
- PDF

## Future Improvements

Planned future improvements:

- Better multi-server dashboard filtering
- Dashboard search function
- Better rule engine for PM checks
- Chatbot-style PM explanation
- n8n workflow integration

## Project Status

This project is currently working as a local and browser-based PM automation prototype.

Completed:

Bash collector
Python analyzer
Markdown checklist
JSON findings
Explanation report
Per-server HTML dashboard
Multi-server HTML index dashboard
CSV summary
PDF PM checklist report
Streamlit web upload interface
Safe sample data
GitHub Actions CI
GitHub release tagging
Author

Harith Haiqal
