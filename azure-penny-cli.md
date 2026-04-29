# azure-penny — Azure CLI

Projekt: serverless cost management dashboard — čte Cost Management exporty z Blob Storage, servuje přes FastAPI na Azure Container Apps.
Repo: `azure-penny` — `scripts/bootstrap-tfstate.sh`

---

## Co CLI dělá v tomto projektu

Bootstrap před Terraformem: vytvoří resource group, storage account pro tfstate a přiřadí RBAC roli.
Aplikační infrastruktura (Container Apps, ACR, Managed Identity) je pak čistý Terraform.

---

## 1. Vytvoření Resource Group

```bash
PREFIX="azpenny"
LOCATION="westeurope"
RG="${PREFIX}-rg"

az group create \
  --name "$RG" \
  --location "$LOCATION" \
  --output none

echo "Resource group: $RG"
```

---

## 2. Storage Account pro Terraform state

```bash
SA="${PREFIX}tfstate"

az storage account create \
  --name "$SA" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --allow-blob-public-access false \
  --output none
```

---

## 3. Blob Container pro tfstate

```bash
az storage container create \
  --name "tfstate" \
  --account-name "$SA" \
  --auth-mode login \
  --output none
```

`--auth-mode login` — AAD autentifikace, žádný storage account key.

---

## 4. Ověření storage accountu — čtení výstupu

```bash
# Zjištění resource ID pro scope RBAC role
SA_ID=$(az storage account show \
  --name "$SA" \
  --resource-group "$RG" \
  --query id \
  -o tsv)

echo "Storage Account ID: $SA_ID"
```

`--query id` — JMESPath filtr, vrátí jen resource ID (string).

---

## 5. RBAC — přiřazení role pro Terraform

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Terraform potřebuje Storage Blob Data Contributor pro přístup ke state
az role assignment create \
  --assignee-object-id "$(az ad signed-in-user show --query id -o tsv)" \
  --assignee-principal-type User \
  --role "Storage Blob Data Contributor" \
  --scope "$SA_ID" \
  --output none 2>/dev/null || true
```

Scope na konkrétní storage account — ne celou subscription.
`|| true` zajišťuje idempotentnost (role může už existovat).

---

## Celý bootstrap skript najednou

```bash
#!/usr/bin/env bash
set -euo pipefail

PREFIX="${PREFIX:-azpenny}"
LOCATION="${LOCATION:-westeurope}"
RG="${PREFIX}-rg"
SA="${PREFIX}tfstate"

echo "==> Creating resource group..."
az group create --name "$RG" --location "$LOCATION" --output none

echo "==> Creating storage account..."
az storage account create \
  --name "$SA" --resource-group "$RG" --location "$LOCATION" \
  --sku Standard_LRS --allow-blob-public-access false --output none

echo "==> Creating tfstate container..."
az storage container create \
  --name "tfstate" --account-name "$SA" --auth-mode login --output none

echo "==> Getting storage account ID..."
SA_ID=$(az storage account show --name "$SA" --resource-group "$RG" --query id -o tsv)

echo "==> Assigning Storage Blob Data Contributor role..."
az role assignment create \
  --assignee-object-id "$(az ad signed-in-user show --query id -o tsv)" \
  --assignee-principal-type User \
  --role "Storage Blob Data Contributor" \
  --scope "$SA_ID" \
  --output none 2>/dev/null || true

echo "Done. Run: terraform -chdir=terraform init"
```

---

## Návaznost: co Terraform vytvoří po bootstrapu

Po `terraform apply` vznikne:
- **Azure Container Apps** prostředí a aplikace (scale 0→1)
- **Azure Container Registry** (bez admin uživatele)
- **User Assigned Managed Identity** pro Container App
- **Blob container** pro Cost Management exporty
- **RBAC**: Managed Identity dostane `Storage Blob Data Reader` na storage account

Aplikace pak běží bez jakýchkoli secrets — čte Blob Storage přes Managed Identity.
