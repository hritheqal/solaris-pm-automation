from pathlib import Path
import csv
import json
import re
import sys


FILESYSTEM_THRESHOLD = 80


# ============================================================
# Basic file helpers
# ============================================================

def read_file(path):
    return Path(path).read_text(errors="ignore")


def normalize_key(value):
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def clean_output_line(output):
    for line in output.splitlines():
        clean_line = line.strip()

        if not clean_line:
            continue

        if set(clean_line) <= {"-"}:
            continue

        return clean_line

    return "Not captured"


def clean_section_output(output):
    cleaned_lines = []

    for line in output.splitlines():
        clean_line = line.strip()

        if not clean_line:
            continue

        if set(clean_line) <= {"-"}:
            continue

        cleaned_lines.append(clean_line)

    return "\n".join(cleaned_lines)


# ============================================================
# Section parser
# ============================================================

def extract_sections(text):
    sections = {}

    pattern = re.compile(
        r"Section\s*:\s*(.*?)\n"
        r"Command\s*:\s*(.*?)\n"
        r"Output\s*:\s*\n"
        r"(.*?)(?=\nSection\s*:|\Z)",
        re.IGNORECASE | re.DOTALL,
    )

    for match in pattern.finditer(text):
        section_name = match.group(1).strip()
        command = match.group(2).strip()
        output = clean_section_output(match.group(3).strip())

        normalized_name = normalize_key(section_name)

        sections[normalized_name] = {
            "name": section_name,
            "command": command,
            "output": output,
        }

    return sections


def get_section_output(sections, possible_names):
    for possible_name in possible_names:
        key = normalize_key(possible_name)

        if key in sections:
            return sections[key]["output"]

    for section_key, section_data in sections.items():
        for possible_name in possible_names:
            possible_key = normalize_key(possible_name)

            if possible_key in section_key:
                return section_data["output"]

    return ""


# ============================================================
# Inventory fields
# ============================================================

def get_hostname(sections):
    output = get_section_output(sections, ["Hostname"])
    return clean_output_line(output)


def get_date(sections):
    output = get_section_output(sections, ["Date"])
    return clean_output_line(output)


def get_uptime(sections):
    output = get_section_output(sections, ["Uptime"])
    return clean_output_line(output)


def detect_serial(text, sections):
    serial_output = get_section_output(sections, ["Serial Number"])
    serial_line = clean_output_line(serial_output)

    if serial_line != "Not captured":
        if "command not found" not in serial_line.lower():
            if re.fullmatch(r"[A-Z0-9\-]+", serial_line, re.IGNORECASE):
                return serial_line.strip()

    match = re.search(
        r"Chassis Serial Number\s*\n[-\s]*\n\s*([A-Z0-9\-]+)",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()

    match = re.search(r"Serial_Number\s*:\s*([A-Z0-9\-]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    match = re.search(r"serial\s*number\s*[:=]\s*([A-Z0-9\-]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return "Not captured"


def detect_model(text, sections):
    output = get_section_output(sections, ["Model", "System Model"])
    value = clean_output_line(output)

    if value != "Not captured":
        return value

    match = re.search(
        r"System Configuration:.*?(SPARC\s+[A-Z0-9\-]+)",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip().upper()

    match = re.search(r"Name\s*:\s*(SPARC\s+[A-Z0-9\-]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip().upper()

    match = re.search(r"model\s*=\s*(SPARC\s+[A-Z0-9\-]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip().upper()

    return "Not captured"


def detect_firmware(text, sections):
    output = get_section_output(sections, ["Firmware Version"])
    value = clean_output_line(output)

    if value != "Not captured":
        if "," in value:
            value = value.split(",")[0].strip()
        return value

    match = re.search(r"SP firmware\s+([0-9A-Za-z.\-_]+)", text, re.IGNORECASE)
    if match:
        return f"ILOM v{match.group(1)}"

    match = re.search(r"Sun System Firmware\s+([0-9A-Za-z.\-_]+)", text, re.IGNORECASE)
    if match:
        return f"ILOM v{match.group(1)}"

    return "Not captured"


def detect_os(text, sections):
    output = get_section_output(sections, ["OS Information"])
    value = clean_output_line(output)

    if value != "Not captured":
        return value

    match = re.search(r"SunOS.*?(11\.4\.[0-9.]+)", text)
    if match:
        return f"Oracle Solaris {match.group(1)}"

    if re.search(r"Oracle Solaris\s+11\.4", text, re.IGNORECASE):
        return "Oracle Solaris 11.4"

    return "Not captured"


# ============================================================
# Health checks
# ============================================================

def detect_disk_management_status(text, sections):
    output = get_section_output(sections, ["Disk Management"])

    if output:
        lower_output = output.lower()

        if "all pools are healthy" in lower_output:
            return "OK"

        if "no known data errors" in lower_output:
            return "OK"

        if re.search(r"\b(DEGRADED|FAULTED|UNAVAIL|OFFLINE|REMOVED)\b", output, re.IGNORECASE):
            return "Not OK"

        if "online" in lower_output:
            return "OK"

        return "Not captured"

    if re.search(r"errors:\s+No known data errors", text, re.IGNORECASE):
        return "OK"

    if re.search(r"\b(DEGRADED|FAULTED|UNAVAIL|OFFLINE|REMOVED)\b", text, re.IGNORECASE):
        return "Not OK"

    return "Not captured"


def detect_filesystem_status(sections):
    output = get_section_output(sections, ["Filesystem Status", "File System Status"])

    if not output:
        return "Not captured"

    lower_output = output.lower()

    if "all healthy" in lower_output:
        return "OK"

    percentages = re.findall(r"\((\d+)%\)|\b(\d+)%", output)
    found_percentage = False

    for pair in percentages:
        percent_text = pair[0] or pair[1]

        if not percent_text:
            continue

        found_percentage = True
        percent_value = int(percent_text)

        if percent_value >= FILESYSTEM_THRESHOLD:
            return "Not OK"

    if found_percentage:
        return "OK"

    if "needs cleaning" in lower_output:
        return "Not OK"

    return "OK"


def detect_syslog_status(sections):
    output = get_section_output(sections, ["System status from syslog", "System Status from Syslog"])

    if not output:
        return "Not captured"

    lower_output = output.lower().strip()

    if lower_output == "healthy":
        return "OK"

    issue_pattern = (
        r"\b(warning|fatal|crit)\b|"
        r"daemon\.error|"
        r"kern\.warning|"
        r"user\.error|"
        r"core dumped|"
        r"not registered with auto service request|"
        r"datalink does not exist|"
        r"authentication failed|"
        r"tx stall"
    )

    if re.search(issue_pattern, lower_output, re.IGNORECASE):
        return "Not OK"

    if "error" in lower_output:
        return "Not OK"

    return "OK"


def detect_fma_status(sections):
    output = get_section_output(sections, ["FMA Hardware Status", "FMA (Hardware Status)"])

    if not output:
        return "Not captured"

    lower_output = output.lower().strip()

    if lower_output == "healthy":
        return "OK"

    if "no faults" in lower_output:
        return "OK"

    if re.search(r"problem status\s*:\s*(open|isolated)", lower_output, re.IGNORECASE):
        return "Not OK"

    if re.search(r"\b(open|isolated)\b", lower_output) and "problem status" in lower_output:
        return "Not OK"

    return "OK"


def detect_services_status(sections):
    output = get_section_output(sections, ["Services"])

    if not output:
        return "Not captured"

    lower_output = output.lower().strip()

    if lower_output == "healthy":
        return "OK"

    if re.search(r"\b(maintenance|offline|disabled|not running)\b", lower_output, re.IGNORECASE):
        return "Not OK"

    return "OK"


def detect_hardware_diagnostic_status(text, sections):
    output = get_section_output(sections, ["Hardware Diagnostic", "Hardware diagnostic"])

    if output:
        lower_output = output.lower()

        if "picl_initialize failed" in lower_output:
            return "Not OK"

        if "prtdiag can only be run in the global zone" in lower_output:
            return "Not OK"

        if "system configuration:" in lower_output:
            return "OK"

        return "Not captured"

    if re.search(r"System Configuration:", text, re.IGNORECASE):
        return "OK"

    return "Not captured"


def detect_hard_disk_status(sections):
    output = get_section_output(sections, ["Hard disk device statistics", "Hard Disk Device Statistics"])

    if not output:
        return "Not captured"

    lower_output = output.lower().strip()

    if "not ok" in lower_output:
        return "Not OK"

    if lower_output.startswith("ok") or lower_output.startswith("all ok") or lower_output.startswith("healthy"):
        return "OK"

    hard_error = re.search(r"Hard Errors:\s*([0-9]+)", output, re.IGNORECASE)
    media_error = re.search(r"Media Error:\s*([0-9]+)", output, re.IGNORECASE)
    pfa_error = re.search(r"Predictive Failure Analysis:\s*([0-9]+)", output, re.IGNORECASE)

    if hard_error and int(hard_error.group(1)) > 0:
        return "Not OK"

    if media_error and int(media_error.group(1)) > 0:
        return "Not OK"

    if pfa_error and int(pfa_error.group(1)) > 0:
        return "Not OK"

    if hard_error or media_error or pfa_error:
        return "OK"

    return "Not captured"


def detect_hba_status(sections):
    output = get_section_output(sections, ["HBA Port Link Status"])

    if not output:
        return "Not captured"

    lower_output = output.lower().strip()

    if "not ok" in lower_output:
        return "Not OK"

    if lower_output.startswith("all ok") or lower_output.startswith("ok") or lower_output.startswith("healthy"):
        return "OK"

    if "not applicable" in lower_output:
        return "Not Applicable"

    if "no hba" in lower_output:
        return "Not Applicable"

    return "Not captured"


def detect_enclosure_status(sections):
    output = get_section_output(sections, ["Enclosure/Disk Status", "Enclosure Disk Status"])

    if not output:
        return "Not captured"

    lower_output = output.lower().strip()

    if "not ok" in lower_output:
        return "Not OK"

    if lower_output.startswith("all ok") or lower_output.startswith("ok") or lower_output.startswith("healthy"):
        return "OK"

    if "not applicable" in lower_output:
        return "Not Applicable"

    return "Not captured"


def detect_virtualization_status(text, sections):
    output = get_section_output(sections, ["Virtualization Check", "VM Health Check"])
    combined_text = text + "\n" + output

    has_ldom = False
    has_zone = False

    if re.search(r"\bprimary\s+active\b", combined_text, re.IGNORECASE):
        has_ldom = True

    if re.search(r"Virtualization_Type\s*:\s*logical-domain", combined_text, re.IGNORECASE):
        has_ldom = True

    for line in combined_text.splitlines():
        if re.search(r"\b\d+\s+\S+\s+running\b", line, re.IGNORECASE):
            if "global" not in line.lower():
                has_zone = True

    if has_ldom and has_zone:
        return "LDOM + Zone"

    if has_ldom:
        return "LDOM"

    if has_zone:
        return "Zone"

    if "non-virtualized" in combined_text.lower():
        return "Not Applicable"

    if "zoneadm list -cv" in combined_text.lower() and "global" in combined_text.lower():
        return "Not Applicable"

    return "Not captured"


def detect_vm_health_status(
    virtualization_status,
    fma_status,
    services_status,
    hardware_status,
    filesystem_status,
):
    if virtualization_status == "Not captured":
        return "Not captured"

    if virtualization_status == "Not Applicable":
        return "Not Applicable"

    if fma_status == "Not OK":
        return "Not OK"

    if services_status == "Not OK":
        return "Not OK"

    if hardware_status == "Not OK":
        return "Not OK"

    if filesystem_status == "Not OK":
        return "Not OK"

    return "OK"


# ============================================================
# Overall status
# ============================================================

def calculate_overall_status(row):
    check_columns = [
        "Disk Management Status",
        "System Status from Syslog",
        "Filesystem Status",
        "FMA Hardware Status",
        "Services",
        "Hardware Diagnostic",
        "Hard Disk Device Statistics",
        "HBA Port Link Status",
        "Enclosure/Disk Status",
        "VM Health Check",
    ]

    failed_checks = []

    for column in check_columns:
        status = row.get(column)

        if status == "Not OK":
            failed_checks.append(column)

    if failed_checks:
        return "Not OK", len(failed_checks), "; ".join(failed_checks)

    return "OK", 0, ""


# ============================================================
# Main row extraction
# ============================================================

def extract_statuses(text, input_file):
    sections = extract_sections(text)

    hostname = get_hostname(sections)
    report_date = get_date(sections)
    uptime = get_uptime(sections)

    serial = detect_serial(text, sections)
    model = detect_model(text, sections)
    firmware = detect_firmware(text, sections)
    os_info = detect_os(text, sections)

    disk_status = detect_disk_management_status(text, sections)
    syslog_status = detect_syslog_status(sections)
    filesystem_status = detect_filesystem_status(sections)
    fma_status = detect_fma_status(sections)
    services_status = detect_services_status(sections)
    hardware_status = detect_hardware_diagnostic_status(text, sections)
    hard_disk_status = detect_hard_disk_status(sections)
    hba_status = detect_hba_status(sections)
    enclosure_status = detect_enclosure_status(sections)

    virtualization_status = detect_virtualization_status(text, sections)

    vm_health_status = detect_vm_health_status(
        virtualization_status,
        fma_status,
        services_status,
        hardware_status,
        filesystem_status,
    )

    row = {
        "File": input_file.name,
        "Hostname": hostname,
        "Date": report_date,
        "Uptime": uptime,
        "Serial Number": serial,
        "Model": model,
        "Firmware Version": firmware,
        "OS Information": os_info,
        "Disk Management Status": disk_status,
        "System Status from Syslog": syslog_status,
        "Filesystem Status": filesystem_status,
        "FMA Hardware Status": fma_status,
        "Services": services_status,
        "Hardware Diagnostic": hardware_status,
        "Hard Disk Device Statistics": hard_disk_status,
        "HBA Port Link Status": hba_status,
        "Enclosure/Disk Status": enclosure_status,
        "Virtualization Check": virtualization_status,
        "VM Health Check": vm_health_status,
    }

    overall_status, failed_count, failed_checks = calculate_overall_status(row)

    row["Overall Status"] = overall_status
    row["Failed Check Count"] = failed_count
    row["Failed Checks"] = failed_checks

    return row


# ============================================================
# Markdown checklist
# ============================================================

def generate_checklist(row):
    report = f"""
# Solaris PM Checklist

| Check Item | Status |
|---|---|
| Hostname | {row["Hostname"]} |
| Date | {row["Date"]} |
| Uptime | {row["Uptime"]} |
| Serial Number | {row["Serial Number"]} |
| Model | {row["Model"]} |
| Firmware Version | {row["Firmware Version"]} |
| OS Information | {row["OS Information"]} |
| Disk Management Status | {row["Disk Management Status"]} |
| System Status from Syslog | {row["System Status from Syslog"]} |
| Filesystem Status | {row["Filesystem Status"]} |
| FMA Hardware Status | {row["FMA Hardware Status"]} |
| Services | {row["Services"]} |
| Hardware Diagnostic | {row["Hardware Diagnostic"]} |
| Hard Disk Device Statistics | {row["Hard Disk Device Statistics"]} |
| HBA Port Link Status | {row["HBA Port Link Status"]} |
| Enclosure/Disk Status | {row["Enclosure/Disk Status"]} |
| Virtualization Check | {row["Virtualization Check"]} |
| VM Health Check | {row["VM Health Check"]} |
| Overall Status | {row["Overall Status"]} |
"""

    return report.strip()


# ============================================================
# Findings JSON
# ============================================================

def add_section_finding(findings, section, status, evidence):
    finding = {
        "section": section,
        "status": status,
        "line": None,
        "evidence": evidence.strip(),
    }

    if finding not in findings:
        findings.append(finding)


def generate_findings(text):
    sections = extract_sections(text)
    findings = []

    disk_output = get_section_output(sections, ["Disk Management"])
    if detect_disk_management_status(text, sections) == "Not OK":
        add_section_finding(
            findings,
            "Disk Management Status",
            "Not OK",
            disk_output,
        )

    syslog_output = get_section_output(sections, ["System status from syslog", "System Status from Syslog"])
    if detect_syslog_status(sections) == "Not OK":
        for line in syslog_output.splitlines():
            clean_line = line.strip()
            if clean_line:
                add_section_finding(
                    findings,
                    "System Status from Syslog",
                    "Not OK",
                    clean_line,
                )

    filesystem_output = get_section_output(sections, ["Filesystem Status", "File System Status"])
    if detect_filesystem_status(sections) == "Not OK":
        for line in filesystem_output.splitlines():
            clean_line = line.strip()
            if clean_line:
                add_section_finding(
                    findings,
                    "Filesystem Status",
                    "Not OK",
                    clean_line,
                )

    fma_output = get_section_output(sections, ["FMA Hardware Status", "FMA (Hardware Status)"])
    if detect_fma_status(sections) == "Not OK":
        add_section_finding(
            findings,
            "FMA Hardware Status",
            "Not OK",
            fma_output,
        )

    services_output = get_section_output(sections, ["Services"])
    if detect_services_status(sections) == "Not OK":
        add_section_finding(
            findings,
            "Services",
            "Not OK",
            services_output,
        )

    hardware_output = get_section_output(sections, ["Hardware Diagnostic", "Hardware diagnostic"])
    if detect_hardware_diagnostic_status(text, sections) == "Not OK":
        add_section_finding(
            findings,
            "Hardware Diagnostic",
            "Not OK",
            hardware_output,
        )

    hard_disk_output = get_section_output(sections, ["Hard disk device statistics", "Hard Disk Device Statistics"])
    if detect_hard_disk_status(sections) == "Not OK":
        add_section_finding(
            findings,
            "Hard Disk Device Statistics",
            "Not OK",
            hard_disk_output,
        )

    hba_output = get_section_output(sections, ["HBA Port Link Status"])
    if detect_hba_status(sections) == "Not OK":
        add_section_finding(
            findings,
            "HBA Port Link Status",
            "Not OK",
            hba_output,
        )

    enclosure_output = get_section_output(sections, ["Enclosure/Disk Status", "Enclosure Disk Status"])
    if detect_enclosure_status(sections) == "Not OK":
        add_section_finding(
            findings,
            "Enclosure/Disk Status",
            "Not OK",
            enclosure_output,
        )

    return findings


# ============================================================
# Human-readable explanation report
# ============================================================

def generate_explanation_report(row, findings):
    hostname = row.get("Hostname", "Not captured")
    serial = row.get("Serial Number", "Not captured")
    model = row.get("Model", "Not captured")
    overall_status = row.get("Overall Status", "Not captured")
    failed_checks = row.get("Failed Checks", "")

    report_lines = []

    report_lines.append("# Solaris PM Finding Explanation")
    report_lines.append("")
    report_lines.append("## Server Summary")
    report_lines.append("")
    report_lines.append("| Item | Value |")
    report_lines.append("|---|---|")
    report_lines.append(f"| Hostname | {hostname} |")
    report_lines.append(f"| Serial Number | {serial} |")
    report_lines.append(f"| Model | {model} |")
    report_lines.append(f"| Overall Status | {overall_status} |")
    report_lines.append(f"| Failed Checks | {failed_checks if failed_checks else 'None'} |")
    report_lines.append("")

    if not findings:
        report_lines.append("## Findings")
        report_lines.append("")
        report_lines.append("No Not OK findings were detected from the PM report.")
        return "\n".join(report_lines)

    report_lines.append("## Findings")
    report_lines.append("")

    for index, finding in enumerate(findings, start=1):
        section = finding.get("section", "Unknown")
        status = finding.get("status", "Unknown")
        evidence = finding.get("evidence", "")
        lower_evidence = evidence.lower()

        possible_meaning = (
            "The PM analyzer detected this section as abnormal based on the collected command output."
        )
        recommended_action = (
            "Review the raw PM output and verify the condition manually."
        )

        if section == "System Status from Syslog":
            if "unexpected scsi sense data" in lower_evidence:
                possible_meaning = (
                    "The server reported unexpected SCSI SENSE data. "
                    "This may indicate a disk, disk firmware, controller firmware, "
                    "or compatibility-related storage warning."
                )
                recommended_action = (
                    "Check the affected disk or FRU mentioned in the log, verify iostat -En, "
                    "fmadm faulty, disk firmware, controller firmware, and monitor whether the warning repeats."
                )

            elif "kern.warning" in lower_evidence or "warning" in lower_evidence:
                possible_meaning = (
                    "The system log contains kernel warning messages. "
                    "This may indicate hardware, driver, storage, or OS-level warnings."
                )
                recommended_action = (
                    "Review the full dmesg/syslog context, identify the affected device, "
                    "and compare with fmadm faulty and iostat -En output."
                )

            elif "daemon.error" in lower_evidence or "error" in lower_evidence:
                possible_meaning = (
                    "The system log contains error messages. "
                    "This may indicate a service, hardware, or device-related issue."
                )
                recommended_action = (
                    "Review the exact error source and confirm whether it is current, repeated, or historical."
                )

        elif section == "Hard Disk Device Statistics":
            possible_meaning = (
                "Disk statistics reported a possible disk-level issue, such as hard errors, "
                "media errors, or predictive failure indicators."
            )
            recommended_action = (
                "Check iostat -En for the affected disk, confirm whether errors are increasing, "
                "check fmadm faulty, and prepare disk replacement if errors are persistent."
            )

        elif section == "HBA Port Link Status":
            if "not connected" in lower_evidence:
                possible_meaning = (
                    "One or more Fibre Channel HBA ports are not connected. "
                    "This can be normal if the server is not using SAN, but it is abnormal if SAN connectivity is expected."
                )
                recommended_action = (
                    "Confirm whether the server is supposed to use SAN. "
                    "If yes, check FC cable, SFP, switch port, zoning, and storage path status."
                )
            else:
                possible_meaning = "The HBA port check reported an abnormal status."
                recommended_action = (
                    "Check luxadm -e port, FC cabling, switch login status, zoning, and storage visibility."
                )

        elif section == "Disk Management Status":
            possible_meaning = "ZFS pool status reported an abnormal disk or pool condition."
            recommended_action = (
                "Run zpool status -xv, check affected vdev or disk, and verify whether the pool is degraded or faulted."
            )

        elif section == "Filesystem Status":
            possible_meaning = "One or more filesystems exceeded the configured usage threshold."
            recommended_action = (
                "Check df -h, identify large files or old logs, and clean up safely based on customer approval."
            )

        elif section == "FMA Hardware Status":
            possible_meaning = "Solaris Fault Management Architecture reported an active hardware fault."
            recommended_action = (
                "Run fmadm faulty, collect the fault UUID, identify the FRU, and raise hardware support ticket if required."
            )

        elif section == "Services":
            possible_meaning = "One or more Solaris services are not in a healthy state."
            recommended_action = (
                "Run svcs -xv, identify the affected service, review logs, and restart only after customer approval."
            )

        elif section == "Hardware Diagnostic":
            possible_meaning = "Hardware diagnostic output reported an issue or could not complete properly."
            recommended_action = (
                "Review prtdiag -v output and compare with FMA and ILOM hardware status."
            )

        elif section == "Enclosure/Disk Status":
            possible_meaning = "Disk enclosure or disk path status reported an abnormal condition."
            recommended_action = (
                "Check luxadm display/probe output, disk LEDs, enclosure status, and storage path health."
            )

        report_lines.append(f"### Finding {index}: {section}")
        report_lines.append("")
        report_lines.append(f"**Status:** {status}")
        report_lines.append("")
        report_lines.append("**Evidence:**")
        report_lines.append("")
        report_lines.append("```text")
        report_lines.append(evidence)
        report_lines.append("```")
        report_lines.append("")
        report_lines.append("**Possible Meaning:**")
        report_lines.append("")
        report_lines.append(possible_meaning)
        report_lines.append("")
        report_lines.append("**Recommended Action:**")
        report_lines.append("")
        report_lines.append(recommended_action)
        report_lines.append("")

    return "\n".join(report_lines)


# ============================================================
# CSV summary
# ============================================================

def write_summary_csv(rows):
    if not rows:
        return

    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    summary_path = output_dir / "summary.csv"
    fieldnames = list(rows[0].keys())

    with summary_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved summary to: {summary_path}")


# ============================================================
# File processing
# ============================================================

def process_file(input_file):
    text = read_file(input_file)

    row = extract_statuses(text, input_file)
    checklist = generate_checklist(row)
    findings = generate_findings(text)
    explanation = generate_explanation_report(row, findings)

    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    input_name = input_file.stem

    checklist_path = output_dir / f"{input_name}_checklist.md"
    findings_path = output_dir / f"{input_name}_findings.json"
    explanation_path = output_dir / f"{input_name}_explanation.md"

    checklist_path.write_text(checklist, encoding="utf-8")
    findings_path.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    explanation_path.write_text(explanation, encoding="utf-8")

    print(f"Processed: {input_file}")
    print(f"Saved checklist to: {checklist_path}")
    print(f"Saved findings to: {findings_path}")
    print(f"Saved explanation to: {explanation_path}")
    print()

    return row


# ============================================================
# Main
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python src/solaris_pm.py inputs/sample_raw_output.txt")
        print("  python src/solaris_pm.py inputs")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    summary_rows = []

    if input_path.is_file():
        summary_rows.append(process_file(input_path))

    elif input_path.is_dir():
        txt_files = sorted(input_path.glob("*.txt"))

        if not txt_files:
            print(f"No .txt files found in: {input_path}")
            sys.exit(1)

        for txt_file in txt_files:
            summary_rows.append(process_file(txt_file))

    else:
        print(f"Input path not found: {input_path}")
        sys.exit(1)

    write_summary_csv(summary_rows)


if __name__ == "__main__":
    main()