# Solaris PM Automation

A Python-based analyzer for Solaris / SPARC preventive maintenance reports.

This project collects Solaris PM command outputs using a Bash collector script, then analyzes the generated TXT report using Python. The analyzer produces a clean Markdown checklist, JSON findings evidence, and a CSV summary.

## Features

- Parses Solaris PM TXT reports generated from Bash collector
- Generates Markdown checklist per server
- Generates JSON findings with evidence
- Generates summary CSV for multiple servers
- Supports one-file or folder-based analysis
- Section-based parser for structured PM output
- Detects common PM checks:
  - Hostname
  - Serial Number
  - Model
  - Firmware Version
  - OS Information
  - Disk Management
  - Syslog / dmesg status
  - Filesystem usage
  - FMA hardware status
  - Services status
  - Hardware diagnostic
  - Hard disk statistics
  - HBA port link status
  - Enclosure / disk status
  - Virtualization status

## Folder Structure

```text
solaris-pm-automation/
├── src/
│   ├── solaris_pm.py
│   └── debug_sections.py
├── inputs/
├── outputs/
├── reports/
├── examples/
├── backups/
├── .gitignore
└── README.md