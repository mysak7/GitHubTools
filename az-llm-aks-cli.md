# az-llm-aks — Azure CLI

Projekt: LLM inference na AKS Spot uzlech — Ollama na Karpenter-provisioned CPU nodech, sdílená BlobFuse2 cache modelů.
Repo: `az-llm-aks` — `CLAUDE.md`, `docs/security.md`, `.github/workflows/deploy.yml`

---

## Co CLI dělá v tomto projektu

CLI se používá ve dvou situacích:
1. **Lokální setup** — připojení kubectl na AKS cluster
2. **CI/CD (GitHub Actions)** — synchronizace Cosmos DB klíče do Kubernetes secretu

---

## 1. Připojení kubectl na AKS cluster

```bash
# Stažení credentials a přidání kontextu do ~/.kube/config
az aks get-credentials \
  --resource-group az-llm-aks-rg \
  --name az-llm-aks \
  --overwrite-existing

# Ověření připojení
kubectl get nodes
kubectl get svc control-plane -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

`--overwrite-existing` — přepíše existující kontext stejného jména (bezpečné pro opakované spuštění).

Po připojení:
```bash
# Nasazení control-plane manifestů
kubectl apply -f k8s/control-plane/
```

---

## 2. Čtení Cosmos DB klíče (CI/CD)

```bash
# .github/workflows/deploy.yml
COSMOS_KEY=$(az cosmosdb keys list \
  --name azllmakscosmos \
  --resource-group az-llm-aks-rg \
  --query primaryMasterKey \
  -o tsv)
```

`--query primaryMasterKey` — JMESPath filtr, vrátí jen klíč bez ostatních polí.

---

## 3. Synchronizace Cosmos klíče do Kubernetes secretu

```bash
# Patch existujícího K8s secretu s novým Cosmos klíčem po každém deployi
kubectl patch secret control-plane-secrets \
  --type=json \
  -p='[{
    "op":    "add",
    "path":  "/data/cosmos-key",
    "value": "'"$(echo -n "$COSMOS_KEY" | base64 -w0)"'"
  }]'
```

Kombinace CLI (`az cosmosdb keys list`) + kubectl patch — aktualizuje secret bez redeploye podu.
`base64 -w0` — K8s secrets jsou base64-encoded, `-w0` vypne zalamování řádků.

---

## 4. Typický workflow nasazení

```bash
# 1. Přihlášení (lokálně nebo přes GitHub Actions OIDC)
az login
# nebo v CI: azure/login@v2 action

# 2. Připojení na cluster
az aks get-credentials \
  --resource-group az-llm-aks-rg \
  --name az-llm-aks \
  --overwrite-existing

# 3. Build a push image do ACR
az acr build \
  --registry azllmaksacr \
  --image control-plane:${{ github.sha }} \
  .

# 4. Aktualizace Cosmos klíče v K8s secretu
COSMOS_KEY=$(az cosmosdb keys list \
  --name azllmakscosmos \
  --resource-group az-llm-aks-rg \
  --query primaryMasterKey -o tsv)

kubectl patch secret control-plane-secrets --type=json \
  -p='[{"op":"add","path":"/data/cosmos-key","value":"'"$(echo -n "$COSMOS_KEY" | base64 -w0)"'"}]'

# 5. Rolling restart control-plane
kubectl rollout restart deployment/control-plane
kubectl rollout status deployment/control-plane --timeout=120s
```

---

## 5. Přehled Azure zdrojů v projektu

| Zdroj | Název | CLI příkaz pro check |
|-------|-------|---------------------|
| AKS cluster | `az-llm-aks` | `az aks show -g az-llm-aks-rg -n az-llm-aks` |
| Cosmos DB | `azllmakscosmos` | `az cosmosdb show -g az-llm-aks-rg -n azllmakscosmos` |
| ACR | `azllmaksacr` | `az acr show -g az-llm-aks-rg -n azllmaksacr` |
| Blob Storage | BlobFuse2 mount | `az storage account list -g az-llm-aks-rg -o table` |

---

## Poznámka: Workload Identity vs. statické klíče

Projekt používá **dvě strategie** pro autentifikaci:

- **Blob Storage** — Azure Workload Identity (OIDC, bez klíče): Terraform nastaví federated credential, pod má ServiceAccount annotation → `DefaultAzureCredential` funguje automaticky
- **Cosmos DB** — klíč synchronizovaný do K8s secretu přes CLI (jednodušší setup pro první verzi)

```bash
# Ověření Workload Identity na clusteru
az aks show \
  --resource-group az-llm-aks-rg \
  --name az-llm-aks \
  --query "oidcIssuerProfile.issuerUrl" \
  -o tsv
```
