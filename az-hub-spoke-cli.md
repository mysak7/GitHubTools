# az-hub-spoke — Azure CLI

Projekt: enterprise Hub-and-Spoke síť v Azure (Terraform + CLI bootstrap)
Repo: `az-hub-spoke` — `bootstrap/init-state.sh`

---

## Co CLI dělá v tomto projektu

Před prvním `terraform init` je potřeba vytvořit storage account pro remote state.
Terraform nemůže vytvořit vlastní backend — **chicken & egg problém**. CLI to řeší jedním skriptem.

---

## 1. Login check

```bash
# Ověření přihlášení před spuštěním skriptu
if ! az account show &>/dev/null; then
  echo "Not logged in — run: az login"
  exit 1
fi

# Čtení subscription ID a object ID přihlášeného uživatele
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)
```

`az ad signed-in-user show` — vrátí object ID aktuálně přihlášeného uživatele (ne service principal).
Použití: přiřazení RBAC role bez nutnosti znát ID předem.

---

## 2. Resource Group s tagy

```bash
PREFIX="hubspoke"
ENVIRONMENT="dev"
LOCATION="westeurope"
LOCATION_SHORT="weu"
RG_NAME="rg-${PREFIX}-tfstate-${ENVIRONMENT}-${LOCATION_SHORT}"

az group create \
  --name "$RG_NAME" \
  --location "$LOCATION" \
  --tags \
      Project="$PREFIX" \
      Environment="$ENVIRONMENT" \
      ManagedBy="az-cli" \
      Purpose="terraform-state" \
  --output none
```

`--tags` — klíč=hodnota páry, best practice pro cost management a přehled zdrojů.

---

## 3. Storage Account s bezpečnostními nastaveními

```bash
# Náhodný suffix — zajišťuje unikátnost názvu (storage account musí být globálně unikátní)
SA_NAME="st${PREFIX}tfst$(openssl rand -hex 4)"

az storage account create \
  --name "$SA_NAME" \
  --resource-group "$RG_NAME" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --min-tls-version TLS1_2 \
  --allow-blob-public-access false \
  --tags Project="$PREFIX" Environment="$ENVIRONMENT" ManagedBy="az-cli" Purpose="terraform-state" \
  --output none
```

`--allow-blob-public-access false` + `--min-tls-version TLS1_2` — produkční security baseline.

---

## 4. Blob versioning a soft delete

```bash
az storage account blob-service-properties update \
  --account-name "$SA_NAME" \
  --resource-group "$RG_NAME" \
  --enable-versioning true \
  --enable-delete-retention true \
  --delete-retention-days 30 \
  --output none
```

Pro terraform state je toto kritické — versioning umožňuje rollback state souboru,
soft delete chrání před náhodným smazáním.

---

## 5. Blob Container

```bash
az storage container create \
  --name "tfstate" \
  --account-name "$SA_NAME" \
  --auth-mode login \
  --output none
```

`--auth-mode login` — používá AAD token přihlášeného uživatele místo storage account key.

---

## 6. RBAC — přiřazení role přihlášenému uživateli

```bash
# Získání resource ID storage accountu
SA_ID=$(az storage account show \
  --name "$SA_NAME" \
  --resource-group "$RG_NAME" \
  --query id -o tsv)

# Role scoped na konkrétní storage account (ne celou subscription)
az role assignment create \
  --assignee-object-id "$(az ad signed-in-user show --query id -o tsv)" \
  --assignee-principal-type User \
  --role "Storage Blob Data Contributor" \
  --scope "$SA_ID" \
  --output none
```

Scope na konkrétní resource (ne `--scope /subscriptions/$ID`) = princip least privilege.

---

## 7. Výstup — generování backend.tf

```bash
cat <<EOF
terraform {
  backend "azurerm" {
    resource_group_name  = "$RG_NAME"
    storage_account_name = "$SA_NAME"
    container_name       = "tfstate"
    key                  = "dev.terraform.tfstate"
    use_azuread_auth     = true
  }
}
EOF
```

`use_azuread_auth = true` — Terraform se autentifikuje přes AAD (az login), žádný storage key v kódu.

---

## Vzor: idempotentní bootstrap skript

```bash
#!/usr/bin/env bash
set -euo pipefail   # exit on error, unbound vars, pipe failures

# Login check před jakoukoli prací
if ! az account show &>/dev/null; then exit 1; fi

# Všechny az příkazy s --output none (tichý výstup pro CI)
az group create ... --output none
az storage account create ... --output none
az storage container create ... --output none
az role assignment create ... --output none 2>/dev/null || true
```

`|| true` na role assignment — příkaz selže pokud role už existuje; idempotentnost zajistí pokračování.
