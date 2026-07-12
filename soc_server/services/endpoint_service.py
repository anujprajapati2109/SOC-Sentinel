import logging
from datetime import timedelta
from secrets import token_urlsafe

from models import Endpoint, db, utc_now
from utils.constants import (
    ENDPOINT_ID_PREFIX,
    IDENTITY_CHANGED,
    IDENTITY_NORMAL,
    IDENTITY_UNKNOWN,
    STATUS_OFFLINE,
    STATUS_ONLINE,
)
from utils.validators import require_non_empty


logger = logging.getLogger(__name__)


def generate_api_key() -> str:
    """Generate a high-entropy API key for an endpoint agent."""

    return token_urlsafe(48)


def generate_endpoint_id() -> str:
    """Generate the next human-readable endpoint identifier."""

    last_endpoint = Endpoint.query.order_by(Endpoint.id.desc()).first()
    next_number = 1 if last_endpoint is None else last_endpoint.id + 1
    return f"{ENDPOINT_ID_PREFIX}-{next_number:06d}"


def serialize_endpoint(endpoint: Endpoint, include_api_key: bool = False) -> dict:
    """Convert an Endpoint model into a JSON-safe dictionary."""

    payload = {
        "id": endpoint.id,
        "endpoint_id": endpoint.endpoint_id,
        "hostname": endpoint.hostname,
        "username": endpoint.username,
        "operating_system": endpoint.operating_system,
        "os_version": endpoint.os_version,
        "ip_address": endpoint.ip_address,
        "mac_address": endpoint.mac_address,
        "agent_version": endpoint.agent_version,
        "python_version": endpoint.python_version,
        "architecture": endpoint.architecture,
        "processor": endpoint.processor,
        "cpu_count": endpoint.cpu_count,
        "total_memory_mb": endpoint.total_memory_mb,
        "system_drive": endpoint.system_drive,
        "device_fingerprint": endpoint.device_fingerprint,
        "identity_status": endpoint.identity_status or IDENTITY_UNKNOWN,
        "identity_previous_fingerprint": endpoint.identity_previous_fingerprint,
        "identity_observed_fingerprint": endpoint.identity_observed_fingerprint,
        "identity_last_changed": _isoformat(endpoint.identity_last_changed),
        "status": endpoint.status,
        "registered_at": _isoformat(endpoint.registered_at),
        "last_seen": _isoformat(endpoint.last_seen),
    }

    if include_api_key:
        payload["api_key"] = endpoint.api_key

    return payload


def register_endpoint(payload: dict) -> Endpoint:
    """Register an endpoint or reuse an existing identity for this hardware."""

    hostname = require_non_empty(payload.get("hostname", ""), "hostname")
    device_fingerprint = _normalize_fingerprint(payload.get("device_fingerprint"))
    mac_address = _optional_text(payload.get("mac_address"))
    existing_endpoint = find_endpoint_by_identity(device_fingerprint, mac_address)
    if existing_endpoint is not None:
        update_endpoint_metadata(existing_endpoint, payload)
        existing_endpoint.status = STATUS_ONLINE
        existing_endpoint.last_seen = utc_now()
        if not existing_endpoint.api_key:
            existing_endpoint.api_key = generate_api_key()
        apply_identity_fingerprint(existing_endpoint, device_fingerprint)
        db.session.commit()
        return existing_endpoint

    endpoint = Endpoint(
        endpoint_id=generate_endpoint_id(),
        hostname=hostname,
        username=_optional_text(payload.get("username")),
        operating_system=_optional_text(payload.get("operating_system")),
        os_version=_optional_text(payload.get("os_version")),
        ip_address=_optional_text(payload.get("ip_address")),
        mac_address=mac_address,
        agent_version=_optional_text(payload.get("agent_version")),
        python_version=_optional_text(payload.get("python_version")),
        architecture=_optional_text(payload.get("architecture")),
        processor=_optional_text(payload.get("processor")),
        cpu_count=_optional_text(payload.get("cpu_count")),
        total_memory_mb=_optional_text(payload.get("total_memory_mb")),
        system_drive=_optional_text(payload.get("system_drive")),
        device_fingerprint=device_fingerprint,
        identity_status=IDENTITY_NORMAL if device_fingerprint else IDENTITY_UNKNOWN,
        api_key=generate_api_key(),
        status=STATUS_ONLINE,
        registered_at=utc_now(),
        created_at=utc_now(),
        last_seen=utc_now(),
    )

    db.session.add(endpoint)
    db.session.commit()
    return endpoint


def update_heartbeat(
    endpoint_id: str,
    api_key: str | None = None,
    device_fingerprint: str | None = None,
    payload: dict | None = None,
) -> Endpoint | None:
    """Update endpoint heartbeat and mark it online."""

    endpoint = get_endpoint(endpoint_id)
    if endpoint is None:
        return None

    if api_key is not None and endpoint.api_key != api_key:
        return None

    apply_identity_fingerprint(endpoint, device_fingerprint)
    update_endpoint_metadata(endpoint, payload or {})
    endpoint.status = STATUS_ONLINE
    endpoint.last_seen = utc_now()
    db.session.commit()
    return endpoint


def find_endpoint_by_identity(
    device_fingerprint: str | None,
    mac_address: str | None,
) -> Endpoint | None:
    """Find an existing endpoint by stable hardware identity."""

    if device_fingerprint:
        endpoint = Endpoint.query.filter_by(
            device_fingerprint=device_fingerprint
        ).first()
        if endpoint is not None:
            return endpoint

    normalized_mac = _optional_text(mac_address)
    if normalized_mac:
        return Endpoint.query.filter(
            Endpoint.mac_address.ilike(normalized_mac)
        ).first()

    return None


def update_endpoint_metadata(endpoint: Endpoint, payload: dict) -> None:
    """Refresh inventory fields reported by the agent."""

    field_names = [
        "hostname",
        "username",
        "operating_system",
        "os_version",
        "ip_address",
        "mac_address",
        "agent_version",
        "python_version",
        "architecture",
        "processor",
        "cpu_count",
        "total_memory_mb",
        "system_drive",
    ]

    for field_name in field_names:
        value = _optional_text(payload.get(field_name))
        if value is not None:
            setattr(endpoint, field_name, value)


def apply_identity_fingerprint(
    endpoint: Endpoint,
    device_fingerprint: str | None,
) -> None:
    """Update endpoint identity state from a reported device fingerprint."""

    fingerprint = _normalize_fingerprint(device_fingerprint)
    if fingerprint is None:
        if not endpoint.identity_status:
            endpoint.identity_status = IDENTITY_UNKNOWN
        return

    if not endpoint.device_fingerprint:
        endpoint.device_fingerprint = fingerprint
        endpoint.identity_status = IDENTITY_NORMAL
        return

    if endpoint.device_fingerprint == fingerprint:
        if endpoint.identity_status != IDENTITY_CHANGED:
            endpoint.identity_status = IDENTITY_NORMAL
        return

    changed_at = utc_now()
    should_audit = (
        endpoint.identity_status != IDENTITY_CHANGED
        or endpoint.identity_observed_fingerprint != fingerprint
    )

    endpoint.identity_status = IDENTITY_CHANGED
    endpoint.identity_previous_fingerprint = endpoint.device_fingerprint
    endpoint.identity_observed_fingerprint = fingerprint
    endpoint.identity_last_changed = changed_at

    if should_audit:
        logger.warning(
            "Endpoint identity changed | endpoint=%s old_fingerprint=%s "
            "new_fingerprint=%s timestamp=%s",
            endpoint.endpoint_id,
            endpoint.device_fingerprint,
            fingerprint,
            changed_at.isoformat(),
        )


def mark_expired_endpoints_offline(timeout_seconds: int) -> int:
    """Mark endpoints offline when their heartbeat is older than the timeout."""

    cutoff = utc_now() - timedelta(seconds=timeout_seconds)
    expired = Endpoint.query.filter(
        Endpoint.status == STATUS_ONLINE,
        Endpoint.last_seen.isnot(None),
        Endpoint.last_seen < cutoff,
    ).all()

    for endpoint in expired:
        endpoint.status = STATUS_OFFLINE

    db.session.commit()
    return len(expired)


def list_endpoints() -> list[Endpoint]:
    """Return endpoints ordered by most recently seen."""

    return Endpoint.query.order_by(
        Endpoint.last_seen.desc().nullslast(),
        Endpoint.registered_at.desc(),
    ).all()


def get_endpoint(endpoint_id: str) -> Endpoint | None:
    """Return a single endpoint by public endpoint ID."""

    return Endpoint.query.filter_by(endpoint_id=endpoint_id).first()


def count_endpoints() -> int:
    """Return total registered endpoint count."""

    return Endpoint.query.count()


def count_online_endpoints() -> int:
    """Return endpoint count currently marked online."""

    return Endpoint.query.filter_by(status=STATUS_ONLINE).count()


def _optional_text(value: str | None) -> str | None:
    """Normalize optional text payload values."""

    if value is None:
        return None

    cleaned = str(value).strip()
    return cleaned or None


def _normalize_fingerprint(value: str | None) -> str | None:
    """Return a lowercase SHA-256 fingerprint when the input is valid."""

    cleaned = _optional_text(value)
    if cleaned is None:
        return None

    cleaned = cleaned.lower()
    if len(cleaned) != 64:
        return None

    if any(character not in "0123456789abcdef" for character in cleaned):
        return None

    return cleaned


def _isoformat(value) -> str | None:
    """Serialize datetimes for API responses."""

    return None if value is None else value.isoformat()
