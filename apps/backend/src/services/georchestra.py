"""geOrchestra security context extraction service.

This module provides utilities for extracting security context from
geOrchestra gateway headers injected into requests.
"""

from dataclasses import dataclass

from fastapi import Request


@dataclass
class GeorchestraContext:
    """Security context extracted from geOrchestra gateway headers.

    Attributes:
        username: User's username from sec-username header
        roles: Set of roles (normalized to uppercase) from sec-roles header
        email: User's email from sec-email header
        firstname: User's first name from sec-firstname header
        lastname: User's last name from sec-lastname header
        organization: User's organization from sec-org header
    """

    username: str
    roles: set[str]
    email: str
    firstname: str
    lastname: str
    organization: str

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role.

        Args:
            role: Role name to check (case-insensitive)

        Returns:
            True if user has the specified role, False otherwise
        """
        return role.upper() in self.roles

    def is_administrator(self) -> bool:
        """Check if user has the ADMINISTRATOR role.

        Returns:
            True if user has ADMINISTRATOR role, False otherwise
        """
        return self.has_role("ADMINISTRATOR")


def get_georchestra_context(request: Request) -> GeorchestraContext:
    """Extract geOrchestra security context from request headers.

    Headers injected by geOrchestra gateway:
    - sec-username: User's username (required for authenticated requests)
    - sec-roles: Semicolon-separated roles
    - sec-email: User's email address
    - sec-firstname: User's first name
    - sec-lastname: User's last name
    - sec-org: User's organization

    Args:
        request: FastAPI Request object

    Returns:
        GeorchestraContext with extracted security information
    """
    username = request.headers.get("sec-username", "")
    roles_str = request.headers.get("sec-roles", "")

    # Parse roles: semicolon-separated, normalize to uppercase set
    roles = {r.strip().upper() for r in roles_str.split(";") if r.strip()}

    return GeorchestraContext(
        username=username,
        roles=roles,
        email=request.headers.get("sec-email", ""),
        firstname=request.headers.get("sec-firstname", ""),
        lastname=request.headers.get("sec-lastname", ""),
        organization=request.headers.get("sec-org", ""),
    )
