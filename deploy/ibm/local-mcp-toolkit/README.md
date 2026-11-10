# watsonx Orchestrate — Local MCP Toolkit (stdio)

Register your MCP server as a **local MCP toolkit**: you ship the server *code*
to watsonx Orchestrate, which installs it (via a `requirements.txt`) and runs it
**over stdio inside the Orchestrate runtime**. There is **no HTTP endpoint, no
container, no Code Engine, and no image registry** — the lowest-overhead path
for a novice to get a Python MCP server into Orchestrate.

> **Why this is the lowest-overhead route.** Ranked by setup burden:
>
> | Option | You must… | Overhead |
> |---|---|---|
> | **Local MCP toolkit (this kit)** | drop a `server.py` + `requirements.txt`, run one command | **Lowest** — reuses your FastMCP server unchanged; no HTTP, no deploy |
> | **Remote MCP toolkit** (`../code-engine-git-build/`, `../prebuilt-image/`) | build/deploy an HTTP server to Code Engine, manage a public URL | Medium — cloud deploy + (maybe) registry authority |
>
> Trade-off: it runs *inside* Orchestrate with a ~100–300 ms process-startup cost
> per call (fine for moderate use), and it only works from a machine that has the
> ADK + your repo.

## How it reuses this template

`server.py` in this folder is a tiny stdio entrypoint that imports the existing
FastMCP app (`example_server.app:mcp`) and runs it over stdio. The register
script stages a **flattened** copy of the package so **you do not duplicate or
rewrite any tool code** — edits in `src/example_server/` are picked up on the
next import.

```
deploy/ibm/local-mcp-toolkit/
├── server.py           # stdio entrypoint: `from example_server.app import mcp; mcp.run(transport="stdio")`
├── requirements.txt    # pinned runtime deps staged next to the package
├── toolkit.yaml        # import config template (kind: mcp, command: python server.py, tools: *)
├── register-toolkit.sh # stage flattened package_root + activate ADK env + import (idempotent)
├── .env.example        # instance URL + env/toolkit names (no secrets)
└── README.md           # this runbook
```

> **How the register script assembles the upload:** Orchestrate uploads
> `package_root`, installs a `requirements.txt` found there, then runs `command`
> over stdio. The script builds a small **staging** dir (`_stage/`, git-ignored)
> containing a **flattened** copy of the package — `example_server/` and
> `server.py` at the top level (no `src/` prefix) plus the pinned
> `requirements.txt` — and points `package_root` at it. This avoids a 413
> (uploading the whole repo), a `ModuleNotFoundError` (src-layout not importable
> at runtime), and a missing-deps error (the ADK reads `requirements.txt`).

---

## Part 1 — Prerequisites

```bash
pip install --upgrade ibm-watsonx-orchestrate   # Python 3.11-3.14
orchestrate --version
```

Your Orchestrate instance URL + API key are on the wxO service page in IBM Cloud
(Resource List → your watsonx Orchestrate instance).

> **Security:** treat the API key as a secret. Pass it via `WXO_API_KEY`; never
> commit it.

---

## Part 2 — Register the toolkit

### 2.1 Configure the env file

```bash
cp deploy/ibm/local-mcp-toolkit/.env.example deploy/ibm/local-mcp-toolkit/.env
# edit: WXO_INSTANCE_URL, WXO_ENV_NAME / TOOLKIT_NAME (defaults are fine)
set -a; source deploy/ibm/local-mcp-toolkit/.env; set +a
```

### 2.2 Provide your API keys and run the register script

```bash
export WXO_API_KEY="<your Orchestrate API key>"   # else prompted (hidden)
export BLS_API_KEY="<your BLS API key>"           # else prompted (hidden); omit to use v1
bash deploy/ibm/local-mcp-toolkit/register-toolkit.sh
```

The script:
1. Creates/updates the `bls_api_connection` key_value connection in Orchestrate,
   injecting `BLS_API_KEY` for both `draft` and `live` environments.
2. Activates the ADK env and stages a minimal flattened `package_root`.
3. Imports (or re-imports) the toolkit, bound to `bls_api_connection`.
4. Lists toolkits to confirm, then cleans up.

It is idempotent — re-runs pick up code/dependency changes and refresh the key.

> **BLS API key:** Register free at <https://data.bls.gov/registrationEngine/>.
> Without a key the server falls back to BLS API v1 (25 req/day, 10-year range).
> With a v2 key: 500 req/day, 20-year range.

> **If you renamed the package** from `example_server`, run with
> `PACKAGE_NAME=<your_pkg>` exported (and update `server.py`'s import).

### 2.2a Corporate TLS interception (Zscaler / GSA network) — may be required

On a GSA-managed network the ADK's IAM login may fail with
`SSLCertVerificationError: unable to get local issuer certificate`. This is a
TLS-inspection proxy re-signing HTTPS with a private CA that Python's `certifi`
bundle doesn't trust. Fix by giving Python a CA bundle that includes the proxy
root exported from the keychain:

```bash
# 1. Confirm interception (issuer names your proxy, e.g. Zscaler):
openssl s_client -connect iam.cloud.ibm.com:443 -showcerts </dev/null 2>/dev/null \
  | openssl x509 -noout -issuer

# 2. Export the proxy root(s) from the macOS System keychain:
security find-certificate -a -c "Zscaler" -p /Library/Keychains/System.keychain \
  > /tmp/zscaler-roots.pem 2>/dev/null
security find-certificate -a -c "Zscaler" -p /System/Library/Keychains/SystemRootCertificates.keychain \
  >> /tmp/zscaler-roots.pem 2>/dev/null

# 3. Merge with certifi:
CERTIFI="$(python -c 'import certifi; print(certifi.where())')"
cat "$CERTIFI" /tmp/zscaler-roots.pem > /tmp/wxo-ca-bundle.pem

# 4. Point the ADK at the merged bundle IN THIS SHELL, then run the register script:
export SSL_CERT_FILE=/tmp/wxo-ca-bundle.pem
export REQUESTS_CA_BUNDLE=/tmp/wxo-ca-bundle.pem
```

### 2.3 (Optional) Verify the entrypoint locally first

```bash
# From the repo root, with the repo installed (uv sync or pip install -e .):
python deploy/ibm/local-mcp-toolkit/server.py
# It blocks waiting for MCP stdio input; Ctrl-C to exit. No error = good.
```

---

## Part 3 — Build an agent that uses it

In the Orchestrate UI, create/edit an agent, add your toolkit's tools, give it a
clear instruction, and chat-test a question.

---

## BLS API key connection (`bls_api_connection`)

The toolkit uses a `key_value` connection named `bls_api_connection` to inject
`BLS_API_KEY` as an environment variable into the stdio process. The register
script creates and configures it automatically — no manual UI steps needed.

If you need to update the key without re-running the full register script:

```bash
# Update the key in both environments
for env in draft live; do
  orchestrate connections set-credentials -a bls_api_connection \
    --env "${env}" -e "BLS_API_KEY=<your_new_key>"
done
```

To inspect the current connection configuration:

```bash
orchestrate connections list
```

> **Note:** Only `key_value` connections are supported for local MCP toolkits.
> The `BLS_API_KEY` is stored in Orchestrate's secret store and never written
> to disk or committed to version control.

---

## Teardown

```bash
orchestrate toolkits remove --name example_mcp_local
```

---

## Known gaps / notes

- **Runs inside Orchestrate:** no public endpoint, so you can't curl it. Verify
  by chat-testing in the UI, or run `server.py` locally (2.3).
- **Startup overhead:** process-per-invocation adds ~100–300 ms/call. Fine for a
  hackathon; for high-frequency tools the ADK docs recommend a Python toolkit.
- **Import machine needs Python + the repo:** run the register script from a
  machine that has the ADK and a checkout of your repo.
