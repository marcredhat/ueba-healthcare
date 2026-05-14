#!/usr/bin/env python3
"""
Avelios Medical Sample Data Generator
=====================================
Generates BSI and NIS2 compliance-relevant events for the Avelios Medical
hospital information platform.

Event Categories (BSI/NIS2 relevant):
- Authentication events (login/logout, MFA, failed attempts)
- Patient data access (PHI/ePHI access logging)
- Administrative actions (user management, config changes)
- System health and availability monitoring
- Data export/transfer events
- Audit trail events
- Security incidents

Author: Marc Chisinevski
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Avelios-specific configuration
AVELIOS_MODULES = [
    "PatientAdmission",
    "ClinicalDocumentation", 
    "OrderEntry",
    "Pharmacy",
    "Laboratory",
    "Radiology",
    "Scheduling",
    "Billing",
    "ReportingAnalytics",
    "AdminConsole"
]

DEPARTMENTS = [
    "Emergency", "ICU", "Cardiology", "Oncology", "Pediatrics",
    "Surgery", "Radiology", "Laboratory", "Pharmacy", "Administration"
]

HOSPITALS = [
    {"id": "HOSP-001", "name": "Universitätsklinikum Berlin", "location": "Berlin"},
    {"id": "HOSP-002", "name": "Klinikum München", "location": "Munich"},
    {"id": "HOSP-003", "name": "Charité Hospital", "location": "Berlin"},
]

USERS = [
    {"id": "USR-001", "name": "Dr. Anna Schmidt", "role": "Physician", "department": "Cardiology"},
    {"id": "USR-002", "name": "Dr. Thomas Weber", "role": "Physician", "department": "Emergency"},
    {"id": "USR-003", "name": "Nurse Maria Müller", "role": "Nurse", "department": "ICU"},
    {"id": "USR-004", "name": "Admin Klaus Fischer", "role": "SystemAdmin", "department": "IT"},
    {"id": "USR-005", "name": "Dr. Lisa Bauer", "role": "Radiologist", "department": "Radiology"},
    {"id": "USR-006", "name": "Pharmacist Hans Meyer", "role": "Pharmacist", "department": "Pharmacy"},
    {"id": "USR-007", "name": "Lab Tech Sarah Koch", "role": "LabTechnician", "department": "Laboratory"},
    {"id": "USR-008", "name": "Billing Clerk Peter Wolf", "role": "BillingClerk", "department": "Administration"},
]

PATIENT_IDS = [f"PAT-{i:06d}" for i in range(1, 101)]

# BSI/NIS2 relevant event types
EVENT_TYPES = {
    "authentication": [
        "USER_LOGIN_SUCCESS",
        "USER_LOGIN_FAILURE", 
        "USER_LOGOUT",
        "MFA_CHALLENGE_SUCCESS",
        "MFA_CHALLENGE_FAILURE",
        "SESSION_TIMEOUT",
        "PASSWORD_CHANGE",
        "PASSWORD_RESET_REQUEST",
        "ACCOUNT_LOCKED",
        "ACCOUNT_UNLOCKED"
    ],
    "patient_access": [
        "PATIENT_RECORD_VIEW",
        "PATIENT_RECORD_CREATE",
        "PATIENT_RECORD_UPDATE",
        "PATIENT_RECORD_DELETE",
        "PATIENT_SEARCH",
        "CLINICAL_NOTE_ACCESS",
        "LAB_RESULT_VIEW",
        "MEDICATION_LIST_ACCESS",
        "IMAGING_STUDY_VIEW",
        "EMERGENCY_ACCESS_OVERRIDE"
    ],
    "administrative": [
        "USER_CREATED",
        "USER_MODIFIED",
        "USER_DELETED",
        "ROLE_ASSIGNED",
        "ROLE_REVOKED",
        "PERMISSION_CHANGED",
        "CONFIG_MODIFIED",
        "SYSTEM_SETTING_CHANGED",
        "AUDIT_LOG_EXPORT",
        "BACKUP_INITIATED"
    ],
    "data_transfer": [
        "DATA_EXPORT_INITIATED",
        "DATA_EXPORT_COMPLETED",
        "DATA_IMPORT_INITIATED",
        "DATA_IMPORT_COMPLETED",
        "HL7_MESSAGE_SENT",
        "HL7_MESSAGE_RECEIVED",
        "FHIR_API_REQUEST",
        "REPORT_GENERATED",
        "PRINT_JOB_SUBMITTED",
        "EMAIL_NOTIFICATION_SENT"
    ],
    "security": [
        "UNAUTHORIZED_ACCESS_ATTEMPT",
        "PRIVILEGE_ESCALATION_ATTEMPT",
        "SUSPICIOUS_ACTIVITY_DETECTED",
        "DATA_BREACH_ALERT",
        "MALWARE_DETECTED",
        "CERTIFICATE_EXPIRY_WARNING",
        "ENCRYPTION_KEY_ROTATION",
        "FIREWALL_RULE_TRIGGERED",
        "INTRUSION_DETECTED",
        "COMPLIANCE_VIOLATION"
    ],
    "system": [
        "SERVICE_STARTED",
        "SERVICE_STOPPED",
        "SERVICE_HEALTH_CHECK",
        "DATABASE_CONNECTION_POOL",
        "CACHE_CLEARED",
        "SCHEDULED_TASK_EXECUTED",
        "ERROR_THRESHOLD_EXCEEDED",
        "PERFORMANCE_DEGRADATION",
        "DISK_SPACE_WARNING",
        "MEMORY_THRESHOLD_ALERT"
    ]
}

SEVERITY_LEVELS = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

# Severity mapping for event types
SEVERITY_MAP = {
    "USER_LOGIN_SUCCESS": "INFO",
    "USER_LOGIN_FAILURE": "MEDIUM",
    "ACCOUNT_LOCKED": "HIGH",
    "PATIENT_RECORD_VIEW": "INFO",
    "EMERGENCY_ACCESS_OVERRIDE": "HIGH",
    "UNAUTHORIZED_ACCESS_ATTEMPT": "CRITICAL",
    "PRIVILEGE_ESCALATION_ATTEMPT": "CRITICAL",
    "DATA_BREACH_ALERT": "CRITICAL",
    "MALWARE_DETECTED": "CRITICAL",
    "INTRUSION_DETECTED": "CRITICAL",
    "COMPLIANCE_VIOLATION": "HIGH",
    "DATA_EXPORT_INITIATED": "MEDIUM",
    "AUDIT_LOG_EXPORT": "MEDIUM",
}


def generate_timestamp(base_time: datetime = None, offset_minutes: int = 0) -> str:
    """Generate ISO8601 timestamp."""
    if base_time is None:
        base_time = datetime.utcnow()
    ts = base_time - timedelta(minutes=offset_minutes)
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def generate_source_ip() -> str:
    """Generate realistic internal IP addresses."""
    networks = ["10.0", "172.16", "192.168"]
    network = random.choice(networks)
    if network == "10.0":
        return f"10.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
    elif network == "172.16":
        return f"172.{random.randint(16,31)}.{random.randint(1,254)}.{random.randint(1,254)}"
    else:
        return f"192.168.{random.randint(1,254)}.{random.randint(1,254)}"


def generate_authentication_event(base_time: datetime, offset: int) -> Dict[str, Any]:
    """Generate authentication-related events."""
    event_type = random.choice(EVENT_TYPES["authentication"])
    user = random.choice(USERS)
    hospital = random.choice(HOSPITALS)
    
    event = {
        "timestamp": generate_timestamp(base_time, offset),
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_category": "authentication",
        "severity": SEVERITY_MAP.get(event_type, "INFO"),
        "source": {
            "application": "Avelios Medical",
            "version": "8.5.2",
            "module": "AuthenticationService",
            "hostname": f"avelios-app-{random.randint(1,3):02d}.{hospital['location'].lower()}.local",
            "ip": generate_source_ip()
        },
        "actor": {
            "user_id": user["id"],
            "username": user["name"].lower().replace(" ", ".").replace("dr.", "").strip(),
            "display_name": user["name"],
            "role": user["role"],
            "department": user["department"]
        },
        "client": {
            "ip": generate_source_ip(),
            "user_agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/17.0",
                "AveliosMobile/3.2.1 (iOS 17.0)",
                "AveliosMobile/3.2.1 (Android 14)"
            ]),
            "device_type": random.choice(["Workstation", "Mobile", "Tablet", "Terminal"])
        },
        "organization": {
            "hospital_id": hospital["id"],
            "hospital_name": hospital["name"],
            "location": hospital["location"]
        },
        "outcome": "success" if "SUCCESS" in event_type or event_type in ["USER_LOGOUT", "SESSION_TIMEOUT", "PASSWORD_CHANGE"] else "failure",
        "details": {}
    }
    
    # Add event-specific details
    if event_type == "USER_LOGIN_FAILURE":
        event["details"]["failure_reason"] = random.choice([
            "Invalid password",
            "Account disabled",
            "IP not whitelisted",
            "Certificate expired"
        ])
        event["details"]["attempt_count"] = random.randint(1, 5)
    elif event_type == "MFA_CHALLENGE_SUCCESS":
        event["details"]["mfa_method"] = random.choice(["TOTP", "SMS", "Push", "Hardware Token"])
    elif event_type == "ACCOUNT_LOCKED":
        event["details"]["lock_reason"] = "Exceeded maximum login attempts"
        event["details"]["lock_duration_minutes"] = 30
    
    return event


def generate_patient_access_event(base_time: datetime, offset: int) -> Dict[str, Any]:
    """Generate patient data access events (PHI/ePHI)."""
    event_type = random.choice(EVENT_TYPES["patient_access"])
    user = random.choice(USERS)
    hospital = random.choice(HOSPITALS)
    patient_id = random.choice(PATIENT_IDS)
    
    event = {
        "timestamp": generate_timestamp(base_time, offset),
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_category": "patient_access",
        "severity": SEVERITY_MAP.get(event_type, "INFO"),
        "source": {
            "application": "Avelios Medical",
            "version": "8.5.2",
            "module": random.choice(AVELIOS_MODULES),
            "hostname": f"avelios-app-{random.randint(1,3):02d}.{hospital['location'].lower()}.local",
            "ip": generate_source_ip()
        },
        "actor": {
            "user_id": user["id"],
            "username": user["name"].lower().replace(" ", ".").replace("dr.", "").strip(),
            "display_name": user["name"],
            "role": user["role"],
            "department": user["department"]
        },
        "patient": {
            "patient_id": patient_id,
            "encounter_id": f"ENC-{random.randint(100000, 999999)}",
            "department": random.choice(DEPARTMENTS)
        },
        "organization": {
            "hospital_id": hospital["id"],
            "hospital_name": hospital["name"],
            "location": hospital["location"]
        },
        "outcome": "success",
        "details": {
            "access_reason": random.choice([
                "Treatment",
                "Consultation",
                "Emergency",
                "Administrative",
                "Quality Review"
            ])
        }
    }
    
    # Add event-specific details
    if event_type == "EMERGENCY_ACCESS_OVERRIDE":
        event["details"]["override_reason"] = "Emergency patient care"
        event["details"]["supervisor_notified"] = True
        event["severity"] = "HIGH"
    elif event_type == "PATIENT_RECORD_DELETE":
        event["details"]["deletion_reason"] = random.choice([
            "Patient request (GDPR)",
            "Data retention policy",
            "Duplicate record"
        ])
        event["details"]["approval_id"] = f"APR-{random.randint(10000, 99999)}"
    elif event_type in ["LAB_RESULT_VIEW", "IMAGING_STUDY_VIEW"]:
        event["details"]["study_type"] = random.choice([
            "Blood Panel", "CT Scan", "MRI", "X-Ray", "Ultrasound", "ECG"
        ])
    
    return event


def generate_administrative_event(base_time: datetime, offset: int) -> Dict[str, Any]:
    """Generate administrative/configuration events."""
    event_type = random.choice(EVENT_TYPES["administrative"])
    admin_user = [u for u in USERS if u["role"] == "SystemAdmin"][0]
    hospital = random.choice(HOSPITALS)
    
    event = {
        "timestamp": generate_timestamp(base_time, offset),
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_category": "administrative",
        "severity": SEVERITY_MAP.get(event_type, "MEDIUM"),
        "source": {
            "application": "Avelios Medical",
            "version": "8.5.2",
            "module": "AdminConsole",
            "hostname": f"avelios-admin-01.{hospital['location'].lower()}.local",
            "ip": generate_source_ip()
        },
        "actor": {
            "user_id": admin_user["id"],
            "username": admin_user["name"].lower().replace(" ", ".").replace("admin", "").strip(),
            "display_name": admin_user["name"],
            "role": admin_user["role"],
            "department": admin_user["department"]
        },
        "organization": {
            "hospital_id": hospital["id"],
            "hospital_name": hospital["name"],
            "location": hospital["location"]
        },
        "outcome": "success",
        "details": {}
    }
    
    # Add event-specific details
    if event_type in ["USER_CREATED", "USER_MODIFIED", "USER_DELETED"]:
        target_user = random.choice(USERS)
        event["target"] = {
            "user_id": target_user["id"],
            "username": target_user["name"].lower().replace(" ", "."),
            "role": target_user["role"]
        }
    elif event_type == "CONFIG_MODIFIED":
        event["details"]["config_key"] = random.choice([
            "session.timeout",
            "password.policy.min_length",
            "audit.retention_days",
            "mfa.required_roles"
        ])
        event["details"]["old_value"] = "previous_value"
        event["details"]["new_value"] = "new_value"
    elif event_type == "AUDIT_LOG_EXPORT":
        event["details"]["export_format"] = random.choice(["CSV", "JSON", "PDF"])
        event["details"]["date_range_days"] = random.randint(7, 90)
        event["details"]["record_count"] = random.randint(1000, 50000)
    
    return event


def generate_security_event(base_time: datetime, offset: int) -> Dict[str, Any]:
    """Generate security-related events (BSI/NIS2 critical)."""
    event_type = random.choice(EVENT_TYPES["security"])
    hospital = random.choice(HOSPITALS)
    
    event = {
        "timestamp": generate_timestamp(base_time, offset),
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_category": "security",
        "severity": SEVERITY_MAP.get(event_type, "HIGH"),
        "source": {
            "application": "Avelios Medical",
            "version": "8.5.2",
            "module": "SecurityMonitor",
            "hostname": f"avelios-sec-01.{hospital['location'].lower()}.local",
            "ip": generate_source_ip()
        },
        "organization": {
            "hospital_id": hospital["id"],
            "hospital_name": hospital["name"],
            "location": hospital["location"]
        },
        "threat": {
            "indicator_type": random.choice(["IP", "Hash", "Domain", "Behavior"]),
            "confidence": random.randint(70, 100)
        },
        "outcome": "detected",
        "details": {}
    }
    
    # Add threat actor if applicable
    if event_type in ["UNAUTHORIZED_ACCESS_ATTEMPT", "PRIVILEGE_ESCALATION_ATTEMPT"]:
        user = random.choice(USERS)
        event["actor"] = {
            "user_id": user["id"],
            "username": user["name"].lower().replace(" ", "."),
            "role": user["role"]
        }
        event["details"]["target_resource"] = random.choice([
            "Admin Console",
            "Patient Database",
            "Audit Logs",
            "System Configuration"
        ])
    elif event_type == "MALWARE_DETECTED":
        event["details"]["malware_name"] = random.choice([
            "Trojan.GenericKD",
            "Ransomware.WannaCry",
            "Spyware.Keylogger"
        ])
        event["details"]["file_path"] = "/tmp/suspicious_file.exe"
        event["details"]["action_taken"] = "Quarantined"
    elif event_type == "COMPLIANCE_VIOLATION":
        event["details"]["violation_type"] = random.choice([
            "BSI-Grundschutz: Access control violation",
            "NIS2: Incident reporting delay",
            "GDPR: Unauthorized data access",
            "HIPAA: PHI disclosure without consent"
        ])
        event["details"]["regulation"] = random.choice(["BSI", "NIS2", "GDPR", "HIPAA"])
    
    return event


def generate_data_transfer_event(base_time: datetime, offset: int) -> Dict[str, Any]:
    """Generate data transfer/export events."""
    event_type = random.choice(EVENT_TYPES["data_transfer"])
    user = random.choice(USERS)
    hospital = random.choice(HOSPITALS)
    
    event = {
        "timestamp": generate_timestamp(base_time, offset),
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_category": "data_transfer",
        "severity": SEVERITY_MAP.get(event_type, "INFO"),
        "source": {
            "application": "Avelios Medical",
            "version": "8.5.2",
            "module": random.choice(["IntegrationEngine", "ReportingAnalytics", "DataExchange"]),
            "hostname": f"avelios-int-01.{hospital['location'].lower()}.local",
            "ip": generate_source_ip()
        },
        "actor": {
            "user_id": user["id"],
            "username": user["name"].lower().replace(" ", ".").replace("dr.", "").strip(),
            "display_name": user["name"],
            "role": user["role"]
        },
        "organization": {
            "hospital_id": hospital["id"],
            "hospital_name": hospital["name"],
            "location": hospital["location"]
        },
        "outcome": "success",
        "details": {}
    }
    
    # Add event-specific details
    if "HL7" in event_type:
        event["details"]["message_type"] = random.choice(["ADT^A01", "ORM^O01", "ORU^R01", "MDM^T02"])
        event["details"]["message_id"] = f"HL7-{random.randint(100000, 999999)}"
        event["details"]["destination"] = random.choice([
            "Laboratory System",
            "Radiology PACS",
            "Pharmacy System",
            "External Lab"
        ])
    elif "FHIR" in event_type:
        event["details"]["resource_type"] = random.choice([
            "Patient", "Observation", "MedicationRequest", "DiagnosticReport"
        ])
        event["details"]["operation"] = random.choice(["read", "search", "create", "update"])
        event["details"]["response_code"] = random.choice([200, 201, 200, 200])
    elif "EXPORT" in event_type:
        event["details"]["export_type"] = random.choice([
            "Patient Summary",
            "Clinical Report",
            "Billing Data",
            "Quality Metrics"
        ])
        event["details"]["record_count"] = random.randint(1, 1000)
        event["details"]["destination"] = random.choice([
            "Insurance Provider",
            "External Specialist",
            "Research Database",
            "Regulatory Authority"
        ])
    
    return event


def generate_system_event(base_time: datetime, offset: int) -> Dict[str, Any]:
    """Generate system health/availability events."""
    event_type = random.choice(EVENT_TYPES["system"])
    hospital = random.choice(HOSPITALS)
    
    event = {
        "timestamp": generate_timestamp(base_time, offset),
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_category": "system",
        "severity": "INFO" if event_type in ["SERVICE_STARTED", "SERVICE_HEALTH_CHECK", "SCHEDULED_TASK_EXECUTED"] else "MEDIUM",
        "source": {
            "application": "Avelios Medical",
            "version": "8.5.2",
            "module": random.choice(AVELIOS_MODULES),
            "hostname": f"avelios-app-{random.randint(1,3):02d}.{hospital['location'].lower()}.local",
            "ip": generate_source_ip()
        },
        "organization": {
            "hospital_id": hospital["id"],
            "hospital_name": hospital["name"],
            "location": hospital["location"]
        },
        "outcome": "success",
        "details": {}
    }
    
    # Add event-specific details
    if event_type == "SERVICE_HEALTH_CHECK":
        event["details"]["service_name"] = random.choice(AVELIOS_MODULES)
        event["details"]["status"] = random.choice(["healthy", "healthy", "healthy", "degraded"])
        event["details"]["response_time_ms"] = random.randint(10, 500)
    elif event_type == "DATABASE_CONNECTION_POOL":
        event["details"]["active_connections"] = random.randint(10, 100)
        event["details"]["max_connections"] = 150
        event["details"]["wait_queue"] = random.randint(0, 10)
    elif event_type in ["DISK_SPACE_WARNING", "MEMORY_THRESHOLD_ALERT"]:
        event["severity"] = "HIGH"
        event["details"]["current_usage_percent"] = random.randint(85, 98)
        event["details"]["threshold_percent"] = 85
    
    return event


def generate_events(count: int = 100, hours_back: int = 24) -> List[Dict[str, Any]]:
    """Generate a mix of Avelios Medical events."""
    events = []
    base_time = datetime.utcnow()
    
    # Event type weights (BSI/NIS2 focus)
    generators = [
        (generate_authentication_event, 25),
        (generate_patient_access_event, 30),
        (generate_administrative_event, 10),
        (generate_security_event, 15),
        (generate_data_transfer_event, 15),
        (generate_system_event, 5)
    ]
    
    for i in range(count):
        offset = random.randint(0, hours_back * 60)
        
        # Weighted random selection
        total_weight = sum(w for _, w in generators)
        r = random.randint(1, total_weight)
        cumulative = 0
        for generator, weight in generators:
            cumulative += weight
            if r <= cumulative:
                events.append(generator(base_time, offset))
                break
    
    # Sort by timestamp
    events.sort(key=lambda x: x["timestamp"])
    return events


def main():
    """Generate and output sample Avelios Medical events."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate Avelios Medical sample events")
    parser.add_argument("--count", type=int, default=100, help="Number of events to generate")
    parser.add_argument("--hours", type=int, default=24, help="Hours of history to generate")
    parser.add_argument("--output", type=str, default=None, help="Output file (default: stdout)")
    parser.add_argument("--format", choices=["json", "ndjson"], default="ndjson", help="Output format")
    
    args = parser.parse_args()
    
    events = generate_events(args.count, args.hours)
    
    if args.format == "json":
        output = json.dumps(events, indent=2)
    else:
        output = "\n".join(json.dumps(e) for e in events)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Generated {len(events)} events to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
