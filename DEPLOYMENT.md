# Deployment (AWS EC2 + Docker Compose)

The live demo runs on a single AWS EC2 instance using the `Dockerfile` and
`docker-compose.yml` already at the repo root — nothing here should ever require a second
copy of those files. This document is about the cloud setup around them: instance,
security group, volume, and the exact commands to reproduce or redeploy it.

## Current deployment

| | |
| --- | --- |
| URL | http://65.2.234.77:8000 |
| Instance | `t3.medium`, Amazon Linux 2023, `ap-south-1` (Mumbai) |
| Storage | 20 GB root EBS volume, **encrypted at rest** |
| Networking | Elastic IP (`65.2.234.77`) — survives instance stop/reboot |
| Services | `db` (Postgres 16), `api` (FastAPI + built React UI), via `docker compose` |

## Provisioning from scratch

1. **Launch an EC2 instance**: Ubuntu 22.04 or Amazon Linux 2023, `t3.medium` or larger.
   EasyOCR's PyTorch backend needs real memory headroom — a free-tier `t2.micro`/`t3.micro`
   (1 GB RAM) will not load the model.
2. **Security group**: open port 22 (SSH) and port 8000 (the app). Restrict port 22 to a
   known IP range where possible — the current deployment has it open to `0.0.0.0/0`,
   which is a known, accepted gap for this hackathon demo, not a recommended default.
3. **Allocate and associate an Elastic IP** so the URL survives a reboot (a plain EC2
   public IP changes every time the instance stops and starts):
   ```bash
   aws ec2 allocate-address --domain vpc
   aws ec2 associate-address --instance-id <id> --allocation-id <allocation-id>
   ```
4. **SSH in, install Docker + git**:
   ```bash
   # Amazon Linux 2023
   sudo dnf install -y docker git
   sudo systemctl enable --now docker
   sudo usermod -aG docker $USER   # log out/in once after this

   # get the Compose plugin (dnf's docker package doesn't include it)
   mkdir -p ~/.docker/cli-plugins
   curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
     -o ~/.docker/cli-plugins/docker-compose
   chmod +x ~/.docker/cli-plugins/docker-compose
   ```
   (On Ubuntu, use Docker's official apt repo instead — see their install docs — then
   `apt-get install docker-compose-plugin`.)
5. **Clone and configure**:
   ```bash
   git clone https://github.com/Rayyan-mohammed/Land-Lekha.git
   cd Land-Lekha
   echo "LL_JWT_SECRET=$(openssl rand -hex 32)" > .env
   echo "POSTGRES_PASSWORD=$(openssl rand -hex 16)" >> .env
   ```
   Never type these values into a terminal by hand or paste them anywhere — the two
   commands above generate and write them directly, and `.env` is git-ignored.
6. **Build and start**:
   ```bash
   docker compose up --build -d
   ```
   First start also downloads ~100 MB of EasyOCR models into a named volume — allow a
   few extra minutes beyond the build itself.

## Verifying a deployment (don't assume, check)

```bash
docker compose ps                       # both db and api should show Up/healthy
docker compose logs -f api              # watch for "OCR engine ready", no repeated restarts
curl localhost:8000/api/health          # {"status":"ok","ocr_ready":true,"queue":0}
```
Then confirm from outside the box: `http://<public-ip-or-domain>:8000/`, `/docs`, `/api/graphql`.

## Redeploying an update

```bash
git pull
docker compose up --build -d
```
Compose only rebuilds and restarts what changed; the Postgres data volume and EasyOCR
model cache are untouched. If a migration changed the DB schema, the API logs a line
like `database upgraded, added columns: ...` on the next startup — this is expected and
requires no manual step.

## Restart / logs

```bash
docker compose restart          # restart without rebuilding
docker compose logs -f api      # follow API logs
docker compose logs -f db       # follow Postgres logs
```

## Encryption at rest

The root EBS volume is encrypted. This isn't the default for a newly launched instance —
it requires either launching from an encrypted AMI/snapshot, or migrating an existing
unencrypted volume: snapshot it, copy the snapshot with `--encrypted`, create a new volume
from that encrypted snapshot, then stop the instance, swap the volume, and restart.
That's a real few minutes of downtime, not a live toggle — plan for it, don't run it
during a demo.

## Known gaps (not fixed, on purpose — documented instead of hidden)

- **SSH is open to `0.0.0.0/0`**, not restricted to a specific IP. Fine for a short-lived
  hackathon demo; not fine for anything longer-lived.
- **The AWS account used to provision this runs as root**, not a scoped IAM user. Anyone
  continuing this deployment should create an IAM user with least-privilege EC2/Route53
  permissions instead of using root credentials for CLI work.
- **No custom domain** — the live URL is a raw IP. A `.in`/`.com` domain was priced
  (`landlekha.in` ≈ $8/year via Route 53) but not purchased, to avoid real charges during
  the hackathon. `http://ec2-65-2-234-77.ap-south-1.compute.amazonaws.com:8000` is a free
  alternative hostname pointing at the same instance, for networks that block raw
  `*.amazonaws.com` addresses but allow the IP (or vice versa).
- **Horizontal scaling** (`docker compose up --scale api=3`) only works once
  `LL_DATABASE_URL` points at Postgres (the default in this compose file) — the queue is
  database-backed and multiple replicas claim work atomically (`backend/api/processing.py`),
  but this hasn't been load-tested under real concurrent traffic.
