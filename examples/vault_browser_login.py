"""Secrets vault — store a credential once, log in without ever re-handling it.

A stateless agent that automates a website has nowhere safe to keep the login: it
either re-prompts a human or carries the password in its context every run. The vault
fixes that. You store the credential ONCE (encrypted at rest under a key derived from
your own agent secret — a DB leak can't read it), and then:

  • vault_login  — the ZERO-EXPOSURE path (MCP): the gateway decrypts server-side and
                   fills the browser form directly. The password NEVER re-enters your
                   context. Shown as commented usage below (needs a real login page).
  • vault_get    — the explicit path, for when YOU must use the secret yourself (e.g. an
                   API Authorization header). Returns the plaintext to you, on purpose.

Everything is owner-gated by your agent secret (Authorization: Bearer) and free. This
script exercises the REST round-trip live; the vault_login block is documented usage.

Run:  python vault_browser_login.py
"""

import json
import urllib.error
import urllib.request

BASE = "https://agent.wingmanprotocol.com"
_KEY = {"v": None}


def _req(path, payload=None, token=None, method=None):
    headers = {"content-type": "application/json"}
    if _KEY["v"]:
        headers["X-API-Key"] = _KEY["v"]
    if token:
        headers["Authorization"] = f"Bearer {token}"  # your agent secret — owner gate
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, headers=headers, method=method or ("POST" if data else "GET")
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "detail": e.read().decode(errors="replace")}


def main():
    _KEY["v"] = _req("/keys/issue", {"email": "you@example.com", "tier": "free"})["api_key"]
    reg = _req("/agents/register", {"handle": "vault-demo", "auto_suffix": True})
    handle, secret = reg["handle"], reg["secret"]
    print(f"registered as: {handle}")

    # 1. Store a credential ONCE (encrypted at rest). The entry NAME is plaintext — never
    #    put a secret in it; the value is what gets encrypted.
    _req("/vault",
         {"handle": handle, "name": "demo-site",
          "value": {"username": "octocat", "password": "s3cr3t-pw"},
          "metadata": {"site": "example.com"}},
         token=secret)

    # 2. List — names + metadata only; values are NEVER returned here.
    listing = _req(f"/vault?handle={handle}", token=secret)
    print("vault entries (no values):", [e["name"] for e in listing["entries"]])

    # 3a. vault_login — the ZERO-EXPOSURE browser path (MCP). You browse_open a login page,
    #     snapshot it for @eN refs, then map each form field to a vault entry[:field]. The
    #     gateway verifies you own the session, decrypts server-side, fills the form, and
    #     returns only {ok,url} — the password never enters this script or the response:
    #
    #       POST /mcp  (Authorization: Bearer <secret>)
    #       {"jsonrpc":"2.0","id":1,"method":"tools/call","params":{
    #         "name":"vault_login",
    #         "arguments":{"handle":"<you>","browser_id":"<from browse_open>",
    #           "vault_fields":{"@e3":"demo-site:username","@e4":"demo-site:password"},
    #           "submit_ref":"@e5"}}}

    # 3b. vault_get — the explicit path, for when YOU need the secret (e.g. an API header).
    got = _req(f"/vault/demo-site?handle={handle}", token=secret)
    print("retrieved (explicit, for your own use):", got["value"]["username"], "+ <password hidden>")

    # 4. Clean up the demo entry.
    _req(f"/vault/demo-site?handle={handle}", token=secret, method="DELETE")
    print("done — entry deleted.")


if __name__ == "__main__":
    main()
