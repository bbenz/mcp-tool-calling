"""Local standards-based development authorization server (local use only)."""

from .server import create_app, issue_access_token

__all__ = ["create_app", "issue_access_token"]
