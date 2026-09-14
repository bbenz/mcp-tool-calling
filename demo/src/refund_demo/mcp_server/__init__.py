"""Protected MCP server (Resource A)."""

from .verifier import ValidatingTokenVerifier, principal_from_access_token

__all__ = ["ValidatingTokenVerifier", "principal_from_access_token"]
