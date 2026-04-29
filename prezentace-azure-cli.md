# Azure CLI — Prezentační podklady

> Zdroje: vlastní projekty az-spot-orchestrator, azure-log-analyzer, az-hub-spoke, azure-penny

---

## 1. Úvod — co je Azure CLI

Azure CLI (`az`) je multiplatformní příkazový řádek pro správu Azure zdrojů.
Instaluje se jedním příkazem, funguje na Linux/Mac/Windows, autentifikuje se přes `az login`.

**Typické použití:**
- Bootstrap infrastruktury před Terraformem
- CI/CD pipeline (GitHub Actions, Azure DevOps)
- Skriptování opakujících se operací
- Rychlé dotazování a debugging live prostředí

---

## 2. Přihlášení a kontext

```bash
# Interaktivní přihlášení
az login

# Výpis dostupných subscriptions
az account list --output table

# Přepnutí subscription
az account set --subscription "my-subscription-name"

# Ověření aktuálního kontextu
az account show --query "{sub:id, tenant:tenantId}" -o tsv
```

*Použití v projektu* (`az-spot-orchestrator/scripts/setup-env.sh`):
```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
```

---

## 3. Resource Group & Storage Account

Každý projekt začíná resource group a storage účtem pro Terraform remote state.

```bash
# Vytvoření resource group
az group create \
  --name "loganalyzer-rg" \
  --location "eastus" \
  --output none

# Vytvoření storage účtu (unikátní název, LRS, bez public access)
az storage account create \
  --name "loganalyzermodels" \
  --resource-group "loganalyzer-rg" \
  --location "eastus" \
  --sku Standard_LRS \
  --allow-blob-public-access false \
  --output none

# Vytvoření kontejneru pro tfstate
az storage container create \
  --name "tfstate" \
  --account-name "loganalyzermodels" \
  --auth-mode login \
  --output none
```

*Zdroj:* `azure-log-analyzer/scripts/bootstrap-tfstate.sh`

---

## 4. Service Principal a RBAC

```bash
# Vytvoření service principal s rolí Contributor
az ad sp create-for-rbac \
  --name "az-spot-orch" \
  --role Contributor \
  --scopes "/subscriptions/$SUBSCRIPTION_ID" \
  --output json

# Přiřazení role (Storage Blob Data Contributor na konkrétní storage account)
az role assignment create \
  --assignee-object-id "$SP_OID" \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG/providers/Microsoft.Storage/storageAccounts/$SA" \
  --output none
```

*Zdroj:* `azure-log-analyzer/scripts/bootstrap-tfstate.sh`

---

## 5. Workload Identity / OIDC pro GitHub Actions

Místo dlouhodobých secrets — federovaná identita pro CI/CD.

```bash
# Vytvoření App Registration
APP_ID=$(az ad app create \
  --display-name "loganalyzer-github-actions" \
  --query appId -o tsv)

# Vytvoření Service Principal
az ad sp create --id "$APP_ID" --output none

# Federated credential pro GitHub Actions (main branch)
az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:myorg/myrepo:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Totéž pro Pull Requesty
az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters '{
    "name": "github-pr",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:myorg/myrepo:pull_request",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

*Zdroj:* `azure-log-analyzer/scripts/bootstrap-tfstate.sh`

**GitHub Actions workflow pak používá:**
```yaml
permissions:
  id-token: write
  contents: read

- uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
```

---

## 6. Blob Storage — upload a SAS URL

```bash
# Upload souboru do blob storage
az storage blob upload \
  --account-name  "$STORAGE_ACCOUNT" \
  --account-key   "$STORAGE_KEY" \
  --container-name "models" \
  --name          "Qwen2.5-0.5B-Instruct-Q6_K.gguf" \
  --file          "/tmp/model.gguf" \
  --overwrite

# Generování SAS URL s platností 1 rok (read-only)
EXPIRY="$(date -u -d '+365 days' '+%Y-%m-%dT%H:%MZ')"
SAS_URL=$(az storage blob generate-sas \
  --account-name   "$STORAGE_ACCOUNT" \
  --account-key    "$STORAGE_KEY" \
  --container-name "models" \
  --name           "model.gguf" \
  --permissions    r \
  --expiry         "$EXPIRY" \
  --full-uri \
  --output tsv)
```

*Zdroj:* `azure-log-analyzer/scripts/upload-model.sh`

---

## 7. AKS — získání credentials

```bash
# Přidání clusteru do ~/.kube/config
az aks get-credentials \
  --resource-group az-llm-aks-rg \
  --name az-llm-aks \
  --overwrite-existing

# Ověření připojení
kubectl get nodes
```

*Zdroj:* `az-llm-aks/README.md`

---

## 8. Service Bus — connection string pro lokální vývoj

```bash
# Získání connection stringu pro Service Bus namespace
SERVICEBUS_CONNECTION_STRING=$(az servicebus namespace authorization-rule keys list \
  --resource-group "seiplog-rg" \
  --namespace-name "seiplogbus" \
  --name "monitor-rule" \
  --query primaryConnectionString \
  --output tsv)

export SERVICEBUS_CONNECTION_STRING
```

*Zdroj:* `azure-log-analyzer/run-api.sh`

---

## 9. Output formáty — `--output` / `-o`

```bash
az account show                          # JSON (default)
az account show -o tsv                   # Tab-separated (pro scripting)
az account show -o table                 # Čitelná tabulka
az account show -o yaml                  # YAML

# JMESPath query pro filtrování
az account show --query "{id:id, name:name}"
az account list --query "[].{name:name, id:id}" -o table
az vm list --query "[?location=='eastus'].name" -o tsv
```

---

## 10. Tipy pro produkční skripty

```bash
#!/usr/bin/env bash
set -euo pipefail   # exit on error, unset vars, pipe failures

# Idempotentní operace — nevadí spustit vícekrát
az group create --name "$RG" --location "$LOCATION" --output none
az ad sp create --id "$APP_ID" --output none 2>/dev/null || true

# Tichý výstup v CI (--output none / --only-show-errors)
az storage container create \
  --name "tfstate" \
  --account-name "$SA" \
  --auth-mode login \
  --output none \
  --only-show-errors

# Čtení hodnot do proměnných
APP_ID=$(az ad app list --display-name "$APP_NAME" --query '[0].appId' -o tsv)
```

---

## Shrnutí — kdy použít CLI vs Terraform

| Situace | CLI | Terraform |
|---------|-----|-----------|
| Bootstrap (storage pro tfstate) | ✅ | nelze — chicken & egg |
| CI/CD federated credentials | ✅ | komplikované |
| Infrastruktura (VNet, AKS, DB) | pro debug | ✅ |
| Opakované provisioning | nebezpečné | ✅ idempotentní |
| Ad-hoc dotazy na live prostředí | ✅ | ❌ |
