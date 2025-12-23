from urllib.parse import urlencode

from src.core.config import get_settings

settings = get_settings()


def build_callback_url(route: str, query_params: dict[str, str] | None = None) -> str:
    """Build full callback URL for Airflow DAG callbacks.

    Args:
        route: Backend route path (e.g., '/print_dag_success')
        query_params: Optional query parameters to append to the URL

    Returns:
        Full URL for the callback endpoint with query parameters
    """
    base_url = f"{settings.BACKEND_URL}{route}"

    if query_params:
        query_string = urlencode(query_params)
        return f"{base_url}?{query_string}"

    return base_url
