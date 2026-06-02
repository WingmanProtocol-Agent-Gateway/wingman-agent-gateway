"""Call the WingmanProtocol Agent Gateway over plain HTTP (free-tier key)."""
import json
import urllib.request

BASE = "https://agent.wingmanprotocol.com"


def _post(path, payload, headers=None):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"content-type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


if __name__ == "__main__":
    key = _post("/keys/issue", {"email": "you@example.com", "tier": "free"})["api_key"]
    out = _post("/tools/mortgage",
                {"home_price": 400000, "annual_rate": 0.07, "down_payment": 80000},
                headers={"X-API-Key": key})
    print(json.dumps(out, indent=2))
