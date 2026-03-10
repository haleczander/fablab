import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class ProbeResult:
    adapter_name: str
    reachable: bool
    model_hint: str | None
    serial_hint: str | None = None
    details: str | None = None


def _http_get(ip: str, path: str, timeout_s: float) -> tuple[int, str]:
    url = f"http://{ip}{path}"
    request = Request(url=url, method="GET")
    try:
        with urlopen(request, timeout=timeout_s) as response:
            return response.status, response.read().decode("utf-8", errors="ignore")
    except HTTPError as err:
        body = err.read().decode("utf-8", errors="ignore")
        return err.code, body
    except (URLError, TimeoutError):
        return 0, ""


def _infer_model_from_text(text: str) -> str | None:
    normalized = text.upper()
    known_models = [
        "CORE ONE",
        "XL",
        "MK4S",
        "MK4",
        "MK3.9S",
        "MK3.9",
        "MK3.5S",
        "MK3.5",
        "MINI+",
        "MINI",
        "SL1S",
        "SL1",
        "HT90",
    ]
    for model in known_models:
        if model in normalized:
            return model
    return None


def _extract_serial_from_payload(payload: dict) -> str | None:
    serial = payload.get("serial")
    if serial is None:
        return None
    normalized = str(serial).strip()
    return normalized or None


def probe_prusalink(ip: str, timeout_s: float) -> ProbeResult | None:
    candidates = ["/api/v1/info", "/api/v1/status", "/api/version", "/api/printer", "/"]
    for path in candidates:
        status, body = _http_get(ip, path, timeout_s)
        if status == 0:
            continue
        body_upper = body.upper()
        is_prusalink = "PRUSALINK" in body_upper
        if not is_prusalink and status == 200 and path in {"/api/v1/info", "/api/v1/status"} and body:
            try:
                parsed = json.loads(body)
                if path == "/api/v1/info" and isinstance(parsed, dict) and parsed.get("serial"):
                    is_prusalink = True
                if path == "/api/v1/status" and isinstance(parsed, dict) and isinstance(parsed.get("printer"), dict):
                    is_prusalink = True
            except json.JSONDecodeError:
                is_prusalink = False

        if is_prusalink:
            model = None
            serial = None
            if body:
                model = _infer_model_from_text(body)
                if model is None:
                    try:
                        parsed = json.loads(body)
                        model = _infer_model_from_text(json.dumps(parsed))
                        if path == "/api/v1/info":
                            serial = _extract_serial_from_payload(parsed)
                    except json.JSONDecodeError:
                        pass
            return ProbeResult(
                adapter_name="prusalink",
                reachable=True,
                model_hint=model,
                serial_hint=serial,
                details=f"{path} -> {status}",
            )
    return None


def probe_device(ip: str, timeout_s: float) -> ProbeResult:
    prusa = probe_prusalink(ip, timeout_s)
    if prusa:
        return prusa
    status, _ = _http_get(ip, "/", timeout_s)
    if status in {200, 301, 302, 401, 403}:
        return ProbeResult(adapter_name="http-unknown", reachable=True, model_hint=None, details=f"/ -> {status}")
    return ProbeResult(adapter_name="unreachable", reachable=False, model_hint=None, details=None)


class HttpDeviceProber:
    def probe(self, ip: str, timeout_s: float) -> ProbeResult:
        return probe_device(ip=ip, timeout_s=timeout_s)

