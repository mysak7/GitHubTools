# mysak.fun — Cloudflare / TLS / Access architektura

> Určeno pro technický pohovor. Popisuje DNS, TLS tok, Cloudflare Access + Entra ID a Vertex Proxy integraci pro projekty AWS SEIP, Azure SEIP, AWS Penny a Azure Penny.

---

## 1. DNS — kde je autoritativní zóna

DNS zóna `mysak.fun` je registrovaná u WEDOS, ale **nameservery ukazují na Cloudflare**. Cloudflare je tedy autoritativní — všechny záznamy se spravují Cloudflare providerem v Terraformu (`dns-mysak-cloudflare/main.tf`).

Souběžně existuje Azure DNS zona `mysak.fun` (Terraform `azurerm_dns_zone`), ale ta je dekorativní — záznamy z ní byly migrované do Cloudflare a Azure DNS se jen drží kvůli několika legacy záznamům (`llm`, `grafana.llm`, `cloudfire`).

```
Registrátor (WEDOS) → NS záznamy → Cloudflare nameservery
                                          │
                                    záznamy v Cloudflare
                                    (spravuje TF provider cloudflare/cloudflare)
```

---

## 2. TLS termination — kde se šifrování ukončuje

Každý záznam v Cloudflare je nastaven na `proxied = true`. To znamená, že **klient nikdy nekomunikuje přímo s originem** — komunikuje s Cloudflare edge PoP.

### Globální nastavení zóny

```hcl
resource "cloudflare_zone_settings_override" "mysak_fun" {
  settings {
    ssl = "full"   # origin musí mít platný certifikát, ale chain se nekontroluje
  }
}
```

### Přehled SSL módů a kde platí

| Mód | Popis | Kde se používá |
|-----|-------|----------------|
| `flexible` | Client↔CF = HTTPS, CF↔origin = **HTTP** | aws-penny, penny |
| `full` | Client↔CF = HTTPS, CF↔origin = HTTPS (certifikát se ověřuje) | az-seip, aws-seip, az-penny (default zóny) |
| `strict` | jako full + ověří celý řetězec | nepoužívá se |

### Proč `flexible` pro aws-penny?

ALB má ACM certifikát a HTTPS listener (port 443), ale **Cloudflare se připojuje k ALB DNS jménu** (`alb-prd-euc1-penny-279184951.eu-central-1.elb.amazonaws.com`), a ACM certifikát je vydán pro `aws-penny.mysak.fun`. Cloudflare by ho tedy v `full` módu odmítl jako neplatný (CN mismatch). Řešení: použít `flexible`, kde CF → ALB teče přes HTTP (port 80), a ALB sám si HTTP→HTTPS redirectuje interně.

Toto je přepsáno Cloudflare Configuration Rule (přepsání zone-wide nastavení jen pro jeden host):

```hcl
resource "cloudflare_ruleset" "aws_penny_ssl" {
  phase = "http_config_settings"
  rules {
    action = "set_config"
    action_parameters { ssl = "flexible" }
    expression = "(http.host eq \"aws-penny.mysak.fun\") or (http.host eq \"penny.mysak.fun\")"
  }
}
```

---

## 3. Projekty — TLS tok krok za krokem

### AWS SEIP (`aws-seip.mysak.fun`)

```
Client
  │  HTTPS (TLS na CF edge)
  ▼
Cloudflare Edge
  │  HTTPS — CF → origin (ssl=full)
  │  ověří certifikát na originu
  ▼
Elastic IP (dev-nat-bastion-eip)   ← AWS eu-central-1
  │  iptables DNAT
  ▼
Bastion / NAT instance (port 80/443)
  │
  └── seip-portal / nginx-ingress na EC2
```

**DNS**: `A` záznam → EIP dynamicky čtený `data.aws_eip.nat_bastion` (Terraform data source z AWS).

---

### Azure SEIP (`az-seip.mysak.fun`)

```
Client
  │  HTTPS (TLS na CF edge)
  ▼
Cloudflare Edge
  │  HTTPS (ssl=full)
  ▼
nginx-ingress LoadBalancer IP (20.103.44.124)   ← AKS, Azure
  │  Ingress rule
  ▼
SEIP Portal pod (AKS)
```

**DNS**: `A` záznam → `var.azure_seip_nginx_ip` (output z `azure-seip/infra` terraform).

---

### AWS Penny (`aws-penny.mysak.fun`, `penny.mysak.fun`)

```
Client
  │  HTTPS (TLS na CF edge, CF cert)
  ▼
Cloudflare Edge
  │  HTTP (ssl=flexible! — CF → ALB je nešifrované)
  ▼
ALB (eu-central-1)   ← port 80 redirect → 443
  │  HTTPS, ACM cert pro aws-penny.mysak.fun
  ▼
ALB HTTPS listener (port 443)
  │  forward
  ▼
Target Group → ECS Fargate container (port 8000, HTTP)
```

**ACM certifikát** je vytvořen v `dns-mysak-cloudflare/main.tf` (DNS validace přes Cloudflare CNAME), ARN se předává do `aws-penny/terraform` jako input variable. Toto vazání přes dva TF státy je záměrné — certifikát musí existovat dřív než ALB listener.

**DNS**: `CNAME` → ALB DNS jméno (statická hodnota v `variables.tf`).

---

### Azure Penny (`az-penny.mysak.fun`)

```
Client
  │  HTTPS (TLS na CF edge)
  ▼
Cloudflare Edge
  │  HTTPS (ssl=full — ACA má vlastní certifikát pro svoji FQDN)
  ▼
Azure Container App (eastus)
  │  *.azurecontainerapps.io certifikát
  ▼
Container (FastAPI, port 8000)
```

**DNS validace**: Dva TXT záznamy v Cloudflare (`asuid.az-penny` a `_5ke9xvuuxhhbsnk4xskmsaxq53qxmtc`) povolují Azure ověřit vlastnictví domény pro custom domain na ACA.

**DNS**: `CNAME` → ACA FQDN (`ca-prd-eus-penny.thankfulisland-4131bb98.eastus.azurecontainerapps.io`).

---

## 4. Cloudflare Access + Entra ID

### Co to je

Cloudflare Access je Zero Trust brána — každý HTTP požadavek musí projít autentizací, než se dostane k originu. Funguje jako reverzní proxy s identity awareness.

### Identity Provider — Entra ID (Azure AD)

Jeden `cloudflare_access_identity_provider` je sdílený pro všechny aplikace:

```hcl
resource "cloudflare_access_identity_provider" "entra_id" {
  type = "azureAD"
  config {
    client_id      = var.entra_seip_client_id
    client_secret  = var.entra_seip_client_secret
    directory_id   = "f50acfeb-1d10-42e2-80af-2f0ca0a0d6a0"
    support_groups = true
  }
}
```

**Setup v Azure portal**: App Registration s redirect URI `https://<team>.cloudflareaccess.com/cdn-cgi/access/callback`. Cloudflare mluví s Entra ID přes OAuth 2.0 / OIDC.

### Přihlašovací tok uživatele

```
1. Uživatel navštíví https://aws-seip.mysak.fun
2. auto_redirect_to_identity = true → CF Access ihned přesměruje na Entra ID login
3. Entra ID ověří identitu (MFA, Conditional Access...)
4. Entra ID vydá token → vrátí na cloudflareaccess.com/cdn-cgi/access/callback
5. CF Access zkontroluje policy: povolena jen michal.burdik@gmail.com
6. CF Access vydá session cookie (platná 24h)
7. Požadavky s platnou cookie procházejí na origin
```

### Aplikace a policies

Každá subdoména má vlastní `cloudflare_access_application` + `cloudflare_access_policy`:

| Aplikace | Doména | Allowed IDP |
|----------|--------|-------------|
| SEIP Portal (AWS) | aws-seip.mysak.fun | Entra ID |
| SEIP Portal (Azure) | az-seip.mysak.fun | Entra ID |
| SEIP (alias) | seip.mysak.fun | Entra ID |
| aws-penny | aws-penny.mysak.fun | Entra ID |
| penny | penny.mysak.fun | Entra ID |
| az-penny | az-penny.mysak.fun | Entra ID |

### Telegram webhook bypass

az-penny má Telegram Bot webhook na `/telegram/webhook`. Telegram Bot API neumí projít CF Access (nepřihlásí se). Řešení: dedikovaná Access aplikace pro tuto cestu s `decision = "bypass"`, ale bezpečnost zajišťuje aplikační vrstva:

```python
# routers/ai.py
token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
if token != TELEGRAM_WEBHOOK_SECRET:
    return JSONResponse({"ok": False}, status_code=403)
```

---

## 5. Vertex Proxy — LLM backend pro Penny apps

### Co to je

Vertex Proxy je OpenAI-kompatibilní proxy pro Google Vertex AI (Gemini modely). Postavena na **LiteLLM** — open-source proxy, která překládá OpenAI API formát na různé LLM providery.

### Kde běží

Na Azure VM `llm.mysak.fun` (IP `20.230.229.131`) jako Docker Compose stack.

### Komponenty stack

```
┌─────────────────────────────────────────────────────────┐
│  Docker Compose na llm.mysak.fun                        │
│                                                         │
│  vertex-proxy (port 4001)                               │
│    LiteLLM + litellm_config.yaml                        │
│    ↕ GOOGLE_APPLICATION_CREDENTIALS                     │
│                                                         │
│  gcp-token-refresh                                      │
│    gcloud auth application-default print-access-token   │
│    → každých 45 min zapíše token do /tmp/gcp/token      │
│                                                         │
│  db (PostgreSQL)                                        │
│    spend tracking, metriky LiteLLM                      │
│                                                         │
│  proxy-gui (Dozzle, port 4002)                          │
│    log viewer pro vertex-proxy container                │
│                                                         │
│  cloudflared                                            │
│    Cloudflare Tunnel → vystaví proxy ven bez otevřeného │
│    portu na firewallu                                   │
└─────────────────────────────────────────────────────────┘
```

### Modely

LiteLLM mapuje vlastní jména na Vertex AI modely. Klient volá `/v1/chat/completions` s `model: gemini-3.5-flash` a LiteLLM to přeloží na `vertex_ai/gemini-3.5-flash`. Vertex AI API vrátí odpověď, LiteLLM ji zabalí do OpenAI response formátu.

### Expozice přes Cloudflare Tunnel (ne Access)

Vertex Proxy **nepoužívá Cloudflare Access**, ale **Cloudflare Tunnel**:

- Cloudflare Tunnel = odchozí připojení z VM do Cloudflare edge, žádný inbound port není otevřen
- Přístup je chráněn LiteLLM master key (`LITELLM_MASTER_KEY`) — Bearer token v Authorization headeru
- Penny apps se autentizují vůči CF Access Service Tokenem (CF-Access-Client-Id/Secret headers) — to je Machine-to-Machine auth mechanismus CF Access

### Jak Penny volá Vertex Proxy

```python
# config.py (aws-penny i azure-penny, identické)
VERTEX_PROXY_URL    = os.environ.get("VERTEX_PROXY_URL", "")      # URL za CF Tunnelem
VERTEX_PROXY_API_KEY = os.environ.get("VERTEX_PROXY_API_KEY", "") # LiteLLM master key
CF_ACCESS_CLIENT_ID     = os.environ.get("CF_ACCESS_CLIENT_ID", "")
CF_ACCESS_CLIENT_SECRET = os.environ.get("CF_ACCESS_CLIENT_SECRET", "")

# routers/ai.py
headers = {
    "Authorization": f"Bearer {VERTEX_PROXY_API_KEY}",
    "CF-Access-Client-Id":     CF_ACCESS_CLIENT_ID,
    "CF-Access-Client-Secret": CF_ACCESS_CLIENT_SECRET,
}
resp = await client.post(f"{VERTEX_PROXY_URL}/v1/chat/completions", headers=headers, json=payload)
```

### AI Chat — agentic loop

Penny apps implementují agentic loop s tool use (max 5 iterací):

```
User question
    │
    ▼
POST /v1/chat/completions (model + tools + tool_choice=auto)
    │
    ▼
LiteLLM → Vertex AI (Gemini)
    │
    ├── model chce tool call? → execute tool (get_cost_summary, get_anomalies, ...)
    │       │ append tool result do messages
    │       └── repeat (až 5×)
    │
    └── model vrátí text → SSE stream na klienta
```

---

## 6. Přehled certifikátů

| Doména | Certifikát na originu | Kdo ho vydal | TLS mód |
|--------|-----------------------|-------------|---------|
| aws-seip.mysak.fun | (bastion/nginx) Let's Encrypt nebo self-signed | certbot / nginx | full |
| az-seip.mysak.fun | nginx-ingress cert-manager Let's Encrypt | cert-manager (AKS) | full |
| aws-penny.mysak.fun | ALB — ACM cert pro aws-penny.mysak.fun | AWS ACM | flexible* |
| az-penny.mysak.fun | ACA built-in cert pro *.azurecontainerapps.io | Azure | full |

\* CF → ALB teče HTTP (flexible), ALB sám má ACM cert jen pro HTTPS listener. Z pohledu klienta vždy HTTPS.

---

## 7. Co je na tom zajímavé pro pohovor

### Vícevrstvý TLS

Existují tři různé SSL módy pro tři různé originy ve stejné zóně, přičemž výjimka pro aws-penny je dynamicky přepsána Configuration Rule (HTTP config settings phase). Kandidát by měl vědět: proč flexible a ne full, co je CN mismatch, jak Configuration Rules přepisují zone settings.

### Zero Trust bez VPN

Všechny aplikace jsou dostupné z internetu, ale chráněné Cloudflare Access. Žádná VPN, žádný bastion jump pro uživatele. SEIP bastion existuje z jiného důvodu (NAT / iptables DNAT).

### Jeden IdP pro multi-cloud

Jedna App Registration v Entra ID obsluhuje CF Access pro AWS i Azure projekty. Session trvá 24h, auto-redirect. V reálném nasazení by se daly přidat Conditional Access policies v Entra (MFA, device compliance).

### Service Tokens vs User Auth

Vertex Proxy je chráněn jinak než aplikace — ne user flow (browser cookie), ale **Service Token** (CF-Access-Client-Id/Secret). To je M2M pattern: backend-to-backend volání bez uživatele.

### Cloudflare Tunnel vs otevřený port

Vertex Proxy běží na VM bez otevřeného inbound portu. `cloudflared` vytvoří odchozí WebSocket tunel do Cloudflare. Snižuje attack surface — VM neexpozuje žádný port na internet.

### LiteLLM jako abstrakční vrstva

Penny apps píší proti OpenAI API (`/v1/chat/completions`, OpenAI SDK kompatibilní), ale skutečný backend je Google Vertex AI (Gemini). Přechod na jiný model = změna v `litellm_config.yaml`, ne v aplikaci.

### ACM certifikát spravovaný v jiném TF state

Certifikát pro `aws-penny.mysak.fun` se vytváří v `dns-mysak-cloudflare` Terraform (DNS validace přes Cloudflare CNAME), ale používá ho `aws-penny` Terraform (ALB listener). ARN se předává jako output → input variable. Toto je cross-state dependency pattern.

### Telegram webhook a Access bypass

CF Access blokuje neinteraktivní klienty (boty). Řešení: dedikovaná Access aplikace s `decision = bypass` pro konkrétní path, bezpečnost delegovaná na aplikační secret. Demonstruje, kdy Zero Trust musí ustoupit integračním požadavkům.

---

## 8. Rychlý přehled toků

```
Browser uživatele
      │
      │ HTTPS → Cloudflare edge (TLS terminace zde)
      ▼
 [CF Access]  ← ověří session cookie
      │         pokud chybí → redirect na Entra ID login
      │
      │ HTTPS nebo HTTP (dle ssl mode)
      ▼
    Origin (AWS EIP / AKS nginx / ALB / ACA)
      │
      └── aplikace (SEIP portal / Penny FastAPI)
               │
               │ (pokud AI feature) HTTPS → Cloudflare Tunnel
               ▼
          Vertex Proxy (llm.mysak.fun)
               │
               └── Vertex AI API (GCP) → Gemini model
```
