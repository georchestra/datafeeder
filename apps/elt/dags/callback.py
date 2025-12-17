import logging
import requests

logger = logging.getLogger(__name__)

def call_callback(callback_url: str, callback_type: str) -> None:
    """Call a callback URL and log the request and response.

    Args:
        callback_url: The URL to call
        callback_type: Type of callback (e.g., "success", "failure") for logging
    """
    logger.info(f"Calling {callback_type} callback URL: {callback_url}")
    try:
        response = requests.post(callback_url, timeout=10)
        logger.info(
            f"{callback_type.capitalize()} callback responded | "
            f"status_code={response.status_code} | "
            f"response={response.text[:200]}"
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(
            f"{callback_type.capitalize()} callback failed | url={callback_url} | error={str(e)}"
        )
