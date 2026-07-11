from models import DetectionRule, db


DEFAULT_RULES = [
    {
        "rule_id": "RULE-FAILED-LOGIN",
        "name": "Failed Login",
        "description": "Five failed login events within sixty seconds.",
        "severity": "high",
        "threshold": 5,
        "time_window": 60,
        "mitre_tactic": "Credential Access",
        "mitre_technique": "T1110 Brute Force",
    },
    {
        "rule_id": "RULE-POWERSHELL",
        "name": "PowerShell Execution",
        "description": "PowerShell process execution observed.",
        "severity": "medium",
        "threshold": 1,
        "time_window": 0,
        "mitre_tactic": "Execution",
        "mitre_technique": "T1059.001 PowerShell",
    },
    {
        "rule_id": "RULE-RANSOMWARE",
        "name": "Possible Ransomware File Deletion",
        "description": "Twenty file deletion events within thirty seconds.",
        "severity": "critical",
        "threshold": 20,
        "time_window": 30,
        "mitre_tactic": "Impact",
        "mitre_technique": "T1485 Data Destruction",
    },
    {
        "rule_id": "RULE-SUSPICIOUS-PROCESS",
        "name": "Suspicious Process",
        "description": "Known suspicious process name observed.",
        "severity": "critical",
        "threshold": 1,
        "time_window": 0,
        "mitre_tactic": "Credential Access",
        "mitre_technique": "T1003 OS Credential Dumping",
    },
    {
        "rule_id": "RULE-PROCESS-SPIKE",
        "name": "Process Spike",
        "description": "Fifty process start events within twenty seconds.",
        "severity": "medium",
        "threshold": 50,
        "time_window": 20,
        "mitre_tactic": "Execution",
        "mitre_technique": "T1059 Command and Scripting Interpreter",
    },
]


def seed_detection_rules() -> None:
    """Create default detection rules if they do not already exist."""

    for rule_data in DEFAULT_RULES:
        rule = DetectionRule.query.filter_by(rule_id=rule_data["rule_id"]).first()
        if rule is None:
            db.session.add(DetectionRule(enabled=True, **rule_data))
            continue

        for key, value in rule_data.items():
            setattr(rule, key, value)

    db.session.commit()
