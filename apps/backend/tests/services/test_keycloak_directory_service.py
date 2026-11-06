from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.services.directory_service import DirectoryServiceError
from src.services.keycloak_directory_service import KeycloakDirectoryService

MODULE = "src.services.keycloak_directory_service"
ADMIN_URL = "http://kc.example.com/admin/realms/georchestra"

PSC = {
    "id": "g-psc",
    "name": "PSC",
    "attributes": {"o": ["Project Steering Committee"], "mail": ["psc@example.org"]},
}
C2C = {"id": "g-c2c", "name": "C2C", "attributes": {}}


def _response(payload: Any) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    return response


def _service(org_group_path: str = "") -> KeycloakDirectoryService:
    provider = MagicMock()
    provider.get_token.return_value = "token"
    return KeycloakDirectoryService(
        "http://kc.example.com/", "georchestra", provider, org_group_path=org_group_path
    )


class TestOrganizations:
    @patch(f"{MODULE}.httpx.get")
    def test_get_all_organizations_maps_groups(self, mock_get: MagicMock) -> None:
        """Given top-level groups, then they are returned as console-shaped organizations."""
        mock_get.return_value = _response([PSC, C2C])

        result = _service().get_all_organizations()

        assert result == [
            {
                "id": "g-psc",
                "shortName": "PSC",
                "name": "Project Steering Committee",
                "mail": "psc@example.org",
            },
            {"id": "g-c2c", "shortName": "C2C", "name": "C2C", "mail": None},
        ]
        assert mock_get.call_args.args[0] == f"{ADMIN_URL}/groups"
        assert mock_get.call_args.kwargs["params"] == {"briefRepresentation": "false", "max": "-1"}

    @patch(f"{MODULE}.httpx.get")
    def test_get_all_organizations_under_parent_group(self, mock_get: MagicMock) -> None:
        """Given KEYCLOAK_ORG_GROUP_PATH, then the organizations are its children."""
        mock_get.side_effect = [_response({"id": "parent"}), _response([PSC])]

        result = _service("/orgs").get_all_organizations()

        assert [o["shortName"] for o in result] == ["PSC"]
        assert mock_get.call_args_list[0].args[0] == f"{ADMIN_URL}/group-by-path/orgs"
        assert mock_get.call_args_list[1].args[0] == f"{ADMIN_URL}/groups/parent/children"

    @patch(f"{MODULE}.httpx.get")
    def test_get_all_organizations_raises_on_error(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = httpx.ConnectError("down")

        with pytest.raises(DirectoryServiceError):
            _service().get_all_organizations()

    @patch(f"{MODULE}.httpx.get")
    def test_code_attribute_is_the_short_name(self, mock_get: MagicMock) -> None:
        """With a code attribute, the group name is the organization name."""
        mock_get.return_value = _response(
            [{"id": "g1", "name": "Project Steering Committee", "attributes": {"cn": ["PSC"]}}, C2C]
        )
        provider = MagicMock()
        provider.get_token.return_value = "token"
        service = KeycloakDirectoryService(
            "http://kc.example.com", "georchestra", provider, org_code_attribute="cn"
        )

        orgs = service.get_all_organizations()

        assert orgs[0]["shortName"] == "PSC"
        assert orgs[0]["name"] == "Project Steering Committee"
        assert orgs[1]["shortName"] == "C2C", "no code attribute: the group name"
        assert service.get_organization("PSC") == orgs[0]

    @patch(f"{MODULE}.httpx.get")
    def test_only_flagged_groups_are_organizations(self, mock_get: MagicMock) -> None:
        flagged = {
            **PSC,
            "attributes": {
                "o": ["Project Steering Committee"],
                "mail": ["psc@example.org"],
                "isOrganization": ["true"],
            },
        }
        mock_get.return_value = _response([flagged, C2C])
        provider = MagicMock()
        provider.get_token.return_value = "token"
        service = KeycloakDirectoryService(
            "http://kc.example.com", "georchestra", provider, org_flag_attribute="isOrganization"
        )

        assert [o["shortName"] for o in service.get_all_organizations()] == ["PSC"]

    @patch(f"{MODULE}.httpx.get")
    def test_get_organization_by_short_name(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _response([PSC, C2C])

        result = _service().get_organization("C2C")

        assert result is not None
        assert result["id"] == "g-c2c"

    @patch(f"{MODULE}.httpx.get")
    def test_get_organization_unknown_or_error_returns_none(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _response([PSC])
        assert _service().get_organization("UNKNOWN") is None

        mock_get.side_effect = httpx.ConnectError("down")
        assert _service().get_organization("PSC") is None

    @patch(f"{MODULE}.httpx.get")
    def test_fetch_organizations_by_short_names(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _response([PSC, C2C])

        result = _service().fetch_organizations_by_short_names(["PSC", "OTHER"])

        assert result == {"PSC": "Project Steering Committee"}

    @patch(f"{MODULE}.httpx.get")
    def test_fetch_organizations_by_short_names_degrades_gracefully(
        self, mock_get: MagicMock
    ) -> None:
        mock_get.side_effect = httpx.ConnectError("down")
        assert _service().fetch_organizations_by_short_names(["PSC"]) == {}
        assert _service().fetch_organizations_by_short_names([]) == {}


class TestGroups:
    PROJET = {
        "id": "g-projet",
        "name": "Projet Littoral",
        "path": "/Projet Littoral",
        "attributes": {"cn": ["PROJET_LITTORAL"], "isOrganization": ["false"]},
    }

    @patch(f"{MODULE}.httpx.get")
    def test_get_all_groups_includes_plain_groups(self, mock_get: MagicMock) -> None:
        flagged = {**PSC, "path": "/PSC", "attributes": {"isOrganization": ["true"]}}
        mock_get.return_value = _response([flagged, self.PROJET])
        provider = MagicMock()
        provider.get_token.return_value = "token"
        service = KeycloakDirectoryService(
            "http://kc.example.com",
            "georchestra",
            provider,
            org_code_attribute="cn",
            org_flag_attribute="isOrganization",
        )

        assert [g["shortName"] for g in service.get_all_organizations()] == ["PSC"]
        assert [g["shortName"] for g in service.get_all_groups()] == ["PSC", "PROJET_LITTORAL"]

    @patch(f"{MODULE}.httpx.get")
    def test_get_user_groups(self, mock_get: MagicMock) -> None:
        """Top-level groups of the user, organization or not; subgroups are ignored."""
        subgroup = {"id": "g-sub", "name": "editors", "path": "/Projet Littoral/editors"}
        mock_get.side_effect = [
            _response([{"id": "u1", "username": "testuser"}]),
            _response([{**PSC, "path": "/PSC"}, self.PROJET, subgroup]),
        ]
        provider = MagicMock()
        provider.get_token.return_value = "token"
        service = KeycloakDirectoryService(
            "http://kc.example.com", "georchestra", provider, org_code_attribute="cn"
        )

        groups = service.get_user_groups("testuser")

        assert [g["id"] for g in groups] == ["g-psc", "g-projet"]
        assert mock_get.call_args_list[1].args[0] == f"{ADMIN_URL}/users/u1/groups"

    @patch(f"{MODULE}.httpx.get")
    def test_get_user_groups_degrades_gracefully(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = httpx.ConnectError("down")
        assert _service().get_user_groups("testuser") == []


class TestRoles:
    @patch(f"{MODULE}.httpx.get")
    def test_get_all_roles_skips_keycloak_builtin_roles(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _response(
            [
                {"id": "r1", "name": "GN_EDITOR", "description": "Edit in GeoNetwork"},
                {"id": "r2", "name": "offline_access"},
                {"id": "r3", "name": "uma_authorization"},
                {"id": "r4", "name": "default-roles-georchestra"},
                {"id": "r5", "name": "IMPORT"},
            ]
        )

        result = _service().get_all_roles()

        assert result == [
            {"id": "r1", "name": "GN_EDITOR", "description": "Edit in GeoNetwork"},
            {"id": "r5", "name": "IMPORT", "description": None},
        ]
        assert mock_get.call_args.args[0] == f"{ADMIN_URL}/roles"

    @patch(f"{MODULE}.httpx.get")
    def test_get_all_roles_raises_on_error(self, mock_get: MagicMock) -> None:
        response = _response(None)
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Forbidden", request=MagicMock(), response=MagicMock(status_code=403)
        )
        mock_get.return_value = response

        with pytest.raises(DirectoryServiceError):
            _service().get_all_roles()


class TestUsers:
    @patch(f"{MODULE}.httpx.get")
    def test_fetch_users_by_usernames(self, mock_get: MagicMock) -> None:
        """One exact lookup per distinct username; users without a name are omitted."""
        mock_get.side_effect = [
            _response([{"username": "jdoe", "firstName": "John", "lastName": "Doe"}]),
            _response([{"username": "noname"}]),
            _response([]),
        ]

        result = _service().fetch_users_by_usernames(["jdoe", "noname", "jdoe", "ghost"])

        assert result == {"jdoe": "John Doe"}
        assert mock_get.call_count == 3
        assert mock_get.call_args_list[0].kwargs["params"] == {
            "username": "jdoe",
            "exact": "true",
            "briefRepresentation": "true",
        }

    @patch(f"{MODULE}.httpx.get")
    def test_fetch_users_by_usernames_degrades_gracefully(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = httpx.ConnectError("down")
        assert _service().fetch_users_by_usernames(["jdoe"]) == {}
