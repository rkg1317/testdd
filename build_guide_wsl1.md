# Backup Build Guide — WSL1 + Docker Desktop (Hyper-V)

*For machines where WSL2 is unavailable. Uses Docker Desktop with the Hyper-V
backend instead of the WSL2 engine. The application stack is identical; only the
Docker integration and filesystem layout differ.*

*Last updated: 2026-06-24.*

---

## Try this first — upgrade WSL1 to WSL2 (recommended)

Before following this guide, check whether you can simply upgrade in place:

```powershell
# In PowerShell (admin) or Windows Terminal:
wsl --set-version Ubuntu 2   # replace "Ubuntu" with your distro name from: wsl -l -v
```

Requires virtualization (Hyper-V / VT-x) to be enabled in BIOS.
After that, use `build_guide.md` directly — no changes needed.

**Verify it worked:**
```bash
wsl -l -v   # VERSION column must show 2
```

**Only continue with this guide if the upgrade is unavailable on your machine.**

---

## 0. What you need

| Component | Minimum | Notes |
|---|---|---|
| Windows | 10 / 11 Pro/Enterprise | Hyper-V requires Pro/Enterprise — Home edition does **not** have Hyper-V |
| WSL1 distro | Ubuntu 22.04+ | Verify: `wsl -l -v` shows VERSION **1** |
| Docker Desktop | 4.x | Hyper-V backend, **not** WSL2 engine |
| RAM (machine) | 16 GB | Docker VM gets 8 GB; machine needs headroom |
| Free disk | 20 GB | Dify images + Docker VM overhead |
| Git | any | Available in Ubuntu by default |
| LLM endpoint | OpenAI-compatible | Any `/v1/chat/completions` API |
| Offline plugin bundle | `*-offline.difypkg` | Transfer from source machine |

> **Hyper-V availability check** — run in PowerShell:
> ```powershell
> systeminfo | findstr /i "hyper-v"
> ```
> All four lines must say **Yes**. If any say **No** or the command returns nothing,
> virtualization is not enabled — enable it in BIOS settings before proceeding.

---

## 1. Docker Desktop setup (Hyper-V mode)

1. **Install Docker Desktop** on Windows. If the installer offers "Use WSL 2
   instead of Hyper-V", **leave it unchecked**.

2. After installation: **Settings → General** → **uncheck** "Use the WSL 2
   based engine" → **Apply & Restart**.

3. **Configure the Docker VM resources** (replaces `.wslconfig` — that file has
   no effect here):
   **Settings → Resources → Advanced**:
   - Memory: **8192 MB**
   - CPUs: **4**
   - Swap: **2048 MB**
   → **Apply & Restart**

4. **Enable drive sharing** so Docker can bind-mount Windows paths:
   **Settings → Resources → File Sharing** → click **+** → add `C:\` (or
   whichever drive you'll clone to) → **Apply & Restart**.

5. **Skip WSL Integration** — that setting is only relevant for the WSL2 engine.

6. **Verify inside your Ubuntu WSL1 shell:**
   ```bash
   docker --version          # Docker version 27.x or newer
   docker compose version    # Docker Compose version v2.x
   docker run --rm hello-world
   ```
   If `docker` is "command not found": confirm Docker Desktop is **running**,
   then check that Windows executables are in your WSL1 PATH:
   ```bash
   echo $PATH | grep -o '/mnt/c/[^:]*'
   # must show /mnt/c/Program Files/Docker/Docker/resources/bin or similar
   ```
   If missing, add to `~/.bashrc`:
   ```bash
   export PATH="$PATH:/mnt/c/Program Files/Docker/Docker/resources/bin"
   ```

---

## 2. Clone into the Windows filesystem

**Critical difference from the standard guide.**

Docker Desktop Hyper-V maps `/mnt/c/...` WSL1 paths to `C:\...` Windows paths
for bind mounts. WSL1's Linux home (`~/`) has no such mapping and bind-mounted
paths from it will appear **empty** inside containers.

All work must happen under `/mnt/c/...`:

```bash
mkdir -p "/mnt/c/Users/<your-windows-username>/agi/research"
git clone <repo-url> "/mnt/c/Users/<your-windows-username>/agi/research/aipg"
cd "/mnt/c/Users/<your-windows-username>/agi/research/aipg"
```

Shorthand: set an env var so you don't retype it:
```bash
export AIPG="/mnt/c/Users/<your-windows-username>/agi/research/aipg"
# add this line to ~/.bashrc to persist across sessions
```

All subsequent commands use `$AIPG` as the repo root.

---

## 3. Fix line endings (one-time)

Files cloned or edited on Windows may have CRLF line endings. Linux containers
expect LF — CRLF causes `\r: command not found` errors inside containers.

```bash
sudo apt-get install -y dos2unix

cd $AIPG
# Fix shell scripts, env templates, compose files
find . -name "*.sh" -not -path "./.git/*" | xargs dos2unix 2>/dev/null
find . -name "*.env*" -not -path "./.git/*" | xargs dos2unix 2>/dev/null
find dify/docker -name "*.yml" -o -name "*.yaml" 2>/dev/null | xargs dos2unix 2>/dev/null

# Tell git not to auto-convert line endings on checkout
git config core.autocrlf false
```

---

## 4. Transfer the offline plugin bundle

Same as the standard guide §3. Transfer `openai_api_compatible-0.0.53-offline.difypkg`
to this machine and save it somewhere accessible:

```bash
cp /path/to/openai_api_compatible-0.0.53-offline.difypkg /mnt/c/Users/<you>/
```

---

## 5. Merge the Dify upstream source

```bash
cd $AIPG
git clone https://github.com/langgenius/dify.git /tmp/dify-src
cp -rn /tmp/dify-src/. dify/
rm -rf /tmp/dify-src

# Fix line endings on the merged files
find dify/docker -name "*.yml" -o -name "*.yaml" | xargs dos2unix 2>/dev/null
find dify -name "*.sh" | xargs dos2unix 2>/dev/null

# Confirm tracked files are still there
ls dify/docker/docker-compose.yaml dify/docker/docker-compose.override.yml

# Confirm git is still clean
git status --short dify/ | head
```

---

## 6. Create the Postgres named-volume override

**WSL1-specific step — no equivalent in the standard guide.**

Postgres refuses to start if its data directory has world-writable permissions.
NTFS (the Windows filesystem underlying `/mnt/c/...`) does not honour Unix
ownership, so every directory appears as `777 root:root`. Postgres detects this
and exits.

The fix: redirect Postgres data to a **named Docker volume** (which lives inside
the Docker Hyper-V VM on a real ext4 filesystem).

Create `$AIPG/dify/docker/docker-compose.wsl1.yml`:

```yaml
services:
  db:
    volumes:
      - pg_data:/var/lib/postgresql/data

  redis:
    volumes:
      - redis_data:/data

volumes:
  pg_data:
  redis_data:
```

> The compose merge replaces the bind-mount entries for those two targets with
> named volumes. All other Dify services remain unchanged.

---

## 7. Create the live environment file

```bash
cd $AIPG/dify/docker
cp .env.dify.example .env
dos2unix .env

python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
```

Edit `.env` and set:

| Variable | Value |
|---|---|
| `SECRET_KEY` | paste the 64-char hex value |
| `INIT_PASSWORD` | choose an admin password |
| `FORCE_VERIFYING_SIGNATURE` | `false` |
| `PLUGIN_MAX_PACKAGE_SIZE` | `524288000` |
| `NGINX_CLIENT_MAX_BODY_SIZE` | `500M` |

---

## 8. Create a compose alias

Every compose command in this setup requires three `-f` flags. Create a shell
alias to avoid repeating them:

```bash
# Add to ~/.bashrc
alias dcw='docker compose \
  -f docker-compose.yaml \
  -f docker-compose.override.yml \
  -f docker-compose.wsl1.yml'
```

```bash
source ~/.bashrc   # apply immediately
```

All `docker compose` commands from the standard guide become `dcw` here.

---

## 9. Build and start the stack

```bash
cd $AIPG/dify/docker

# Pull images and start Dify (first run downloads images — allow several minutes)
dcw up -d

# Build the custom parser sidecar
dcw build parser-sidecar

# Start the sidecar
dcw up -d parser-sidecar

# Verify all containers are running
dcw ps
```

Expected: 12 containers, all `Up` or `Up (healthy)` — same list as the standard
guide §6.

---

## 10. Verify services

```bash
cd $AIPG/dify/docker

# Parser sidecar health check
dcw exec api curl -s http://parser-sidecar:8000/health
# → {"status":"ok"}

# Heavy libraries loaded in sidecar
dcw exec parser-sidecar python -c \
  "import openpyxl,pandas,matplotlib; print('all imports OK')"

# Sidecar unit tests
dcw exec parser-sidecar pytest /app/tests/ -q
```

Open `http://localhost` in your browser. Create the admin account with
`INIT_PASSWORD` from §7.

---

## 11–14. Remaining steps

Identical to the standard guide §8–§12:

- **§8** — Install offline plugin
- **§9** — Configure LLM model
- **§10** — Import workflow DSL
- **§11** — Generate synthetic data
- **§12** — Run smoke tests

Use `dcw` instead of `docker compose` everywhere.

---

## 15. Day-to-day operations

All commands from `$AIPG/dify/docker/`.

```bash
dcw up -d                     # start everything
dcw down                      # stop (data preserved in named volumes)
dcw down -v                   # stop + wipe volumes (fresh start)
dcw ps                        # check status
dcw logs -f api               # tail API logs
dcw logs -f parser-sidecar    # tail sidecar logs

# After changing sidecar source:
dcw build parser-sidecar && dcw up -d parser-sidecar
```

---

## 16. Troubleshooting (WSL1-specific)

| Symptom | Fix |
|---|---|
| `docker: command not found` in WSL1 | Docker Desktop is not running, or Windows executables not in PATH — see §1 step 6 |
| Containers start but volumes are empty inside | Clone is under `~/` (Linux home) — move everything to `/mnt/c/...` |
| Postgres exits immediately (`FATAL: data directory has wrong ownership`) | `docker-compose.wsl1.yml` not applied — confirm `dcw` alias includes it; run `dcw ps` |
| Redis exits immediately | Same cause — named volume override not applied |
| `\r: command not found` inside container | CRLF in a shell script — run `dos2unix` on the file and `dcw build` the affected service |
| File changes not picked up by container | NTFS file-watch is unreliable — `dcw restart parser-sidecar` after edits |
| `docker compose` says "no configuration file" | Run from `$AIPG/dify/docker/`, not repo root |
| Bind-mount path not found inside container | Path is under `~/` not `/mnt/c/...` — Docker Hyper-V cannot mount WSL1 Linux home |
| Storage upload permission denied | `chmod 777 $AIPG/dify/docker/volumes/app/storage` from WSL1 |
| Plugin install "corrupted or network unstable" | Confirm `FORCE_VERIFYING_SIGNATURE=false` in `.env`; confirm `*-offline.difypkg` was uploaded |
| Hyper-V not available / Docker won't start | Virtualization not enabled in BIOS — enable it and restart; no workaround without it |
| `dcw` alias not found after opening a new shell | Add the alias to `~/.bashrc` and re-run `source ~/.bashrc` |

---

## 17. Key differences summary vs standard guide

| Area | Standard guide (WSL2) | This guide (WSL1 Hyper-V) |
|---|---|---|
| Docker backend | WSL2 engine | Hyper-V |
| Docker VM memory | `.wslconfig` on Windows | Docker Desktop UI → Resources → Advanced |
| WSL Integration toggle | ON | Irrelevant — leave OFF |
| Clone location | `~/agi/research/aipg` | `/mnt/c/Users/<you>/agi/research/aipg` |
| Line endings | Not an issue | Must run `dos2unix` once after clone |
| Postgres volume | Bind mount | Named volume (`docker-compose.wsl1.yml`) |
| Redis volume | Bind mount | Named volume (`docker-compose.wsl1.yml`) |
| Compose command | `docker compose` | `dcw` alias (3-file chain) |
| Storage permissions | Handled by init_permissions | May need manual `chmod 777` |
