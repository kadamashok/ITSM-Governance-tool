from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock

from app.utils.security import decrypt_text, encrypt_text


@dataclass
class _EncryptedOAuthConfig:
    instance_url: str
    client_id: str
    client_secret: str
    tenant_id: str
    oauth_scope: str
    access_token: str | None
    refresh_token: str | None
    token_expires_at: datetime | None


@dataclass
class _OAuthState:
    nonce: str
    expires_at: datetime


_lock = RLock()
_config: _EncryptedOAuthConfig | None = None
_state: _OAuthState | None = None


def save_oauth_settings(
    instance_url: str,
    client_id: str,
    client_secret: str,
    tenant_id: str,
    oauth_scope: str,
) -> None:
    global _config
    with _lock:
        _config = _EncryptedOAuthConfig(
            instance_url=instance_url.rstrip("/"),
            client_id=encrypt_text(client_id),
            client_secret=encrypt_text(client_secret),
            tenant_id=encrypt_text(tenant_id),
            oauth_scope=encrypt_text(oauth_scope),
            access_token=None,
            refresh_token=None,
            token_expires_at=None,
        )


def update_tokens(access_token: str, refresh_token: str | None, token_expires_at: datetime) -> None:
    with _lock:
        if _config is None:
            raise RuntimeError("ServiceNow OAuth is not configured")
        _config.access_token = encrypt_text(access_token)
        _config.refresh_token = encrypt_text(refresh_token) if refresh_token else None
        _config.token_expires_at = token_expires_at.astimezone(UTC)


def set_oauth_state(nonce: str, expires_at: datetime) -> None:
    global _state
    with _lock:
        _state = _OAuthState(nonce=nonce, expires_at=expires_at.astimezone(UTC))


def consume_oauth_state(nonce: str) -> bool:
    global _state
    with _lock:
        if _state is None:
            return False
        now = datetime.now(UTC)
        is_valid = _state.nonce == nonce and _state.expires_at > now
        _state = None
        return is_valid


def get_status() -> dict[str, object]:
    with _lock:
        now = datetime.now(UTC)
        has_refresh = bool(_config and _config.refresh_token)
        has_valid_access = bool(
            _config
            and _config.access_token
            and _config.token_expires_at
            and _config.token_expires_at > now
        )
        connected = bool(
            _config and (has_valid_access or has_refresh)
        )
        return {
            "connected": connected,
            "instance_url": _config.instance_url if _config else "",
            "token_expires_at": _config.token_expires_at.isoformat() if _config and _config.token_expires_at else None,
        }


def get_oauth_config() -> dict[str, str] | None:
    with _lock:
        if _config is None:
            return None
        return {
            "instance_url": _config.instance_url,
            "client_id": decrypt_text(_config.client_id),
            "client_secret": decrypt_text(_config.client_secret),
            "tenant_id": decrypt_text(_config.tenant_id),
            "oauth_scope": decrypt_text(_config.oauth_scope),
        }


def get_token_bundle() -> dict[str, object] | None:
    with _lock:
        if _config is None:
            return None
        return {
            "access_token": decrypt_text(_config.access_token) if _config.access_token else None,
            "refresh_token": decrypt_text(_config.refresh_token) if _config.refresh_token else None,
            "token_expires_at": _config.token_expires_at,
        }
