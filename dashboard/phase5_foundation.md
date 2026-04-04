# Phase 5 Foundation

This repo had started a broad `phase5_production.py`, but the safer next-step path is
foundational hardening instead of another giant prototype branch.

## What this foundation adds

- a lightweight JSON-backed persistence layer in `storage.py`
- persistence for users, sessions, and alerts across restarts
- a clean stepping stone before committing to PostgreSQL everywhere

## Why this is useful

Right now the prototype loses state on restart. That makes testing annoying and
makes the app feel fake even when the UI is solid. JSON persistence gives us:

- sticky demo sessions / alerts
- fewer moving parts than full Postgres wiring
- a cleaner migration path later

## Next recommended steps

1. Wire `phase4_simple.py` to `storage.py`
2. Move templates out of inline strings into `templates/`
3. Add real profile/settings update endpoints
4. Add database-backed mode behind an env flag
5. Connect real TikTok data only once approval/data access is ready
