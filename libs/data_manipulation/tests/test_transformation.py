import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from data_manipulation.transformation.transform import apply_transformations
from data_manipulation.transformation.transform_encoding import apply_encoding
from data_manipulation.transformation.transform_projection import apply_projection


def test_apply_encoding_basic():
    """Test basic encoding transformation"""
    df = pd.DataFrame({"text": ["Hello", "World"], "number": [1, 2]})

    result = apply_encoding(df, "utf-8")

    assert isinstance(result, pd.DataFrame)
    assert "text" in result.columns
    assert len(result) == 2


def test_apply_projection_basic():
    """Test basic projection transformation"""
    gdf = gpd.GeoDataFrame(
        {"name": ["A", "B"]}, geometry=[Point(0, 0), Point(1, 1)], crs="EPSG:4326"
    )

    result = apply_projection(gdf, "EPSG:3857")

    assert isinstance(result, gpd.GeoDataFrame)
    assert result.crs.to_string() == "EPSG:3857"  # type: ignore[misc]
    assert len(result) == 2


def test_apply_transformations_with_geometry():
    """Test apply_transformations with geometry creation"""
    df = pd.DataFrame({"lon": [1.0, 2.0], "lat": [48.0, 49.0], "name": ["Paris", "Lyon"]})

    config: dict[str, str | object | None] = {
        "force_projection": {"type": "EPSG:4326", "x_column": "lon", "y_column": "lat"}
    }

    result = apply_transformations(df, config)

    assert isinstance(result, gpd.GeoDataFrame)
    assert "geometry" in result.columns
    assert len(result) == 2


def test_apply_transformations_with_encoding():
    """Test apply_transformations with encoding"""
    df = pd.DataFrame({"text": ["café", "élève"], "number": [1, 2]})

    config: dict[str, str | object | None] = {"encoding": "utf-8"}

    result = apply_transformations(df, config)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2


def test_apply_transformations_empty_config():
    """Test apply_transformations with empty config returns unchanged data"""
    df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})

    result = apply_transformations(df, {})

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3
    assert list(result.columns) == ["col1", "col2"]


def test_apply_encoding_with_accents():
    """Test encoding transformation with accented characters"""
    df = pd.DataFrame({"city": ["Paris", "Zürich", "Montréal"], "code": [1, 2, 3]})

    result = apply_encoding(df, "utf-8")

    assert isinstance(result, pd.DataFrame)
    assert "city" in result.columns
    assert len(result) == 3


def test_apply_encoding_mixed_types():
    """Test encoding with mixed column types (text and numeric)"""
    df = pd.DataFrame({"text": ["Hello", "World"], "number": [1, 2], "float": [1.5, 2.5]})

    result = apply_encoding(df, "utf-8")

    assert isinstance(result, pd.DataFrame)
    assert result["number"].dtype in [int, "int64"]
    assert result["float"].dtype in [float, "float64"]


def test_apply_projection_coordinate_change():
    """Test that projection actually changes coordinates"""
    gdf = gpd.GeoDataFrame(
        {"name": ["Point"]},
        geometry=[Point(2.3522, 48.8566)],  # Paris coordinates
        crs="EPSG:4326",
    )

    result = apply_projection(gdf, "EPSG:3857")

    # Coordinates should be different after reprojection
    original_coords = (2.3522, 48.8566)
    new_coords = (result.geometry.iloc[0].x, result.geometry.iloc[0].y)  # type: ignore[misc]

    assert new_coords != original_coords
    assert result.crs.to_string() == "EPSG:3857"  # type: ignore[misc]


def test_apply_projection_multiple_points():
    """Test projection with multiple points"""
    points = [Point(0, 0), Point(1, 1), Point(2, 2), Point(-1, -1)]
    gdf = gpd.GeoDataFrame({"id": [1, 2, 3, 4]}, geometry=points, crs="EPSG:4326")

    result = apply_projection(gdf, "EPSG:3857")

    assert isinstance(result, gpd.GeoDataFrame)
    assert len(result) == 4
    assert result.crs.to_string() == "EPSG:3857"  # type: ignore[misc]
    assert all(result.geometry.is_valid)


def test_apply_transformations_geometry_and_encoding():
    """Test combining geometry creation and encoding"""
    df = pd.DataFrame(
        {"lon": [2.3522, 4.8357], "lat": [48.8566, 45.7640], "city": ["Paris", "Lyon"]}
    )

    config = {
        "force_projection": {"type": "EPSG:4326", "x_column": "lon", "y_column": "lat"},
        "encoding": "utf-8",
    }

    result = apply_transformations(df, config)  # type: ignore[misc]

    assert isinstance(result, gpd.GeoDataFrame)
    assert "geometry" in result.columns
    assert "city" in result.columns
    assert len(result) == 2
