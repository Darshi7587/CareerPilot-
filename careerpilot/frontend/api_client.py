"""HTTP client helpers for the CareerPilot FastAPI backend."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Iterator

import httpx
import streamlit as st

DEFAULT_BACKEND = os.getenv("CAREERPILOT_BACKEND_URL", "http://127.0.0.1:8000")


@st.cache_resource
def get_http_client() -> httpx.Client:
    return httpx.Client(timeout=120.0)


def backend_url() -> str:
    return st.session_state.get("backend_url", DEFAULT_BACKEND).rstrip("/")


def api_url(path: str) -> str:
    return f"{backend_url()}{path}"


def api_get(path: str, params: dict | None = None, *, silent: bool = False) -> dict | list | None:
    try:
        response = get_http_client().get(api_url(path), params=params or {}, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError:
        if not silent:
            st.error("Cannot reach the backend. Start FastAPI on port 8000.")
    except httpx.HTTPStatusError as exc:
        if not silent:
            st.error(f"Backend error {exc.response.status_code}")
    except Exception as exc:
        if not silent:
            st.error(f"Request failed: {exc}")
    return None


def api_post(path: str, payload: dict | None = None, timeout: float = 120.0, *, silent: bool = False) -> dict | list | None:
    try:
        response = get_http_client().post(api_url(path), json=payload or {}, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError:
        if not silent:
            st.error("Cannot reach the backend. Start FastAPI on port 8000.")
    except httpx.HTTPStatusError as exc:
        if not silent:
            detail = ""
            try:
                detail = exc.response.json().get("detail", "")
            except Exception:
                detail = exc.response.text[:200]
            st.error(f"Backend error {exc.response.status_code}: {detail}")
    except httpx.TimeoutException:
        if not silent:
            st.error("Request timed out.")
    except Exception as exc:
        if not silent:
            st.error(f"Request failed: {exc}")
    return None


def api_upload(path: str, files_data: list[tuple[str, bytes]], session_id: str) -> list | None:
    try:
        files = [("files", (name, data, "application/pdf")) for name, data in files_data]
        response = get_http_client().post(
            api_url(path),
            files=files,
            data={"session_id": session_id},
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError:
        st.error("Cannot reach the backend.")
    except httpx.HTTPStatusError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("detail", "")
        except Exception:
            detail = exc.response.text[:200]
        st.error(f"Upload error {exc.response.status_code}: {detail}")
    except Exception as exc:
        st.error(f"Upload failed: {exc}")
    return None


def api_delete(path: str, params: dict | None = None) -> bool:
    try:
        response = get_http_client().delete(api_url(path), params=params or {}, timeout=30.0)
        response.raise_for_status()
        return True
    except Exception as exc:
        st.error(f"Delete failed: {exc}")
    return False


@st.cache_data(ttl=5)
def check_health(url: str) -> dict[str, str] | None:
    try:
        response = httpx.get(f"{url.rstrip('/')}/health", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def send_chat(message: str, focus: str = "all", *, silent: bool = False) -> dict[str, Any] | None:
    payload = {
        "message": message,
        "session_id": st.session_state.session_id,
        "focus": focus,
    }
    for attempt in range(3):
        try:
            response = get_http_client().post(api_url("/chat"), json=payload, timeout=120.0)
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as exc:
            if attempt < 2:
                time.sleep(0.8 * (attempt + 1))
                continue
            if not silent:
                st.error(f"Backend unavailable after {attempt + 1} attempts: {exc}")
        except httpx.HTTPStatusError as exc:
            if attempt < 2 and exc.response.status_code >= 500:
                time.sleep(0.8 * (attempt + 1))
                continue
            if not silent:
                detail = ""
                try:
                    detail = exc.response.json().get("detail", "")
                except Exception:
                    pass
                st.error(f"Error {exc.response.status_code}: {detail}")
            break
        except Exception as exc:
            if not silent:
                st.error(f"Unexpected error: {exc}")
            break
    return None


def api_reindex(document_id: str, session_id: str) -> dict | None:
    try:
        response = get_http_client().post(
            api_url(f"/documents/{document_id}/reindex"),
            params={"session_id": session_id},
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.error(f"Reindex failed: {exc}")
    return None


def stream_chat(message: str, focus: str = "all") -> Iterator[str]:
    """Yield streamed response chunks from the SSE chat endpoint."""

    payload = {
        "message": message,
        "session_id": st.session_state.session_id,
        "focus": focus,
    }
    meta: dict[str, Any] = {}
    buffer = ""

    with httpx.Client(timeout=120.0) as client:
        with client.stream("POST", api_url("/chat/stream"), json=payload) as response:
            response.raise_for_status()
            event = "message"
            for line in response.iter_lines():
                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    data = line.split(":", 1)[1].strip()
                    if event == "meta":
                        meta.update(json.loads(data))
                        st.session_state._stream_meta = meta
                    elif event == "token":
                        token = json.loads(data)
                        buffer += token
                        yield token
                    elif event == "done":
                        st.session_state._stream_meta = meta
                        st.session_state._stream_full = buffer
                    elif event == "error":
                        raise RuntimeError(json.loads(data).get("detail", "Stream failed"))
