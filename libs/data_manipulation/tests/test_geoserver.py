"""Tests for GeoServer utilities in data_manipulation library."""

from unittest.mock import MagicMock, patch

import pytest


class TestCreateWorkspace:
    """Test cases for create_workspace function."""

    @pytest.fixture
    def mock_geoserver(self) -> MagicMock:
        """Create a mock GeoServerCloud instance."""
        return MagicMock()

    def test_create_workspace_success(self, mock_geoserver: MagicMock) -> None:
        """Test successful workspace and datastore creation."""
        from data_manipulation.geoserver import (
            create_workspace,  # type: ignore[reportUnknownVariableType]
        )

        workspace_name = "test_workspace"
        datastore_name = "test_datastore"
        jndi_reference = "jdbc/datakern"
        pg_schema = "test_schema"
        description = "Test description"

        create_workspace(
            geoserver=mock_geoserver,
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            jndi_reference=jndi_reference,
            pg_schema=pg_schema,
            description=description,
        )

        # Verify workspace creation was called
        mock_geoserver.create_workspace.assert_called_once_with(workspace_name)

        # Verify JNDI datastore creation was called with correct parameters
        mock_geoserver.create_jndi_datastore.assert_called_once_with(
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            jndi_reference=jndi_reference,
            pg_schema=pg_schema,
            description=description,
        )

    def test_create_workspace_handles_workspace_error(self, mock_geoserver: MagicMock) -> None:
        """Test that workspace creation errors are propagated."""
        from data_manipulation.geoserver import (
            create_workspace,  # type: ignore[reportUnknownVariableType]
        )

        mock_geoserver.create_workspace.side_effect = Exception("Workspace creation failed")

        with pytest.raises(Exception, match="Workspace creation failed"):
            create_workspace(
                geoserver=mock_geoserver,
                workspace_name="test_workspace",
                datastore_name="test_datastore",
                jndi_reference="jdbc/datakern",
                pg_schema="test_schema",
                description="Test description",
            )

        # Verify workspace creation was attempted
        mock_geoserver.create_workspace.assert_called_once()
        # Verify datastore creation was not attempted
        mock_geoserver.create_jndi_datastore.assert_not_called()

    def test_create_workspace_handles_datastore_error(self, mock_geoserver: MagicMock) -> None:
        """Test that datastore creation errors are propagated."""
        from data_manipulation.geoserver import (
            create_workspace,  # type: ignore[reportUnknownVariableType]
        )

        mock_geoserver.create_jndi_datastore.side_effect = Exception("Datastore creation failed")

        with pytest.raises(Exception, match="Datastore creation failed"):
            create_workspace(
                geoserver=mock_geoserver,
                workspace_name="test_workspace",
                datastore_name="test_datastore",
                jndi_reference="jdbc/datakern",
                pg_schema="test_schema",
                description="Test description",
            )

        # Verify both operations were attempted
        mock_geoserver.create_workspace.assert_called_once()
        mock_geoserver.create_jndi_datastore.assert_called_once()


class TestCreateLayer:
    """Test cases for create_layer function."""

    @pytest.fixture
    def mock_geoserver(self) -> MagicMock:
        """Create a mock GeoServerCloud instance."""
        return MagicMock()

    def test_create_layer_success(self, mock_geoserver: MagicMock) -> None:
        """Test successful layer creation."""
        from data_manipulation.geoserver import (
            create_layer,  # type: ignore[reportUnknownVariableType]
        )

        workspace_name = "test_workspace"
        datastore_name = "test_datastore"
        table_name = "test_table"
        title = "Test Layer"
        abstract = "Test layer description"

        create_layer(
            geoserver=mock_geoserver,
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            table_name=table_name,
            title=title,
            abstract=abstract,
        )

        # Verify feature type creation was called
        mock_geoserver.create_feature_type.assert_called_once_with(
            layer_name=table_name,
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            title=title,
            abstract=abstract,
            epsg=4326,
        )

        # Verify get_feature_type was not called (no error occurred)
        mock_geoserver.get_feature_type.assert_not_called()

    def test_create_layer_with_error_but_layer_exists(self, mock_geoserver: MagicMock) -> None:
        """Test layer creation when create_feature_type fails but layer exists."""
        from data_manipulation.geoserver import (
            create_layer,  # type: ignore[reportUnknownVariableType]
        )

        workspace_name = "test_workspace"
        datastore_name = "test_datastore"
        table_name = "test_table"
        title = "Test Layer"
        abstract = "Test layer description"

        # Mock create_feature_type to raise an exception
        mock_geoserver.create_feature_type.side_effect = Exception("500 Server Error")
        # Mock get_feature_type to succeed (layer exists)
        mock_geoserver.get_feature_type.return_value = {"name": table_name}

        # Should not raise an exception
        create_layer(
            geoserver=mock_geoserver,
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            table_name=table_name,
            title=title,
            abstract=abstract,
        )

        # Verify both methods were called
        mock_geoserver.create_feature_type.assert_called_once()
        mock_geoserver.get_feature_type.assert_called_once_with(
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            feature_type_name=table_name,
        )

    def test_create_layer_with_error_and_layer_not_exists(self, mock_geoserver: MagicMock) -> None:
        """Test layer creation when create_feature_type fails and layer doesn't exist."""
        from data_manipulation.geoserver import (
            create_layer,  # type: ignore[reportUnknownVariableType]
        )

        workspace_name = "test_workspace"
        datastore_name = "test_datastore"
        table_name = "test_table"
        title = "Test Layer"
        abstract = "Test layer description"

        error_message = "Table does not exist"

        # Mock create_feature_type to raise an exception
        mock_geoserver.create_feature_type.side_effect = Exception(error_message)
        # Mock get_feature_type to also fail (layer doesn't exist)
        mock_geoserver.get_feature_type.side_effect = Exception("Layer not found")

        # Should raise an exception with the original error
        with pytest.raises(Exception, match=f"Failed to create layer '{table_name}' in GeoServer"):
            create_layer(
                geoserver=mock_geoserver,
                workspace_name=workspace_name,
                datastore_name=datastore_name,
                table_name=table_name,
                title=title,
                abstract=abstract,
            )

        # Verify both methods were called
        mock_geoserver.create_feature_type.assert_called_once()
        mock_geoserver.get_feature_type.assert_called_once()

    def test_create_layer_propagates_real_error(self, mock_geoserver: MagicMock) -> None:
        """Test that real errors during layer creation are propagated."""
        from data_manipulation.geoserver import (
            create_layer,  # type: ignore[reportUnknownVariableType]
        )

        workspace_name = "test_workspace"
        datastore_name = "test_datastore"
        table_name = "nonexistent_table"
        title = "Test Layer"
        abstract = "Test layer description"

        original_error = "Connection timeout"
        mock_geoserver.create_feature_type.side_effect = Exception(original_error)
        mock_geoserver.get_feature_type.side_effect = Exception("Layer not found")

        with pytest.raises(Exception) as exc_info:
            create_layer(
                geoserver=mock_geoserver,
                workspace_name=workspace_name,
                datastore_name=datastore_name,
                table_name=table_name,
                title=title,
                abstract=abstract,
            )

        # Verify the error message contains the original error
        assert original_error in str(exc_info.value)
        assert table_name in str(exc_info.value)

    def test_create_layer_non_geographic_success(self, mock_geoserver: MagicMock) -> None:
        """Test successful layer creation for non-geographic data with fake bounds."""
        from data_manipulation.geoserver import (
            create_layer,  # type: ignore[reportUnknownVariableType]
        )

        workspace_name = "test_workspace"
        datastore_name = "test_datastore"
        table_name = "test_table"
        title = "Test Non-Geographic Layer"
        abstract = "Test non-geographic layer description"
        epsg = 2154

        mock_geoserver.url = "http://localhost:8080/geoserver"
        mock_geoserver.auth = ("admin", "geoserver")

        with patch("data_manipulation.geoserver.RestService") as mock_rest_service_class:
            mock_rest_service_instance = MagicMock()
            mock_rest_service_class.return_value = mock_rest_service_instance

            create_layer(
                geoserver=mock_geoserver,
                workspace_name=workspace_name,
                datastore_name=datastore_name,
                table_name=table_name,
                title=title,
                abstract=abstract,
                epsg=epsg,
                is_geographic=False,
            )

            # Verify that geoserver.create_feature_type was NOT called
            mock_geoserver.create_feature_type.assert_not_called()

            # Verify that RestService was instantiated with correct parameters
            mock_rest_service_class.assert_called_once_with(
                url=mock_geoserver.url,
                auth=mock_geoserver.auth,
            )

            # Verify that RestService.create_feature_type was called
            mock_rest_service_instance.create_feature_type.assert_called_once()

            # Get the FeatureType object that was passed to create_feature_type
            call_args = mock_rest_service_instance.create_feature_type.call_args
            feature_type_arg = call_args[0][0]

            # Verify that a FeatureType was passed
            from geoservercloud.models.featuretype import FeatureType

            assert isinstance(feature_type_arg, FeatureType)

            # Get the serialized payload to verify the fake bounds
            feature_type_dict = feature_type_arg.post_payload()
            feature_type_data = feature_type_dict["featureType"]
            
            # Verify basic properties
            assert feature_type_data["name"] == table_name
            assert feature_type_data["nativeName"] == table_name
            assert feature_type_data["title"] == title
            assert feature_type_data["abstract"] == abstract
            assert feature_type_data["srs"] == f"EPSG:{epsg}"
            
            # Verify the native bounding box has fake bounds
            native_bbox = feature_type_data["nativeBoundingBox"]
            assert native_bbox["minx"] == 0
            assert native_bbox["miny"] == 0
            assert native_bbox["maxx"] == -1
            assert native_bbox["maxy"] == -1
            assert native_bbox["crs"]["$"] == f"EPSG:{epsg}"
            assert native_bbox["crs"]["@class"] == "projected"
            
            # Verify the lat/lon bounding box has fake bounds
            latlon_bbox = feature_type_data["latLonBoundingBox"]
            assert latlon_bbox["minx"] == -1
            assert latlon_bbox["miny"] == -1
            assert latlon_bbox["maxx"] == 0
            assert latlon_bbox["maxy"] == 0
            assert latlon_bbox["crs"] == f"EPSG:{epsg}"
