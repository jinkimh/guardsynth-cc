"""Bounded CPU child tasks. Invoked by the Studio worker, never a web code runner."""

import json
import http.client
import os
import resource
import sys

from .common import dumps


def responses_http(request):
    """One fixed HTTPS POST. Key stays in child memory and Authorization only."""
    connection = None
    try:
        secret = os.environ.get("OPENAI_API_KEY")
        if not secret:
            return {"error_code": "PROVIDER_KEY_MISSING"}
        connection = http.client.HTTPSConnection("api.openai.com", timeout=request["timeout_s"])
        connection.request("POST", "/v1/responses", body=dumps(request["body"]).encode(),
                           headers={"Content-Type": "application/json", "Authorization": "Bearer " + secret})
        response = connection.getresponse()
        if response.status != 200:
            code = {401: "PROVIDER_AUTH", 403: "PROVIDER_AUTH", 429: "PROVIDER_RATE_LIMIT"}.get(response.status, "PROVIDER_HTTP")
            return {"error_code": code}
        raw = response.read(65537)
        if len(raw) > 65536:
            return {"error_code": "PROVIDER_RESPONSE_SIZE"}
        value = json.loads(raw)
        if secret in dumps(value):
            return {"error_code": "PROVIDER_SECRET_ECHO"}
        return {"response": value}
    except TimeoutError:
        return {"error_code": "PROVIDER_TIMEOUT"}
    except (ValueError, UnicodeError):
        return {"error_code": "PROVIDER_JSON"}
    except Exception:
        return {"error_code": "PROVIDER_TRANSPORT"}
    finally:
        if connection:
            connection.close()


def main():
    kind = sys.argv[1]
    cap = (2 if kind in ("PROBE", "EXTRACT") else 1) * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    resource.setrlimit(resource.RLIMIT_CPU, (300 if kind == "EXTRACT" else 30,) * 2)
    request = json.load(sys.stdin)
    if kind == "OPENAI_HTTP":
        result = responses_http(request)
    elif kind == "PROBE":
        from .media import probe
        result = probe(request["path"])
    elif kind == "EXTRACT":
        from .media import extract
        result = extract(request["path"], request["output"], request["interval_s"])
    elif kind in ("CHECK", "CNL"):
        from guard_synth.studio_contract import check, render
        result = check(request["contract"], request["binding"]) if kind == "CHECK" else render(request["contract"], request["binding"], request["check"])
    else:
        raise ValueError("Unknown task")
    print(dumps(result))


if __name__ == "__main__":
    main()
