# az-llm-aks — Azure SDK

Projekt: LLM inference na AKS Spot uzlech — Ollama na Karpenter-provisioned CPU nodech, sdílená BlobFuse2 cache modelů.
Repo: `az-llm-aks` — `api/routes/cache.py`, `api/routes/models.py`, `api/routes/inventory.py`

---

## Použité SDK balíčky

```
azure-identity          # DefaultAzureCredential (Workload Identity na AKS)
azure-storage-blob      # BlobServiceClient — sdílená cache modelů
azure-cosmos            # CosmosClient — registr LLM modelů
azure-mgmt-compute      # ComputeManagementClient — Spot VM quota, SKU data
```

---

## 1. Blob Storage — sdílená cache Ollama modelů

```python
# api/routes/cache.py
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import os

_blob_svc: BlobServiceClient | None = None

def _container():
    global _blob_svc
    if _blob_svc is None:
        account = os.environ["BLOB_STORAGE_ACCOUNT"]
        _blob_svc = BlobServiceClient(
            account_url=f"https://{account}.blob.core.windows.net",
            credential=DefaultAzureCredential(),   # Workload Identity na AKS podu
        )
    return _blob_svc.get_container_client(
        os.environ.get("BLOB_CONTAINER_NAME", "ollama-models")
    )
```

Na AKS s Workload Identity: `DefaultAzureCredential` automaticky použije OIDC token podu
(žádný secret, žádný klíč — čistá federovaná identita).

---

## 2. Listing blobů — výpis stažených modelů

```python
# api/routes/cache.py — GET /cache/
@router.get("/")
async def list_cache():
    ctr = _container()
    models = []

    # Manifest soubory = seznam stažených modelů
    prefix = "manifests/registry.ollama.ai/library/"
    for blob in ctr.list_blobs(name_starts_with=prefix):
        rel = blob.name[len(prefix):]
        parts = rel.split("/")
        if len(parts) == 2:
            models.append({
                "model": parts[0],
                "tag":   parts[1],
                "manifest_path": blob.name,
                "last_modified": blob.last_modified.isoformat(),
            })

    # Celková velikost blob vrstev
    blobs_total = sum(
        blob.size or 0
        for blob in ctr.list_blobs(name_starts_with="blobs/")
    )
    return {"models": models, "blobs_total_bytes": blobs_total}
```

Ollama ukládá modely jako OCI artefakty: `manifests/{registry}/{model}/{tag}` + `blobs/{digest}`.

---

## 3. Smazání modelu z cache (manifest + bloby)

```python
# api/routes/cache.py — DELETE /cache/models/{model}/{tag}
@router.delete("/models/{model}/{tag}", status_code=204)
async def delete_cached_model(model: str, tag: str):
    ctr = _container()
    manifest_path = f"manifests/registry.ollama.ai/library/{model}/{tag}"

    # Přečti manifest — obsahuje seznam digestů (config + layers)
    bc = ctr.get_blob_client(manifest_path)
    raw = bc.download_blob().readall()
    manifest = json.loads(raw)

    digests: set[str] = set()
    if "config" in manifest:
        digests.add(manifest["config"]["digest"].replace(":", "-"))
    for layer in manifest.get("layers", []):
        digests.add(layer["digest"].replace(":", "-"))

    bc.delete_blob()   # smaž manifest

    for digest in digests:
        try:
            ctr.get_blob_client(f"blobs/{digest}").delete_blob()
        except Exception:
            pass        # blob mohl být sdílený s jiným modelem
```

---

## 4. Spuštění K8s Job pro stažení modelu do cache

```python
# api/routes/cache.py — POST /cache/pull
from kubernetes import client, config

def _k8s_batch() -> client.BatchV1Api:
    try:
        config.load_incluster_config()     # uvnitř AKS podu
    except config.ConfigException:
        config.load_kube_config()          # lokální kubectl kontext
    return client.BatchV1Api()

@router.post("/pull", status_code=202)
async def pull_model_to_cache(model: str, tag: str = "latest"):
    job_name = f"cache-pull-{model}-{tag}-{int(time.time()) % 100000}"

    job = {
        "apiVersion": "batch/v1", "kind": "Job",
        "metadata": {"name": job_name, "namespace": "default"},
        "spec": {
            "ttlSecondsAfterFinished": 7200,
            "backoffLimit": 0,
            "template": {
                "spec": {
                    "restartPolicy": "Never",
                    "tolerations": [
                        # Tolerace pro Karpenter Spot uzly
                        {"key": "kubernetes.azure.com/scalesetpriority",
                         "operator": "Equal", "value": "spot", "effect": "NoSchedule"},
                    ],
                    "containers": [{
                        "name": "pull",
                        "image": "ollama/ollama:latest",
                        "command": ["/bin/sh", "-c",
                            f"ollama serve & until ollama list >/dev/null 2>&1; do sleep 1; done "
                            f"&& ollama pull {model}:{tag}"],
                        "volumeMounts": [{"name": "cache", "mountPath": "/cache"}],
                    }],
                    "volumes": [{"name": "cache",
                        "persistentVolumeClaim": {"claimName": "ollama-models-pvc-rw"}}],
                }
            },
        },
    }
    _k8s_batch().create_namespaced_job(namespace="default", body=job)
    return {"job": job_name, "model": f"{model}:{tag}"}
```

---

## 5. Cosmos DB — registr LLM modelů

```python
# api/routes/models.py
from azure.cosmos import CosmosClient, exceptions
from azure.identity import DefaultAzureCredential
import os

_cosmos_client: CosmosClient | None = None

def get_container():
    global _cosmos_client
    if _cosmos_client is None:
        key = os.environ.get("COSMOS_KEY")
        # Fallback na Workload Identity pokud klíč není nastaven
        credential = key if key else DefaultAzureCredential()
        _cosmos_client = CosmosClient(
            url=os.environ["COSMOS_ENDPOINT"],
            credential=credential,
        )
    return _cosmos_client \
        .get_database_client("az-llm-aks") \
        .get_container_client("models")
```

**CRUD operace:**
```python
# Výpis všech modelů
def list_models():
    container = get_container()
    return list(container.query_items(
        "SELECT * FROM c",
        enable_cross_partition_query=True
    ))

# Čtení jednoho modelu (point read — nejlevnější operace v Cosmos)
def get_model(model_id: str):
    try:
        return container.read_item(item=model_id, partition_key=model_id)
    except exceptions.CosmosResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Model not found")

# Vytvoření
def create_model(model: dict):
    container.create_item(body=model)

# Partial update
def patch_model(model_id: str, updates: dict):
    item = container.read_item(item=model_id, partition_key=model_id)
    item.update(updates)
    container.replace_item(item=model_id, body=item)
```

---

## 6. Compute Management — Spot VM quota a SKU data

```python
# api/routes/inventory.py
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID")
REGION = "westus2"

def get_spot_vcpu_limit() -> int | None:
    credential = DefaultAzureCredential()
    client = ComputeManagementClient(credential, SUBSCRIPTION_ID)

    for usage in client.usage.list(location=REGION):
        if (getattr(usage.name, "value", None) or "").lower() == "lowprioritycores":
            return usage.limit   # celkový limit Spot vCPU pro subscription v regionu
    return None

def get_available_vm_sizes() -> set[str]:
    credential = DefaultAzureCredential()
    client = ComputeManagementClient(credential, SUBSCRIPTION_ID)

    available: set[str] = set()
    for sku in client.resource_skus.list(filter=f"location eq '{REGION}'"):
        if sku.resource_type != "virtualMachines":
            continue
        restricted = any(
            r.reason_code in ("NotAvailableForSubscription", "QuotaId")
            for r in (sku.restrictions or [])
        )
        if not restricted:
            available.add(sku.name.lower())
    return available
```

`client.usage.list(location=)` — vrátí všechny quotas v regionu (vCPU, cores, rodiny SKU).
`client.resource_skus.list()` — stránkovaný iterátor přes všechna dostupná SKU v subscription.

---

## Workload Identity — jak funguje na AKS

```
Terraform vytvoří:
  azurerm_user_assigned_identity "control-plane"
  azurerm_federated_identity_credential → váže K8s ServiceAccount na UAMI
  azurerm_role_assignment → Storage Blob Data Contributor na Blob container

K8s manifest:
  serviceAccountName: control-plane-sa   (s annotation azure.workload.identity/client-id)

Pod:
  DefaultAzureCredential()
    → detekuje AZURE_CLIENT_ID z env
    → použije OIDC projected volume token
    → vymění za Azure AD access token
    → žádný secret, žádný klíč nikde
```
