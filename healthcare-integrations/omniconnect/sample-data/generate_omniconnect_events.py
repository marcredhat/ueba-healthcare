#!/usr/bin/env python3
"""
Omniconnect Sample Data Generator
=================================
Generates BSI and NIS2 compliance-relevant events for Omniconnect,
the software interface ensuring secure communication between the
Hospital Information System (HIS) and the German Telematics Infrastructure (TI).

Event Categories (BSI/NIS2 relevant):
- TI Connection events (Konnektor status, VPN, certificates)
- eHealth Card operations (eGK, HBA, SMC-B)
- Prescription services (eRezept)
- Patient data exchange (ePA - elektronische Patientenakte)
- KIM (Kommunikation im Medizinwesen) messaging
- VSDM (Versichertenstammdatenmanagement)
- Security and audit events

German Telematics Infrastructure Components:
- Konnektor: Hardware security module connecting to TI
- eGK: Elektronische Gesundheitskarte (patient health card)
- HBA: Heilberufsausweis (healthcare professional card)
- SMC-B: Security Module Card Type B (institution card)
- ePA: Elektronische Patientenakte (electronic health record)
- eRezept: Electronic prescription
- KIM: Secure healthcare messaging

Author: Marc Chisinevski
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Omniconnect-specific configuration
TI_SERVICES = [
    "VSDM",           # Versichertenstammdatenmanagement
    "eRezept",        # Electronic prescription
    "ePA",            # Elektronische Patientenakte
    "KIM",            # Kommunikation im Medizinwesen
    "NFDM",           # Notfalldatenmanagement
    "eMP",            # Elektronischer Medikationsplan
    "eAU",            # Elektronische Arbeitsunfähigkeitsbescheinigung
    "DiGA",           # Digitale Gesundheitsanwendungen
]

KONNEKTOR_TYPES = [
    {"vendor": "RISE", "model": "Konnektor 5.0", "firmware": "5.0.3"},
    {"vendor": "secunet", "model": "Konnektor 4.0", "firmware": "4.8.2"},
    {"vendor": "T-Systems", "model": "TI-Konnektor", "firmware": "3.5.1"},
]

CARD_TYPES = {
    "eGK": "Elektronische Gesundheitskarte",
    "HBA": "Heilberufsausweis",
    "SMC-B": "Security Module Card Type B",
    "SMC-KT": "Security Module Card Kartenterminal"
}

INSURANCE_PROVIDERS = [
    {"id": "IK-104940005", "name": "AOK Bayern", "type": "GKV"},
    {"id": "IK-109519005", "name": "Techniker Krankenkasse", "type": "GKV"},
    {"id": "IK-103411401", "name": "BARMER", "type": "GKV"},
    {"id": "IK-105313145", "name": "DAK-Gesundheit", "type": "GKV"},
    {"id": "IK-168140346", "name": "Allianz PKV", "type": "PKV"},
]

HEALTHCARE_FACILITIES = [
    {"id": "BSNR-123456789", "name": "Praxis Dr. Schmidt", "type": "Arztpraxis", "location": "Berlin"},
    {"id": "BSNR-987654321", "name": "Universitätsklinikum München", "type": "Krankenhaus", "location": "Munich"},
    {"id": "BSNR-456789123", "name": "Apotheke am Markt", "type": "Apotheke", "location": "Hamburg"},
    {"id": "BSNR-789123456", "name": "MVZ Kardiologie", "type": "MVZ", "location": "Frankfurt"},
]

HEALTHCARE_PROFESSIONALS = [
    {"id": "LANR-123456789", "name": "Dr. med. Anna Schmidt", "specialty": "Allgemeinmedizin", "hba_id": "HBA-001"},
    {"id": "LANR-987654321", "name": "Dr. med. Thomas Weber", "specialty": "Kardiologie", "hba_id": "HBA-002"},
    {"id": "LANR-456789123", "name": "Dr. med. Lisa Bauer", "specialty": "Radiologie", "hba_id": "HBA-003"},
    {"id": "LANR-789123456", "name": "Apotheker Hans Meyer", "specialty": "Pharmazie", "hba_id": "HBA-004"},
]

# BSI/NIS2 relevant event types
EVENT_TYPES = {
    "ti_connection": [
        "KONNEKTOR_CONNECTED",
        "KONNEKTOR_DISCONNECTED",
        "KONNEKTOR_HEALTH_CHECK",
        "VPN_TUNNEL_ESTABLISHED",
        "VPN_TUNNEL_FAILED",
        "VPN_TUNNEL_RECONNECT",
        "TI_SERVICE_AVAILABLE",
        "TI_SERVICE_UNAVAILABLE",
        "CERTIFICATE_VALID",
        "CERTIFICATE_EXPIRING",
        "CERTIFICATE_EXPIRED",
        "CERTIFICATE_RENEWED"
    ],
    "card_operations": [
        "CARD_INSERTED",
        "CARD_REMOVED",
        "CARD_READ_SUCCESS",
        "CARD_READ_FAILURE",
        "CARD_PIN_VERIFIED",
        "CARD_PIN_FAILED",
        "CARD_PIN_BLOCKED",
        "CARD_SIGNATURE_CREATED",
        "CARD_DECRYPTION_SUCCESS",
        "CARD_AUTHENTICATION_SUCCESS",
        "CARD_AUTHENTICATION_FAILED"
    ],
    "vsdm": [
        "VSDM_READ_VSD",
        "VSDM_UPDATE_VSD",
        "VSDM_ONLINE_CHECK",
        "VSDM_OFFLINE_CHECK",
        "VSDM_PRUEFUNGSNACHWEIS_CREATED",
        "VSDM_INSURANCE_VALID",
        "VSDM_INSURANCE_INVALID",
        "VSDM_CARD_LOCKED"
    ],
    "erezept": [
        "EREZEPT_CREATED",
        "EREZEPT_SIGNED",
        "EREZEPT_TRANSMITTED",
        "EREZEPT_DISPENSED",
        "EREZEPT_CANCELLED",
        "EREZEPT_RETRIEVED",
        "EREZEPT_VALIDATION_SUCCESS",
        "EREZEPT_VALIDATION_FAILED",
        "EREZEPT_SIGNATURE_VERIFIED"
    ],
    "epa": [
        "EPA_DOCUMENT_UPLOADED",
        "EPA_DOCUMENT_RETRIEVED",
        "EPA_DOCUMENT_DELETED",
        "EPA_ACCESS_GRANTED",
        "EPA_ACCESS_REVOKED",
        "EPA_CONSENT_GIVEN",
        "EPA_CONSENT_REVOKED",
        "EPA_EMERGENCY_ACCESS",
        "EPA_AUDIT_LOG_RETRIEVED"
    ],
    "kim": [
        "KIM_MESSAGE_SENT",
        "KIM_MESSAGE_RECEIVED",
        "KIM_MESSAGE_ENCRYPTED",
        "KIM_MESSAGE_DECRYPTED",
        "KIM_ATTACHMENT_ADDED",
        "KIM_DELIVERY_CONFIRMED",
        "KIM_DELIVERY_FAILED",
        "KIM_ADDRESS_LOOKUP"
    ],
    "security": [
        "UNAUTHORIZED_ACCESS_ATTEMPT",
        "CERTIFICATE_VALIDATION_FAILED",
        "SIGNATURE_VERIFICATION_FAILED",
        "ENCRYPTION_FAILED",
        "DECRYPTION_FAILED",
        "TAMPER_DETECTION",
        "SECURITY_POLICY_VIOLATION",
        "AUDIT_LOG_EXPORT",
        "INTRUSION_DETECTED",
        "COMPLIANCE_CHECK_PASSED",
        "COMPLIANCE_CHECK_FAILED"
    ],
    "system": [
        "SERVICE_STARTED",
        "SERVICE_STOPPED",
        "SERVICE_HEALTH_CHECK",
        "CONFIG_CHANGED",
        "FIRMWARE_UPDATE_AVAILABLE",
        "FIRMWARE_UPDATE_INSTALLED",
        "BACKUP_COMPLETED",
        "ERROR_THRESHOLD_EXCEEDED"
    ]
}

SEVERITY_MAP = {
    "KONNEKTOR_DISCONNECTED": "HIGH",
    "VPN_TUNNEL_FAILED": "HIGH",
    "CERTIFICATE_EXPIRED": "CRITICAL",
    "CERTIFICATE_EXPIRING": "HIGH",
    "CARD_PIN_BLOCKED": "HIGH",
    "CARD_READ_FAILURE": "MEDIUM",
    "CARD_AUTHENTICATION_FAILED": "MEDIUM",
    "VSDM_INSURANCE_INVALID": "MEDIUM",
    "EREZEPT_VALIDATION_FAILED": "MEDIUM",
    "EPA_EMERGENCY_ACCESS": "HIGH",
    "KIM_DELIVERY_FAILED": "MEDIUM",
    "UNAUTHORIZED_ACCESS_ATTEMPT": "CRITICAL",
    "CERTIFICATE_VALIDATION_FAILED": "HIGH",
    "SIGNATURE_VERIFICATION_FAILED": "HIGH",
    "TAMPER_DETECTION": "CRITICAL",
    "SECURITY_POLICY_VIOLATION": "HIGH",
    "INTRUSION_DETECTED": "CRITICAL",
    "COMPLIANCE_CHECK_FAILED": "HIGH",
    "TI_SERVICE_UNAVAILABLE": "HIGH",
}


def generate_timestamp(base_time: datetime = None, offset_minutes: int = 0) -> str:
    """Generate ISO8601 timestamp."""
    if base_time is None:
        base_time = datetime.utcnow()
    ts = base_time - timedelta(minutes=offset_minutes)
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def generate_kvnr() -> str:
    """Generate a sample KVNR (Krankenversichertennummer)."""
    letter = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    numbers = "".join([str(random.randint(0, 9)) for _ in range(9)])
    return f"{letter}{numbers}"


def generate_telematik_id() -> str:
    """Generate a sample Telematik-ID."""
    return f"3-{random.randint(10, 99)}.{random.randint(1000000, 9999999)}.{random.randint(100, 999)}"


def generate_ti_connection_event(base_time: datetime, offset: int) -> Dict[str, Any]:
    """Generate TI connection/infrastructure events."""
    event_type = random.choice(EVENT_TYPES["ti_connection"])
    facility = random.choice(HEALTHCARE_FACILITIES)
    konnektor = random.choice(KONNEKTOR_TYPES)
    
    event = {
        "timestamp": generate_timestamp(base_time, offset),
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_category": "ti_connection",
        "severity": SEVERITY_MAP.get(event_type, "INFO"),
        "source": {
            "application": "Omniconnect",
            "version": "4.2.1",
            "module": "TI-Gateway",
            "hostname": f"omniconnect-{facility['location'].lower()[:3]}-01.local",
        },
        "konnektor": {
            "vendor": konnektor["vendor"],
            "model": konnektor["model"],
            "firmware_version": konnektor["firmware"],
            "serial_number": f"KON-{random.randint(100000, 999999)}",
            "telematik_id": generate_telematik_id()
        },
        "facility": {
            "bsnr": facility["id"],
            "name": facility["name"],
            "type": facility["type"],
            "location": facility["location"]
        },
        "outcome": "success" if "SUCCESS" in event_type or "CONNECTED" in event_type or "ESTABLISHED" in event_type or "VALID" in event_type or "AVAILABLE" in event_type or "RENEWED" in event_type else ("failure" if "FAILED" in event_type or "EXPIRED" in event_type or "UNAVAILABLE" in event_type else "info"),
        "details": {}
    }
    
    # Add event-specific details
    if "VPN" in event_type:
        event["details"]["vpn_gateway"] = f"ti-vpn-{random.randint(1,5)}.telematik.de"
        event["details"]["tunnel_id"] = f"TUN-{random.randint(10000, 99999)}"
        if "FAILED" in event_type:
            event["details"]["failure_reason"] = random.choice([
                "Certificate expired",
                "Network timeout",
                "Authentication failed",
                "Gateway unreachable"
            ])
    elif "CERTIFICATE" in event_type:
        event["details"]["certificate_type"] = random.choice(["TLS", "SMC-B", "Konnektor"])
        event["details"]["certificate_cn"] = f"CN={facility['name']}"
        if "EXPIRING" in event_type:
            event["details"]["days_until_expiry"] = random.randint(1, 30)
        elif "EXPIRED" in event_type:
            event["details"]["expired_since_days"] = random.randint(1, 7)
    elif "SERVICE" in event_type:
        event["details"]["service_name"] = random.choice(TI_SERVICES)
        event["details"]["service_endpoint"] = f"https://{random.choice(TI_SERVICES).lower()}.telematik.de/api/v1"
    
    return event


def generate_card_operation_event(base_time: datetime, offset: int) -> Dict[str, Any]:
    """Generate card operation events (eGK, HBA, SMC-B)."""
    event_type = random.choice(EVENT_TYPES["card_operations"])
    facility = random.choice(HEALTHCARE_FACILITIES)
    card_type = random.choice(list(CARD_TYPES.keys()))
    
    event = {
        "timestamp": generate_timestamp(base_time, offset),
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_category": "card_operations",
        "severity": SEVERITY_MAP.get(event_type, "INFO"),
        "source": {
            "application": "Omniconnect",
            "version": "4.2.1",
            "module": "CardTerminal",
            "hostname": f"omniconnect-{facility['location'].lower()[:3]}-01.local",
        },
        "card": {
            "type": card_type,
            "type_description": CARD_TYPES[card_type],
            "iccsn": f"80276{random.randint(10000000000, 99999999999)}",
            "terminal_id": f"CT-{random.randint(100, 999)}"
        },
        "facility": {
            "bsnr": facility["id"],
            "name": facility["name"],
            "type": facility["type"]
        },
        "outcome": "success" if "SUCCESS" in event_type or "VERIFIED" in event_type or "INSERTED" in event_type or "CREATED" in event_type else ("failure" if "FAILED" in event_type or "BLOCKED" in event_type else "info"),
        "details": {}
    }
    
    # Add card-specific details
    if card_type == "eGK":
        insurance = random.choice(INSURANCE_PROVIDERS)
        event["card"]["kvnr"] = generate_kvnr()
        event["card"]["insurance_id"] = insurance["id"]
        event["card"]["insurance_name"] = insurance["name"]
    elif card_type == "HBA":
        professional = random.choice(HEALTHCARE_PROFESSIONALS)
        event["card"]["hba_id"] = professional["hba_id"]
        event["card"]["holder_name"] = professional["name"]
        event["card"]["specialty"] = professional["specialty"]
    
    # Add event-specific details
    if "PIN" in event_type:
        event["details"]["pin_type"] = random.choice(["PIN.CH", "PIN.QES", "PIN.HOME"])
        if "FAILED" in event_type:
            event["details"]["attempts_remaining"] = random.randint(0, 2)
        elif "BLOCKED" in event_type:
            event["details"]["unblock_required"] = True
    elif "SIGNATURE" in event_type:
        event["details"]["signature_type"] = random.choice(["QES", "nonQES"])
        event["details"]["algorithm"] = "ECDSA-SHA256"
    
    return event


def generate_vsdm_event(base_time: datetime, offset: int) -> Dict[str, Any]:
    """Generate VSDM (insurance data management) events."""
    event_type = random.choice(EVENT_TYPES["vsdm"])
    facility = random.choice(HEALTHCARE_FACILITIES)
    insurance = random.choice(INSURANCE_PROVIDERS)
    
    event = {
        "timestamp": generate_timestamp(base_time, offset),
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_category": "vsdm",
        "severity": SEVERITY_MAP.get(event_type, "INFO"),
        "source": {
            "application": "Omniconnect",
            "version": "4.2.1",
            "module": "VSDM-Service",
            "hostname": f"omniconnect-{facility['location'].lower()[:3]}-01.local",
        },
        "patient": {
            "kvnr": generate_kvnr(),
            "insurance_id": insurance["id"],
            "insurance_name": insurance["name"],
            "insurance_type": insurance["type"]
        },
        "facility": {
            "bsnr": facility["id"],
            "name": facility["name"],
            "type": facility["type"]
        },
        "outcome": "success" if "VALID" in event_type or "SUCCESS" in event_type or "CREATED" in event_type else ("failure" if "INVALID" in event_type or "LOCKED" in event_type else "info"),
        "details": {}
    }
    
    # Add event-specific details
    if "ONLINE_CHECK" in event_type or "OFFLINE_CHECK" in event_type:
        event["details"]["check_mode"] = "online" if "ONLINE" in event_type else "offline"
        event["details"]["vsd_version"] = f"5.{random.randint(1, 9)}.0"
    elif "PRUEFUNGSNACHWEIS" in event_type:
        event["details"]["pruefungsnachweis_id"] = f"PN-{random.randint(100000, 999999)}"
        event["details"]["valid_until"] = generate_timestamp(base_time, -random.randint(1, 90) * 24 * 60)
    elif "INSURANCE" in event_type:
        if "INVALID" in event_type:
            event["details"]["invalid_reason"] = random.choice([
                "Card expired",
                "Insurance terminated",
                "Card blocked",
                "Data mismatch"
            ])
    
    return event


def generate_erezept_event(base_time: datetime, offset: int) -> Dict[str, Any]:
    """Generate eRezept (electronic prescription) events."""
    event_type = random.choice(EVENT_TYPES["erezept"])
    facility = random.choice(HEALTHCARE_FACILITIES)
    professional = random.choice(HEALTHCARE_PROFESSIONALS)
    
    event = {
        "timestamp": generate_timestamp(base_time, offset),
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_category": "erezept",
        "severity": SEVERITY_MAP.get(event_type, "INFO"),
        "source": {
            "application": "Omniconnect",
            "version": "4.2.1",
            "module": "eRezept-Service",
            "hostname": f"omniconnect-{facility['location'].lower()[:3]}-01.local",
        },
        "prescription": {
            "prescription_id": f"160.{random.randint(100, 999)}.{random.randint(100000000, 999999999)}.{random.randint(10000, 99999)}.{random.randint(10, 99)}",
            "task_id": str(uuid.uuid4()),
            "workflow_type": random.choice(["160", "169", "200", "209"]),  # Different prescription types
            "medication_pzn": f"{random.randint(1000000, 9999999)}",
        },
        "prescriber": {
            "lanr": professional["id"],
            "name": professional["name"],
            "specialty": professional["specialty"],
            "telematik_id": generate_telematik_id()
        },
        "patient": {
            "kvnr": generate_kvnr()
        },
        "facility": {
            "bsnr": facility["id"],
            "name": facility["name"],
            "type": facility["type"]
        },
        "outcome": "success" if "SUCCESS" in event_type or "CREATED" in event_type or "SIGNED" in event_type or "TRANSMITTED" in event_type or "DISPENSED" in event_type or "VERIFIED" in event_type else ("failure" if "FAILED" in event_type else "info"),
        "details": {}
    }
    
    # Add event-specific details
    if "SIGNED" in event_type:
        event["details"]["signature_type"] = "QES"
        event["details"]["signer_hba"] = professional["hba_id"]
    elif "DISPENSED" in event_type:
        event["details"]["dispensing_pharmacy"] = f"Apotheke-{random.randint(100, 999)}"
        event["details"]["dispensing_telematik_id"] = generate_telematik_id()
    elif "VALIDATION_FAILED" in event_type:
        event["details"]["validation_error"] = random.choice([
            "Invalid signature",
            "Prescription expired",
            "Medication not covered",
            "Patient data mismatch"
        ])
    
    return event


def generate_epa_event(base_time: datetime, offset: int) -> Dict[str, Any]:
    """Generate ePA (electronic health record) events."""
    event_type = random.choice(EVENT_TYPES["epa"])
    facility = random.choice(HEALTHCARE_FACILITIES)
    professional = random.choice(HEALTHCARE_PROFESSIONALS)
    
    event = {
        "timestamp": generate_timestamp(base_time, offset),
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_category": "epa",
        "severity": SEVERITY_MAP.get(event_type, "INFO"),
        "source": {
            "application": "Omniconnect",
            "version": "4.2.1",
            "module": "ePA-Service",
            "hostname": f"omniconnect-{facility['location'].lower()[:3]}-01.local",
        },
        "epa": {
            "record_id": f"EPA-{random.randint(100000000, 999999999)}",
            "insurance_id": random.choice(INSURANCE_PROVIDERS)["id"]
        },
        "patient": {
            "kvnr": generate_kvnr()
        },
        "accessor": {
            "lanr": professional["id"],
            "name": professional["name"],
            "telematik_id": generate_telematik_id(),
            "facility_bsnr": facility["id"]
        },
        "facility": {
            "bsnr": facility["id"],
            "name": facility["name"],
            "type": facility["type"]
        },
        "outcome": "success" if "UPLOADED" in event_type or "RETRIEVED" in event_type or "GRANTED" in event_type or "GIVEN" in event_type else ("revoked" if "REVOKED" in event_type or "DELETED" in event_type else "info"),
        "details": {}
    }
    
    # Add event-specific details
    if "DOCUMENT" in event_type:
        event["details"]["document_type"] = random.choice([
            "Arztbrief",
            "Laborbefund",
            "Bildgebung",
            "Medikationsplan",
            "Impfpass",
            "Notfalldaten"
        ])
        event["details"]["document_id"] = f"DOC-{random.randint(100000, 999999)}"
        event["details"]["document_format"] = random.choice(["PDF/A", "CDA", "FHIR"])
    elif "ACCESS" in event_type or "CONSENT" in event_type:
        event["details"]["access_level"] = random.choice(["read", "write", "full"])
        event["details"]["validity_days"] = random.randint(1, 365)
    elif "EMERGENCY_ACCESS" in event_type:
        event["details"]["emergency_reason"] = "Patient unconscious - emergency treatment"
        event["details"]["emergency_code"] = f"EMG-{random.randint(1000, 9999)}"
    
    return event


def generate_kim_event(base_time: datetime, offset: int) -> Dict[str, Any]:
    """Generate KIM (secure healthcare messaging) events."""
    event_type = random.choice(EVENT_TYPES["kim"])
    facility = random.choice(HEALTHCARE_FACILITIES)
    
    event = {
        "timestamp": generate_timestamp(base_time, offset),
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_category": "kim",
        "severity": SEVERITY_MAP.get(event_type, "INFO"),
        "source": {
            "application": "Omniconnect",
            "version": "4.2.1",
            "module": "KIM-Client",
            "hostname": f"omniconnect-{facility['location'].lower()[:3]}-01.local",
        },
        "message": {
            "message_id": f"KIM-{str(uuid.uuid4())[:8]}",
            "subject_hash": f"SHA256:{random.randbytes(16).hex()}",  # Hashed for privacy
            "size_bytes": random.randint(1000, 5000000)
        },
        "sender": {
            "kim_address": f"{facility['name'].lower().replace(' ', '.')}@kim.telematik.de",
            "telematik_id": generate_telematik_id()
        },
        "recipient": {
            "kim_address": f"{random.choice(HEALTHCARE_FACILITIES)['name'].lower().replace(' ', '.')}@kim.telematik.de",
            "telematik_id": generate_telematik_id()
        },
        "facility": {
            "bsnr": facility["id"],
            "name": facility["name"],
            "type": facility["type"]
        },
        "outcome": "success" if "SENT" in event_type or "RECEIVED" in event_type or "ENCRYPTED" in event_type or "DECRYPTED" in event_type or "CONFIRMED" in event_type else ("failure" if "FAILED" in event_type else "info"),
        "details": {}
    }
    
    # Add event-specific details
    if "ATTACHMENT" in event_type:
        event["details"]["attachment_count"] = random.randint(1, 5)
        event["details"]["attachment_types"] = random.sample(["PDF", "DICOM", "CDA", "JPEG"], k=random.randint(1, 3))
    elif "ENCRYPTED" in event_type or "DECRYPTED" in event_type:
        event["details"]["encryption_algorithm"] = "AES-256-GCM"
        event["details"]["key_exchange"] = "ECDH"
    elif "DELIVERY_FAILED" in event_type:
        event["details"]["failure_reason"] = random.choice([
            "Recipient address not found",
            "Recipient mailbox full",
            "Certificate validation failed",
            "Network timeout"
        ])
    
    return event


def generate_security_event(base_time: datetime, offset: int) -> Dict[str, Any]:
    """Generate security-related events (BSI/NIS2 critical)."""
    event_type = random.choice(EVENT_TYPES["security"])
    facility = random.choice(HEALTHCARE_FACILITIES)
    
    event = {
        "timestamp": generate_timestamp(base_time, offset),
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_category": "security",
        "severity": SEVERITY_MAP.get(event_type, "HIGH"),
        "source": {
            "application": "Omniconnect",
            "version": "4.2.1",
            "module": "SecurityMonitor",
            "hostname": f"omniconnect-{facility['location'].lower()[:3]}-01.local",
        },
        "facility": {
            "bsnr": facility["id"],
            "name": facility["name"],
            "type": facility["type"]
        },
        "threat": {
            "indicator_type": random.choice(["Certificate", "Signature", "Access", "Policy"]),
            "confidence": random.randint(70, 100)
        },
        "outcome": "detected",
        "details": {}
    }
    
    # Add event-specific details
    if "UNAUTHORIZED" in event_type:
        event["details"]["target_resource"] = random.choice([
            "Patient Records",
            "Prescription Service",
            "Admin Console",
            "Konnektor Configuration"
        ])
        event["details"]["source_ip"] = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
    elif "CERTIFICATE" in event_type or "SIGNATURE" in event_type:
        event["details"]["certificate_cn"] = f"CN={facility['name']}"
        event["details"]["validation_error"] = random.choice([
            "Certificate revoked",
            "Certificate expired",
            "Invalid certificate chain",
            "Signature mismatch"
        ])
    elif "COMPLIANCE" in event_type:
        event["details"]["compliance_framework"] = random.choice(["BSI-Grundschutz", "NIS2", "GDPR", "gematik"])
        event["details"]["check_name"] = random.choice([
            "Certificate validity check",
            "Access control audit",
            "Encryption strength verification",
            "Audit log integrity"
        ])
        if "FAILED" in event_type:
            event["details"]["remediation_required"] = True
    elif "TAMPER" in event_type:
        event["details"]["tamper_type"] = random.choice([
            "Konnektor case opened",
            "Firmware modification detected",
            "Configuration tampering"
        ])
    
    return event


def generate_system_event(base_time: datetime, offset: int) -> Dict[str, Any]:
    """Generate system health/operational events."""
    event_type = random.choice(EVENT_TYPES["system"])
    facility = random.choice(HEALTHCARE_FACILITIES)
    
    event = {
        "timestamp": generate_timestamp(base_time, offset),
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_category": "system",
        "severity": "INFO" if event_type in ["SERVICE_STARTED", "SERVICE_HEALTH_CHECK", "BACKUP_COMPLETED"] else "MEDIUM",
        "source": {
            "application": "Omniconnect",
            "version": "4.2.1",
            "module": "SystemMonitor",
            "hostname": f"omniconnect-{facility['location'].lower()[:3]}-01.local",
        },
        "facility": {
            "bsnr": facility["id"],
            "name": facility["name"],
            "type": facility["type"]
        },
        "outcome": "success",
        "details": {}
    }
    
    # Add event-specific details
    if "HEALTH_CHECK" in event_type:
        event["details"]["services_checked"] = random.sample(TI_SERVICES, k=random.randint(3, 6))
        event["details"]["all_healthy"] = random.choice([True, True, True, False])
    elif "CONFIG_CHANGED" in event_type:
        event["details"]["config_key"] = random.choice([
            "ti.vpn.timeout",
            "security.certificate.check_interval",
            "kim.max_attachment_size",
            "audit.retention_days"
        ])
        event["details"]["changed_by"] = "admin"
    elif "FIRMWARE" in event_type:
        event["details"]["current_version"] = "4.2.1"
        event["details"]["new_version"] = "4.3.0"
        event["details"]["konnektor_serial"] = f"KON-{random.randint(100000, 999999)}"
    
    return event


def generate_events(count: int = 100, hours_back: int = 24) -> List[Dict[str, Any]]:
    """Generate a mix of Omniconnect events."""
    events = []
    base_time = datetime.utcnow()
    
    # Event type weights (BSI/NIS2 focus on TI infrastructure)
    generators = [
        (generate_ti_connection_event, 15),
        (generate_card_operation_event, 20),
        (generate_vsdm_event, 15),
        (generate_erezept_event, 15),
        (generate_epa_event, 10),
        (generate_kim_event, 10),
        (generate_security_event, 10),
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
    """Generate and output sample Omniconnect events."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate Omniconnect sample events")
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
