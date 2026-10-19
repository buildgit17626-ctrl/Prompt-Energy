"""Loopback-only Ollama transport; preserve bytes before interpreting responses."""

import base64
import http.client
import json
import time
from datetime import UTC, datetime
from urllib.parse import urlsplit

from experiments.config import OLLAMA, OLLAMA_RESPONSE_FIELDS, SYSTEM_PROMPT


def utc_now() -> str:
    """Return an unambiguous timestamp for joining later sensor logs."""
    return datetime.now(UTC).isoformat()


def generation_request(model: str, prompt: str, keep_alive: int) -> dict:
    """Explicitly supply all registered decoding options, without chat history."""
    keys = ("temperature", "seed", "num_predict", "num_ctx", "num_thread", "num_gpu", "stop")
    return {
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "keep_alive": keep_alive,
        "options": {key: OLLAMA[key] for key in keys},
    }


class Client:
    """Use direct HTTP so proxy settings and redirects cannot send prompts elsewhere."""

    def __init__(self, base_url: str = OLLAMA["base_url"]) -> None:
        url = urlsplit(base_url)
        if (
            url.scheme != "http"
            or url.hostname not in {"127.0.0.1", "::1"}
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path not in {"", "/"}
        ):
            raise ValueError("Only literal loopback HTTP addresses are permitted")
        self.host = url.hostname
        self.port = url.port or 80

    def exchange(self, path: str, payload: dict | None = None) -> dict:
        """Return an auditable envelope even for HTTP errors or partial transfers."""
        if not path.startswith("/api/"):
            raise ValueError("Expected an Ollama API path")
        started = utc_now()
        start = time.perf_counter()
        timeout = OLLAMA["request_timeout_seconds"]
        connection = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        body = bytearray()
        status = None
        error = None
        try:
            encoded = None if payload is None else json.dumps(payload).encode("utf-8")
            connection.request(
                "GET" if payload is None else "POST",
                path,
                body=encoded,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            status = response.status
            while True:
                remaining = timeout - (time.perf_counter() - start)
                if remaining <= 0:
                    raise TimeoutError("HTTP deadline exceeded")
                if connection.sock is not None:
                    connection.sock.settimeout(remaining)
                chunk = response.read1(65536)
                if not chunk:
                    break
                body.extend(chunk)
        except (OSError, http.client.HTTPException) as exc:
            error = {
                "type": "timeout" if isinstance(exc, TimeoutError) else "transport_error",
                "detail": f"{type(exc).__name__}: {exc}",
            }
        finally:
            connection.close()
        return {
            "started_at": started,
            "ended_at": utc_now(),
            "wall_seconds": time.perf_counter() - start,
            "path": path,
            "request": payload,
            "http_status": status,
            "body_base64": base64.b64encode(body).decode("ascii"),
            "error": error,
        }


def decode_response(envelope: dict, *, generation: bool = False) -> dict:
    """Validate native fields; never reconstruct token counts from text."""
    if envelope["error"]:
        raise ValueError(str(envelope["error"]))
    if envelope["http_status"] != 200:
        raise ValueError(f"HTTP {envelope['http_status']}")
    value = json.loads(base64.b64decode(envelope["body_base64"], validate=True))
    if not isinstance(value, dict) or "error" in value:
        raise ValueError("Invalid/error Ollama object")
    if generation:
        if value.get("done") is not True or not isinstance(value.get("response"), str):
            raise ValueError("Incomplete generation or missing response text")
        for field in OLLAMA_RESPONSE_FIELDS:
            if type(value.get(field)) is not int or value[field] < 0:
                raise ValueError(f"Invalid/missing API measurement: {field}")
        if value["eval_count"] and not value["eval_duration"]:
            raise ValueError("Output tokens without output duration")
    return value
