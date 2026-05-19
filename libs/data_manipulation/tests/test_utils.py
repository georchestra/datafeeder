"""Unit tests for data_manipulation.utils module."""

from unittest.mock import MagicMock, patch

from data_manipulation.constants import POSTGIS_TABLE_NAME_MAX_LENGTH
from data_manipulation.utils import resolve_url, sanitize_name


class TestSanitizeName:
    """Test cases for the sanitize_name function."""

    def test_basic_name(self):
        """Test basic alphanumeric name remains unchanged (except lowercase)."""
        assert sanitize_name("MyOrganization") == "myorganization"
        assert sanitize_name("testlayer") == "testlayer"
        assert sanitize_name("Layer123") == "layer123"

    def test_spaces_replaced_with_underscores(self):
        """Test that spaces are replaced with underscores."""
        assert sanitize_name("My Organization Name") == "my_organization_name"
        assert sanitize_name("test layer name") == "test_layer_name"
        assert sanitize_name("a b c") == "a_b_c"

    def test_special_characters_removed(self):
        """Test that special characters are removed."""
        assert sanitize_name("Org@123 #Test!") == "org123_test"
        assert sanitize_name("test$layer%name") == "testlayername"
        assert sanitize_name("name&with*symbols") == "namewithsymbols"
        assert sanitize_name("email@domain.com") == "emaildomaincom"

    def test_hyphens_preserved(self):
        """Test that hyphens are preserved (they're allowed)."""
        assert sanitize_name("test-layer-name") == "test-layer-name"
        assert sanitize_name("my-org-123") == "my-org-123"

    def test_underscores_preserved(self):
        """Test that underscores are preserved."""
        assert sanitize_name("test_layer_name") == "test_layer_name"
        assert sanitize_name("my_org_123") == "my_org_123"

    def test_multiple_underscores_and_hyphens(self):
        """Test that multiple consecutive underscores/hyphens are preserved."""
        assert sanitize_name("test--layer__name") == "test--layer__name"
        assert sanitize_name("name___with---many") == "name___with---many"

    def test_leading_trailing_underscores_removed(self):
        """Test that leading and trailing underscores are removed."""
        assert sanitize_name("_MyOrg_") == "myorg"
        assert sanitize_name("__test__") == "test"
        assert sanitize_name("_layer") == "layer"
        assert sanitize_name("layer_") == "layer"

    def test_leading_trailing_hyphens_removed(self):
        """Test that leading and trailing hyphens are removed."""
        assert sanitize_name("-MyOrg-") == "myorg"
        assert sanitize_name("--test--") == "test"
        assert sanitize_name("-layer") == "layer"
        assert sanitize_name("layer-") == "layer"

    def test_mixed_leading_trailing_chars_removed(self):
        """Test that mixed leading/trailing underscores and hyphens are removed."""
        assert sanitize_name("_-test-_") == "test"
        assert sanitize_name("-_layer_-") == "layer"

    def test_starts_with_number_prefixed(self):
        """Test that names starting with numbers get 'layer_' prefix."""
        assert sanitize_name("123_dataset") == "layer_123_dataset"
        assert sanitize_name("2024data") == "layer_2024data"
        assert sanitize_name("9test") == "layer_9test"

    def test_lowercase_conversion(self):
        """Test that all names are converted to lowercase."""
        assert sanitize_name("UPPERCASE") == "uppercase"
        assert sanitize_name("MixedCase") == "mixedcase"
        assert sanitize_name("TEST_LAYER_NAME") == "test_layer_name"

    def test_complex_cases(self):
        """Test complex real-world scenarios."""
        assert sanitize_name("My Organization 2024!") == "my_organization_2024"
        assert sanitize_name("__Test Layer #1__") == "test_layer_1"
        assert sanitize_name("@@@123DataSet") == "layer_123dataset"
        assert sanitize_name("Layer (v2.0)") == "layer_v20"

    def test_default_truncates_to_63(self):
        """Default cap matches PostgreSQL's identifier length."""
        result = sanitize_name("a" * 100)
        assert len(result) == 63

    def test_custom_max_length_truncates(self):
        """max_length overrides the default 63-char cap."""
        result = sanitize_name("a" * 100, max_length=POSTGIS_TABLE_NAME_MAX_LENGTH)
        assert len(result) == POSTGIS_TABLE_NAME_MAX_LENGTH

    def test_empty_after_sanitization(self):
        """Test edge case where sanitization might result in empty string."""
        # Note: This would result in empty string after removing special chars
        result = sanitize_name("@@@")
        assert result == ""

    def test_unicode_characters(self):
        """Test that unicode/accented characters are replaced with their base ASCII equivalents."""
        assert sanitize_name("café_layer") == "cafe_layer"
        assert sanitize_name("naïve_dataset") == "naive_dataset"
        assert sanitize_name("über_test") == "uber_test"

    def test_only_numbers(self):
        """Test name that is only numbers gets prefixed."""
        assert sanitize_name("123456") == "layer_123456"

    def test_starts_with_special_char_then_number(self):
        """Test name starting with special char followed by number."""
        # After removing special chars and stripping, if it starts with number, prefix it
        assert sanitize_name("@123test") == "layer_123test"
        assert sanitize_name("_-_9data") == "layer_9data"


class TestResolveUrl:
    """Test cases for the resolve_url function."""

    def _mock_response(self, status_code: int, location: str | None = None) -> MagicMock:
        response = MagicMock()
        response.status_code = status_code
        response.headers = {"Location": location} if location else {}
        return response

    @patch("data_manipulation.utils.requests.head")
    def test_no_redirect_returns_original_url(self, mock_head: MagicMock):
        """Test that a 200 response returns the original URL unchanged."""
        mock_head.return_value = self._mock_response(200)
        url = "https://example.com/data.geojson"
        assert resolve_url(url) == url

    @patch("data_manipulation.utils.requests.head")
    def test_absolute_redirect_location_returned_as_is(self, mock_head: MagicMock):
        """Test that an absolute Location header is returned directly."""
        mock_head.return_value = self._mock_response(302, "https://cdn.example.com/data.geojson")
        result = resolve_url("https://example.com/data.geojson")
        assert result == "https://cdn.example.com/data.geojson"

    @patch("data_manipulation.utils.requests.head")
    def test_relative_redirect_location_made_absolute(self, mock_head: MagicMock):
        """Test that a relative Location header is resolved against the original URL."""
        mock_head.return_value = self._mock_response(
            302, "/delay/5000/https:/gist.githubusercontent.com/file.geojson"
        )
        result = resolve_url(
            "https://app.requestly.io/delay/5000/https://gist.githubusercontent.com/file.geojson"
        )
        assert (
            result
            == "https://app.requestly.io/delay/5000/https:/gist.githubusercontent.com/file.geojson"
        )

    @patch("data_manipulation.utils.requests.head")
    def test_redirect_without_location_returns_original_url(self, mock_head: MagicMock):
        """Test that a 3xx without Location header returns the original URL."""
        mock_head.return_value = self._mock_response(301, None)
        url = "https://example.com/data.geojson"
        assert resolve_url(url) == url
