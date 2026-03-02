import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from src.core.config import get_settings
from src.core.logging import get_logger

router = APIRouter(prefix="/geonetwork", tags=["GeoNetwork"])
logger = get_logger()

# Hop-by-hop headers that should not be forwarded
HOP_BY_HOP_HEADERS = {
    "authorization",  # Don't forward frontend JWT, we add our own GN auth
    "connection",
    "content-encoding",  # httpx auto-decompresses, so don't forward encoding header
    "cookie",  # Don't forward browser cookies, we use Basic Auth
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "x-forwarded-prefix",  # Causes GeoNetwork internal routing issues
}

# Header prefixes that should not be forwarded (geOrchestra security headers)
FILTERED_HEADER_PREFIXES = ("sec-",)


def _get_geonetwork_auth() -> tuple[str, str]:
    """Get GeoNetwork authentication credentials."""
    settings = get_settings()
    return (settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD)


def _should_filter_header(header_name: str) -> bool:
    """Check if a header should be filtered out."""
    lower_name = header_name.lower()
    if lower_name in HOP_BY_HOP_HEADERS:
        return True
    if lower_name.startswith(FILTERED_HEADER_PREFIXES):
        return True
    return False


def _filter_headers(headers: dict[str, str]) -> dict[str, str]:
    """Filter out hop-by-hop and security proxy headers that shouldn't be forwarded."""
    return {k: v for k, v in headers.items() if not _should_filter_header(k)}


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    summary="GeoNetwork proxy",
    description="Pass-through proxy to GeoNetwork. Forwards all requests transparently.",
    include_in_schema=False,
)
async def proxy_geonetwork(path: str, request: Request) -> Response:
    """
    Full pass-through proxy to GeoNetwork.

    Preserves:
    - HTTP method
    - Headers (except hop-by-hop)
    - Query parameters
    - Request body
    - Response status code, headers, and content
    """
    settings = get_settings()

    # Build upstream URL
    upstream_base = settings.GEONETWORK_URL.rstrip("/")
    upstream_url = f"{upstream_base}/{path}"

    # Preserve query string
    if request.url.query:
        upstream_url = f"{upstream_url}?{request.url.query}"

    # Filter and forward headers
    headers = _filter_headers(dict(request.headers))
    headers["X-XSRF-TOKEN"] = settings.GEONETWORK_XSRF_TOKEN
    headers["Cookie"] = f"XSRF-TOKEN={settings.GEONETWORK_XSRF_TOKEN}"

    # Get body for methods that support it
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()

    logger.info(f"Proxying {request.method} request to GeoNetwork: {upstream_url}")
    try:
        async with httpx.AsyncClient() as client:
            upstream_response = await client.request(
                method=request.method,
                url=upstream_url,
                headers=headers,
                content=body,
                auth=_get_geonetwork_auth(),
                timeout=30.0,
            )

        # Return response preserving status, headers, and content
        response_headers = _filter_headers(dict(upstream_response.headers))

        return Response(
            content=upstream_response.content,
            status_code=upstream_response.status_code,
            headers=response_headers,
            media_type=upstream_response.headers.get("content-type"),
        )

    except httpx.TimeoutException:
        logger.error(f"Timeout proxying to GeoNetwork: {upstream_url}")
        raise HTTPException(status_code=504, detail="GeoNetwork request timeout")
    except httpx.RequestError as e:
        logger.error(f"Failed to proxy to GeoNetwork: {e}")
        raise HTTPException(status_code=502, detail="Failed to connect to GeoNetwork")
