"""Local HTTP server that hosts the Plaid Link flow in the user's browser.

Flow:
  1. Serve a dark-themed HTML page that loads the Plaid Link JS SDK.
  2. Open the page in the default browser.
  3. User authenticates with their bank inside the Plaid Link iframe.
  4. On success, the page POSTs the public_token + metadata back to the server.
  5. The server captures the result and shuts down.
"""

import json
import logging
import socket
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

_logger = logging.getLogger('budget_app.plaid_link_server')

# Inline HTML page — dark theme, loads Plaid Link JS
_LINK_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Link Bank Account</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: #1e1e2e; color: #cdd6f4;
    display: flex; align-items: center; justify-content: center;
    height: 100vh;
  }
  .container { text-align: center; max-width: 480px; padding: 2rem; }
  h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
  p  { color: #a6adc8; margin-bottom: 1.5rem; }
  .status { font-size: 1rem; margin-top: 1rem; }
  .success { color: #a6e3a1; }
  .error   { color: #f38ba8; }
  .spinner {
    display: inline-block; width: 24px; height: 24px;
    border: 3px solid #45475a; border-top-color: #89b4fa;
    border-radius: 50%; animation: spin 0.8s linear infinite;
    vertical-align: middle; margin-right: 8px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
<script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
</head>
<body>
<div class="container">
  <h1>Personal Budget Manager</h1>
  <p>Connecting to your bank via Plaid...</p>
  <div id="status" class="status"><span class="spinner"></span> Loading Plaid Link&hellip;</div>
</div>
<script>
const LINK_TOKEN = "{{LINK_TOKEN}}";
const CALLBACK  = "{{CALLBACK_URL}}";

const handler = Plaid.create({
  token: LINK_TOKEN,
  onSuccess: function(public_token, metadata) {
    document.getElementById("status").innerHTML =
      '<span class="success">&#10003; Connected! You can close this tab.</span>';
    fetch(CALLBACK, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({public_token: public_token, metadata: metadata})
    });
  },
  onExit: function(err, metadata) {
    if (err) {
      document.getElementById("status").innerHTML =
        '<span class="error">&#10007; ' + (err.display_message || err.error_message || 'Link closed') + '</span>';
      fetch(CALLBACK, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({error: err, metadata: metadata})
      });
    } else {
      document.getElementById("status").innerHTML =
        '<span class="error">Link closed without connecting.</span>';
      fetch(CALLBACK, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({cancelled: true})
      });
    }
  },
  onLoad: function() {
    handler.open();
  }
});
</script>
</body>
</html>"""


class _LinkHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Plaid Link page."""

    def log_message(self, format, *args):
        _logger.debug(format, *args)

    def do_GET(self):
        html = _LINK_HTML.replace(
            "{{LINK_TOKEN}}", self.server.link_token
        ).replace(
            "{{CALLBACK_URL}}", f"http://127.0.0.1:{self.server.server_port}/callback"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            self.server.result = json.loads(body)
        except json.JSONDecodeError:
            self.server.result = {"error": "Invalid JSON from Plaid Link"}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

        # Signal the server to stop after sending response
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


class PlaidLinkServer(HTTPServer):
    """HTTP server that captures the Plaid Link callback."""

    def __init__(self, link_token: str):
        # Find a free port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        sock.close()

        super().__init__(('127.0.0.1', port), _LinkHandler)
        self.link_token = link_token
        self.result: Optional[dict] = None


def run_plaid_link(link_token: str, timeout: int = 300) -> dict:
    """Launch Plaid Link in the browser and wait for the callback.

    Args:
        link_token: The link_token from Plaid's API.
        timeout: Max seconds to wait (default 5 minutes).

    Returns:
        Dict with 'public_token' and 'metadata' on success,
        or 'error'/'cancelled' keys on failure.
    """
    server = PlaidLinkServer(link_token)
    url = f"http://127.0.0.1:{server.server_port}/"
    _logger.info("Starting Plaid Link server at %s", url)

    # Serve with a timeout
    server.timeout = timeout
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    webbrowser.open(url)

    thread.join(timeout=timeout)
    server.server_close()

    if server.result is None:
        return {"error": "Plaid Link timed out — no response received."}
    return server.result
