from unittest.mock import MagicMock, patch

import pytest

from src.services.geoserver import GeoServerService  # type: ignore[attr-defined]


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
        jndi_reference = "jdbc/datakern"
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
            description=f"DataKern datasets for {workspace_name}",
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
        jndi_reference = "jdbc/datakern"
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
        )

        # Verify return value structure
        assert result["workspace"] == workspace_name
        assert result["datastore"] == datastore_name
        assert result["layer"] == table_name
        assert result["table"] == table_name
        assert result["layer_qualified_name"] == f"{workspace_name}:{table_name}"

        # Verify WMS URLs
        assert result["wms"] is not None
        assert "capabilities" in result["wms"]
        assert "getmap" in result["wms"]
        assert "legend" in result["wms"]
        wms = result["wms"]
        wms_capabilities_val = ""
        wms_getmap_val = ""
        if isinstance(wms, dict):
            cap = wms.get("capabilities", "")
            gm = wms.get("getmap", "")
            if isinstance(cap, str):
                wms_capabilities_val = cap
            if isinstance(gm, str):
                wms_getmap_val = gm
        assert str(workspace_name) in wms_capabilities_val
        assert str(table_name) in wms_getmap_val

        # Verify WFS URLs
        assert result["wfs"] is not None
        assert "capabilities" in result["wfs"]
        assert "getfeature" in result["wfs"]
        wfs = result["wfs"]
        capabilities_val = ""
        getfeature_val = ""
        if isinstance(wfs, dict):
            cap = wfs.get("capabilities", "")
            gf = wfs.get("getfeature", "")
            if isinstance(cap, str):
                capabilities_val = cap
            if isinstance(gf, str):
                getfeature_val = gf
        assert str(workspace_name) in capabilities_val
        assert str(table_name) in getfeature_val

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
            )

            mock_gs_cloud.assert_called_once_with(
                url="http://custom.example.com/geoserver",
                user="customuser",
                password="custompass",
            )
