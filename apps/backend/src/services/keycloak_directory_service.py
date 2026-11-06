"""Directory backed by the Keycloak admin REST API.

Mapping with the geOrchestra model:

- organization = Keycloak group: ``shortName`` (the code) comes from the
  ``KEYCLOAK_ORG_CODE_ATTRIBUTE`` group attribute, else the group name; ``name`` from the
  ``KEYCLOAK_ORG_NAME_ATTRIBUTE`` group attribute, else the group name; ``mail`` from
  ``KEYCLOAK_ORG_MAIL_ATTRIBUTE``. With a code attribute, the group name is the organization
  name, the only one people manage.
  Organizations are the top-level groups, or the children of ``KEYCLOAK_ORG_GROUP_PATH``.
- role = Keycloak realm role (Keycloak built-in roles are ignored).
- identifiers are the Keycloak group / role ids.

With the geOrchestra LDAP federated in Keycloak (group mapper on ``ou=orgs``, role mapper on
``ou=roles``), this exposes the same organizations and roles as the console did, but with
Keycloak identifiers.

The service account (``KEYCLOAK_CLIENT_ID``) needs the ``realm-management`` client roles
``view-users``, ``query-groups`` and ``view-realm``.
"""

from typing import Any
from urllib.parse import quote

import httpx

from src.core.config import Settings
from src.core.logging import get_logger
from src.services.directory_service import DirectoryServiceError
from src.services.keycloak_auth import KeycloakHttpxAuth, KeycloakTokenProvider, get_token_provider

logger = get_logger()

TIMEOUT_SECONDS = 5.0


class KeycloakDirectoryService:
    def __init__(
        self,
        base_url: str,
        realm: str,
        token_provider: KeycloakTokenProvider,
        org_group_path: str = "",
        org_name_attribute: str = "o",
        org_code_attribute: str = "",
        org_flag_attribute: str = "",
        org_mail_attribute: str = "mail",
    ):
        self.admin_url = f"{base_url.rstrip('/')}/admin/realms/{realm}"
        self.realm = realm
        self.auth = KeycloakHttpxAuth(token_provider)
        self.org_group_path = org_group_path.strip("/")
        self.org_name_attribute = org_name_attribute
        self.org_code_attribute = org_code_attribute
        self.org_flag_attribute = org_flag_attribute
        self.org_mail_attribute = org_mail_attribute

    @classmethod
    def from_settings(cls, settings: Settings) -> "KeycloakDirectoryService":
        return cls(
            base_url=settings.KEYCLOAK_INTERNAL_URL,
            realm=settings.KEYCLOAK_REALM,
            token_provider=get_token_provider(settings),
            org_group_path=settings.KEYCLOAK_ORG_GROUP_PATH,
            org_name_attribute=settings.KEYCLOAK_ORG_NAME_ATTRIBUTE,
            org_code_attribute=settings.KEYCLOAK_ORG_CODE_ATTRIBUTE,
            org_flag_attribute=settings.KEYCLOAK_ORG_FLAG_ATTRIBUTE,
            org_mail_attribute=settings.KEYCLOAK_ORG_MAIL_ATTRIBUTE,
        )

    # ------------------------------------------------------------------ HTTP

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.admin_url}{path}"
        try:
            response = httpx.get(url, params=params, auth=self.auth, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise DirectoryServiceError(f"Keycloak admin API call failed ({url}): {exc}") from exc

    # ------------------------------------------------------------ organizations

    def _org_groups(self) -> list[dict[str, Any]]:
        params = {"briefRepresentation": "false", "max": "-1"}
        if not self.org_group_path:
            return self._get("/groups", params)
        parent = self._get(f"/group-by-path/{quote(self.org_group_path)}")
        return self._get(f"/groups/{parent['id']}/children", params)

    def _to_organization(self, group: dict[str, Any]) -> dict[str, Any]:
        attributes: dict[str, list[str]] = group.get("attributes") or {}

        def first(name: str) -> str | None:
            values = attributes.get(name) or []
            return values[0] if values else None

        return {
            "id": group["id"],
            "shortName": (first(self.org_code_attribute) if self.org_code_attribute else None)
            or group["name"],
            "name": first(self.org_name_attribute) or group["name"],
            "mail": first(self.org_mail_attribute),
        }

    def _is_flagged(self, group: dict[str, Any]) -> bool:
        if not self.org_flag_attribute:
            return True
        values = (group.get("attributes") or {}).get(self.org_flag_attribute) or []
        return bool(values) and str(values[0]).lower() == "true"

    def get_all_organizations(self) -> list[dict[str, Any]]:
        return [self._to_organization(g) for g in self._org_groups() if self._is_flagged(g)]

    def get_all_groups(self) -> list[dict[str, Any]]:
        """Every candidate group (top-level, or child of KEYCLOAK_ORG_GROUP_PATH), organization
        or not"""
        return [self._to_organization(g) for g in self._org_groups()]

    def _is_candidate(self, group: dict[str, Any]) -> bool:
        parent = f"/{self.org_group_path}" if self.org_group_path else ""
        return group.get("path") == f"{parent}/{group.get('name')}"

    def get_user_groups(self, username: str) -> list[dict[str, Any]]:
        try:
            users = self._get(
                "/users", {"username": username, "exact": "true", "briefRepresentation": "true"}
            )
            user = next((u for u in users if u.get("username") == username.lower()), None)
            if user is None:
                return []
            groups = self._get(f"/users/{user['id']}/groups", {"briefRepresentation": "false"})
        except DirectoryServiceError as exc:
            logger.warning("Failed to fetch the groups of user '%s': %s", username, exc)
            return []
        return [self._to_organization(g) for g in groups if self._is_candidate(g)]

    def get_organization(self, org_short_name: str) -> dict[str, Any] | None:
        try:
            organizations = self.get_all_organizations()
        except DirectoryServiceError as exc:
            logger.warning("Failed to fetch organization '%s': %s", org_short_name, exc)
            return None
        organization = next((o for o in organizations if o["shortName"] == org_short_name), None)
        if organization is None:
            logger.info("Organization '%s' not found in Keycloak", org_short_name)
        return organization

    def fetch_organizations_by_short_names(self, short_names: list[str]) -> dict[str, str]:
        if not short_names:
            return {}
        try:
            organizations = self.get_all_organizations()
        except DirectoryServiceError as exc:
            logger.warning("Failed to fetch organization names: %s", exc)
            return {}
        wanted = set(short_names)
        return {o["shortName"]: o["name"] for o in organizations if o["shortName"] in wanted}

    # -------------------------------------------------------------------- roles

    def _is_builtin_role(self, name: str) -> bool:
        return name in {"offline_access", "uma_authorization", f"default-roles-{self.realm}"}

    def get_all_roles(self) -> list[dict[str, Any]]:
        roles = self._get("/roles", {"briefRepresentation": "false", "max": "-1"})
        return [
            {"id": r["id"], "name": r["name"], "description": r.get("description")}
            for r in roles
            if r.get("id") and r.get("name") and not self._is_builtin_role(r["name"])
        ]

    # -------------------------------------------------------------------- users

    def fetch_users_by_usernames(self, usernames: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        for username in dict.fromkeys(usernames):
            try:
                users = self._get(
                    "/users",
                    {"username": username, "exact": "true", "briefRepresentation": "true"},
                )
            except DirectoryServiceError as exc:
                logger.warning("Failed to fetch user display names from Keycloak: %s", exc)
                return {}
            for user in users:
                if user.get("username") != username:
                    continue
                first = (user.get("firstName") or "").strip()
                last = (user.get("lastName") or "").strip()
                display = f"{first} {last}".strip()
                if display:
                    result[username] = display
        return result
