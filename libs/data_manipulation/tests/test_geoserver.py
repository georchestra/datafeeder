"""Tests for GeoServer utilities in data_manipulation library."""

from unittest.mock import MagicMock, patch

import pytest
from geoservercloud.models.featuretype import FeatureType

from data_manipulation.geoserver import (  # type: ignore[reportUnknownVariableType]
    create_layer,
    create_workspace,
)


def _geoserver_mock() -> MagicMock:
    """GeoServerCloud mock wired for the REST calls create_workspace makes."""
    geoserver = MagicMock()
    geoserver.rest_service.rest_client.get.return_value.json.return_value = {
        "namespace": {"uri": "http://test_workspace"}
    }
    return geoserver


class TestCreateWorkspace:
    """Test cases for create_workspace function."""

    @pytest.fixture
    def mock_geoserver(self) -> MagicMock:
        """Create a mock GeoServerCloud instance."""
        return _geoserver_mock()

    def test_create_workspace_success(self, mock_geoserver: MagicMock) -> None:
        """Test successful workspace and datastore creation."""
        result = create_workspace(
            geoserver=mock_geoserver,
            workspace_name="test_workspace",
            datastore_name="test_datastore",
            jndi_reference="jdbc/datafeeder",
            pg_schema="test_schema",
            description="Test description",
        )

        mock_geoserver.create_workspace.assert_called_once_with("test_workspace")

        mock_geoserver.rest_service.create_datastore.assert_called_once()
        kwargs = mock_geoserver.rest_service.create_datastore.call_args.kwargs
        assert kwargs["workspace_name"] == "test_workspace"
        datastore = kwargs["datastore"]
        assert datastore.connection_parameters["jndiReferenceName"] == "jdbc/datafeeder"
        assert datastore.connection_parameters["schema"] == "test_schema"
        # The namespace must match the one GeoServer reports for the workspace, not a
        # pattern guessed from its name.
        assert datastore.connection_parameters["namespace"] == "http://test_workspace"

        assert result.workspace == "test_workspace"
        assert result.datastore == "test_datastore"
        assert result.pg_schema == "test_schema"

    def test_create_workspace_defaults_schema_to_workspace_name(
        self, mock_geoserver: MagicMock
    ) -> None:
        """Test that a None pg_schema falls back to the sanitized workspace name."""
        result = create_workspace(
            geoserver=mock_geoserver,
            workspace_name="Test Workspace",
            datastore_name="test_datastore",
            jndi_reference="jdbc/datafeeder",
            pg_schema=None,
        )

        assert result.workspace == "test_workspace"
        assert result.pg_schema == "test_workspace"

    def test_create_workspace_handles_workspace_error(self, mock_geoserver: MagicMock) -> None:
        """Test that workspace creation errors are propagated."""
        mock_geoserver.create_workspace.side_effect = Exception("Workspace creation failed")

        with pytest.raises(Exception, match="Workspace creation failed"):
            create_workspace(
                geoserver=mock_geoserver,
                workspace_name="test_workspace",
                datastore_name="test_datastore",
                jndi_reference="jdbc/datafeeder",
                pg_schema="test_schema",
                description="Test description",
            )

        mock_geoserver.create_workspace.assert_called_once()
        mock_geoserver.rest_service.create_datastore.assert_not_called()

    def test_create_workspace_handles_datastore_error(self, mock_geoserver: MagicMock) -> None:
        """Test that datastore creation errors are propagated."""
        mock_geoserver.rest_service.create_datastore.side_effect = Exception(
            "Datastore creation failed"
        )

        with pytest.raises(Exception, match="Datastore creation failed"):
            create_workspace(
                geoserver=mock_geoserver,
                workspace_name="test_workspace",
                datastore_name="test_datastore",
                jndi_reference="jdbc/datafeeder",
                pg_schema="test_schema",
                description="Test description",
            )

        mock_geoserver.create_workspace.assert_called_once()
        mock_geoserver.rest_service.create_datastore.assert_called_once()


class TestCreateLayer:
    """Test cases for create_layer function."""

    @pytest.fixture
    def mock_geoserver(self) -> MagicMock:
        """Create a mock GeoServerCloud instance."""
        geoserver = MagicMock()
        geoserver.url = "http://localhost:8080/geoserver"
        geoserver.auth = ("admin", "geoserver")
        return geoserver

    def test_create_layer_success(self, mock_geoserver: MagicMock) -> None:
        """Test successful layer creation."""
        with patch("data_manipulation.geoserver.RestService") as rest_service_class:
            rest_service = rest_service_class.return_value

            create_layer(
                geoserver=mock_geoserver,
                workspace_name="test_workspace",
                datastore_name="test_datastore",
                table_name="test_table",
                title="Test Layer",
                abstract="Test layer description",
            )

        rest_service_class.assert_called_once_with(
            url=mock_geoserver.url,
            auth=mock_geoserver.auth,
        )
        rest_service.create_feature_type.assert_called_once()

        feature_type = rest_service.create_feature_type.call_args[0][0]
        assert isinstance(feature_type, FeatureType)
        payload = feature_type.post_payload()["featureType"]
        assert payload["name"] == "test_table"
        assert payload["nativeName"] == "test_table"
        assert payload["title"] == "Test Layer"
        assert payload["abstract"] == "Test layer description"
        assert payload["srs"] == "EPSG:4326"

        # No error, so the existence fallback must not run.
        mock_geoserver.get_feature_type.assert_not_called()

    def test_create_layer_defaults_datastore_title_and_abstract(
        self, mock_geoserver: MagicMock
    ) -> None:
        """Test that omitted datastore/title/abstract are derived from the table name."""
        with patch("data_manipulation.geoserver.RestService") as rest_service_class:
            rest_service = rest_service_class.return_value

            create_layer(
                geoserver=mock_geoserver,
                workspace_name="test_workspace",
                datastore_name=None,
                table_name="test_table",
            )

        feature_type = rest_service.create_feature_type.call_args[0][0]
        payload = feature_type.post_payload()["featureType"]
        assert payload["title"] == "test_table"
        assert payload["abstract"] == "test_table"
        assert payload["store"]["name"] == "test_workspace:test_workspace_ds"

    def test_create_layer_with_error_but_layer_exists(self, mock_geoserver: MagicMock) -> None:
        """Test layer creation when create_feature_type fails but layer exists."""
        mock_geoserver.get_feature_type.return_value = {"name": "test_table"}

        with patch("data_manipulation.geoserver.RestService") as rest_service_class:
            rest_service = rest_service_class.return_value
            rest_service.create_feature_type.side_effect = Exception("500 Server Error")

            # The layer exists despite the error, so this must not raise.
            create_layer(
                geoserver=mock_geoserver,
                workspace_name="test_workspace",
                datastore_name="test_datastore",
                table_name="test_table",
                title="Test Layer",
                abstract="Test layer description",
            )

        rest_service.create_feature_type.assert_called_once()
        mock_geoserver.get_feature_type.assert_called_once_with(
            workspace_name="test_workspace",
            datastore_name="test_datastore",
            feature_type_name="test_table",
        )

    def test_create_layer_with_error_and_layer_not_exists(self, mock_geoserver: MagicMock) -> None:
        """Test layer creation when create_feature_type fails and layer doesn't exist."""
        mock_geoserver.get_feature_type.side_effect = Exception("Layer not found")

        with patch("data_manipulation.geoserver.RestService") as rest_service_class:
            rest_service = rest_service_class.return_value
            rest_service.create_feature_type.side_effect = Exception("Table does not exist")

            with pytest.raises(Exception, match="Failed to create layer 'test_table' in GeoServer"):
                create_layer(
                    geoserver=mock_geoserver,
                    workspace_name="test_workspace",
                    datastore_name="test_datastore",
                    table_name="test_table",
                    title="Test Layer",
                    abstract="Test layer description",
                )

        rest_service.create_feature_type.assert_called_once()
        mock_geoserver.get_feature_type.assert_called_once()

    def test_create_layer_propagates_real_error(self, mock_geoserver: MagicMock) -> None:
        """Test that real errors during layer creation are propagated."""
        mock_geoserver.get_feature_type.side_effect = Exception("Layer not found")

        with patch("data_manipulation.geoserver.RestService") as rest_service_class:
            rest_service_class.return_value.create_feature_type.side_effect = Exception(
                "Connection timeout"
            )

            with pytest.raises(Exception) as exc_info:
                create_layer(
                    geoserver=mock_geoserver,
                    workspace_name="test_workspace",
                    datastore_name="test_datastore",
                    table_name="nonexistent_table",
                    title="Test Layer",
                    abstract="Test layer description",
                )

        assert "Connection timeout" in str(exc_info.value)
        assert "nonexistent_table" in str(exc_info.value)

    def test_create_layer_non_geographic_success(self, mock_geoserver: MagicMock) -> None:
        """Test successful layer creation for non-geographic data with fake bounds."""
        epsg = 2154

        with patch("data_manipulation.geoserver.RestService") as rest_service_class:
            rest_service = rest_service_class.return_value

            create_layer(
                geoserver=mock_geoserver,
                workspace_name="test_workspace",
                datastore_name="test_datastore",
                table_name="test_table",
                title="Test Non-Geographic Layer",
                abstract="Test non-geographic layer description",
                epsg=epsg,
                is_geographic=False,
            )

        rest_service.create_feature_type.assert_called_once()
        feature_type = rest_service.create_feature_type.call_args[0][0]
        assert isinstance(feature_type, FeatureType)
        payload = feature_type.post_payload()["featureType"]

        assert payload["name"] == "test_table"
        assert payload["srs"] == f"EPSG:{epsg}"

        # is_geographic=False skips bbox derivation, so the default placeholder bounds
        # are sent as-is and GeoServer treats the layer as having no valid extent.
        native_bbox = payload["nativeBoundingBox"]
        assert (native_bbox["minx"], native_bbox["miny"]) == (-1.0, -1.0)
        assert (native_bbox["maxx"], native_bbox["maxy"]) == (0.0, 0.0)
        assert native_bbox["crs"]["$"] == f"EPSG:{epsg}"
        assert native_bbox["crs"]["@class"] == "projected"

        latlon_bbox = payload["latLonBoundingBox"]
        assert (latlon_bbox["minx"], latlon_bbox["miny"]) == (-1.0, -1.0)
        assert (latlon_bbox["maxx"], latlon_bbox["maxy"]) == (0.0, 0.0)
        assert latlon_bbox["crs"] == "EPSG:4326"
