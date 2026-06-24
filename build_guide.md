# Build and Run Guide

*Complete runbook for setting up and running this system on a Windows + WSL2 machine with Docker Desktop. Generic by design — replace all `<PLACEHOLDER>` values with real credentials. Last updated: 2026-06-24.*

---

## 0. What you need

| Component | Minimum | Notes |
|---|---|---|
| Windows | 10 / 11 | WSL2 support required |
| WSL2 distro | Ubuntu 22.04+ | All commands run inside WSL |
| Docker Desktop | 4.x | WSL2 backend enabled |
| RAM available to Docker | 8 GB | Configure via `.wslconfig` |
| Free disk | 20 GB | Dify images + database volumes |
| Git | any | Available in Ubuntu by default |
| LLM endpoint | OpenAI-compatible | Any `/v1/chat/completions` API |
| Offline plugin bundle | `*-offline.difypkg` | Transfer from source machine (see §3) |

---

## 1. Docker Desktop setup (one-time)

1. **Install Docker Desktop** on Windows. During setup, keep **"Use WSL 2 instead of Hyper-V"** checked.

2. Open Docker Desktop → **Settings → General** → confirm **"Use the WSL 2 based engine"** is ON.

3. **Settings → Resources → WSL Integration** → toggle ON for your Ubuntu distro → **Apply & Restart**.

4. **Give Docker enough RAM.** Create or edit `C:\Users\<you>\.wslconfig` on the Windows side:
   ```ini
   [wsl2]
   memory=8GB
   processors=4
   swap=2GB
   ```
   Then in PowerShell: `wsl --shutdown` (restart WSL to apply the limits).

5. **Verify inside your Ubuntu WSL2 shell:**
   ```bash
   docker --version          # Docker version 27.x or newer
   docker compose version    # Docker Compose version v2.x
   docker run --rm hello-world
   ```
   If `docker` is "command not found", re-check step 3 and restart Docker Desktop.

> **Always work in the Linux filesystem** (`~/...`), never under `/mnt/c/...`. Bind mounts and Dify volumes behave incorrectly on the Windows-side path.

---

## 2. Get the code

Run everything below inside your **Ubuntu WSL2 shell**.

```bash
git clone <repo-url> ~/agi/research/aipg
cd ~/agi/research/aipg
ls dify/docker
# must show: docker-compose.override.yml   .env.dify.example
```

---

## 3. Transfer the offline plugin bundle

The model-provider plugin needs to be installed offline. Transfer the pre-built bundle from the source machine before proceeding:

**On the source machine:**
```bash
# locate it
ls ~/dify-plugin-repackaging/openai_api_compatible-0.0.53-offline.difypkg
```

**Transfer options:**
- USB / shared drive → copy to this machine
- Private file share / object storage → download to this machine

**Save it somewhere accessible**, e.g.:
```bash
cp /path/to/openai_api_compatible-0.0.53-offline.difypkg ~/
```
You will upload it via the browser UI in §8.

---

## 4. Merge the Dify upstream source

The compose override requires the upstream Dify source tree to exist at `aipg/dify/`. Clone it into a temp directory, then merge without overwriting the tracked files:

```bash
cd ~/agi/research/aipg
git clone https://github.com/langgenius/dify.git /tmp/dify-src
cp -rn /tmp/dify-src/. dify/        # -n = never overwrite tracked files
rm -rf /tmp/dify-src

# Confirm both files exist
ls dify/docker/docker-compose.yaml dify/docker/docker-compose.override.yml
```

Confirm git is still clean (the merged clone must be invisible to git):
```bash
git status --short dify/ | head
# Expected: nothing, or only the tracked files (override, .env.dify.example, .gitignore, workflows/)
```

---

## 5. Create the live environment file

```bash
cd ~/agi/research/aipg/dify/docker
cp .env.dify.example .env

# Generate a fresh secret key
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
```

Edit `.env` and set these values:

| Variable | Value |
|---|---|
| `SECRET_KEY` | paste the 64-char hex value from the command above |
| `INIT_PASSWORD` | choose an admin password (used at first browser login) |
| `FORCE_VERIFYING_SIGNATURE` | leave as `false` (required for offline plugin) |
| `PLUGIN_MAX_PACKAGE_SIZE` | leave as `524288000` |
| `NGINX_CLIENT_MAX_BODY_SIZE` | leave as `500M` |

> `.env` is git-ignored and must never be committed. It holds real credentials.

---

## 6. Build and start the stack

```bash
cd ~/agi/research/aipg/dify/docker

# Pull and start Dify (first run downloads images — allow several minutes)
docker compose up -d

# Build the custom parser sidecar from source
docker compose build parser-sidecar

# Start the sidecar
docker compose up -d parser-sidecar

# Verify all services are running
docker compose ps
```

Expected: 12 containers, all showing `Up` or `Up (healthy)`:

```
docker-api-1             Up (healthy)
docker-api_websocket-1   Up
docker-db_postgres-1     Up (healthy)
docker-nginx-1           Up
docker-plugin_daemon-1   Up
docker-redis-1           Up (healthy)
docker-sandbox-1         Up (healthy)
docker-ssrf_proxy-1      Up
docker-web-1             Up
docker-worker-1          Up
docker-worker_beat-1     Up
parser-sidecar           Up (healthy)
```

---

## 7. Verify services

```bash
cd ~/agi/research/aipg/dify/docker

# Parser sidecar responds internally
docker compose exec api curl -s http://parser-sidecar:8000/health
# → {"status":"ok"}

# Heavy libraries are available inside the sidecar
docker compose exec parser-sidecar python -c \
  "import openpyxl,pandas,matplotlib; print('all imports OK')"

# Sidecar unit tests pass
docker compose exec parser-sidecar pytest /app/tests/ -q
```

Open `http://localhost` in your browser. The Dify setup/login page should load. Create the admin account using the `INIT_PASSWORD` you set in §5.

---

## 8. Install the model-provider plugin (offline)

1. In the Dify UI: **Settings → Model Provider → Install from local file**.
2. Upload the `openai_api_compatible-0.0.53-offline.difypkg` bundle you transferred in §3.
3. Installation should complete with no "corrupted or network unstable" error.

> The `.env` flag `FORCE_VERIFYING_SIGNATURE=false` is what allows the offline bundle to install. This is intentional — the plugin is the unmodified community plugin, repackaged with its dependencies bundled.

---

## 9. Configure the LLM model

After the plugin installs:

1. **Settings → Model Provider → OpenAI-API-Compatible → Add Model**.
2. Fill in the three fields that identify your endpoint:

   | Field | Value |
   |---|---|
   | **Base URL** | `<YOUR_LLM_BASE_URL>` — must end in `/v1` |
   | **API Key** | `<YOUR_API_KEY>` |
   | **Model Name** | `<YOUR_MODEL_NAME>` |
   | Max Tokens | `4096` (adjust to your model's limit) |
   | Context Window | appropriate for your model |

3. **Save → Test connection** — must succeed before continuing.

> These three fields are the only things that differ between environments. No workflow or code is ever edited when switching LLM endpoints. To use a different model later, edit only these fields.

---

## 10. Import the workflow

If a DSL file is included in the repo (`dify/workflows/skeleton_workflow.yml`):

1. Dify UI → **Studio → Create App → Import DSL**.
2. Select the `.yml` file.
3. Confirm the workflow opens and shows all nodes.

If no DSL is present, build the workflow manually following `dify_setup_guide.md §3.4`.

---

## 11. Generate synthetic data

The workflow needs test files to run. Generate them:

```bash
cd ~/agi/research/aipg/app/parser_service

# Create and activate a local Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Generate the synthetic Excel fixtures
cd ..
python synthetic_data/generate.py
# → writes synthetic_data/out/region_a.xlsx (and sibling files)
```

---

## 12. Run a smoke test

### Tool-calling check (CLI)

```bash
cd ~/agi/research/aipg

LLM_BASE_URL=<YOUR_LLM_BASE_URL> \
LLM_API_KEY=<YOUR_API_KEY> \
LLM_MODEL=<YOUR_MODEL_NAME> \
python3 app/scripts/toolcall_smoke.py
```

Expected output:
```
ENV-05 PASS: tool_calls present
  function name : calculate
  arguments     : {"expression": "15 * 4"}
```

If it returns `ENV-05 FAIL`, the model does not support tool calling — try a different model.

### Workflow end-to-end check (UI)

1. Open the imported workflow in Dify UI.
2. Click **Run**.
3. Upload `app/synthetic_data/out/region_a.xlsx` as `excel_file`; enter any text as `user_query`.
4. The End node must return a response with no red node errors.

This confirms: Docker networking → parser sidecar → Code node sandbox → LLM endpoint all working end-to-end.

---

## 13. Day-to-day operations

All commands from `~/agi/research/aipg/dify/docker/`.

```bash
docker compose up -d                   # start everything
docker compose down                    # stop (data preserved)
docker compose down -v                 # stop + wipe volumes (fresh start)
docker compose ps                      # check status
docker compose logs -f api             # tail API logs
docker compose logs -f parser-sidecar  # tail sidecar logs

# After changing sidecar source code:
docker compose build parser-sidecar && docker compose up -d parser-sidecar
```

---

## 14. Swapping the LLM endpoint

This system is designed so the only change between environments is the model endpoint. To switch:

1. Dify UI → **Settings → Model Provider → OpenAI-API-Compatible → edit the model**.
2. Update **Base URL**, **API Key**, and **Model Name**.
3. **Save → Test connection**.
4. Re-run any workflow — no workflow DSL changes needed.

---

## 15. Troubleshooting

| Symptom | Fix |
|---|---|
| `docker: command not found` in WSL | Re-enable WSL Integration in Docker Desktop → Settings → Resources; restart Docker Desktop |
| `docker compose` says "no configuration file" | You must run compose commands from `dify/docker/`, not the repo root |
| `parser-sidecar` build fails | `docker compose build --no-cache parser-sidecar`; confirm Dify was merged into `aipg/dify/` (§4) |
| `api → parser-sidecar:8000` not reachable | Both containers must be Up; run `docker compose up -d` to ensure override applied |
| Containers OOM / very slow | Raise `memory=` in `.wslconfig` to 12 GB; `wsl --shutdown`; restart Docker Desktop |
| `git status` shows thousands of `dify/...` files | `dify/.gitignore` didn't apply — confirm it exists and you didn't `git add -f` the clone |
| Plugin install "corrupted or network unstable" | Confirm `FORCE_VERIFYING_SIGNATURE=false` in `.env`; confirm you uploaded the `*-offline.difypkg`, not the original |
| Model "Test connection" fails | Verify Base URL ends in `/v1`; confirm API key is valid for this endpoint; confirm model name is exact |
| Workflow parse node returns empty | Restart sidecar: `docker compose restart parser-sidecar`; check `docker compose logs parser-sidecar` |
| Synthetic data file missing | Run `python synthetic_data/generate.py` from `app/parser_service/` with `.venv` active (§11) |

---

## 16. Changelog

- 2026-06-07 — skeleton created; parser sidecar local steps verified.
- 2026-06-24 — full rewrite; all ENV-01–05 checks verified; complete copy-paste runbook covering offline plugin, sidecar build, model config, workflow import, and LLM swap.
