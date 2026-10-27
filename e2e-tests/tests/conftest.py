import threading
from collections.abc import Iterator
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest
from common import E2E_HOST, FILES_DIR, FILES_PORT
from playwright.sync_api import Playwright


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
    }


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="session")
def files_base_url() -> Iterator[str]:
    """Serve ``files/`` over HTTP so URL imports don't depend on a third-party host."""
    server = ThreadingHTTPServer(("", FILES_PORT), partial(_QuietHandler, directory=FILES_DIR))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://{E2E_HOST}:{FILES_PORT}"
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="session")
def advertised_public_layer(playwright: Playwright, base_url: str) -> Iterator[None]:
    """Advertise the stack's ``geor:public_layer`` while the service tests use it.

    The geOrchestra GeoServer image ships it with ``advertised=false``, which hides it
    from GetCapabilities: the wizard's layer picker would then have nothing to list.
    """
    request = playwright.request.new_context(
        base_url=base_url,
        http_credentials={"username": "testadmin", "password": "testadmin"},
    )
    url = "/geoserver/rest/workspaces/geor/datastores/automated_tests/featuretypes/public_layer"

    def set_advertised(advertised: bool) -> None:
        response = request.put(url, data={"featureType": {"advertised": advertised}})
        assert response.ok, f"Could not set advertised={advertised}: {response.status}"

    set_advertised(True)
    yield
    set_advertised(False)
    request.dispose()
