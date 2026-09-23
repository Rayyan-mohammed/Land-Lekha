# Deployment (AWS EC2 + Docker Compose + CloudFront)

The live demo runs on a single AWS EC2 instance using the `Dockerfile` and
`docker-compose.yml` already at the repo root — nothing here should ever require a second
copy of those files. CloudFront sits in front of that EC2 instance as a CDN/HTTPS layer;
it does not replace it, and it does not run any application code itself. This document is
about the cloud setup around them: instance, security group, volume, CloudFront, DNS, and
the exact commands to reproduce or redeploy it.

## Current deployment

| | |
| --- | --- |
| URL | https://landlekha.in (CloudFront, HTTPS) — direct origin: http://65.2.234.77:8000 |
| Instance | `t3.medium`, Amazon Linux 2023, `ap-south-1` (Mumbai) |
| Storage | 20 GB root EBS volume, **encrypted at rest** |
| Networking | Elastic IP (`65.2.234.77`) — survives instance stop/reboot |
| CDN/TLS | CloudFront distribution `EVAJ9HA9V7GGC`, ACM certificate, Route 53 hosted zone for `landlekha.in` |
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
Then confirm from outside the box: `https://landlekha.in/`, `/docs`, `/api/graphql` (and, to
check the origin directly without CloudFront in the path, `http://65.2.234.77:8000/`).

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

## CloudFront + custom domain

CloudFront is a CDN/HTTPS layer in front of the EC2 origin above — it forwards everything
(all methods, all headers except `Host`) to the origin with caching disabled by default, so
the app behaves identically to hitting the origin directly, just over HTTPS with edge
caching for static assets. It does **not** run the app itself; the origin still has to be
up. Reproducing this from scratch:

1. **Get a domain** — `landlekha.in` was registered via Route 53 (Console: Route 53 →
   Registered domains → Register domain; this is a real charge, so it has to be a deliberate
   console action, not something to script blindly). Registering it auto-creates a public
   hosted zone.
2. **Request an ACM certificate in `us-east-1` specifically** (CloudFront only accepts certs
   from that region, regardless of where the origin lives):
   ```bash
   aws acm request-certificate --domain-name landlekha.in \
     --subject-alternative-names www.landlekha.in --validation-method DNS --region us-east-1
   ```
   Add the DNS validation CNAME records ACM returns to the hosted zone (`aws route53
   change-resource-record-sets`), then `aws acm wait certificate-validated`.
3. **Create the CloudFront distribution**, origin = the EC2 public DNS name, port 8000,
   `OriginProtocolPolicy: http-only` (the origin itself has no TLS — CloudFront terminates
   HTTPS for viewers and talks plain HTTP to the origin over the AWS network). Critically:
   the default cache behavior must use the `CachingDisabled` managed cache policy and the
   `AllViewerExceptHostHeader` managed origin request policy — without the latter, CloudFront
   strips the `Authorization` header by default and every authenticated API call breaks
   silently. A second cache behavior for `/assets/*` uses `CachingOptimized` instead, since
   the built frontend's JS/CSS bundles are content-hashed and safe to cache aggressively.
4. **Add the domain as a CloudFront alias** with the ACM certificate attached
   (`aws cloudfront update-distribution`), then **point DNS at CloudFront**: an `A` record
   (alias, not CNAME) for `landlekha.in` and `www.landlekha.in`, target = the CloudFront
   distribution's domain name, hosted zone ID always `Z2FDTNDATAQYW2` (a fixed constant for
   all CloudFront distributions, not specific to this one).
5. **Verify end to end**, not just a health check — login and an authenticated request, since
   header forwarding is the part most likely to silently break:
   ```bash
   curl https://landlekha.in/api/health
   TOKEN=$(curl -s -X POST https://landlekha.in/api/auth/login -d "username=operator&password=upload@123" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
   curl -H "Authorization: Bearer $TOKEN" https://landlekha.in/api/auth/me
   ```

A brand-new domain can get auto-blocked for a while by some institutional/campus network
security proxies under a "newly observed domain" heuristic — that's the network's policy,
not a sign the deployment is broken. Check from a different network before assuming
something's wrong.

## Known gaps (not fixed, on purpose — documented instead of hidden)

- **SSH is open to `0.0.0.0/0`**, not restricted to a specific IP. Fine for a short-lived
  hackathon demo; not fine for anything longer-lived.
- **The AWS account used to provision this runs as root**, not a scoped IAM user. Anyone
  continuing this deployment should create an IAM user with least-privilege EC2/Route53/
  CloudFront/ACM permissions instead of using root credentials for CLI work.
- **Horizontal scaling** (`docker compose up --scale api=3`) only works once
  `LL_DATABASE_URL` points at Postgres (the default in this compose file) — the queue is
  database-backed and multiple replicas claim work atomically (`backend/api/processing.py`),
  but this hasn't been load-tested under real concurrent traffic.
