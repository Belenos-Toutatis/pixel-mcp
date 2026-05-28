"""OAuth 2.0 flow with Google Health API: loopback redirect, token persistence, auto-refresh."""

from __future__ import annotations

import json
import os
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx
from dotenv import load_dotenv

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# Full Google Health API scopes (read + write all domains).
_SCOPE_PREFIX = "https://www.googleapis.com/auth/googlehealth"
DEFAULT_SCOPES = [
    f"{_SCOPE_PREFIX}.activity_and_fitness.readonly",
    f"{_SCOPE_PREFIX}.activity_and_fitness.writeonly",
    f"{_SCOPE_PREFIX}.ecg.readonly",
    f"{_SCOPE_PREFIX}.health_metrics_and_measurements.readonly",
    f"{_SCOPE_PREFIX}.health_metrics_and_measurements.writeonly",
    f"{_SCOPE_PREFIX}.irn.readonly",
    f"{_SCOPE_PREFIX}.location.readonly",
    f"{_SCOPE_PREFIX}.nutrition.readonly",
    f"{_SCOPE_PREFIX}.nutrition.writeonly",
    f"{_SCOPE_PREFIX}.profile.readonly",
    f"{_SCOPE_PREFIX}.profile.writeonly",
    f"{_SCOPE_PREFIX}.settings.readonly",
    f"{_SCOPE_PREFIX}.settings.writeonly",
    f"{_SCOPE_PREFIX}.sleep.readonly",
    f"{_SCOPE_PREFIX}.sleep.writeonly",
]

LOOPBACK_HOST = "127.0.0.1"
LOOPBACK_PORT = 8733  # distinct from strava (8731) / old fitbit (8732)
REDIRECT_URI = f"http://{LOOPBACK_HOST}:{LOOPBACK_PORT}/callback"

TOKENS_PATH = Path(os.path.expanduser("~/.config/pixel-mcp/tokens.json"))


@dataclass
class Tokens:
    access_token: str
    refresh_token: str
    expires_at: int
    scope: str

    def to_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "scope": self.scope,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Tokens":
        return cls(
            access_token=d["access_token"],
            refresh_token=d["refresh_token"],
            expires_at=int(d["expires_at"]),
            scope=d.get("scope", ""),
        )


def _save_tokens(tokens: Tokens) -> None:
    TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKENS_PATH.write_text(json.dumps(tokens.to_dict(), indent=2))
    try:
        os.chmod(TOKENS_PATH, 0o600)
    except OSError:
        pass


def _load_tokens() -> Tokens | None:
    if not TOKENS_PATH.exists():
        return None
    try:
        return Tokens.from_dict(json.loads(TOKENS_PATH.read_text()))
    except (json.JSONDecodeError, KeyError):
        return None


class _CallbackHandler(BaseHTTPRequestHandler):
    server_state: dict = {}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        params = urllib.parse.parse_qs(parsed.query)
        state = (params.get("state") or [""])[0]
        if state != self.server_state.get("expected_state"):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"State mismatch")
            return
        code = (params.get("code") or [""])[0]
        self.server_state["code"] = code
        self.server_state["error"] = (params.get("error") or [""])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h2>Pixel MCP connect\xc3\xa9 (Google Health). Tu peux fermer cet onglet.</h2></body></html>"
        )

    def log_message(self, format: str, *args) -> None:
        return


def _exchange_code(client_id: str, client_secret: str, code: str) -> Tokens:
    resp = httpx.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Google token exchange {resp.status_code}: {resp.text}")
    data = resp.json()
    if "refresh_token" not in data:
        raise RuntimeError(
            "Google n'a pas renvoyé de refresh_token. "
            "Révoque l'app sur https://myaccount.google.com/permissions et relance — "
            "ou vérifie que prompt=consent est bien envoyé."
        )
    return Tokens(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=int(time.time()) + int(data["expires_in"]),
        scope=data.get("scope", ""),
    )


def _refresh(client_id: str, client_secret: str, refresh_token: str) -> Tokens:
    resp = httpx.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Google refresh {resp.status_code}: {resp.text}")
    data = resp.json()
    tokens = Tokens(
        access_token=data["access_token"],
        # Google ne renvoie pas systématiquement un nouveau refresh_token.
        refresh_token=data.get("refresh_token", refresh_token),
        expires_at=int(time.time()) + int(data["expires_in"]),
        scope=data.get("scope", ""),
    )
    _save_tokens(tokens)
    return tokens


def _run_oauth_flow(client_id: str, client_secret: str, scopes: list[str]) -> Tokens:
    state = secrets.token_urlsafe(24)
    _CallbackHandler.server_state = {"expected_state": state, "code": None, "error": ""}

    httpd = HTTPServer((LOOPBACK_HOST, LOOPBACK_PORT), _CallbackHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    auth_params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": " ".join(scopes),
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "access_type": "offline",  # nécessaire pour obtenir le refresh_token
        "prompt": "consent",        # force renvoi du refresh_token
        "include_granted_scopes": "true",
    }
    url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"
    print(f"[pixel-mcp] Ouvre ce lien pour autoriser Google Health :\n  {url}", file=sys.stderr)
    try:
        webbrowser.open(url)
    except Exception:
        pass

    deadline = time.time() + 300
    while time.time() < deadline:
        if _CallbackHandler.server_state.get("code") or _CallbackHandler.server_state.get("error"):
            break
        time.sleep(0.25)

    httpd.shutdown()
    code = _CallbackHandler.server_state.get("code")
    err = _CallbackHandler.server_state.get("error")
    if err:
        raise RuntimeError(f"OAuth Google erreur: {err}")
    if not code:
        raise RuntimeError("OAuth Google: timeout en attente du code.")

    tokens = _exchange_code(client_id, client_secret, code)
    _save_tokens(tokens)
    return tokens


class TokenManager:
    """Credentials Google + OAuth bootstrap + refresh auto."""

    def __init__(self, scopes: list[str] | None = None) -> None:
        load_dotenv()
        self.client_id = os.environ.get("GOOGLE_HEALTH_CLIENT_ID", "").strip()
        self.client_secret = os.environ.get("GOOGLE_HEALTH_CLIENT_SECRET", "").strip()
        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "GOOGLE_HEALTH_CLIENT_ID / GOOGLE_HEALTH_CLIENT_SECRET manquants. "
                "Crée un projet sur https://console.cloud.google.com, active la Google Health API, "
                "crée un OAuth client 'Web application' avec redirect "
                f"{REDIRECT_URI} et renseigne .env."
            )
        self.scopes = scopes or DEFAULT_SCOPES
        self._tokens: Tokens | None = _load_tokens()

    def ensure_authorized(self) -> Tokens:
        if self._tokens is None:
            self._tokens = _run_oauth_flow(self.client_id, self.client_secret, self.scopes)
        return self._tokens

    def access_token(self) -> str:
        tokens = self.ensure_authorized()
        if tokens.expires_at - int(time.time()) < 60:
            tokens = _refresh(self.client_id, self.client_secret, tokens.refresh_token)
            self._tokens = tokens
        return tokens.access_token
