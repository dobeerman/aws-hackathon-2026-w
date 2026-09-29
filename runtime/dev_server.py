"""Tiny local adapter for the Lambda handler."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app import handler


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()

    def _dispatch(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else None
        event = {
            "rawPath": self.path.split("?", 1)[0],
            "body": body,
            "requestContext": {"http": {"method": self.command}},
        }
        response = handler(event, None)
        self.send_response(response["statusCode"])
        for key, value in response.get("headers", {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response.get("body", "").encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        print(f"[local] {format % args}")


if __name__ == "__main__":
    address = ("127.0.0.1", 8080)
    print(f"Topic Signals running at http://{address[0]}:{address[1]}")
    ThreadingHTTPServer(address, RequestHandler).serve_forever()
