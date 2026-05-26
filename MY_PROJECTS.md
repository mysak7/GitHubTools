# MY PROJECTS — DEVOPS ARCHITECTURE SPEC

> Deep technical analysis of all GitHub workspace projects. Used as context for Hermes mock-interview training.
> Last generated: 2026-05-26 | Projects: 15

---

## Project: SEIP — Security Event Intelligence Platform (AWS)

- **Business Domain:** Cybersecurity / Windows Endpoint Threat Detection
- **Core Architecture:** Event-driven hybrid pipeline. Windows Sysmon logs → Fluent Bit → Kafka → `seip-kafka-consumer` writes to DynamoDB → `seip-deep-mind` workers pull unclaimed events via distributed claim mechanism (DynamoDB conditional update `analyzing_by / analyzing_at`), run LLM analysis via Amazon Bedrock, write back severity + analysis. ASG scales 0–5 workers based on custom CloudWatch metric `UnprocessedEvents`. All services run as Docker containers on a single ARM64 EC2 (`t4g.small`), workers on separate x86 ASG (`t3.micro`).
- **Primary Tech Stack:** Python 3.11, FastAPI ≥0.111, uvicorn ≥0.29, confluent-kafka 2.3.0, boto3 ≥1.34.69, sentence-transformers (all-MiniLM-L6-v2 pre-cached in image), Jinja2 3.1.4, Node.js / Express 4.18.2 (seip-gui), Terraform AWS provider ~5.0

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** AWS (eu-central-1)
- **IaC Tool:** Terraform; state backend S3 `seip-terraform-state-dev` + DynamoDB lock table `seip-terraform-locks`. Modules: `vpc`, `ec2`, `dynamodb`, `asg`, `ecr`, `cloudwatch`, `kms`, `s3`.
- **Compute & Runtime:** Bastion/NAT: `t3.micro` fck-nat (x86, public subnet `10.0.1.0/24`). App host: `t4g.small` ARM64 (Amazon Linux 2023, private subnet `10.0.2.0/24`). Deep Mind workers: ASG `t3.micro` x86 (min 0, max 5, target-tracking on `UnprocessedEvents`, target 30 events/instance, scale-in cooldown 300 s). Health check grace 180 s, warmup 120 s.
- **Networking & Security:** VPC `10.0.0.0/16`. fck-nat performs DNAT for ports 8765 (MCP) and 443 (portal) to app-host. Security groups: `nat-bastion-sg` opens 22/8765/443; `app-host-sg` allows 8184 from ASG workers; `deep_mind_worker-sg` outbound-only. Elastic IP on fck-nat for stable DNS. No VPC endpoints — all AWS API calls over NAT. KMS key `lua_signing` for S3 Lua filter scripts.
- **Storage & Databases:** DynamoDB `dev-security-events` (PAY_PER_REQUEST, PITR enabled, TTL attribute): GSIs on `status-timestamp`, `item_type-timestamp`, `host-timestamp`, `analyzed_at`. DynamoDB `dev-seip-patterns` (PAY_PER_REQUEST, TTL): GSI `timeline-index`. S3 `mysak7-seip-lua` (public-read for Lua hot-reload), S3 `seip-terraform-state-dev` (encrypted), S3 `seip-cur-reports` (CUR).

### 2. CI/CD & GitOps Automation

- **Pipelines:** GitHub Actions per service. Triggers on push to `master`. Multi-arch strategy: `ubuntu-24.04-arm` for `linux/arm64`, `ubuntu-latest` for `linux/amd64` (parallel native runners, no QEMU). Separate base-image job runs only when `requirements.txt` changes (tagged `base-{sha256[:12]}-{arch}`). Images merged into multi-arch manifest and tagged `{github.sha}` + `latest`. IAM: OIDC trust `repo:mysak7/*` → `role/github-actions-deploy-role`.
- **Kubernetes Delivery:** Not Kubernetes — SSM RunShellScript to app-host: `docker pull`, `docker tag :current`, `systemctl restart {service}`, `docker image prune -f`. Rollback stores `stable` tag; reverts on failure.
- **Security Gates:** None explicitly configured (no Trivy/Snyk in seip-* workflows).

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** CloudWatch custom namespace `SEIP/DeepMind`, metric `UnprocessedEvents` (published by deep-mind workers). CloudWatch Log Group `/dynamo-dev-security-events` (30 days).
- **Log Forwarding:** Docker `awslogs` driver to CloudWatch.
- **Alerting Criteria:** `deepmind-unprocessed-events-high` > 500 / 10 min; `security-events-high-rcu` > 3000 RCU/min / 5 min; `seip-patterns-high-rcu` > 500 RCU/min / 5 min; `dynamo-cu-log-rate-high` > 300 log lines/min / 5 min.

### 4. Technical Challenges & Complex Workflows Resolved

- **Distributed Claim Mechanism:** DynamoDB conditional `UpdateItem` sets `analyzing_by` (worker ID) + `analyzing_at` (timestamp). Worker checks `analyzing_at < NOW() - 2 min` to reclaim stale locks — prevents duplicate processing without a message broker.
- **Multi-Arch CI without Cross-Compilation:** App-host is ARM64 (`t4g.small`), workers x86 — required native ARM/x86 GitHub Actions runners to build separate layers, then merge into a multi-arch manifest. Avoids QEMU emulation overhead.
- **Semantic Caching (sentence-transformers):** deep-mind pre-caches `all-MiniLM-L6-v2` in the Docker image layer during build to avoid runtime download. Ring buffer of 2000 recent embeddings for duplicate suppression before calling Bedrock.

### 5. Potential Bottlenecks & Day-2 Technical Debt

- EKS module exists in Terraform but is commented out; manual deploy script `deploy_eks.sh` — architecture undecided between ASG and EKS.
- All SEIP services colocated on single `t4g.small` — no HA, no process isolation beyond Docker. Single point of failure for orchestrator, gui, manager, mcp, kafka-consumer.
- `MODELS_URL` hardcoded to `http://seip-models:8184` in all services — Docker DNS-dependent, breaks outside Compose network.
- No Secrets Manager integration; environment variables passed via SSM RunShellScript in CI, visible in CloudWatch logs.
- DynamoDB scan used for unprocessed event queries (expensive at scale); should migrate to GSI with sparse index.

---

## Project: azure-seip — SEIP Azure Migration (Monorepo)

- **Business Domain:** Cybersecurity / Windows Endpoint Threat Detection — AWS→Azure migration
- **Core Architecture:** Consolidates 10+ separate AWS repos into a single AKS-native monorepo. Same Sysmon→Kafka→Analysis pipeline, but DynamoDB replaced by PostgreSQL 16 Flexible Server, ASG workers replaced by KEDA-scaled pods (0–5), Amazon Bedrock replaced by Azure OpenAI, fck-nat EC2 replaced by Azure NAT Gateway. Atomic claim uses PostgreSQL `UPDATE … WHERE analyzing_by IS NULL OR analyzing_at < NOW() - INTERVAL '120s' RETURNING *`.
- **Primary Tech Stack:** Python 3.11, FastAPI ≥0.111, psycopg[binary] ≥3.1, psycopg-pool ≥3.1, azure-identity ≥1.18, openai ≥1.0, kubernetes ≥28.0, confluent-kafka 2.3.0, Node.js / Express 4.18.2; Terraform azurerm 4.x, Helm KEDA 2.16.0, ingress-nginx 4.11.0, Karpenter (NAP)

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** Azure (westeurope)
- **IaC Tool:** Terraform; state backend Azure Blob Storage `seiptfstatedev` / `tfstate` container. Modules: `vnet`, `aks`, `acr`, `postgresql`, `keyvault`. Resource group `dev-seip-rg`.
- **Compute & Runtime:** AKS `dev-seip-aks` — system pool 2× `Standard_D2ads_v7`, Node Autoprovision (NAP/Karpenter) for app pods: D + B families, 2–4 vCPU, spot + on-demand, consolidation WhenEmpty 30s. Services as K8s Deployments in `seip` namespace. KEDA ScaledObject on deep-mind: trigger `postgresql` query `SELECT COUNT(*) FROM events WHERE analyzed = FALSE AND (analyzing_by IS NULL OR analyzing_at < NOW() - INTERVAL '120 seconds')`, targetQueryValue 30, pollingInterval 30s, cooldown 120s, min 0, max 5.
- **Networking & Security:** VNet `10.0.0.0/16`, subnets: public `10.0.1.0/24`, private `10.0.2.0/24`, AKS `10.0.3.0/22`, PostgreSQL delegated subnet. Azure NAT Gateway (static public IP) for egress. ingress-nginx LoadBalancer → `az-seip.mysak.fun` (Cloudflare Access + Entra ID). cert-manager Let's Encrypt auto-TLS. Workload Identity: managed identity `dev-seip-manager-identity`, federated cred OIDC issuer → SA `seip:seip-deep-mind-sa`. KEDA identity `dev-keda-identity` federated to `keda:keda-operator`.
- **Storage & Databases:** PostgreSQL 16 Flexible Server `dev-seip-pg`, SKU `B_Standard_B1ms`, 32 GB, 7-day backup, no geo-redundancy, private endpoint, admin password in Key Vault `dev-seip-kv` (Standard SKU). ACR `devseipacr` (Basic SKU, admin disabled). Azure Key Vault secrets: `pg-admin-password`, `deep-mind-config`.

### 2. CI/CD & GitOps Automation

- **Pipelines:** GitHub Actions reusable pattern: `_deploy.yml` template called by `deploy-{service}.yml`. Path-filtered triggers per service path (e.g., `apps/deep-mind/**`). Build: Docker multi-arch via QEMU (`linux/amd64`+`linux/arm64`). Push to ACR. Patch K8s Deployment image tag + rollout restart. OIDC Azure auth (no stored secrets). Daily teardown: cron workflow scales deep-mind to 0 + destroys nightly.
- **Kubernetes Delivery:** Direct `kubectl apply` + `kubectl set image`. Manifests in `k8s/` directory. No Helm/ArgoCD for app services.
- **Security Gates:** None in manifests, but Workload Identity (no static creds) and Key Vault for secrets.

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** Log Analytics Workspace (via AKS diagnostics). KEDA polling exposes replica count metrics to Azure Monitor.
- **Log Forwarding:** AKS → Log Analytics via OMS agent (built-in AKS monitoring). No custom Fluent Bit.
- **Alerting Criteria:** No explicit alert rules configured in Terraform (unlike AWS version). PostgreSQL built-in metrics available via Azure Monitor.

### 4. Technical Challenges & Complex Workflows Resolved

- **DynamoDB → PostgreSQL Migration:** `scripts/migrate_dynamo_to_pg.py` handles DynamoDB type descriptors (S/N/M/L/BOOL/NULL/SS/NS) → PostgreSQL schema. `import_aws_to_azure.py` orchestrates live streaming migration.
- **KEDA PostgreSQL Trigger vs. CloudWatch Custom Metric:** Eliminates the need to publish CloudWatch `UnprocessedEvents` metric — KEDA directly queries `SELECT COUNT(*)` on PostgreSQL, reducing infrastructure components and removing the metric publishing loop.
- **Azure Workload Identity Federated Credentials:** Replaces EC2 instance profiles. OIDC token exchange: K8s ServiceAccount projected token → Azure AD identity. No static credentials in K8s Secrets for Azure SDK calls. `DefaultAzureCredential()` picks up OIDC token automatically.

### 5. Potential Bottlenecks & Day-2 Technical Debt

- PostgreSQL `B_Standard_B1ms` (burstable) — inadequate for production write bursts from Kafka consumer; no read replica.
- No Pod Disruption Budgets — NAP can evict pods without graceful termination guarantees.
- KEDA polling interval 30 s — not event-driven; 30 s latency on scale-up vs. CloudWatch's near-real-time metric.
- Single AKS cluster, single region — no DR; if cluster is destroyed, full re-provision takes ~15 min.
- Monorepo complexity: single Terraform apply for all infra — blast radius of a failing module is entire platform.

---

## Project: vertexproxy (seip-models) — Internal LLM Gateway

- **Business Domain:** Internal LLM Gateway / Model Proxy for SEIP Platform
- **Core Architecture:** FastAPI service acting as a unified LLM gateway, routing inference requests to four backend provider types (AWS Bedrock, Google Gemini direct API, Google Vertex AI via service-account OAuth2, and any OpenAI-compatible "bridge" endpoint) based on model-ID prefix or explicit provider field. Config read at runtime from AWS SSM Parameter Store (`/dev/seip-models/config`); every call logged synchronously to DynamoDB (JSONL file fallback), enabling real-time cost accounting per model and per caller.
- **Primary Tech Stack:** Python 3.11, FastAPI ≥0.111, uvicorn ≥0.29 (asyncio loop), Jinja2 ≥3.1, boto3 ≥1.34 (SSM + DynamoDB + Bedrock), google-auth ≥2.0 (Vertex AI SA OAuth2), requests ≥2.31 (Gemini REST + bridge REST), fastmcp ≥2.0 (MCP StreamableHTTP server), python-multipart ≥0.0.9

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** AWS (primary hosting, eu-central-1), Google Cloud (Vertex AI / Gemini as upstream)
- **IaC Tool:** None in this repo — deployed as Docker container on EC2 `dev-app-host`; infrastructure managed by `SEIP/seip-infrastructure/`.
- **Compute & Runtime:** Docker container on single EC2 `dev-app-host`; image in ECR `dev/seip-models`; managed as `systemd` unit `seip-models`; uvicorn bound `0.0.0.0:8184` asyncio loop; healthcheck `GET /health` every 30 s (timeout 5 s, 3 retries, 15 s start period).
- **Networking & Security:** Inside SEIP VPC; external access via bastion EIP proxied through Cloudflare Access + Entra ID. GitHub Actions OIDC → IAM role `github-actions-deploy-role` (account `317781017752`) for ECR push + SSM `send-command` deploy. EC2 instance role requires: `ssm:GetParameter`, `ssm:PutParameter`, `dynamodb:PutItem/Query/Scan/BatchWriteItem`, `bedrock-runtime:InvokeModel`.
- **Storage & Databases:** AWS SSM Parameter Store (`/dev/seip-models/config`, Type=String, Tier=Advanced) — sole config store for all provider credentials and model catalogue. DynamoDB `dev-seip-patterns` (PK `hash`, GSI `timeline-index` PK=`"models_log"` SK=`created_at`); 30-day TTL on log items. Fallback JSONL at `/data/llm_log.jsonl` inside container.

### 2. CI/CD & GitOps Automation

- **Pipelines:** GitHub Actions `deploy.yml`, push to `main` or dispatch. Steps: (1) OIDC auth to AWS; (2) ECR login; (3) Docker Buildx `linux/arm64` with GHA layer cache; (4) push `:<sha>` + `:latest`; (5) ECR lifecycle (keep last 3 tagged, expire untagged after 1 day); (6) locate `dev-app-host` by Name tag → `AWS-RunShellScript` SSM Run Command → `docker pull` + `systemctl restart seip-models` → poll `StatusDetails == "Success"`.
- **Kubernetes Delivery:** N/A — bare EC2 systemd.
- **Security Gates:** No linting/SAST/tests. Secrets in SSM at runtime only — never in repo.

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** Built-in web dashboard at `/` (`usage.html`): total calls, token counts, cost per model, per-caller breakdown, filterable call log. `/chat` UI for interactive testing. `/config` UI for provider/model CRUD. All data from in-memory deque (`_log`, maxlen=500) populated at startup from DynamoDB.
- **Log Forwarding:** Two-tier: startup calls `_load_from_dynamo()`, fallback to `_load_from_file()` (`/data/llm_log.jsonl`). Every call completion fires `_save_to_dynamo()` + `_append_to_file()` synchronously. DynamoDB item key: `hash = "models_log#{ts}#{id}"`, TTL 30 days.
- **Alerting Criteria:** None. Docker HEALTHCHECK marks container unhealthy after 3 failures but no CloudWatch alarm wired.

### 4. Technical Challenges & Complex Workflows Resolved

- **Dynamic Provider Management + Legacy Config Migration:** Original SSM config used flat keys (`gemini_api_key`, `bridge_url`, `vertex_project_id`). New `providers` list supports arbitrary named providers. `_migrate_legacy_providers()` auto-promotes flat keys into dynamic list, persists to SSM via `cfg.patch_config()` — idempotent, zero-downtime migration. `caller.py:call()` checks `cfg["providers"]` first, falls back to legacy flat keys. `tools/migrate_vertex_to_proxy.py` handles SSM rename.
- **MCP Server via FastMCP StreamableHTTP:** Three MCP tools (`chat`, `list_models`, `get_log`) exposed via FastMCP ≥2.0 `StreamableHTTP`, mounted on the same uvicorn process at `/mcp` via `app.mount("/mcp", mcp.http_app(path="/"))`. Tool implementations reuse `caller.call()` and `llm_log.*` — consistent logging. `chat` tool accepts `caller_name` + `purpose` for MCP-vs-HTTP call traceability in DynamoDB.
- **Google Vertex AI per-request OAuth2:** Every Vertex call does `service_account.Credentials.from_service_account_info()` + `creds.refresh(GoogleAuthRequest())`. SA credentials JSON in SSM, loaded per-request. Region-aware URL: `"global"` → `aiplatform.googleapis.com`, otherwise `{region}-aiplatform.googleapis.com`.

### 5. Potential Bottlenecks & Day-2 Technical Debt

- Single EC2, no load balancer, no ASG — `systemctl restart` during deploy = downtime; no HA.
- Per-request Vertex token refresh — Google tokens valid 3600 s; fetching every call wastes 200–500 ms + hammers OAuth2 endpoint. Module-level cache with expiry needed.
- Synchronous DynamoDB write on hot path — `_save_to_dynamo()` in `POST /api/chat` adds 5–20 ms latency per response. Should be background task.
- `ssm:GetParameter` on every request — no in-process TTL cache; 10–30 ms RTT per call, 40 TPS SSM rate limit.
- No auth on REST API / web UI — relies entirely on Cloudflare Access. Any VPC host can call `http://dev-app-host:8184/api/chat` without credentials.
- In-memory `_log` deque (maxlen=500) is process-only — crash loses all in-flight entries.

---

## Project: aws-penny — AWS Cost Management Dashboard

- **Business Domain:** FinOps / AWS Cloud Cost Visibility
- **Core Architecture:** ECS Fargate task running FastAPI. Ingests AWS Cost & Usage Report (CUR 2.0) Parquet files from S3 into pandas DataFrame (in-memory cache, 1 h TTL, `asyncio.Lock`). Second cache for live AWS resource inventory (boto3 Describe* calls, 15 min TTL). Serves cost aggregations, MTD forecasting, anomaly detection (week-over-week delta), and optional resource mutation (EC2 terminate, RDS stop).
- **Primary Tech Stack:** Python 3.11, FastAPI 0.136.1, uvicorn 0.47.0, pandas 3.0.3, pyarrow 24.0.0, boto3 ≥1.34, Jinja2 3.1.6, python-dotenv 1.2.2; Terraform AWS provider ~5.0, ECS Fargate, ECR, ALB

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** AWS (eu-central-1)
- **IaC Tool:** Terraform; state backend S3 `seip-terraform-state-dev` + DynamoDB `seip-terraform-locks`. Variables: `prd.tfvars`.
- **Compute & Runtime:** ECS Service `svc-prd-euc1-penny` — Fargate, 512 CPU units / 1024 MB, 1 desired task, `awsvpc` network mode. ECR `ecr-prd-euc1-penny` (lifecycle: keep last 3 tagged, expire untagged after 1 day, scan on push). ALB `alb-prd-euc1-penny` — HTTP→301 HTTPS, HTTPS listener policy `ELBSecurityPolicy-TLS13-1-2-2021-06`, ACM cert.
- **Networking & Security:** Default VPC, multi-AZ subnets. ALB SG: 0.0.0.0/0→80/443. ECS SG: ALB→8000. Cloudflare Access (Entra ID) gates the ALB DNS. Task execution role: `AmazonECSTaskExecutionRolePolicy`. Task role: 18 granular Sids covering CUR S3 read, EC2/RDS/ECS/S3/Lambda/DynamoDB/ELBv2/CloudFront/ElastiCache describe, CloudWatch GetMetric, Pricing GetProducts, STS GetCallerIdentity. GitHub Actions OIDC role: federated trust `repo:{github_repo}:*`.
- **Storage & Databases:** S3 bucket `{env}-seip-cur-{account-id}` holds CUR 2.0 Parquet (daily delivery, Snappy compression). No database — all analysis in-memory. CloudWatch Log Group `/ecs/prd-euc1-penny` (30-day retention).

### 2. CI/CD & GitOps Automation

- **Pipelines:** GitHub Actions `.github/workflows/deploy.yml`. Stages: (1) `quality-checks` parallel: ruff lint + Trivy CRITICAL scan (SARIF to GitHub Security); (2) `build-push`: OIDC login, ECR push `{sha}` + `latest`, BuildKit GHA cache per branch, provenance `mode=max`, SBOM enabled; (3) `deploy`: read `.aws/task-definition.json`, render new task def with image URI + env vars, ECS rolling update, wait for stability.
- **Kubernetes Delivery:** N/A — ECS Fargate.
- **Security Gates:** Trivy CRITICAL blocks deploy. ECR image scanning on push. Supply-chain: SBOM + provenance attestation.

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** CloudWatch Logs (30 d). ALB access logs (not configured in Terraform). Application exposes `/api/status` (cache age, row count) and `/api/diagnostics` (CUR + live resource cache state).
- **Log Forwarding:** ECS `awslogs` driver → CloudWatch.
- **Alerting Criteria:** ALB target group health check `GET /health` every 30 s, 2 healthy / 3 unhealthy threshold. No custom CloudWatch alarms configured.

### 4. Technical Challenges & Complex Workflows Resolved

- **CUR Auto-Discovery:** `_discover_cur_files()` calls `sts:GetCallerIdentity` to determine account ID for bucket name, then lists S3 to find lexicographically latest billing period folder — adapts without hardcoded paths even if report name changes.
- **Column Mapping Abstraction:** 28 CUR v2 column names mapped to 18 internal `C_*` constants, with `_apply_column_map()` normalizing across CUR schema variants (v1/v2 naming differences).
- **App Inference for Untagged Resources:** Multi-step tag inference: `C_APP` → `C_PROJECT` → raw `resource_tags_user_app` → ARN pattern match (seip/penny/deep-mind) → name tag → "untagged". Avoids data quality gap from poor tagging hygiene.

### 5. Potential Bottlenecks & Day-2 Technical Debt

- ALB always-on (~$16/mo fixed) — no scale-to-zero capability unlike azure-penny's Container Apps.
- `.aws/task-definition.json` in repo AND Terraform define task def — drift risk.
- No historical persistence — trends reset on container restart; no time-series database.
- `DELETE /api/resource` endpoint can terminate EC2 / stop RDS with no approval workflow.
- Pricing API (`pricing:GetProducts`) for spot hints has no throttle fallback.

---

## Project: azure-penny — Azure Cost Management Dashboard

- **Business Domain:** FinOps / Azure Cloud Cost Visibility
- **Core Architecture:** Azure Container App (scale-to-zero, 0–1 replicas) running FastAPI. Reads Azure Cost Management daily Parquet/CSV exports from Blob Storage (`cost-exports` container) into pandas in-memory cache (1 h TTL). Entra ID Easy Auth (ACA built-in) gates all traffic; `penny-admin` app role required for DELETE operations. Managed Identity for all Azure SDK calls — no static credentials.
- **Primary Tech Stack:** Python 3.11, FastAPI 0.111.0, uvicorn 0.29.0, pandas 2.2.2, pyarrow 16.0.0, azure-storage-blob 12.19.1, azure-identity 1.16.0, azure-mgmt-resource 23.1.1, azure-mgmt-compute 31.0.0, azure-mgmt-storage 21.1.0, azure-monitor-query ≥1.4.0, Jinja2 3.1.4; Terraform azurerm 4.67.0, azuread ~3.0, azapi ~2.0

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** Azure (Sweden Central default)
- **IaC Tool:** Terraform; state backend Azure Blob Storage `azurepennytff04cd1` / `tfstate`. Bootstrap script `scripts/bootstrap-tfstate.sh`. Modules: inline (single `main.tf`, 572+ lines).
- **Compute & Runtime:** Container App `ca-{env}-{loc}-penny` (min 0, max 1 replica, 0.5 CPU, 1 GB). Container App Environment shares `azure-penny-prod-env` (cost: reuse free tier). Revision mode: Single. ACR `acr{env}{loc}penny` Standard — admin disabled, AcrPull via managed identity.
- **Networking & Security:** Container App managed HTTPS (platform-provided TLS). Easy Auth: Entra ID AAD, issuer `https://login.microsoftonline.com/{tenant}/v2.0`, unauthenticated → redirect. App roles: `penny-admin` (UUID `f0e1d2c3-b4a5-4968-9c8d-7e6f5a4b3c2d`). User-Assigned Managed Identity `id-{env}-{loc}-penny`: `Storage Blob Data Reader` (storage account scope), `AcrPull` (ACR scope), `Contributor` (subscription scope, for live resources tab). Azure Cost Management SP (`e5408ad0-c4e2-43aa-b6f2-3b4951286d99`): `Storage Blob Data Contributor` on storage account to write exports.
- **Storage & Databases:** Storage Account `st{env}{loc}{random}` — Standard BlobStorage, Hot, LRS, TLS 1.2, versioning enabled, 7-day soft delete. Container `cost-exports` (private). Log Analytics Workspace: PerGB2018, 31 days, 1 GB daily quota.

### 2. CI/CD & GitOps Automation

- **Pipelines:** GitHub Actions: `ci.yml` (PR: ruff, terraform validate, docker build dry-run); `cd.yml` (main/dev push: detect env → OIDC Azure login → `az acr build` → `az containerapp update --image`); `terraform.yml` (terraform/* changes or dispatch: plan on PR, apply on merge).
- **Kubernetes Delivery:** N/A — Container Apps. `az containerapp update` for image rotation.
- **Security Gates:** ruff lint + terraform fmt check on PRs. No Trivy/Snyk.

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** Log Analytics Workspace 31-day retention. Container App streams stdout to workspace. Azure Monitor platform metrics (CPU, memory, requests, latency).
- **Log Forwarding:** Container App native → Log Analytics.
- **Alerting Criteria:** No alerts configured. App `/api/status` + `/api/diagnostics` expose cache health.

### 4. Technical Challenges & Complex Workflows Resolved

- **AKS Managed RG Inference:** AKS creates MC_ resource groups for untagged resources (`mc_{parent-rg}_{cluster-name}_{region}`). `_infer_app_from_mc_rg()` regex-extracts `seip` from `mc_..._dev-seip-aks_...` — recovers cost attribution for infrastructure resources that Azure creates automatically.
- **Cost Management API Fallback:** `_load_from_cost_management_api()` silently invoked when no blob exports exist — queries REST API directly for 90-day lookback (useful first 24 h after setup before first export arrives).
- **Column Variance by Agreement Type:** Azure exports differ between EA, MCA, CSP. `COLUMN_MAP` with ordered fallback list: `PaygCostInBillingCurrency` → `CostInBillingCurrency` → `Cost` → `PreTaxCost` handles schema differences gracefully.

### 5. Potential Bottlenecks & Day-2 Technical Debt

- FastAPI 0.111.0 / pandas 2.2.2 — significantly older than aws-penny (0.136.1 / 3.0.3). Dependencies should be aligned.
- `Contributor` at subscription scope is overly broad — should be scoped to specific resource groups.
- Easy Auth `X-MS-CLIENT-PRINCIPAL` header parsing is silent on decode/JSON errors — returns empty roles (access denied silently).
- Cold start 5–10 s from scale-to-zero (Container Apps) — noticeable for interactive use.
- No historical data persistence — all analysis in-memory, trends lost on restart.

---

## Project: az-llm-aks — Azure Spot LLM Inference on AKS

- **Business Domain:** ML Infrastructure / On-Demand LLM Inference
- **Core Architecture:** AKS cluster (v1.33, Azure CNI, Node Autoprovision/Karpenter) with FastAPI control plane managing Ollama inference pods dynamically. Model weights stored in Azure Blob (BlobFuse2, 500 Gi PVC) — mounted ReadOnlyMany across all inference pods (zero per-node download). Control plane handles: model CRUD in CosmosDB, K8s Deployment provisioning, streaming proxy to Ollama pods, blob cache management (pull jobs), and spot SKU inventory. Nightly cluster auto-destroy (GitHub Actions cron) for cost savings; permanent infra (storage, CosmosDB, static IP) in separate Terraform `base` root.
- **Primary Tech Stack:** Python 3.11, FastAPI 0.111.0+, uvicorn, Azure CosmosDB (SQL API, Session consistency), azure-identity (Workload Identity), kubernetes Python client; Terraform azurerm 4.69.0, Helm cert-manager 1.16.3 + ingress-nginx 4.11.3; Karpenter NodePool `spot-cpu-inference`, BlobFuse2 CSI

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** Azure (West US 2)
- **IaC Tool:** Terraform split: `terraform/base/` (permanent: RG, Storage, CosmosDB, ACR, static IP, state: `dev-base.terraform.tfstate`) + `terraform/cluster/` (destroyable: AKS, identity, RBAC, Helm releases, K8s secrets, state: `dev-cluster.terraform.tfstate`). Backend: Azure Blob Storage `azllmakstf0673`.
- **Compute & Runtime:** AKS `aks-dev-wus2-llm` — system pool: 1× `Standard_D2als_v6` (fixed). Inference nodes: Karpenter NodePool `spot-cpu-inference`, spot preferred + on-demand fallback, D/E/F/A/L families, 2–4 vCPU, taints `workload=inference:NoSchedule`, consolidation 1 min. Control plane: K8s Deployment 1 replica (`Standard_D2als_v6`), 500m/512Mi req, 2 CPU/2 Gi limit, Recreate strategy. ACR `acrdevwus2llm` Standard. Cert-manager + ingress-nginx (static IP `pip-dev-wus2-llm`).
- **Networking & Security:** Azure CNI + Azure Network Policy. Static public IP bound to ingress-nginx via Azure LB annotation. IP whitelist `${ALLOWED_IP}/32` enforced by nginx annotation. TLS via cert-manager (Let's Encrypt, `letsencrypt-prod` ClusterIssuer). Workload Identity: User-Assigned Identity `id-dev-wus2-llm`, federated cred → SA `default:control-plane-sa`. RBAC: `Storage Blob Data Reader` (models blob), `Cosmos DB Account Reader Role` (metadata), `Virtual Machine Contributor` + `Network Contributor` (resource group, for spot inventory API). K8s RBAC: control-plane SA can CRUD Deployments/Services/Jobs/Pods in `default` namespace, read-only cluster Nodes/Events.
- **Storage & Databases:** Storage Account (Standard LRS) + container `ollama-models` (500 Gi PVC ReadOnlyMany via BlobFuse2 FUSE2 protocol, node secret `azure-blob-secret`). RW PVC `ollama-models-pvc-rw` for cache-pull jobs. CosmosDB `az-llm-aks` (GlobalDocumentDB, Session consistency, single region): containers `models` (partition `/id`), serving model metadata. Azure Monitor Workspace `prom-dev-wus2-llm`, App Insights `appi-dev-wus2-llm`.

### 2. CI/CD & GitOps Automation

- **Pipelines:** GitHub Actions `.github/workflows/deploy.yml`. Triggers: push to `main`, PR to `main`. Jobs: (1) `lint-test`: ruff + mypy + pytest; (2) `build-push` (main only): `az acr build`, tags `latest` + `{sha}`; (3) `deploy`: get AKS creds, sync K8s secrets (CosmosDB key, App Insights, subscription ID), apply Karpenter NodePool, apply control-plane manifests with `envsubst` (domain, allowed IP). Terraform: `terraform-base.yml` (auto-apply on base changes), `terraform-cluster.yml` (manual dispatch or cron midnight UTC for nightly destroy/redeploy).
- **Kubernetes Delivery:** Direct `kubectl apply` (manifests in `k8s/`). Inference pod Deployments generated dynamically by `k8s/inference/generate_deployment.py` and applied via control plane Python Kubernetes client.
- **Security Gates:** mypy type checking. No Trivy/Snyk in current pipeline.

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** Azure Monitor Workspace (Prometheus-compatible, AKS `monitor_metrics` addon). App Insights with OpenTelemetry (`azure.monitor.opentelemetry`). Log Analytics `log-dev-wus2-llm` (30 d). Fluent Bit DaemonSet → Log Analytics.
- **Log Forwarding:** Fluent Bit DaemonSet in `kube-system` parses JSON stdout → Elasticsearch (via Log Analytics agent). TLS verify Off on Fluent Bit output.
- **Alerting Criteria:** Prometheus alert rule `NodeCpuHigh` — avg CPU > 90% for 10 min → Action Group `ag-dev-wus2-llm`.

### 4. Technical Challenges & Complex Workflows Resolved

- **BlobFuse2 ReadOnlyMany PVC:** All inference pods mount the same Blob container simultaneously (ReadOnlyMany). Model weights downloaded once to Blob, available cluster-wide with no per-node download. Cache-pull K8s Jobs use a separate ReadWriteMany PVC to write new weights. Eliminates the 15–45 min `ollama pull` bottleneck per new node.
- **Nightly Cluster Destroy + Preserve Permanent Infra:** Terraform split between `base/` (never destroyed) and `cluster/` (nightly teardown). Static IP and storage account survive the cluster deletion. Cluster reconstructed from scratch in ~10 min on next morning's workflow. Cuts dev compute cost by ~75%.
- **Dynamic Inference Deployment Generation:** `generate_deployment.py` generates Kubernetes Deployment + Service YAML at runtime from model parameters (CPU/mem requests, replicas, model name sanitization for K8s naming). Control plane provisions inference pods via Python Kubernetes client API — no manual kubectl required.

### 5. Potential Bottlenecks & Day-2 Technical Debt

- No API authentication — all endpoints public within IP whitelist. Single allowed IP is a single point of access failure.
- Control plane runs as root (no `USER` in Dockerfile), no `securityContext` (`runAsNonRoot`, `readOnlyRootFilesystem`).
- Wildcard CORS (`allow_origins=["*"]`) unnecessary given IP restriction.
- Hardcoded subscription ID default in `inventory.py` — security info leak in source.
- CosmosDB uses key auth (`COSMOS_KEY`) — not RBAC. Key stored in K8s Secret (base64 only).
- Single region (West US 2) — no failover. Cluster destruction = full service outage until re-provision.
- Fluent Bit `tls.verify Off` — certificate validation disabled on log forwarding.

---

## Project: az-spot-orchestrator — Spot VM LLM Orchestration Platform

- **Business Domain:** ML Infrastructure / Cost-Optimized LLM Inference on Azure Spot VMs
- **Core Architecture:** Single stable control-plane VM (`Standard_D2s_v3`, swedencentral) running Docker Compose: FastAPI + Temporal workflow engine (SQLite backend) + ELK stack. Control plane dynamically provisions Azure Spot VMs in cheapest available region, installs Ollama via cloud-init, mounts model weights from Azure Blob (lz4-compressed archive) or Azure Files NFS share. Temporal workflows handle: region selection via Azure Retail Prices API, multi-region fallback on `SkuNotAvailable`, blob seeding, server-side blob copy across regions, NFS share provisioning. IMDS eviction monitor on every Spot VM calls back to control plane on preemption → automatic re-provision.
- **Primary Tech Stack:** Python, FastAPI ≥0.110.0, temporalio ≥1.3.0, azure-cosmos ≥4.7.0, azure-mgmt-compute ≥30.0.0, azure-mgmt-network ≥25.0.0, azure-mgmt-storage ≥21.0.0, azure-storage-blob ≥12.28.0, azure-storage-file-share ≥12.14.0, azure-identity ≥1.15.0, lz4 ≥4.4.5, aiohttp ≥3.9.0, httpx ≥0.26.0; Terraform azurerm ~3.0; Elasticsearch/Kibana/Filebeat 8.13.0

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** Azure (swedencentral for control plane; candidate regions: eastus, westus2, eastus2, westeurope, northeurope, southeastasia, australiaeast, japaneast, canadacentral)
- **IaC Tool:** Terraform; state backend Azure Blob Storage `azspotorchtfstate` / `tfstate`, resource group `az-spot-orchestrator-tfstate-rg`. Providers: azurerm ~3.0, azuread ~2.0, github ~6.0.
- **Compute & Runtime:** Control plane VM `az-spot-orchestrator-vm` (Standard_D2s_v3, Ubuntu 22.04 LTS Gen2, system-assigned managed identity). Spot VMs: ephemeral, provisioned on-demand across cheapest region. Default size: `Standard_NC4as_T4_v3` (GPU) or `Standard_D2s_v3` (CPU-only). Spot VMs use free Azure temp disk (`/mnt/resource`) for Ollama model storage — no paid disk.
- **Networking & Security:** VNet `az-spot-orchestrator-vnet` (`10.1.0.0/16`), subnet `10.1.0.0/24`. NSG: SSH/API/Temporal UI/Kibana restricted to single source IP `78.80.157.131`. Control plane static public IP `135.225.121.221` embedded in cloud-init (Spot VMs call back on eviction). OIDC GitHub Actions (no client secret). Managed identity: Contributor (RG), Storage Blob Delegator + Data Contributor (blob), Cosmos DB Data Contributor.
- **Storage & Databases:** CosmosDB `az-spot-orchestrator` (serverless): containers `llm-models`, `vm-instances`, `model-cache`, `files-shares`, `system-messages`. Azure Blob `azspotmodelcache` / `model-cache` (Standard LRS) for lz4-compressed model archives. Regional Azure Files accounts (`azspotfiles{region}`) for NFS shares (~2 min mount, fastest path). Default models seeded: Qwen 2.5 1.5B, Qwen 3.5 9B, Qwen3 32B (Standard_NC12s_v3), DeepSeek R1 14B, Llama 3.2 11B Vision, SmolLM2 1.7B.

### 2. CI/CD & GitOps Automation

- **Pipelines:** GitHub Actions `cd.yml`: (1) ruff + mypy + Docker build (PR); (2) build + push to GHCR `ghcr.io/mysak7/az-spot-orchestrator:latest`; (3) OIDC Azure login; (4) `az vm run-command invoke` on control plane to sync docker-compose.yml, write .env from GH Vars, pull + start API + worker + ELK stack.
- **Kubernetes Delivery:** N/A — Docker Compose on single VM. 6 services: Temporal (SQLite), API (FastAPI), Worker (Temporal), Elasticsearch, Kibana, Filebeat.
- **Security Gates:** ruff + mypy on PRs. GHCR push. OIDC (no stored Azure credentials).

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** ELK stack (Elasticsearch 8.13.0 + Kibana 8.13.0) for structured log aggregation. Filebeat DaemonSet ships Docker container logs (`/var/lib/docker/containers`, read-only mount). Temporal UI port 8080 for workflow visualization.
- **Log Forwarding:** Filebeat → Elasticsearch 9200. No TLS (xpack.security.enabled=false). Kibana port 5601.
- **Alerting Criteria:** No automated alerts. System messages API (`/api/messages`) posts warnings/errors to dashboard. Keep-alive watchdog re-provisions stale instances (stuck > 20 min in pre-running) automatically.

### 4. Technical Challenges & Complex Workflows Resolved

- **Multi-Region Spot Fallback (Temporal Workflow):** `ProvisionVMWorkflow` queries Azure Retail Prices API for cheapest region, then iterates candidate regions in price order. On `SkuNotAvailable` error, async cleanup of partial resources + retry next region. Deterministic Temporal workflow ensures no partial state — all side effects in Activities.
- **Model Cache Priority Chain:** cloud-init resolves best model source: (1) same-region Azure Files NFS (~2 min); (2) same-region Blob lz4 archive (~10 min); (3) nearest-region Blob copy (~15–20 min); (4) `ollama pull` from internet (~15–45 min). Server-side Blob copy via `CopyBlobWorkflow` avoids data egress charges.
- **IMDS Eviction Monitor:** Bash systemd service on every Spot VM polls IMDS `scheduledevents` every 15 s. On `Preempt` event: `POST /api/vms/{vm_name}/evicted` → control plane starts `DeleteVMWorkflow` + `ProvisionVMWorkflow` in new cheapest region. Zero-touch recovery from Spot preemption.

### 5. Potential Bottlenecks & Day-2 Technical Debt

- One VM per model (proxy picks most-recent) — no load balancing or HA for inference. Single Spot VM preemption = model unavailability until re-provision (5–15 min).
- CosmosDB key auth (not RBAC) — COSMOS_KEY in .env on disk.
- Elasticsearch with `xpack.security.enabled=false` — no auth on log store, accessible to anyone with NSG access.
- `CONTROL_PLANE_URL` hardcoded to `135.225.121.221` in cloud-init — IP change requires Terraform apply + all running VMs to be replaced.
- NSG source IPs hardcoded in Terraform (personal IP `78.80.157.131`) — requires manual Terraform update when IP changes.
- Temporal uses SQLite backend — not suitable for HA; data lost if control plane VM is deleted.

---

## Project: az-hub-spoke — Azure Enterprise Hub-Spoke Network

- **Business Domain:** Enterprise Networking / Azure Network Perimeter (Lab/Demo)
- **Core Architecture:** Hub VNet (`10.0.0.0/16`) with Azure Firewall Basic + Azure Bastion. Two spoke VNets (App `10.1.0.0/16`, Mgmt `10.2.0.0/16`) peered to hub with forced tunneling via UDRs (default route `0.0.0.0/0` → Firewall private IP, BGP propagation disabled). App services (4 Flask/Python Web Apps) behind Azure Front Door Standard + WAF (OWASP DefaultRuleSet v2.1 + BotManagerRuleSet v1.0). Entra ID app-per-service with group-based access control. Private DNS zones for Blob + Key Vault linked to hub and app spoke.
- **Primary Tech Stack:** Terraform azurerm 4.20.0, azuread ~3.0; Azure Firewall Basic, Azure Bastion Basic, Azure Front Door Standard, WAF Policy; Python 3.11 / Gunicorn on App Service Plan Linux B1

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** Azure (swedencentral default)
- **IaC Tool:** Terraform, providers azurerm 4.20.0 + azuread ~3.0 + archive ~2.0. Backend: Azure Blob Storage (configured externally). Naming: `{resource-type}-{env}-{region_short}-{purpose}`.
- **Compute & Runtime:** App Service Plan Linux B1 (1 vCPU, 1.75 GB). 4 Web Apps: `app-hr`, `app-finance`, `app-admin`, `app-status`. All Python 3.11 + Gunicorn. IP restrictions: default Deny + AllowFrontDoor service tag (all except status page). Azure Bastion Basic SKU in `AzureBastionSubnet 10.0.2.0/26`.
- **Networking & Security:** Hub VNet: `AzureFirewallSubnet 10.0.1.0/26`, `AzureFirewallManagementSubnet 10.0.5.0/26`, Bastion `10.0.2.0/26`, Shared Services `10.0.3.0/24`, DNS `10.0.4.0/24`. App Spoke: Web `10.1.1.0/24` (UDR), App `10.1.2.0/24` (UDR), Private Endpoint `10.1.10.0/24` (no UDR), WebApps delegation `10.1.4.0/24`. Mgmt Spoke: Tools `10.2.1.0/24` (UDR), Jump `10.2.2.0/24` (UDR). Firewall rules: allow HTTP/HTTPS + DNS from `10.0.0.0/8`. Private DNS: `privatelink.blob.core.windows.net` + `privatelink.vaultcore.azure.net` linked to hub + app spoke. Network flow logs: 30-day retention, Traffic Analytics 10-min intervals.
- **Storage & Databases:** Storage account for flow logs (LRS, TLS 1.2). No application databases (Web Apps are demo apps).

### 2. CI/CD & GitOps Automation

- **Pipelines:** No CI/CD pipeline in repo. Manual `terraform apply` deployment.
- **Kubernetes Delivery:** N/A.
- **Security Gates:** Terraform plan review. WAF Prevention mode with managed rules.

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** Log Analytics Workspace `law-{env}-{region}` (PerGB2018, 30 days). Diagnostic settings: Firewall → LAW (AZFWNetworkRule, AZFWNatRule), Bastion → LAW (BastionAuditLogs). Network Watcher flow logs on App + Mgmt VNets.
- **Log Forwarding:** Azure Diagnostic Settings → Log Analytics.
- **Alerting Criteria:** 3 metric alerts → Action Group (email): (1) Firewall health < 90%, severity 1, 5-min window; (2) SNAT port utilization > 80%, severity 2, 5-min window; (3) Bastion active sessions > 50, severity 3, 5-min window.

### 4. Technical Challenges & Complex Workflows Resolved

- **Forced Tunneling via UDRs:** All spoke subnets (except Private Endpoint and Bastion subnets) have default route `0.0.0.0/0 → VirtualAppliance` (Firewall private IP) with BGP propagation disabled. Ensures zero-trust egress inspection with no accidental internet breakout via VNet peering.
- **App Service VNet Integration + Delegation:** `10.1.4.0/24` delegated to `Microsoft.Web/serverFarms` for outbound VNet integration from Web Apps. Web Apps route outbound traffic through Firewall via this subnet.
- **Front Door + IP Restriction Combination:** Web Apps restrict inbound to `AzureFrontDoor.Backend` service tag (prevents bypass of WAF by direct ALB access). Status page intentionally has no group restriction (public dashboard).

### 5. Potential Bottlenecks & Day-2 Technical Debt

- Azure Firewall Basic SKU — no stateful packet inspection, no IDPS, no TLS inspection. Not suitable for production security enforcement.
- No private endpoint for App Services (Web Apps expose public endpoints, protected only by Front Door service tag + Entra ID).
- Entra ID client secrets expire `2027-12-31` — no rotation automation.
- Single NAT path through Firewall — if Firewall fails, all spoke egress breaks (no redundancy in Basic tier).
- No DNS Private Resolver configured — custom DNS resolution for privatelink zones requires additional setup.

---

## Project: az-k3s — Multi-Region K3s Cluster with WireGuard Mesh

- **Business Domain:** Kubernetes Infrastructure / Multi-Region Edge Cluster (Lab)
- **Core Architecture:** Terraform provisions VMs across 2 Azure regions (Denmark East + North Europe), then cloud-init bootstraps WireGuard VPN mesh (`10.10.0.0/24`) between all nodes. Master node gets Ansible installed + inventory pre-configured for K3s deployment via playbook. K3s inter-node traffic flows over WireGuard (encrypted cross-region). All VM configuration (WireGuard keys, SSH keys, Ansible inventory) embedded as base64 in cloud-init — stateless provisioning.
- **Primary Tech Stack:** Terraform azurerm, WireGuard (via cloud-init), Python 3 + Ansible (master node); Ubuntu 22.04 LTS; K3s (via Ansible playbook, not in repo itself)

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** Azure (Denmark East + North Europe)
- **IaC Tool:** Terraform single `main.tf`. No remote state configured (local `terraform.tfstate` in repo). Providers: azurerm.
- **Compute & Runtime:** Master: `Standard_B2s` (2 vCPU, 4 GB, Denmark East). Workers: `node1` B1ms (Denmark East), `node2`+`node3` B2ls_v2 (North Europe). All Ubuntu 22.04 LTS Gen2, 30 GB Premium_LRS OS disk. No load balancer — direct public IP per VM.
- **Networking & Security:** Per-region: VNet (`10.1.0.0/16` / `10.2.0.0/16`), subnet, NSG. NSG rules: SSH TCP 22 from `allowed_ssh_cidr` (default `*` — should restrict), WireGuard UDP 51820 from any. WireGuard mesh: each VM assigned `/32` from `10.10.0.0/24` (master: `.1`, node1: `.2`, node2: `.3`, node3: `.4`). PersistentKeepalive 25 s for NAT hole-punching across regions.
- **Storage & Databases:** No additional storage. OS disk only.

### 2. CI/CD & GitOps Automation

- **Pipelines:** None. Manual `terraform apply` then optional Ansible playbook.
- **Kubernetes Delivery:** Ansible playbook (external Git repo via `ansible_playbook_repo` variable). K3s not installed by Terraform — post-provisioning step.
- **Security Gates:** `allowed_ssh_cidr` defaults to `0.0.0.0/0` — must restrict manually.

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** None configured.
- **Log Forwarding:** None.
- **Alerting Criteria:** None.

### 4. Technical Challenges & Complex Workflows Resolved

- **Stateless Cross-Region VPN Bootstrap:** WireGuard config (private key, all peer public keys, endpoints) base64-encoded and embedded in cloud-init `write_files`. No post-provisioning SSH required for network setup — VPN mesh is operational on first boot before Ansible runs.
- **Dynamic Ansible Inventory Generation:** Master's cloud-init writes `/etc/ansible/hosts` with WireGuard IPs (not public IPs) — K3s join tokens flow over encrypted VPN, not public internet. No manual inventory management needed.
- **WireGuard Key Generation Script:** `scripts/gen-wg-keys.sh` generates key pairs and outputs in `terraform.tfvars` format for direct pasting. Separates key management from Terraform state.

### 5. Potential Bottlenecks & Day-2 Technical Debt

- Terraform state stored locally (`terraform.tfstate` in repo) — state loss risk, not team-shareable.
- `allowed_ssh_cidr` defaults to `0.0.0.0/0` — SSH brute-force exposure.
- B-series VMs are burstable — unsuitable for sustained K3s workloads; CPU throttling under load.
- No load balancer — clients connect directly to master's public IP; master failure = cluster unreachable.
- WireGuard private keys in `terraform.tfvars` (gitignored by convention but easy to leak).

---

## Project: az-ledger-lens — Personal Finance Document Intelligence Pipeline

- **Business Domain:** Personal FinTech / Invoice & Receipt Processing with RAG
- **Core Architecture:** Event-driven serverless pipeline on Azure under Free Tier (4 vCPU max). Gmail API (historical backfill or Push Notifications → GCP Pub/Sub → webhook) → Azure Storage Queue (`email-ids`) → KEDA-scaled ACA workers (0–4 replicas, 1 vCPU each, trigger: 5 messages/replica) → GPT-4o multimodal extraction + `text-embedding-3-small` (1536 dims) → SQLite with sqlite-vec + Azure Table Storage. Dashboard (FastAPI + HTMX, always-on 0.25 vCPU) provides CRUD + LLM config hot-reload via Azure App Configuration.
- **Primary Tech Stack:** Python 3.12, FastAPI 0.115+, openai 1.30+ (GPT-4o + text-embedding-3-small), sqlite-vec 0.1.6, azure-storage-blob 12.22+, azure-storage-queue 12.11+, azure-data-tables 12.5+, azure-appconfiguration 1.6+, azure-identity 1.17+, google-api-python-client 2.128+; Terraform azurerm

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** Azure (swedencentral)
- **IaC Tool:** Terraform `terraform/main.tf` (572 lines). State backend: Azure Blob Storage. Reuses shared ACA Environment `azure-penny-prod-env` (Free tier allows 1 environment/subscription).
- **Compute & Runtime:** ACA Worker: min 0 / max 4 replicas, 1 vCPU / 2 Gi (respects 4 vCPU free tier). KEDA custom_scale_rule on Azure Queue, targetQueueLength 5. ACA Dashboard: min 1 / max 1 replica, 0.25 vCPU / 0.5 Gi, external HTTPS. Two User-Assigned Managed Identities: `id-ledgerlens-worker` (Secrets User on KV, blob/queue/table read), `id-ledgerlens-dashboard` (Secrets Officer on KV, App Configuration data owner).
- **Networking & Security:** ACA platform-managed HTTPS. Key Vault (4 secrets: `gmail-credentials`, `gmail-token`, `openai-api-key`, `dashboard-password`). App Configuration (Free tier): LLM provider settings (model, base_url, api_key) — hot-reloadable without container restart. No plaintext secrets in Terraform state (all referenced via KV secret blocks).
- **Storage & Databases:** Storage Account (LRS): queue `email-ids`, container `raw-documents` (private), table `documents`. Blob lifecycle: Hot → Cool after 30 days, Cool → Archive after 90 days on `raw-documents/*`. SQLite + sqlite-vec (in-container, ephemeral per worker instance — not shared). Log Analytics 31-day, 1 GB/day.

### 2. CI/CD & GitOps Automation

- **Pipelines:** GitHub Actions `ci-cd.yml`: (1) ruff lint + pytest (continue-on-error); (2) build+push worker+dashboard to GHCR (`sha-{commit}` + `latest`); (3) Terraform plan on PR (posts to PR comments); (4) Terraform apply on main push (with image tags from build job, concurrency group `terraform-production`). OIDC Azure auth.
- **Kubernetes Delivery:** N/A — ACA. Terraform `azurerm_container_app` resource updates image on apply.
- **Security Gates:** ruff lint. No container vulnerability scanning.

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** Log Analytics Workspace (31 d, 1 GB/day quota). ACA streams container logs. Dashboard `GET /partials/stats` (HTMX polling) shows live queue depth + document counts.
- **Log Forwarding:** ACA native → Log Analytics.
- **Alerting Criteria:** None configured in Terraform.

### 4. Technical Challenges & Complex Workflows Resolved

- **Free Tier Constraint Engineering:** Hard limit 4 vCPU enforced via `max_replicas = 4` with 1 vCPU/worker. Dashboard deliberately 0.25 vCPU. KEDA target 5 messages/replica scales linearly up to quota. Azure App Configuration Free tier used for hot-reload (avoids Key Vault restart cycle).
- **Hybrid RAG (Text-to-SQL + Vector):** sqlite-vec extension adds `vec0` virtual table for cosine similarity search. Same SQLite database stores structured rows (`documents`) and vector embeddings (`document_embeddings`). Falls back to JSON embedding storage if sqlite-vec unavailable.
- **Gmail Push → Azure Webhook Path:** GCP Pub/Sub push subscription delivers Gmail change notifications to ACA webhook endpoint → decodes email ID → enqueues to Azure Storage Queue → KEDA wakes workers. Enables near-real-time invoice processing without polling.

### 5. Potential Bottlenecks & Day-2 Technical Debt

- SQLite not shared between ACA replicas — each worker has its own SQLite instance. With max 4 replicas all processing different emails, the vector store is fragmented across 4 separate files. No consolidated RAG index.
- Worker replicas ephemeral (scale-to-zero) — SQLite data lost on scale-down. Should move to PostgreSQL with pgvector.
- Gmail credentials + token stored in Key Vault as static secrets — OAuth2 token expiry handling manual (no automatic refresh in Terraform).
- Dashboard password auto-generated and stored in KV — no admin account management or MFA.
- No dead-letter queue for failed email processing — failed messages return to queue after visibility timeout, potentially infinite retry.

---

## Project: azure-log-analyzer — AKS Security Log Analysis with llama.cpp

- **Business Domain:** Cybersecurity / Batch Security Log Threat Analysis
- **Core Architecture:** Event-driven batch pipeline on AKS. FastAPI ingestion gateway accepts log batches (up to 30,000 events, `EVENTS_PER_BATCH=500`), tracks pending count in-memory. KEDA ScaledJob monitors `GET /api/v1/pending-count` (returns `{"pending": N}`), spawns K8s Jobs (maxReplicaCount 1 due to quota). Each Job: init container downloads Qwen2.5-0.5B-Instruct GGUF from Azure Blob (SAS) or HuggingFace fallback → worker claims batch → llama-cpp-python inference for each log → threat classification JSON → reports completion. Karpenter NodePool with 1-hour TTL kill-switch destroys nodes regardless of job state (cost protection). Hard budget cap $180/month.
- **Primary Tech Stack:** Python, FastAPI 0.111.0, uvicorn 0.30.1, kubernetes 30.1.0, pydantic 2.7.1; llama-cpp-python 0.3.4, httpx 0.27.0, websockets 12.0; KEDA 2.14.0 (Helm), Karpenter 0.4.0 Azure provider (Helm); Terraform azurerm 3.100+, helm 2.13+, kubernetes 2.30+

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** Azure (eastus)
- **IaC Tool:** Terraform modules: `network.tf`, `aks.tf`, `budget.tf`, `karpenter-identity.tf`, `helm.tf`, `acr.tf`, `storage.tf`. State backend: Azure Blob Storage (OIDC auth `use_oidc=true`).
- **Compute & Runtime:** AKS `loganalyzer-aks` — system pool: 1× `Standard_B2s_v2` (fixed). Worker nodes: Karpenter `log-analyzer-workers` NodePool, on-demand only, 1–2 vCPU, amd64, consolidation WhenEmpty 30 s, `expireAfter=3600s` (1-hour hard TTL). KEDA ScaledJob `log-analyzer-worker`: parallelism 1, completions 1, `activeDeadlineSeconds=3000` (50 min), backoff 1. Worker resources: 400m/800Mi req, 1000m/1Gi limit. ACR `loganalyzeracr` Basic (admin enabled). Karpenter: User-Assigned Identity `loganalyzer-karpenter`, Contributor on node RG + Network Contributor on VNet + Managed Identity Operator on kubelet identity.
- **Networking & Security:** VNet `loganalyzer-vnet` `10.0.0.0/8`, subnet `10.240.0.0/16`. Azure CNI overlay + Azure network policy. OIDC issuer enabled. Workload Identity enabled. API Service: LoadBalancer with `loadBalancerSourceRanges=[78.80.157.131/32]` + `externalTrafficPolicy=Local` (IP restriction at LB level). Bootstrap token (K8s Secret `bootstrap-token-{id}` in kube-system) required by Karpenter 0.4.0.
- **Storage & Databases:** Storage Account `loganalyzermodels` (LRS, Hot): container `models` for GGUF model cache (SAS tokens for workers). In-memory batch registry in API pod (no database — state lost on restart). Budget: `azurerm_consumption_budget_subscription` $180/month, alert at 90% actual + 100% forecasted.

### 2. CI/CD & GitOps Automation

- **Pipelines:** GitHub Actions `ci.yml` (ruff, Docker build dry-run on PRs). `cd.yml` (main push): build+push API+Worker to ACR (tags: `latest` + `sha-{commit}`), `kubectl apply` RBAC + Deployment + ScaledJob, sync worker-secrets K8s Secret, update `WORKER_IMAGE` env on API pod. `terraform.yml`: plan on PRs, apply on main/dispatch, destroy on dispatch.
- **Kubernetes Delivery:** Direct `kubectl apply`. No Helm/ArgoCD for app manifests. KEDA + Karpenter via Helm in Terraform.
- **Security Gates:** ruff lint. ACR Basic admin enabled (no RBAC pull).

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** No dedicated observability stack. Azure Monitor budget alerts. API `GET /api/v1/status` + `/api/v1/diagnostics` expose pipeline state.
- **Log Forwarding:** Stdout JSON logs from API pod to AKS log stream. No aggregation to Log Analytics.
- **Alerting Criteria:** Budget alerts at 90% + 100% forecast via `budget_alert_email`. No K8s-level alerts.

### 4. Technical Challenges & Complex Workflows Resolved

- **Karpenter 1-Hour Node TTL as Cost Kill-Switch:** `expireAfter: 3600s` in NodePool spec forces node replacement regardless of running workloads. Prevents runaway costs from stuck jobs or forgotten nodes. Complements the $180/month budget cap.
- **KEDA metrics-api Trigger for Custom Queue:** No message broker — KEDA polls the FastAPI endpoint `GET /api/v1/pending-count` (returns `{"pending": N}`) as a custom external scaler. Avoids need for Azure Service Bus, SQS, or Kafka.
- **GGUF Model Distribution via SAS Tokens:** Worker init container resolves model URL via `GET /api/v1/config/model-url` (returns SAS-signed blob URL). On SAS failure, falls back to HuggingFace download. Decouples model distribution from cluster networking.

### 5. Potential Bottlenecks & Day-2 Technical Debt

- `maxReplicaCount: 1` — serial batch processing only (single 1–2 vCPU node). Throughput limited to ~500 events per job execution.
- In-memory batch registry in API pod — state lost on pod restart; batches permanently stuck in "pending". No persistence layer.
- 1-hour Karpenter TTL may kill active jobs — job `activeDeadlineSeconds=3000` (50 min) should complete before TTL, but race condition exists.
- ACR Basic with admin enabled — static username/password credentials, no RBAC pull.
- No HTTPS on API Service (plain LoadBalancer) — no TLS for log ingestion.
- Karpenter version 0.4.0 (Azure provider) — early pre-GA release, API stability concerns.

---

## Project: dns-mysak-cloudflare — Multi-Cloud DNS & Access Control

- **Business Domain:** Platform Engineering / Multi-Cloud DNS, TLS, and Zero-Trust Access
- **Core Architecture:** Cloudflare is authoritative for `mysak.fun`. Azure DNS zone exists for Azure-native records (llm.mysak.fun, cloudfire.mysak.fun). Terraform manages Cloudflare records, Access applications, Entra ID identity provider, ACM certificates (AWS), and Azure DNS records in a single `main.tf`. Cloudflare Access (Entra ID / AzureAD) gates all production applications — single `michal.burdik@gmail.com` allow-list policy per application.
- **Primary Tech Stack:** Terraform cloudflare ~4.0, azurerm ~3.0, aws ~5.0; Cloudflare Access (Zero Trust), Entra ID (AzureAD SSO), ACM (AWS Certificate Manager)

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** Multi-cloud: Cloudflare (primary DNS + Access), Azure (DNS zone, Container Apps, AKS ingress), AWS (EIP, ALB, ACM)
- **IaC Tool:** Terraform single `main.tf` (~410 lines), local state (`terraform.tfstate` in repo — includes sensitive outputs). Variables: `cloudflare_api_token`, `entra_seip_client_id/secret`, `azure_seip_nginx_ip` (default `20.103.44.124`), `aws_penny_alb_dns`, `az_penny_aca_fqdn`.
- **Compute & Runtime:** N/A — DNS/proxy layer only. No compute managed here.
- **Networking & Security:** Cloudflare Access Applications (6): `aws-seip`, `az-seip`, `seip`, `aws-penny`, `penny`, `az-penny`. All type `self_hosted`, 24 h session, redirect to Entra ID. Identity Provider: AzureAD tenant `f50acfeb-1d10-42e2-80af-2f0ca0a0d6a0`, client ID from variable, groups enabled. Zone-wide SSL mode "full". Override for aws-penny/penny: `set_config ssl=flexible` (ALB speaks HTTP). ACM cert `aws-penny.mysak.fun`: DNS validation, lifecycle `create_before_destroy`.
- **Storage & Databases:** N/A.

### 2. CI/CD & GitOps Automation

- **Pipelines:** No CI/CD pipeline. Manual `terraform apply`.
- **Kubernetes Delivery:** N/A.
- **Security Gates:** `cloudflare_api_token` and `entra_seip_client_secret` are sensitive variables. Terraform state stored locally (risk: contains secrets).

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** Cloudflare Analytics (built-in dashboard). No custom monitoring.
- **Log Forwarding:** Cloudflare Access logs (available in Zero Trust dashboard). No forwarding to SIEM.
- **Alerting Criteria:** None configured.

### 4. Technical Challenges & Complex Workflows Resolved

- **Multi-Cloud SSL Strategy:** Three SSL modes in one zone: (1) Cloudflare Full for az-seip/az-penny (origin has valid cert); (2) Flexible for aws-penny/penny (ALB terminates HTTP, Cloudflare provides HTTPS to user via Ruleset override); (3) Azure DNS A record for llm.mysak.fun (direct, no Cloudflare proxy). Managed in Terraform `cloudflare_ruleset` by hostname matching.
- **Data Source for AWS EIP:** `data.aws_eip.nat_bastion` fetches current EIP by tag `Name=dev-nat-bastion-eip` — Cloudflare A record automatically updates when EIP changes (without hardcoding the IP in Terraform vars).
- **ACM Certificate Automation:** ACM certificate DNS validation record created as Cloudflare CNAME record in same Terraform apply — fully automated certificate issuance without manual DNS intervention.

### 5. Potential Bottlenecks & Day-2 Technical Debt

- Terraform state stored locally with `terraform.tfstate` — contains `cloudflare_api_token`, `entra_seip_client_secret`. High secret exposure risk.
- Single-person Access policy (`michal.burdik@gmail.com`) — not suitable for team use; no group-based policies.
- No CI/CD — DNS changes require manual `terraform apply` from local workstation with credentials.
- `azure_seip_nginx_ip` hardcoded as default variable `20.103.44.124` — IP changes require var update + apply.
- Cloudflare account ID and Entra Directory ID visible in state — PII/tenant exposure.

---

## Project: cloud-explorer — Multi-Cloud AI Infrastructure Explorer

- **Business Domain:** Platform Engineering / Multi-Cloud Infrastructure Investigation Agent
- **Core Architecture:** Docker Compose (5 services) running Claude Code Web UI in a containerized Ubuntu 24.04 environment with native AWS/GCP/Azure CLIs. Token auto-refresh sidecars (GCP + Azure, every 45 min) write tokens to shared volumes. PostgreSQL 17 + pgvector stores semantic memories (1024-dim Bedrock Titan embeddings, HNSW index). MCP servers: 4 AWS Labs MCP servers (core, api, knowledge, memory), GCP gcloud/Compute/GKE/Logging, Azure CLI wrapper. Netbird VPN (privileged container) enables direct probing of internal cloud IPs.
- **Primary Tech Stack:** Python 3.12, FastMCP, boto3 (Bedrock Titan Text Embeddings v2, eu-central-1), psycopg2-binary, pgvector; Node.js 22 LTS (Claude Code); PostgreSQL 17 (`pgvector` extension, 1024-dim HNSW cosine); Docker Compose

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** Multi-cloud (AWS + GCP + Azure) — this tool explores other clouds, doesn't provision its own beyond local Docker.
- **IaC Tool:** Docker Compose (5 services). No Terraform.
- **Compute & Runtime:** All local via Docker Compose. Services: `netbird` (privileged VPN), `pgvector` (PostgreSQL 17), `azure-token-refresh` (sidecar), `gcp-token-refresh` (sidecar), `agent` (Ubuntu 24.04 + Node 22 + Python 3.12 + Claude Code). Host credentials mounted read-only: `~/.aws`, `~/.config/gcloud`, `~/.azure`.
- **Networking & Security:** Netbird VPN client (`NET_ADMIN`, `SYS_ADMIN` capabilities) on `wt0` interface — enables direct internal IP probing across cloud environments. GCP/Azure tokens expire 60 min, refreshed every 45 min by sidecars. Agent reads token from shared volumes via `GCP_ACCESS_TOKEN_FILE` / `AZURE_ACCESS_TOKEN_FILE` env vars.
- **Storage & Databases:** PostgreSQL 17 (pgvector extension): database `agent_memory`, table `memories` (content, tags[], provider, embedding 1024-dim, HNSW cosine index). Connection: `postgresql://agent:agent_password@pgvector:5432/agent_memory`.

### 2. CI/CD & GitOps Automation

- **Pipelines:** None — local tool only.
- **Kubernetes Delivery:** N/A.
- **Security Gates:** Read-only cloud credential mounts. Agent instructed to operate read-only by default (CLAUDE.md rules).

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** None (local tool).
- **Log Forwarding:** Docker Compose stdout.
- **Alerting Criteria:** None.

### 4. Technical Challenges & Complex Workflows Resolved

- **Token Lifecycle Management for 3 Clouds:** GCP ADC + Azure tokens expire in 60 min. Sidecar containers refresh every 45 min and write to shared Docker volumes. Agent's `entrypoint.sh` loads token files before exec. No manual re-auth required during long sessions.
- **pgvector Semantic Memory:** Custom MCP server `aws-agent-memory` stores investigation findings with Bedrock Titan embeddings (1024 dims, normalized). `search_memory()` performs cosine similarity search over past findings — enables "have I seen this resource/pattern before?" queries across sessions.
- **MCP Server Composition:** 9 MCP servers composed via `.mcp.json`. AWS Labs servers use `uvx` (ephemeral uv environments). GCP/Azure servers use HTTP transport with bearer token from sidecar-refreshed files. Claude Code orchestrates all tools transparently.

### 5. Potential Bottlenecks & Day-2 Technical Debt

- `pgvector` container password `agent_password` hardcoded in docker-compose.yml — not suitable for shared use.
- Netbird requires `SYS_ADMIN` + `NET_ADMIN` capabilities — significant privilege escalation in container.
- GCP/Azure token refresh sidecars write tokens to unencrypted Docker volumes.
- No persistent volume for pgvector data by default — memories lost on `docker compose down -v`.
- AWS credentials mounted from host `~/.aws` — if host credentials are compromised, container inherits full access.

---

## Project: az-mongo — MongoDB Atlas RAG API

- **Business Domain:** Developer Tooling / Retrieval-Augmented Generation API
- **Core Architecture:** FastAPI RAG service on Azure Container Apps. Documents (PDF/Markdown) ingested via multipart upload → PyMuPDF text extraction → 800-char chunks (150 overlap) → batched OpenAI `text-embedding-3-small` (1536 dims, batches of 100) → MongoDB Atlas vector search index (`embedding_index`, cosine). Queries: embed question → MongoDB `$vectorSearch` aggregation (numCandidates = top_k×10) → context assembly → LLM (configurable OpenAI-compatible endpoint) → answer + sources. Optional Azure Monitor OpenTelemetry tracing.
- **Primary Tech Stack:** Python 3.11, FastAPI ≥0.110.0, uvicorn ≥0.27.0, motor ≥3.4.0 (async MongoDB), openai ≥1.30.0, PyMuPDF ≥1.24.0, azure-identity ≥1.15.0, azure-keyvault-secrets ≥4.8.0, azure-monitor-opentelemetry ≥1.3.0, python-json-logger ≥2.0.0; Terraform azurerm + mongodbatlas

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** Azure (Container Apps) + MongoDB Atlas (AZURE EUROPE_NORTH, M0 free tier)
- **IaC Tool:** Terraform (azurerm + mongodbatlas providers). State backend: Azure Blob Storage. Resources: Container App Environment (Log Analytics 31 d, 1 GB/day), Container App (0.5 CPU, 1 Gi, external HTTPS), User-Assigned Identity (Key Vault access), ACR, Key Vault (6 secrets: `mongodb-uri`, `openai-api-key`, `openai-base-url`, `llm-base-url`, `llm-api-key`, `app-api-key`). MongoDB Atlas: project `az-mongo-{env}`, M0 replica set (free), database `ragdb`, collection `chunks`, vector search index 1536-dim cosine, user `app-user` (readWrite on ragdb), IP allowlist `0.0.0.0/0`.
- **Compute & Runtime:** ACA single revision, 0.5 CPU / 1 Gi memory, external HTTPS. Docker image from ACR. User-Assigned Managed Identity for Key Vault secret injection.
- **Networking & Security:** ACA platform HTTPS. API key header auth (`x_api_key` from Key Vault). MongoDB Atlas IP allowlist `0.0.0.0/0` (should restrict post-deploy — documented in Terraform). CORS: allow-all origins, methods, headers.
- **Storage & Databases:** MongoDB Atlas M0 (free replica set, AZURE EUROPE_NORTH, `ragdb`). No Blob Storage (documents stored in MongoDB as text chunks). Log Analytics Workspace (31 d).

### 2. CI/CD & GitOps Automation

- **Pipelines:** GitHub Actions `ci.yml` (PR: ruff check + ruff format + mypy + Docker build dry-run). `deploy.yml` (main, path-filtered): build+push to ACR (SHA + latest tags), `az containerapp update --image`. OIDC Azure auth.
- **Kubernetes Delivery:** N/A — ACA. `az containerapp update` for rolling image update.
- **Security Gates:** mypy type checking. No container scanning.

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** Log Analytics Workspace (31 d). Optional App Insights via `APPLICATIONINSIGHTS_CONNECTION_STRING`. Custom ASGI middleware logs method, path, status, latency_ms as JSON.
- **Log Forwarding:** ACA native → Log Analytics.
- **Alerting Criteria:** None configured.

### 4. Technical Challenges & Complex Workflows Resolved

- **MongoDB Atlas Vector Search Pipeline:** Aggregation uses `$vectorSearch` stage with `numCandidates = top_k * 10` (ANN search widens candidate pool for better recall) then `$project` to return `vectorSearchScore`. Two-stage: ANN retrieval → exact cosine reranking implicit in Atlas.
- **Configurable LLM Endpoint:** `llm-base-url` + `llm-api-key` in Key Vault support any OpenAI-compatible endpoint (Azure OpenAI, local Ollama, etc.) — decoupled from hard-coded OpenAI dependency.
- **Batched Embedding on Ingestion:** `openai.Embeddings.create()` called in batches of 100 chunks — avoids per-chunk API calls (latency) and per-request rate limits.

### 5. Potential Bottlenecks & Day-2 Technical Debt

- MongoDB Atlas M0 free tier — connection limit (500), storage limit (512 MB), no SLA. Not production-suitable.
- IP allowlist `0.0.0.0/0` on Atlas cluster — open to internet until manually restricted.
- CORS allow-all origins — API key is only security layer.
- No pagination on `GET /api/documents/` — full collection scan for document listing; degrades at scale.
- No chunk deduplication — re-uploading same document creates duplicate chunks in MongoDB.
- Single ACA revision (no blue/green) — brief unavailability during image update.

---

## Project: seip-gui-easy — SEIP Service Landing Page & Status Dashboard

- **Business Domain:** Cybersecurity / SEIP Internal Developer Portal
- **Core Architecture:** Lightweight FastAPI web UI serving as a unified landing page for all SEIP microservices. Background: async httpx health probes (2 s timeout) to 8 registered services on `/api/status`. Dashboard renders DaisyUI + Tailwind CSS service cards with pulsing status indicators (green/red/orange/gray). Frontend JavaScript auto-refreshes every 30 s. Data flow diagram (HTML/CSS) visualizes the entire SEIP pipeline: Windows Agent → Kafka → DynamoDB → Deep Mind → Pattern Manager → S3 → hot-reload feedback loop.
- **Primary Tech Stack:** Python 3.11, FastAPI 0.115.5, uvicorn 0.32.1, Jinja2 3.1.4, httpx 0.27.2, DaisyUI 4.12.14 (CDN jsDelivr), Tailwind CSS (CDN)

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** AWS (eu-central-1)
- **IaC Tool:** None — deployed via Docker + SSM.
- **Compute & Runtime:** Docker container on `dev-app-host` EC2 (ARM64, `t4g.small`). ECR `dev/seip-gui-easy`. Port 8080 (internal), mapped to host port.
- **Networking & Security:** Internal Docker network — communicates with other SEIP services via Docker bridge (`HEALTH_CHECK_HOST=172.17.0.1`). No external ingress except through fck-nat DNAT. No authentication on the landing page itself.
- **Storage & Databases:** None.

### 2. CI/CD & GitOps Automation

- **Pipelines:** GitHub Actions `deploy.yml`. Triggers: push to `main`/`develop`, manual dispatch. Runs on `ubuntu-24.04-arm` (native ARM64). Build: `docker/build-push-action`, platform `linux/arm64`, tags `{sha}` + `latest`, GHA cache. Deploy: find EC2 `dev-app-host` by tag, `aws ssm send-command` AWS-RunShellScript: pull image + `systemctl restart seip-gui-easy`. Wait for command completion. IAM: OIDC `role/github-actions-deploy-role`.
- **Kubernetes Delivery:** N/A — Docker + systemd on EC2.
- **Security Gates:** None.

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** Healthcheck: `CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"` (30 s interval, 5 s timeout, 10 s start-period, 3 retries). `GET /api/status` returns live health of all 8 SEIP services.
- **Log Forwarding:** Docker stdout → CloudWatch (via Docker awslogs driver on host).
- **Alerting Criteria:** None.

### 4. Technical Challenges & Complex Workflows Resolved

- **Async Concurrent Health Checks:** `httpx.AsyncClient` with `asyncio.gather(*[check(svc) for svc in services])` — all 8 services probed simultaneously with 2 s timeout. Total `/api/status` response time bounded by slowest service (2 s), not sum (16 s).
- **Docker Bridge Gateway Pattern:** `HEALTH_CHECK_HOST=172.17.0.1` — container accesses other SEIP containers via Docker bridge IP rather than `localhost` or container names, enabling the health checks to work regardless of Docker Compose or standalone run mode.

### 5. Potential Bottlenecks & Day-2 Technical Debt

- Dockerfile `EXPOSE 8080` but README documents port 8090 — port inconsistency.
- No authentication — anyone on the VPN/bridge network can access the admin dashboard.
- Hardcoded service ports in Python (`3000`, `8181`, `8182`, etc.) — any port change requires code update.
- Single container on single EC2 — no HA.
- No SEIP Azure service endpoints registered (only AWS services) — needs update for azure-seip migration.

---

## Project: ZeroDaemon — Local AI DevSecOps Security Agent

- **Business Domain:** DevSecOps / Autonomous Infrastructure Drift Detection & Threat Intelligence
- **Core Architecture:** LangGraph-orchestrated agent (FastAPI on port 8222) with 5 core tools: `check_ip_owner` (ipwhois/RDAP), `scan_services` (python-nmap, presets top-10/100/1000/full), `search_threat_intel` (DuckDuckGo CVE/exploit search), `query_historical_scans` (SQLite), `search_knowledge_base` (FAISS + fastembed BAAI/bge-small-en-v1.5). Background daemon scans registered IPs every 86400 s (configurable). Multi-model registry (YAML): Claude, GPT-4, Gemini, Ollama, custom OpenAI-compatible (`syl`). Per-invocation token tracking + USD cost in SQLite. Optional MCP server integration via `langchain-mcp-adapters`.
- **Primary Tech Stack:** Python ≥3.14, FastAPI ≥0.115, LangGraph ≥0.2, LangChain ≥0.3, langgraph-checkpoint-sqlite ≥2.0, python-nmap ≥0.7, ipwhois ≥1.3, duckduckgo-search ≥6.0, faiss-cpu ≥1.8, fastembed ≥0.3 (BAAI/bge-small-en-v1.5), aiosqlite ≥0.20, langchain-anthropic/openai/google-genai/ollama; pyyaml ≥6.0

### 1. Infrastructure & Cloud Resources

- **Cloud Provider:** Local-first (no cloud infrastructure). Cloud LLM providers optional (Anthropic, OpenAI, Google, Ollama).
- **IaC Tool:** None — `setup.sh` installs system dependencies (nmap, masscan, nikto, whois, nuclei), creates Python 3.14 venv, `pip install -e .`.
- **Compute & Runtime:** Single Python process (uvicorn). SQLite databases: `zerodaemon.db` (scans, threat_intel, llm_usage tables), FAISS index `zerodaemon_rag/`. LangGraph `AsyncSqliteSaver` checkpointer persists full conversation history to SQLite.
- **Networking & Security:** No external networking. nmap requires local privilege (raw socket access). API server bound `0.0.0.0:8222`. No authentication on API. `ZERODAEMON_AUTO_INSTALL_DEPS` env flag for auto-install of system tools.
- **Storage & Databases:** SQLite `zerodaemon.db`: tables `scans` (idx_scans_ts, idx_scans_target), `threat_intel` (indicator PK), `llm_usage` (idx_llm_usage_ts, idx_llm_usage_model). FAISS in-memory + persisted.

### 2. CI/CD & GitOps Automation

- **Pipelines:** None — local tool. `run.sh` kills port 8222 process + starts uvicorn with optional `--reload`.
- **Kubernetes Delivery:** N/A.
- **Security Gates:** None.

### 3. Monitoring, Reporting & Day-2 Operations

- **Observability Stack:** `GET /models/usage/stats` — aggregate token counts + USD cost breakdown per model. `GET /scans` — historical scan results. Structured logging to stdout.
- **Log Forwarding:** Stdout only.
- **Alerting Criteria:** None configured. Daemon posts scan results to SQLite; no alerting integration.

### 4. Technical Challenges & Complex Workflows Resolved

- **Hot-Swap LLM without Restart:** `PATCH /models/{id}/activate` updates `config/models.yaml` atomically (temp file + rename) and switches active model in `registry.py` via `asyncio.Lock`. Next LangGraph invocation builds `ChatModel` from new active model. No process restart.
- **LangGraph State Machine with Tool Loop:** Agent → conditional (has tool_calls?) → tools → agent → … until no tool_calls → END. `AsyncSqliteSaver` persists every state transition — conversation resumable after process restart by thread_id.
- **Drift Detection Pattern:** Agent workflow: (1) query_historical_scans for baseline; (2) scan_services live; (3) diff ports/service versions; (4) on new ports/version changes: search_threat_intel for CVEs. Structured system prompt enforces this sequence before reporting.

### 5. Potential Bottlenecks & Day-2 Technical Debt

- **Python 3.14 requirement** — bleeding edge, not yet stable GA in most Linux distros. Setup.sh handles missing Python with auto-install, but fragile.
- No API authentication — `0.0.0.0:8222` open to any local network user.
- FAISS index not shared across instances — no multi-user support.
- nmap requires elevated privileges (raw sockets) — may fail in sandboxed environments.
- Daemon poll interval 86400 s (1 day) — no event-driven triggers; relies on schedule only.
- No alert dispatch (email, Slack, webhook) — findings stored in SQLite but not proactively surfaced.
- `syl` provider (custom local endpoint `http://syl:8001/v1`) — hardcoded service name assumes Docker network or `/etc/hosts` entry.
