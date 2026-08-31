# Solaris PM Automation

![Python Test](https://github.com/hritheqal/solaris-pm-automation/actions/workflows/test.yml/badge.svg)

A Python-based automation tool for analyzing Solaris / SPARC Preventive Maintenance (PM) reports.

This project uses a Bash collector script to collect read-only Solaris PM command outputs, then analyzes the generated TXT report using Python. The analyzer produces a clean Markdown checklist, JSON findings evidence, human-readable explanation report, per-server HTML dashboard, multi-server HTML index dashboard, and CSV summary.

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

## Features

- Bash collector for Solaris / SPARC PM checks
- Section-based Python parser for structured PM TXT reports
- Generates Markdown checklist per server
- Generates JSON findings with evidence
- Generates human-readable explanation report
- Generates per-server HTML dashboard report for browser-based PM review
- Generates multi-server HTML index dashboard for all analyzed reports
- Generates summary CSV for single or multiple servers
- Supports one-file or folder-based analysis
- Uses safe sample input and output for portfolio demonstration
- Excludes real client/server PM data through `.gitignore`
- PDF PM checklist report export

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
├── scripts/
│   └── Solaris_PM.sh
├── src/
│   ├── solaris_pm.py
│   └── debug_sections.py
├── sample_data/
│   └── sample_solaris_pm_report.txt
├── sample_output/
│   ├── index.html
│   ├── sample_solaris_pm_report_checklist.md
│   ├── sample_solaris_pm_report_findings.json
│   ├── sample_solaris_pm_report_explanation.md
│   └── sample_solaris_pm_report_dashboard.html
├── inputs/
├── outputs/
├── reports/
└── backups/
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

Copy the generated `.txt` file into the local `inputs/` folder:

```text
inputs/CTC-CD01_PM_Report_20260828_090231.txt
```

### 3. Run Python Analyzer

Analyze one PM report:

```powershell
python src\solaris_pm.py inputs\CTC-CD01_PM_Report_20260828_090231.txt
```

Analyze all TXT reports inside `inputs/`:

```powershell
python src\solaris_pm.py inputs
```

Analyze the safe sample data:

```powershell
python src\solaris_pm.py sample_data
```

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

```powershell
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

## Important Security Note

Real client or server PM reports should not be committed to GitHub.

The following folders are ignored by `.gitignore`:

```text
inputs/
outputs/
backups/
```

This prevents accidental upload of real server data, serial numbers, logs, or customer information.

## GitHub Releases

Current release milestones:

```text
v1.0.0 - Initial Solaris PM collector and analyzer baseline
v1.1.0 - Added per-server HTML dashboard report
v1.1.1 - README documentation update
v1.2.0 - Added multi-server HTML index dashboard
v1.4.0 - Added PDF PM checklist report export
```

## Current Version

```text
v1.4.0
```

## Technologies Used

- Python 3
- Bash
- Solaris / SPARC command outputs
- Markdown
- JSON
- CSV
- HTML / CSS

## Future Improvements

Planned future improvements:

- Better multi-server dashboard filtering
- Dashboard search function
- PDF export
- Better rule engine for PM checks
- Configurable thresholds
- Chatbot-style PM explanation
- n8n workflow integration
- Web dashboard upload interface

## Project Status

This project is currently working as a local PM automation prototype.

Completed:

- Bash collector
- Python analyzer
- Markdown checklist
- JSON findings
- Explanation report
- Per-server HTML dashboard
- Multi-server HTML index dashboard
- CSV summary
- Safe sample data
- GitHub release tagging

## Author

Harith Haiqal

Solaris / SPARC PM automation portfolio project.