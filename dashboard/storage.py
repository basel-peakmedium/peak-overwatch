"""
Lightweight persistence layer for Peak Overwatch.

Purpose:
- keep the current prototype usable across restarts
- avoid forcing PostgreSQL before the app actually needs it
- provide a clean upgrade path to a real database later
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / 'data'
STATE_FILE = DATA_DIR / 'state.json'
SESSION_LIFETIME = timedelta(days=7)

DEFAULT_DEMO_PASSWORD_HASH = '$2b$12$1T0pr0LQm1K9D3x7VZlJ7.h6J8XGxTj8mPz0JzQ3A8m8mQ5PpTn2K'

DEFAULT_STATE: dict[str, Any] = {
    'users': {
        'demo@peakoverwatch.com': {
            'id': 1,
            'email': 'demo@peakoverwatch.com',
            'password_hash': DEFAULT_DEMO_PASSWORD_HASH,
            'name': 'Demo User',
            'company': 'Peak Medium',
            'settings': {
                'alert_email': True,
                'alert_notifications': True,
                'fyp_threshold_good': 80,
                'fyp_threshold_warn': 70,
                'fyp_threshold_critical': 60,
            },
            'profiles': [
                {'id': 1, 'username': 'ourviralpicks', 'niche': 'Home & Lifestyle', 'fyp_score': 95, 'last_fyp': 95},
                {'id': 2, 'username': 'homegadgetfinds', 'niche': 'Gadgets & Tech', 'fyp_score': 88, 'last_fyp': 88},
                {'id': 3, 'username': 'beautytrends', 'niche': 'Beauty & Skincare', 'fyp_score': 92, 'last_fyp': 92},
            ],
        }
    },
    'sessions': {},
    'alerts': {},
}


@dataclass
class PersistedUser:
    id: int
    email: str
    password_hash: str
    name: str | None = None
    company: str | None = None
    settings: dict[str, Any] | None = None
    profiles: list[dict[str, Any]] | None = None
    socket_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'PersistedUser':
        return cls(
            id=data['id'],
            email=data['email'],
            password_hash=data['password_hash'],
            name=data.get('name'),
            company=data.get('company'),
            settings=deepcopy(data.get('settings', {})),
            profiles=deepcopy(data.get('profiles', [])),
            socket_id=data.get('socket_id'),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'email': self.email,
            'password_hash': self.password_hash,
            'name': self.name,
            'company': self.company,
            'settings': deepcopy(self.settings or {}),
            'profiles': deepcopy(self.profiles or []),
        }


class JsonStore:
    def __init__(self, path: Path = STATE_FILE):
        self.path = path
        self.lock = Lock()
        self._ensure_seeded()

    def _ensure_seeded(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps(DEFAULT_STATE, indent=2))
            return

        state = json.loads(self.path.read_text())
        demo = state.setdefault('users', {}).setdefault('demo@peakoverwatch.com', {})
        if 'password_hash' not in demo:
            demo['password_hash'] = DEFAULT_DEMO_PASSWORD_HASH
            self.path.write_text(json.dumps(state, indent=2))

    def load(self) -> dict[str, Any]:
        with self.lock:
            return json.loads(self.path.read_text())

    def save(self, state: dict[str, Any]) -> None:
        with self.lock:
            self.path.write_text(json.dumps(state, indent=2))

    def list_users(self) -> dict[str, PersistedUser]:
        state = self.load()
        return {
            email: PersistedUser.from_dict(payload)
            for email, payload in state.get('users', {}).items()
        }

    def upsert_user(self, user: PersistedUser) -> None:
        state = self.load()
        state.setdefault('users', {})[user.email] = user.to_dict()
        self.save(state)

    def get_sessions(self) -> dict[str, dict[str, Any]]:
        state = self.load()
        sessions = state.get('sessions', {})
        now = datetime.now()
        valid = {
            token: payload
            for token, payload in sessions.items()
            if datetime.fromisoformat(payload['expires']) > now
        }
        if len(valid) != len(sessions):
            state['sessions'] = valid
            self.save(state)
        return valid

    def set_session(self, token: str, user_id: int) -> dict[str, Any]:
        state = self.load()
        payload = {
            'user_id': user_id,
            'expires': (datetime.now() + SESSION_LIFETIME).isoformat(),
        }
        state.setdefault('sessions', {})[token] = payload
        self.save(state)
        return payload

    def delete_session(self, token: str) -> None:
        state = self.load()
        if token in state.get('sessions', {}):
            del state['sessions'][token]
            self.save(state)

    def get_alerts(self) -> dict[str, list[dict[str, Any]]]:
        state = self.load()
        return state.get('alerts', {})

    def replace_alerts(self, alerts: dict[str, list[dict[str, Any]]]) -> None:
        state = self.load()
        state['alerts'] = alerts
        self.save(state)
