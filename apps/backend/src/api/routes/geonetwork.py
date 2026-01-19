import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from src.core.config import get_settings
from src.core.logging import get_logger

router = APIRouter(prefix="/geonetwork", tags=["GeoNetwork"])
logger = get_logger()


def _get_geonetwork_auth() -> tuple[str, str]:
    """Get GeoNetwork authentication credentials."""
    settings = get_settings()
    return (settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD)


@router.get(
    "/metadata/{uuid}/xml",
    summary="Get metadata as XML",
    description="Proxy to GeoNetwork to retrieve metadata record in XML format.",
    responses={
        200: {"content": {"application/xml": {}}},
        404: {"description": "Metadata not found"},
        502: {"description": "GeoNetwork unavailable"},
    },
)
async def get_metadata_xml(uuid: str) -> Response:
    """Fetch metadata XML from GeoNetwork."""
    settings = get_settings()
    geonetwork_url = f"{settings.GEONETWORK_URL}/srv/api/records/{uuid}/formatters/xml"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                geonetwork_url,
                auth=_get_geonetwork_auth(),
                timeout=30.0,
            )

        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Metadata not found")

        response.raise_for_status()

        return Response(
            content=response.content,
            media_type="application/xml",
        )

    except httpx.TimeoutException:
        logger.error(f"Timeout fetching metadata {uuid} from GeoNetwork")
        raise HTTPException(status_code=504, detail="GeoNetwork request timeout")
    except httpx.HTTPStatusError as e:
        logger.error(f"GeoNetwork error for {uuid}: {e.response.status_code}")
        raise HTTPException(status_code=502, detail=f"GeoNetwork error: {e.response.status_code}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch metadata {uuid}: {e}")
        raise HTTPException(status_code=502, detail="Failed to connect to GeoNetwork")
