from unittest.mock import MagicMock, patch

import pytest

from src.services.geoserver import GeoServerService


class TestGeoServerService:
    """Test cases for GeoServerService."""

    @pytest.fixture
    def geoserver_service(self):
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
    async def test_create_workspace_with_defaults(self, geoserver_service):
        """Test create_workspace with default parameters."""
        workspace_name = "test_workspace"

        result = await geoserver_service.create_workspace(workspace_name=workspace_name)

        # Verify workspace creation was called
        geoserver_service.geoserver.create_workspace.assert_called_once_with(workspace_name)

        # Verify datastore creation with defaults
        geoserver_service.geoserver.create_jndi_datastore.assert_called_once_with(
            workspace_name=workspace_name,
            datastore_name=f"datafeeder_{workspace_name}",
            jndi_reference="jdbc/datakern",
            pg_schema=workspace_name,
            description=f"Datafeeder uploaded datasets for {workspace_name}",
        )

        # Verify return value
        assert result == {
            "workspace": workspace_name,
            "datastore": f"datafeeder_{workspace_name}",
            "schema": workspace_name,
        }

    @pytest.mark.asyncio
    async def test_create_workspace_with_custom_parameters(self, geoserver_service):
        """Test create_workspace with custom parameters."""
        workspace_name = "custom_workspace"
        datastore_name = "custom_datastore"
        jndi_reference = "jdbc/custom"
        pg_schema = "custom_schema"

        result = await geoserver_service.create_workspace(
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            jndi_reference=jndi_reference,
            pg_schema=pg_schema,
        )

        # Verify workspace creation
        geoserver_service.geoserver.create_workspace.assert_called_once_with(workspace_name)

        # Verify datastore creation with custom parameters
        geoserver_service.geoserver.create_jndi_datastore.assert_called_once_with(
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            jndi_reference=jndi_reference,
            pg_schema=pg_schema,
            description=f"Datafeeder uploaded datasets for {workspace_name}",
        )

        # Verify return value
        assert result == {
            "workspace": workspace_name,
            "datastore": datastore_name,
            "schema": pg_schema,
        }

    @pytest.mark.asyncio
    async def test_create_workspace_handles_exceptions(self, geoserver_service):
        """Test that exceptions from GeoServerCloud are propagated."""
        workspace_name = "error_workspace"
        geoserver_service.geoserver.create_workspace.side_effect = Exception(
            "GeoServer connection error"
        )

        with pytest.raises(Exception, match="GeoServer connection error"):
            await geoserver_service.create_workspace(workspace_name=workspace_name)

    @pytest.mark.asyncio
    async def test_create_workspace_datastore_error(self, geoserver_service):
        """Test that datastore creation errors are propagated."""
        workspace_name = "test_workspace"
        geoserver_service.geoserver.create_jndi_datastore.side_effect = Exception(
            "Datastore creation failed"
        )

        with pytest.raises(Exception, match="Datastore creation failed"):
            await geoserver_service.create_workspace(workspace_name=workspace_name)

        # Verify workspace was created before the error
        geoserver_service.geoserver.create_workspace.assert_called_once_with(workspace_name)

    def test_geoserver_service_initialization(self):
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

    def test_geoserver_service_default_initialization(self):
        """Test GeoServerService initialization with default parameters."""
        with patch("src.services.geoserver.GeoServerCloud") as mock_gs_cloud:
            GeoServerService()

            mock_gs_cloud.assert_called_once_with(
                url="http://localhost:8080/geoserver",
                user="admin",
                password="admin",
            )
