from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.models.integrity_link_rule import RuleValue
from src.services.geoserver import (  # type: ignore[attr-defined]
    _ACL_HEADERS,  # type: ignore[attr-defined]
    ACL_ROLE_EVERYONE,
    AclAccessType,
    GeoServerAclError,
    GeoServerService,
)


class TestGeoServerService:
    """Test cases for GeoServerService."""

    @pytest.fixture
    def geoserver_service(self) -> GeoServerService:
        """Create a GeoServerService instance with mocked GeoServerCloud."""
        with patch("src.services.geoserver.GeoServerCloud"):
            service = GeoServerService(
                base_url="http://test.example.com/geoserver",
                username="testuser",
                password="testpass",
                public_url="http://test.example.com/geoserver",
            )
            service.geoserver = MagicMock()
            return service

    @pytest.mark.asyncio
    @patch("src.services.geoserver.dm_create_workspace")
    async def test_create_workspace(
        self, mock_dm_create_workspace: MagicMock, geoserver_service: GeoServerService
    ) -> None:
        """Test create_workspace with all required parameters."""
        workspace_name = "test_workspace"
        datastore_name = "test_datastore"
        jndi_reference = "jdbc/datafeeder"
        pg_schema = "test_schema"

        # Mock the return value from dm_create_workspace
        expected_result = {
            "workspace": workspace_name,
            "datastore": datastore_name,
            "schema": pg_schema,
        }
        mock_dm_create_workspace.return_value = expected_result

        result = await geoserver_service.create_workspace(
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            jndi_reference=jndi_reference,
            pg_schema=pg_schema,
        )

        # Verify dm_create_workspace was called with correct parameters
        mock_dm_create_workspace.assert_called_once_with(
            geoserver=geoserver_service.geoserver,
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            jndi_reference=jndi_reference,
            pg_schema=pg_schema,
            description=f"Datafeeder datasets for {workspace_name}",
        )

        # Verify return value
        assert result == expected_result

    @pytest.mark.asyncio
    @patch("src.services.geoserver.dm_create_workspace")
    async def test_create_workspace_handles_exceptions(
        self, mock_dm_create_workspace: MagicMock, geoserver_service: GeoServerService
    ) -> None:
        """Test that exceptions from dm_create_workspace are propagated."""
        workspace_name = "error_workspace"
        datastore_name = "error_datastore"
        jndi_reference = "jdbc/datafeeder"
        pg_schema = "error_schema"

        mock_dm_create_workspace.side_effect = Exception("GeoServer connection error")

        with pytest.raises(Exception, match="GeoServer connection error"):
            await geoserver_service.create_workspace(
                workspace_name=workspace_name,
                datastore_name=datastore_name,
                jndi_reference=jndi_reference,
                pg_schema=pg_schema,
            )

    @pytest.mark.asyncio
    @patch("src.services.geoserver.dm_create_layer")
    async def test_create_layer(
        self, mock_dm_create_layer: MagicMock, geoserver_service: GeoServerService
    ) -> None:
        """Test create_layer with all required parameters."""
        workspace_name = "test_workspace"
        datastore_name = "test_datastore"
        table_name = "test_table"
        title = "Test Layer"
        abstract = "Test layer description"

        # Mock the geoserver url
        geoserver_service.geoserver.url = "http://test.example.com/geoserver"

        result = await geoserver_service.create_layer(
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            table_name=table_name,
            title=title,
            abstract=abstract,
        )

        # Verify dm_create_layer was called with correct parameters
        mock_dm_create_layer.assert_called_once_with(
            geoserver=geoserver_service.geoserver,
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            table_name=table_name,
            title=title,
            abstract=abstract,
            epsg=4326,
            is_geographic=True,
            bbox={"minx": -1.0, "miny": -1.0, "maxx": 0.0, "maxy": 0.0},
        )

        # Verify return value structure
        assert result.workspace == workspace_name
        assert result.datastore == datastore_name
        assert result.layer == table_name
        assert result.table == table_name
        assert result.layer_qualified_name == f"{workspace_name}:{table_name}"

        # Verify WMS URLs
        assert result.wms is not None
        assert result.wms.capabilities is not None
        assert result.wms.getmap is not None
        assert result.wms.legend is not None
        assert str(workspace_name) in result.wms.capabilities
        assert str(table_name) in result.wms.getmap

        # Verify WFS URLs
        assert result.wfs is not None
        assert result.wfs.capabilities is not None
        assert result.wfs.getfeature is not None
        assert str(workspace_name) in result.wfs.capabilities
        assert str(table_name) in result.wfs.getfeature

    @pytest.mark.asyncio
    @patch("src.services.geoserver.dm_create_layer")
    async def test_create_layer_handles_exceptions(
        self, mock_dm_create_layer: MagicMock, geoserver_service: GeoServerService
    ) -> None:
        """Test that exceptions from dm_create_layer are propagated."""
        workspace_name = "test_workspace"
        datastore_name = "test_datastore"
        table_name = "test_table"
        title = "Test Layer"
        abstract = "Test layer description"

        mock_dm_create_layer.side_effect = Exception("Layer creation failed")

        with pytest.raises(Exception, match="Layer creation failed"):
            await geoserver_service.create_layer(
                workspace_name=workspace_name,
                datastore_name=datastore_name,
                table_name=table_name,
                title=title,
                abstract=abstract,
            )

    def test_geoserver_service_initialization(self) -> None:
        """Test GeoServerService initialization with custom parameters."""
        with patch("src.services.geoserver.GeoServerCloud") as mock_gs_cloud:
            GeoServerService(
                base_url="http://custom.example.com/geoserver",
                username="customuser",
                password="custompass",
                public_url="http://custom.example.com/geoserver",
            )

            mock_gs_cloud.assert_called_once_with(
                url="http://custom.example.com/geoserver",
                user="customuser",
                password="custompass",
            )

    def test_build_layer_urls_geographic(self, geoserver_service: GeoServerService) -> None:
        """Test build_layer_urls with geographic data (WMS and WFS included)."""
        workspace_name = "test_workspace"
        table_name = "test_table"

        result = geoserver_service.build_layer_urls(
            workspace_name=workspace_name,
            table_name=table_name,
            is_geographic=True,
        )

        # Verify layer_qualified_name
        assert result["layer_qualified_name"] == f"{workspace_name}:{table_name}"

        # Verify ogcfeatures URL
        assert "ogcfeatures" in result
        assert f"collections/{workspace_name}:{table_name}" in result["ogcfeatures"]

        # Verify WFS URLs are present
        assert "wfs" in result
        assert "capabilities" in result["wfs"]
        assert "getfeature" in result["wfs"]
        assert workspace_name in result["wfs"]["capabilities"]
        assert table_name in result["wfs"]["getfeature"]

        # Verify WMS URLs are present
        assert "wms" in result
        assert "capabilities" in result["wms"]
        assert "getmap" in result["wms"]
        assert "legend" in result["wms"]
        assert workspace_name in result["wms"]["capabilities"]
        assert table_name in result["wms"]["getmap"]
        assert table_name in result["wms"]["legend"]

    def test_build_layer_urls_non_geographic(self, geoserver_service: GeoServerService) -> None:
        """Test build_layer_urls with non-geographic data (no WMS/WFS)."""
        workspace_name = "test_workspace"
        table_name = "test_table"

        result = geoserver_service.build_layer_urls(
            workspace_name=workspace_name,
            table_name=table_name,
            is_geographic=False,
        )

        # Verify layer_qualified_name
        assert result["layer_qualified_name"] == f"{workspace_name}:{table_name}"

        # Verify ogcfeatures URL
        assert "ogcfeatures" in result
        assert f"collections/{workspace_name}:{table_name}" in result["ogcfeatures"]

        # Verify WFS URLs are NOT present
        assert "wfs" not in result

        # Verify WMS URLs are NOT present
        assert "wms" not in result

    def test_build_layer_urls_for_metadata_geographic(
        self, geoserver_service: GeoServerService
    ) -> None:
        """Test build_layer_urls_for_metadata with geographic data (filtered URLs)."""
        workspace_name = "test_workspace"
        table_name = "test_table"

        result = geoserver_service.build_layer_urls_for_metadata(
            workspace_name=workspace_name,
            table_name=table_name,
            is_geographic=True,
        )

        # Verify layer_qualified_name
        assert result["layer_qualified_name"] == f"{workspace_name}:{table_name}"

        # Verify ogcfeatures URL
        assert "ogcfeatures" in result

        # Verify WFS URLs are present (only capabilities, no getfeature)
        assert "wfs" in result
        assert "capabilities" in result["wfs"]
        assert "getfeature" not in result["wfs"]  # Filtered out for metadata

        # Verify WMS URLs are present (capabilities and getmap, no legend)
        assert "wms" in result
        assert "capabilities" in result["wms"]
        assert "getmap" in result["wms"]
        assert "legend" not in result["wms"]  # Filtered out for metadata

    def test_build_layer_urls_for_metadata_non_geographic(
        self, geoserver_service: GeoServerService
    ) -> None:
        """Test build_layer_urls_for_metadata with non-geographic data."""
        workspace_name = "test_workspace"
        table_name = "test_table"

        result = geoserver_service.build_layer_urls_for_metadata(
            workspace_name=workspace_name,
            table_name=table_name,
            is_geographic=False,
        )

        # Verify layer_qualified_name
        assert result["layer_qualified_name"] == f"{workspace_name}:{table_name}"

        # Verify ogcfeatures URL
        assert "ogcfeatures" in result

        # Verify WFS URLs are NOT present
        assert "wfs" not in result

        # Verify WMS URLs are NOT present
        assert "wms" not in result

    @pytest.mark.asyncio
    @patch("src.services.geoserver.dm_create_layer")
    async def test_create_layer_non_geographic(
        self, mock_dm_create_layer: MagicMock, geoserver_service: GeoServerService
    ) -> None:
        """Test create_layer with non-geographic data (no WMS/WFS)."""
        workspace_name = "test_workspace"
        datastore_name = "test_datastore"
        table_name = "test_table"
        title = "Test Layer"
        abstract = "Test layer description"

        result = await geoserver_service.create_layer(
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            table_name=table_name,
            title=title,
            abstract=abstract,
            is_geographic=False,
        )

        # Verify dm_create_layer was called with is_geographic=False
        mock_dm_create_layer.assert_called_once_with(
            geoserver=geoserver_service.geoserver,
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            table_name=table_name,
            title=title,
            abstract=abstract,
            epsg=4326,
            is_geographic=False,
            bbox={"minx": -1.0, "miny": -1.0, "maxx": 0.0, "maxy": 0.0},
        )

        # Verify return value structure
        assert result.workspace == workspace_name
        assert result.datastore == datastore_name
        assert result.layer == table_name
        assert result.layer_qualified_name == f"{workspace_name}:{table_name}"

        # Verify WMS is None for non-geographic data
        assert result.wms is None

        # Verify WFS is None for non-geographic data
        assert result.wfs is None

        # Verify ogcfeatures URL is present
        assert result.ogcfeatures is not None
        assert table_name in result.ogcfeatures


class TestAclLayerGet:
    """Tests for acl_layer_get."""

    def test_returns_roles_when_rule_exists(
        self, service: GeoServerService, rest_client: MagicMock
    ) -> None:
        rest_client.get.return_value.status_code = 200
        rest_client.get.return_value.json.return_value = {"geor.my_layer.r": "ROLE_IMPORT,*"}

        result = service.acl_layer_get("geor.my_layer", AclAccessType.READ)

        assert result == ["ROLE_IMPORT", "*"]

    def test_returns_none_when_rule_missing(
        self, service: GeoServerService, rest_client: MagicMock
    ) -> None:
        rest_client.get.return_value.status_code = 200
        rest_client.get.return_value.json.return_value = {}

        result = service.acl_layer_get("geor.my_layer", AclAccessType.READ)

        assert result is None

    def test_raises_on_http_error(self, service: GeoServerService, rest_client: MagicMock) -> None:
        rest_client.get.return_value.status_code = 403
        rest_client.get.return_value.text = "Forbidden"

        with pytest.raises(GeoServerAclError) as exc_info:
            service.acl_layer_get("geor.my_layer", AclAccessType.READ)

        assert exc_info.value.status_code == 403

    def test_trims_whitespace_from_roles(
        self, service: GeoServerService, rest_client: MagicMock
    ) -> None:
        rest_client.get.return_value.status_code = 200
        rest_client.get.return_value.json.return_value = {"geor.my_layer.r": " ROLE_IMPORT , * "}

        result = service.acl_layer_get("geor.my_layer", AclAccessType.READ)

        assert result == ["ROLE_IMPORT", "*"]

    @pytest.fixture
    def service(self) -> GeoServerService:
        with patch("src.services.geoserver.GeoServerCloud"):
            svc = GeoServerService(
                base_url="http://test.example.com/geoserver",
                username="testuser",
                password="testpass",
                public_url="http://test.example.com",
            )
            svc.geoserver = MagicMock()
            return svc

    @pytest.fixture
    def rest_client(self, service: GeoServerService) -> MagicMock:
        client = MagicMock()
        service.geoserver.rest_service.rest_client = client
        return client

    def test_post_success(self, service: GeoServerService, rest_client: MagicMock) -> None:
        rest_client.post.return_value.status_code = 200

        service._acl_write("POST", {"geor.my_layer.r": "ROLE_IMPORT"})  # type: ignore[misc]

        rest_client.post.assert_called_once()

    def test_post_raises_409(self, service: GeoServerService, rest_client: MagicMock) -> None:
        rest_client.post.return_value.status_code = 409
        rest_client.post.return_value.text = "Conflict"

        with pytest.raises(GeoServerAclError) as exc_info:
            service._acl_write("POST", {"geor.my_layer.r": "ROLE_IMPORT"})  # type: ignore[misc]

        assert exc_info.value.status_code == 409

    def test_put_success(self, service: GeoServerService, rest_client: MagicMock) -> None:
        rest_client.put.return_value.status_code = 200

        service._acl_write("PUT", {"geor.my_layer.r": "ROLE_IMPORT"})  # type: ignore[misc]

        rest_client.put.assert_called_once()

    def test_put_raises_on_http_error(
        self, service: GeoServerService, rest_client: MagicMock
    ) -> None:
        rest_client.put.return_value.status_code = 500
        rest_client.put.return_value.text = "Server Error"

        with pytest.raises(GeoServerAclError) as exc_info:
            service._acl_write("PUT", {"geor.my_layer.r": "ROLE_IMPORT"})  # type: ignore[misc]

        assert exc_info.value.status_code == 500

    def test_post_passes_params(self, service: GeoServerService, rest_client: MagicMock) -> None:
        rest_client.post.return_value.status_code = 200
        params = {"key": "value"}

        service._acl_write("POST", {"geor.my_layer.r": "ROLE_IMPORT"}, params=params)  # type: ignore[misc]

        _, kwargs = rest_client.post.call_args
        assert kwargs["params"] == params


class TestAclLayerPostPut:
    """Tests for acl_layer_post and acl_layer_put (delegates to _acl_write)."""

    @pytest.fixture
    def service(self) -> GeoServerService:
        with patch("src.services.geoserver.GeoServerCloud"):
            svc = GeoServerService(
                base_url="http://test.example.com/geoserver",
                username="testuser",
                password="testpass",
                public_url="http://test.example.com",
            )
            svc.geoserver = MagicMock()
            return svc

    def test_acl_layer_post_builds_correct_body(self, service: GeoServerService) -> None:
        service._acl_write = MagicMock()  # type: ignore[method-assign]

        service.acl_layer_post("geor.my_layer", AclAccessType.READ, ["ROLE_IMPORT"])

        service._acl_write.assert_called_once_with("POST", {"geor.my_layer.r": "ROLE_IMPORT"})  # type: ignore[misc]

    def test_acl_layer_post_multiple_roles(self, service: GeoServerService) -> None:
        service._acl_write = MagicMock()  # type: ignore[method-assign]

        service.acl_layer_post(
            "geor.my_layer", AclAccessType.WRITE, ["ROLE_IMPORT", "ROLE_ADMINISTRATOR"]
        )

        call_body = service._acl_write.call_args[0][1]  # type: ignore[misc]
        roles_str = call_body["geor.my_layer.w"]
        assert set(roles_str.split(",")) == {"ROLE_IMPORT", "ROLE_ADMINISTRATOR"}

    def test_acl_layer_put_builds_correct_body(self, service: GeoServerService) -> None:
        service._acl_write = MagicMock()  # type: ignore[method-assign]

        service.acl_layer_put("geor.my_layer", AclAccessType.READ, [ACL_ROLE_EVERYONE])

        service._acl_write.assert_called_once_with("PUT", {"geor.my_layer.r": "*"})  # type: ignore[misc]


class TestAclLayerDelete:
    """Tests for acl_layer_delete."""

    @pytest.fixture
    def service(self) -> GeoServerService:
        with patch("src.services.geoserver.GeoServerCloud"):
            svc = GeoServerService(
                base_url="http://test.example.com/geoserver",
                username="testuser",
                password="testpass",
                public_url="http://test.example.com",
            )
            svc.geoserver = MagicMock()
            return svc

    @pytest.fixture
    def rest_client(self, service: GeoServerService) -> MagicMock:
        client = MagicMock()
        service.geoserver.rest_service.rest_client = client
        return client

    def test_delete_success(self, service: GeoServerService, rest_client: MagicMock) -> None:
        rest_client.delete.return_value.status_code = 200

        service.acl_layer_delete("geor.my_layer", AclAccessType.READ)

        rest_client.delete.assert_called_once_with(
            "/rest/security/acl/layers/geor.my_layer.r",
            headers=_ACL_HEADERS,
        )

    def test_delete_raises_on_http_error(
        self, service: GeoServerService, rest_client: MagicMock
    ) -> None:
        rest_client.delete.return_value.status_code = 404
        rest_client.delete.return_value.text = "Not found"

        with pytest.raises(GeoServerAclError) as exc_info:
            service.acl_layer_delete("geor.my_layer", AclAccessType.READ)

        assert exc_info.value.status_code == 404


class TestAclLayerAddRule:
    """Tests for acl_layer_add_rule (upsert logic)."""

    @pytest.fixture
    def service(self) -> GeoServerService:
        with patch("src.services.geoserver.GeoServerCloud"):
            svc = GeoServerService(
                base_url="http://test.example.com/geoserver",
                username="testuser",
                password="testpass",
                public_url="http://test.example.com",
            )
            svc.geoserver = MagicMock()
            return svc

    def test_post_succeeds_directly(self, service: GeoServerService) -> None:
        service.acl_layer_post = MagicMock()  # type: ignore[method-assign]

        service.acl_layer_add_rule("geor.my_layer", AclAccessType.READ, [ACL_ROLE_EVERYONE])

        service.acl_layer_post.assert_called_once_with(
            "geor.my_layer", AclAccessType.READ, [ACL_ROLE_EVERYONE]
        )

    def test_merges_roles_on_409(self, service: GeoServerService) -> None:
        service.acl_layer_post = MagicMock(side_effect=GeoServerAclError(409, "Conflict"))  # type: ignore[method-assign]
        service.acl_layer_get = MagicMock(return_value=["ROLE_IMPORT"])  # type: ignore[method-assign]
        service.acl_layer_put = MagicMock()  # type: ignore[method-assign]

        service.acl_layer_add_rule("geor.my_layer", AclAccessType.READ, [ACL_ROLE_EVERYONE])

        service.acl_layer_get.assert_called_once_with("geor.my_layer", AclAccessType.READ)
        put_roles = service.acl_layer_put.call_args[0][2]
        assert set(put_roles) == {"ROLE_IMPORT", ACL_ROLE_EVERYONE}

    def test_get_returns_none_on_409_treated_as_empty(self, service: GeoServerService) -> None:
        service.acl_layer_post = MagicMock(side_effect=GeoServerAclError(409, "Conflict"))  # type: ignore[method-assign]
        service.acl_layer_get = MagicMock(return_value=None)  # type: ignore[method-assign]
        service.acl_layer_put = MagicMock()  # type: ignore[method-assign]

        service.acl_layer_add_rule("geor.my_layer", AclAccessType.READ, [ACL_ROLE_EVERYONE])

        put_roles = service.acl_layer_put.call_args[0][2]
        assert set(put_roles) == {ACL_ROLE_EVERYONE}

    def test_reraises_non_409_error(self, service: GeoServerService) -> None:
        service.acl_layer_post = MagicMock(side_effect=GeoServerAclError(500, "Server error"))  # type: ignore[method-assign]

        with pytest.raises(GeoServerAclError) as exc_info:
            service.acl_layer_add_rule("geor.my_layer", AclAccessType.READ, [ACL_ROLE_EVERYONE])

        assert exc_info.value.status_code == 500


class TestAclLayerRemoveRule:
    """Tests for acl_layer_remove_rule."""

    @pytest.fixture
    def service(self) -> GeoServerService:
        with patch("src.services.geoserver.GeoServerCloud"):
            svc = GeoServerService(
                base_url="http://test.example.com/geoserver",
                username="testuser",
                password="testpass",
                public_url="http://test.example.com",
            )
            svc.geoserver = MagicMock()
            return svc

    def test_updates_with_remaining_roles(self, service: GeoServerService) -> None:
        service.acl_layer_get = MagicMock(return_value=["ROLE_IMPORT", ACL_ROLE_EVERYONE])  # type: ignore[method-assign]
        service.acl_layer_put = MagicMock()  # type: ignore[method-assign]
        service.acl_layer_delete = MagicMock()  # type: ignore[method-assign]

        service.acl_layer_remove_rule("geor.my_layer", AclAccessType.READ, [ACL_ROLE_EVERYONE])

        service.acl_layer_put.assert_called_once_with(
            "geor.my_layer", AclAccessType.READ, ["ROLE_IMPORT"]
        )
        service.acl_layer_delete.assert_not_called()

    def test_deletes_when_no_roles_remain(self, service: GeoServerService) -> None:
        service.acl_layer_get = MagicMock(return_value=[ACL_ROLE_EVERYONE])  # type: ignore[method-assign]
        service.acl_layer_put = MagicMock()  # type: ignore[method-assign]
        service.acl_layer_delete = MagicMock()  # type: ignore[method-assign]

        service.acl_layer_remove_rule("geor.my_layer", AclAccessType.READ, [ACL_ROLE_EVERYONE])

        service.acl_layer_delete.assert_called_once_with("geor.my_layer", AclAccessType.READ)
        service.acl_layer_put.assert_not_called()

    def test_get_returns_none_treated_as_empty(self, service: GeoServerService) -> None:
        service.acl_layer_get = MagicMock(return_value=None)  # type: ignore[method-assign]
        service.acl_layer_put = MagicMock()  # type: ignore[method-assign]
        service.acl_layer_delete = MagicMock()  # type: ignore[method-assign]

        service.acl_layer_remove_rule("geor.my_layer", AclAccessType.READ, [ACL_ROLE_EVERYONE])

        service.acl_layer_delete.assert_called_once()
        service.acl_layer_put.assert_not_called()


class TestAclLayerPublishUnpublish:
    """Tests for acl_layer_publish and acl_layer_unpublish."""

    @pytest.fixture
    def service(self) -> GeoServerService:
        with patch("src.services.geoserver.GeoServerCloud"):
            svc = GeoServerService(
                base_url="http://test.example.com/geoserver",
                username="testuser",
                password="testpass",
                public_url="http://test.example.com",
            )
            svc.geoserver = MagicMock()
            return svc

    def test_publish_calls_add_rule_with_everyone(self, service: GeoServerService) -> None:
        service.acl_layer_add_rule = MagicMock()  # type: ignore[method-assign]

        service.acl_layer_publish("geor.my_layer", AclAccessType.READ)

        service.acl_layer_add_rule.assert_called_once_with(
            "geor.my_layer", AclAccessType.READ, [ACL_ROLE_EVERYONE]
        )

    def test_unpublish_calls_delete(self, service: GeoServerService) -> None:
        service.acl_layer_delete = MagicMock()  # type: ignore[method-assign]

        service.acl_layer_unpublish("geor.my_layer", AclAccessType.READ)

        service.acl_layer_delete.assert_called_once_with("geor.my_layer", AclAccessType.READ)


class TestSyncLayerAcl:
    """Tests for GeoServerService.sync_layer_acl and _delete_acl_rule."""

    @pytest.fixture
    def service(self) -> GeoServerService:
        with patch("src.services.geoserver.GeoServerCloud"):
            svc = GeoServerService(
                base_url="http://gs.example.com/geoserver",
                username="admin",
                password="secret",
                public_url="http://gs.example.com/geoserver",
            )
            svc.geoserver = MagicMock()
            return svc

    def _ok(self, status_code: int = 200) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        resp.raise_for_status.return_value = None
        return resp

    def _error(self, status_code: int) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock()
        )
        return resp

    @patch("httpx.post")
    @patch("httpx.delete")
    def test_sync_read_rule_posts_r_rule(
        self, mock_delete: MagicMock, mock_post: MagicMock, service: GeoServerService
    ) -> None:
        mock_post.return_value = self._ok(200)

        service.sync_layer_acl("myws", "mylayer", [("ROLE_IMPORT", RuleValue.READ)])

        mock_post.assert_any_call(
            "http://gs.example.com/geoserver/rest/security/acl/layers",
            json={"myws.mylayer.r": "ROLE_IMPORT"},
            auth=("admin", "secret"),
            timeout=10.0,
        )
        # .w key has no roles → DELETE called
        mock_delete.assert_any_call(
            "http://gs.example.com/geoserver/rest/security/acl/layers/myws.mylayer.w",
            auth=("admin", "secret"),
            timeout=10.0,
        )

    @patch("httpx.post")
    @patch("httpx.delete")
    def test_sync_write_rule_posts_w_rule(
        self, mock_delete: MagicMock, mock_post: MagicMock, service: GeoServerService
    ) -> None:
        mock_post.return_value = self._ok(200)

        service.sync_layer_acl("myws", "mylayer", [("ROLE_EDITOR", RuleValue.WRITE)])

        mock_post.assert_any_call(
            "http://gs.example.com/geoserver/rest/security/acl/layers",
            json={"myws.mylayer.w": "ROLE_EDITOR"},
            auth=("admin", "secret"),
            timeout=10.0,
        )
        mock_delete.assert_any_call(
            "http://gs.example.com/geoserver/rest/security/acl/layers/myws.mylayer.r",
            auth=("admin", "secret"),
            timeout=10.0,
        )

    @patch("httpx.post")
    @patch("httpx.delete")
    def test_sync_multiple_roles_same_access(
        self, mock_delete: MagicMock, mock_post: MagicMock, service: GeoServerService
    ) -> None:
        mock_post.return_value = self._ok(200)

        service.sync_layer_acl(
            "myws",
            "mylayer",
            [("ROLE_A", RuleValue.READ), ("ROLE_B", RuleValue.READ)],
        )

        mock_post.assert_any_call(
            "http://gs.example.com/geoserver/rest/security/acl/layers",
            json={"myws.mylayer.r": "ROLE_A,ROLE_B"},
            auth=("admin", "secret"),
            timeout=10.0,
        )

    @patch("httpx.put")
    @patch("httpx.post")
    @patch("httpx.delete")
    def test_sync_409_falls_back_to_put(
        self,
        mock_delete: MagicMock,
        mock_post: MagicMock,
        mock_put: MagicMock,
        service: GeoServerService,
    ) -> None:
        mock_post.return_value = self._error(409)
        mock_post.return_value.status_code = 409
        mock_post.return_value.raise_for_status.return_value = None
        mock_put.return_value = self._ok(200)

        service.sync_layer_acl("myws", "mylayer", [("ROLE_IMPORT", RuleValue.READ)])

        mock_put.assert_any_call(
            "http://gs.example.com/geoserver/rest/security/acl/layers",
            json={"myws.mylayer.r": "ROLE_IMPORT"},
            auth=("admin", "secret"),
            timeout=10.0,
        )

    @patch("httpx.delete")
    def test_sync_empty_privileges_deletes_both_rules(
        self, mock_delete: MagicMock, service: GeoServerService
    ) -> None:
        mock_delete.return_value = self._ok(200)

        service.sync_layer_acl("myws", "mylayer", [])

        assert mock_delete.call_count == 2
        mock_delete.assert_any_call(
            "http://gs.example.com/geoserver/rest/security/acl/layers/myws.mylayer.r",
            auth=("admin", "secret"),
            timeout=10.0,
        )
        mock_delete.assert_any_call(
            "http://gs.example.com/geoserver/rest/security/acl/layers/myws.mylayer.w",
            auth=("admin", "secret"),
            timeout=10.0,
        )

    @patch("httpx.delete")
    def test_sync_delete_treats_404_as_success(
        self, mock_delete: MagicMock, service: GeoServerService
    ) -> None:
        mock_delete.return_value = self._error(404)
        mock_delete.return_value.status_code = 404

        # Should not raise
        service._delete_acl_rule("myws.mylayer.r")  # type: ignore[reportPrivateUsage]

        mock_delete.assert_called_once()

    @patch("httpx.delete")
    def test_sync_delete_raises_on_other_errors(
        self, mock_delete: MagicMock, service: GeoServerService
    ) -> None:
        mock_delete.return_value = self._error(500)

        with pytest.raises(httpx.HTTPStatusError):
            service._delete_acl_rule("myws.mylayer.r")  # type: ignore[reportPrivateUsage]

    @patch("httpx.post")
    @patch("httpx.delete")
    def test_sync_write_only_deletes_read_rule(
        self, mock_delete: MagicMock, mock_post: MagicMock, service: GeoServerService
    ) -> None:
        mock_post.return_value = self._ok(200)
        mock_delete.return_value = self._ok(200)

        service.sync_layer_acl("myws", "mylayer", [("ROLE_EDITOR", RuleValue.WRITE)])

        # Only .w posted
        assert mock_post.call_count == 1
        mock_post.assert_called_with(
            "http://gs.example.com/geoserver/rest/security/acl/layers",
            json={"myws.mylayer.w": "ROLE_EDITOR"},
            auth=("admin", "secret"),
            timeout=10.0,
        )
        # .r deleted
        mock_delete.assert_called_with(
            "http://gs.example.com/geoserver/rest/security/acl/layers/myws.mylayer.r",
            auth=("admin", "secret"),
            timeout=10.0,
        )

    def test_to_geoserver_role_adds_prefix(self, service: GeoServerService) -> None:
        assert service._to_geoserver_role("IMPORT") == "ROLE_IMPORT"  # type: ignore[reportPrivateUsage]

    def test_to_geoserver_role_idempotent(self, service: GeoServerService) -> None:
        assert service._to_geoserver_role("ROLE_IMPORT") == "ROLE_IMPORT"  # type: ignore[reportPrivateUsage]

    @patch("httpx.post")
    @patch("httpx.delete")
    def test_sync_role_without_prefix_gets_prefixed(
        self, mock_delete: MagicMock, mock_post: MagicMock, service: GeoServerService
    ) -> None:
        """Bare role name stored in DB is prefixed before sending to GeoServer ACL."""
        mock_post.return_value = self._ok(200)

        service.sync_layer_acl("myws", "mylayer", [("IMPORT", RuleValue.READ)])

        mock_post.assert_any_call(
            "http://gs.example.com/geoserver/rest/security/acl/layers",
            json={"myws.mylayer.r": "ROLE_IMPORT"},
            auth=("admin", "secret"),
            timeout=10.0,
        )
