#!/usr/bin/bash

# ============================================================
# Solaris / SPARC Preventive Maintenance Collector
# Version: 1.1
# Purpose:
#   Collect read-only Solaris PM information and generate:
#   1. TXT report for Python analyzer
#   2. CSV summary for manual reference
#
# Important:
#   This script is read-only.
#   It does not modify system configuration.
# ============================================================

PATH=/usr/sbin:/usr/bin:/sbin:/bin:/usr/platform/$(uname -i)/sbin:/usr/local/bin
export PATH

HOSTNAME=$(hostname)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

TXT_FILE="${HOSTNAME}_PM_Report_${TIMESTAMP}.txt"
CSV_FILE="${HOSTNAME}_PM_Report_${TIMESTAMP}.csv"

FILESYSTEM_THRESHOLD=80


# ------------------------------------------------------------
# Utility function: CSV escaping
# ------------------------------------------------------------
csv_escape() {
    echo "$1" | sed 's/"/""/g'
}


# ------------------------------------------------------------
# Utility function: Run one PM check
# ------------------------------------------------------------
run_pm_check() {
    SECTION_NAME="$1"
    DISPLAY_COMMAND="$2"
    RUN_COMMAND="$3"

    if [ -z "$RUN_COMMAND" ]; then
        RUN_COMMAND="$DISPLAY_COMMAND"
    fi

    TMP_OUTPUT="/tmp/pm_check_${$}.out"

    echo "" >> "$TXT_FILE"
    echo "Section : $SECTION_NAME" >> "$TXT_FILE"
    echo "Command : $DISPLAY_COMMAND" >> "$TXT_FILE"
    echo "Output  :" >> "$TXT_FILE"

    eval "$RUN_COMMAND" > "$TMP_OUTPUT" 2>&1

    if [ ! -s "$TMP_OUTPUT" ]; then
        echo "Healthy" > "$TMP_OUTPUT"
    fi

    cat "$TMP_OUTPUT" >> "$TXT_FILE"

    echo "" >> "$TXT_FILE"
    echo "" >> "$TXT_FILE"
    echo "---------------------------------------------------------------------" >> "$TXT_FILE"

    SUMMARY_LINE=$(nawk 'NF {print; exit}' "$TMP_OUTPUT")

    ESC_SECTION=$(csv_escape "$SECTION_NAME")
    ESC_COMMAND=$(csv_escape "$DISPLAY_COMMAND")
    ESC_SUMMARY=$(csv_escape "$SUMMARY_LINE")

    echo "\"$ESC_SECTION\",\"$ESC_COMMAND\",\"$ESC_SUMMARY\"" >> "$CSV_FILE"

    rm -f "$TMP_OUTPUT"
}


# ------------------------------------------------------------
# Check: Model
# ------------------------------------------------------------
check_model() {
    MODEL=""

    if command -v ipmitool >/dev/null 2>&1; then
        MODEL=$(ipmitool sunoem cli 'show /System Model' 2>/dev/null | \
            nawk -F "=" '/model =/ {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}')
    fi

    if [ -z "$MODEL" ]; then
        MODEL=$(prtdiag -v 2>/dev/null | \
            nawk '/System Configuration:/ {
                for (i=1; i<=NF; i++) {
                    if ($i == "SPARC") {
                        print $i " " $(i+1)
                        exit
                    }
                }
            }')
    fi

    if [ -n "$MODEL" ]; then
        echo "$MODEL"
    else
        echo "Not captured"
    fi
}


# ------------------------------------------------------------
# Check: Uptime
# ------------------------------------------------------------
check_uptime() {
    UPTIME_VALUE=$(uptime | sed 's/.*up  *//' | cut -d',' -f1 | sed 's/^ *//;s/ *$//')

    if [ -n "$UPTIME_VALUE" ]; then
        echo "$UPTIME_VALUE"
    else
        uptime
    fi
}


# ------------------------------------------------------------
# Check: Serial Number
# Priority:
#   1. sneep
#   2. prtdiag chassis serial
# ------------------------------------------------------------
check_serial() {
    SERIAL=""

    if command -v sneep >/dev/null 2>&1; then
        SERIAL=$(sneep 2>/dev/null | nawk 'NF {print; exit}')
    fi

    if [ -z "$SERIAL" ]; then
        SERIAL=$(prtdiag -v 2>/dev/null | \
            nawk '
                /Chassis Serial Number/ {
                    found=1
                    next
                }

                found == 1 {
                    if ($0 ~ /^[- \t]*$/) {
                        next
                    }

                    if (NF > 0) {
                        print $1
                        exit
                    }
                }
            ')
    fi

    if [ -n "$SERIAL" ]; then
        echo "$SERIAL"
    else
        echo "Not captured"
    fi
}


# ------------------------------------------------------------
# Check: Firmware Version
# Priority:
#   1. ipmitool ILOM system_description
#   2. prtdiag Sun System Firmware
# ------------------------------------------------------------
check_firmware() {
    FIRMWARE=""

    if command -v ipmitool >/dev/null 2>&1; then
        FIRMWARE=$(ipmitool sunoem cli 'show /SP/ system_description' 2>/dev/null | \
            sed -n '/system_description/s/^[^,]*,//p' | \
            sed 's/^ *//;s/ *$//')
    fi

    if [ -z "$FIRMWARE" ]; then
        FIRMWARE=$(prtdiag -v 2>/dev/null | \
            nawk '
                /Sun System Firmware/ {
                    for (i=1; i<=NF; i++) {
                        if ($i ~ /^[0-9]+\./) {
                            print "ILOM v" $i
                            exit
                        }
                    }
                }
            ')
    fi

    if [ -n "$FIRMWARE" ]; then
        echo "$FIRMWARE"
    else
        echo "Not captured"
    fi
}


# ------------------------------------------------------------
# Check: OS Information
# ------------------------------------------------------------
check_os_info() {
    OS_INFO=""

    if command -v pkg >/dev/null 2>&1; then
        OS_INFO=$(pkg info entire 2>/dev/null | \
            nawk -F "[()]" '/Version/ {print $2; exit}')
    fi

    if [ -n "$OS_INFO" ]; then
        echo "$OS_INFO"
    else
        echo "Oracle Solaris $(uname -v)"
    fi
}


# ------------------------------------------------------------
# Check: Disk Management / ZFS Pool
# ------------------------------------------------------------
check_zpool() {
    if command -v zpool >/dev/null 2>&1; then
        zpool status -xv 2>&1
    else
        echo "Not Applicable"
    fi
}


# ------------------------------------------------------------
# Check: Filesystem Usage
# Threshold: 80%
# ------------------------------------------------------------
check_filesystem() {
    df -h | nawk -v threshold="$FILESYSTEM_THRESHOLD" '
        /%/ {
            cap=$(NF-1)
            sub(/%/, "", cap)

            if (cap + 0 >= threshold) {
                print $NF " :Needs Cleaning (" $(NF-1) ")"
                bad=1
            }
        }

        END {
            if (bad != 1) {
                print "All Healthy"
            }
        }
    '
}


# ------------------------------------------------------------
# Check: System Status from Syslog / dmesg
# ------------------------------------------------------------
check_syslog() {
    dmesg | egrep -i "warn|fatal|error|crit" || echo "Healthy"
}


# ------------------------------------------------------------
# Check: FMA Hardware Status
# Uses fmadm faulty for active/current faults.
# ------------------------------------------------------------
check_fma() {
    if command -v fmadm >/dev/null 2>&1; then
        FMA_OUTPUT=$(fmadm faulty 2>&1)

        if [ -n "$FMA_OUTPUT" ]; then
            echo "$FMA_OUTPUT"
        else
            echo "Healthy"
        fi
    else
        echo "Not captured"
    fi
}


# ------------------------------------------------------------
# Check: Services
# svcs -xv only prints problematic services.
# Blank output means healthy.
# ------------------------------------------------------------
check_services() {
    svcs -xv 2>/dev/null | nawk '
        {
            print
            found=1
        }

        END {
            if (found != 1) {
                print "Healthy"
            }
        }
    '
}


# ------------------------------------------------------------
# Check: Hardware Diagnostic
# ------------------------------------------------------------
check_prtdiag() {
    if command -v prtdiag >/dev/null 2>&1; then
        prtdiag -v 2>&1
    else
        echo "Not captured"
    fi
}


# ------------------------------------------------------------
# Check: Hard Disk Device Statistics
# Improved evidence:
#   If Not OK, print disk name and the exact iostat -En line.
# ------------------------------------------------------------
check_iostat() {
    if ! command -v iostat >/dev/null 2>&1; then
        echo "Not captured"
        return
    fi

    iostat -En 2>&1 | nawk '
        /^c[0-9]/ {
            disk=$1
        }

        /Hard Errors: [1-9][0-9]*/ {
            print "Not OK"
            print "Disk: " disk
            print $0
            bad=1
        }

        /Media Error: [1-9][0-9]*/ {
            print "Not OK"
            print "Disk: " disk
            print $0
            bad=1
        }

        /Predictive Failure Analysis: [1-9][0-9]*/ {
            print "Not OK"
            print "Disk: " disk
            print $0
            bad=1
        }

        END {
            if (bad != 1) {
                print "All OK"
            }
        }
    '
}


# ------------------------------------------------------------
# Check: HBA Port Link Status
# ------------------------------------------------------------
check_luxadm_port() {
    if ! command -v luxadm >/dev/null 2>&1; then
        echo "Not Applicable"
        return
    fi

    LUX_OUTPUT=$(luxadm -e port 2>&1)

    if [ -z "$LUX_OUTPUT" ]; then
        echo "Not Applicable"
        return
    fi

    echo "$LUX_OUTPUT" | egrep -i "not connected|offline|down|fail|fault|error" >/dev/null 2>&1

    if [ $? -eq 0 ]; then
        echo "Not OK"
        echo "$LUX_OUTPUT"
    else
        echo "All OK"
    fi
}


# ------------------------------------------------------------
# Check: Enclosure / Disk Status
# ------------------------------------------------------------
check_luxadm_display() {
    if ! command -v luxadm >/dev/null 2>&1; then
        echo "Not Applicable"
        return
    fi

    PROBE_OUTPUT=$(luxadm probe 2>&1)

    echo "$PROBE_OUTPUT" | egrep -i "not found|not available|error" >/dev/null 2>&1

    if [ $? -eq 0 ]; then
        echo "Not Applicable"
        return
    fi

    DEVICES=$(echo "$PROBE_OUTPUT" | nawk '/Logical Path:/ {print $3}')

    if [ -z "$DEVICES" ]; then
        echo "All OK"
        return
    fi

    BAD=0
    EVIDENCE_FILE="/tmp/luxadm_display_${$}.out"
    > "$EVIDENCE_FILE"

    for DEVICE in $DEVICES
    do
        DISPLAY_OUTPUT=$(luxadm display "$DEVICE" 2>&1)

        echo "$DISPLAY_OUTPUT" | egrep -i "fail|fault|offline|not connected|error" >/dev/null 2>&1

        if [ $? -eq 0 ]; then
            BAD=1
            echo "Device: $DEVICE" >> "$EVIDENCE_FILE"
            echo "$DISPLAY_OUTPUT" >> "$EVIDENCE_FILE"
            echo "" >> "$EVIDENCE_FILE"
        fi
    done

    if [ "$BAD" -eq 1 ]; then
        echo "Not OK"
        cat "$EVIDENCE_FILE"
    else
        echo "All OK"
    fi

    rm -f "$EVIDENCE_FILE"
}


# ------------------------------------------------------------
# Check: Virtualization
# Captures LDOM and Solaris Zone information if available.
# ------------------------------------------------------------
check_virtualization() {
    PRINTED=0

    if command -v ldm >/dev/null 2>&1; then
        LDM_OUTPUT=$(ldm list 2>/dev/null)

        if [ -n "$LDM_OUTPUT" ]; then
            echo "$LDM_OUTPUT"
            PRINTED=1
        fi
    fi

    if command -v zoneadm >/dev/null 2>&1; then
        ZONE_OUTPUT=$(zoneadm list -cv 2>/dev/null)

        if [ -n "$ZONE_OUTPUT" ]; then
            echo "$ZONE_OUTPUT"
            PRINTED=1
        fi
    fi

    if [ "$PRINTED" -ne 1 ]; then
        echo "Not Applicable"
    fi
}


# ============================================================
# Start Report
# ============================================================

echo "Solaris / SPARC Preventive Maintenance Report" > "$TXT_FILE"
echo "Generated : $(date)" >> "$TXT_FILE"
echo "Hostname  : $HOSTNAME" >> "$TXT_FILE"
echo "" >> "$TXT_FILE"
echo "=====================================================================" >> "$TXT_FILE"

echo "\"Section\",\"Command\",\"Output Summary\"" > "$CSV_FILE"


# ============================================================
# PM Checks
# ============================================================

run_pm_check "Hostname" "hostname" "hostname"

run_pm_check "Model" "check_model" "check_model"

run_pm_check "Date" "date '+%d %b %Y'" "date '+%d %b %Y'"

run_pm_check "Uptime" "check_uptime" "check_uptime"

run_pm_check "Serial Number" "check_serial" "check_serial"

run_pm_check "Firmware Version" "check_firmware" "check_firmware"

run_pm_check "OS Information" "check_os_info" "check_os_info"

run_pm_check "Disk Management" "zpool status -xv" "check_zpool"

run_pm_check "Filesystem Status" "df -h usage check, threshold >= 80%" "check_filesystem"

run_pm_check "System status from syslog" "dmesg | egrep -i 'warn|fatal|error|crit'" "check_syslog"

run_pm_check "FMA (Hardware Status)" "fmadm faulty" "check_fma"

run_pm_check "Services" "svcs -xv" "check_services"

run_pm_check "Hardware diagnostic" "prtdiag -v" "check_prtdiag"

run_pm_check "Hard disk device statistics" "iostat -En error check" "check_iostat"

run_pm_check "HBA Port Link Status" "luxadm -e port" "check_luxadm_port"

run_pm_check "Enclosure/Disk Status" "luxadm probe/display" "check_luxadm_display"

run_pm_check "Virtualization Check" "ldm list and zoneadm list -cv" "check_virtualization"


# ============================================================
# End Report
# ============================================================

echo "" >> "$TXT_FILE"
echo "=====================================================================" >> "$TXT_FILE"
echo "Report completed: $(date)" >> "$TXT_FILE"

echo ""
echo "PM collection completed."
echo "TXT report generated: $TXT_FILE"
echo "CSV report generated: $CSV_FILE"
echo ""
echo "Copy the TXT file into your Python analyzer inputs folder."
