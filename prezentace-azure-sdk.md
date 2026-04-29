# Azure SDK pro Python — Prezentační podklady

> Zdroje: vlastní projekty az-spot-orchestrator, az-llm-aks, azure-penny

---

## 1. Úvod — architektura Azure SDK pro Python

Azure SDK se dělí na tři skupiny balíčků:

| Skupina | Balíček | Použití |
|---------|---------|---------|
| **Identity** | `azure-identity` | Autentifikace (credential chain) |
| **Data plane** | `azure-storage-blob`, `azure-cosmos`, `azure-servicebus` | Práce s daty |
| **Management plane** | `azure-mgmt-compute`, `azure-mgmt-network`, `azure-mgmt-storage` | Správa zdrojů |

Všechny sdílejí společný balíček `azure-core` (HTTP pipeline, retry, exceptions).

---

## 2. Autentifikace — DefaultAzureCredential

`DefaultAzureCredential` zkouší credential chain v pořadí:
1. Environment variables (`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`)
2. Workload Identity (Kubernetes pod s OIDC tokenem)
3. Managed Identity (VM, Container App, AKS node)
4. Azure CLI (`az login`)
5. Azure Developer CLI, Visual Studio Code, ...

**Výhoda:** stejný kód funguje lokálně i v produkci bez změn.

```python
from azure.identity import DefaultAzureCredential

# Lokálně používá az login, v AKS Workload Identity, na VM Managed Identity
credential = DefaultAzureCredential()
```

*Pro Managed Identity s konkrétním client_id:*
```python
# azure-penny/storage.py
credential = DefaultAzureCredential(
    managed_identity_client_id=AZURE_CLIENT_ID or None
)
```

---

## 3. Azure Blob Storage — základní použití

```python
# azure-penny/storage.py
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

_blob_client: BlobServiceClient | None = None

def get_blob_service_client() -> BlobServiceClient:
    """Lazy singleton — vytvoří klienta jen jednou."""
    global _blob_client
    if _blob_client is None:
        credential = DefaultAzureCredential()
        account_url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
        _blob_client = BlobServiceClient(
            account_url=account_url,
            credential=credential
        )
    return _blob_client
```

**Stažení blob dat:**
```python
client = get_blob_service_client()
blob = client.get_blob_client(container="exports", blob="cost-2024-01.parquet")
data = blob.download_blob().readall()
df = pd.read_parquet(io.BytesIO(data))
```

---

## 4. Azure Blob Storage — async klient a SAS URL

Projekty s async FastAPI používají `azure.storage.blob.aio`:

```python
# az-spot-orchestrator/services/model_cache.py
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob import BlobSasPermissions, UserDelegationKey, generate_blob_sas
from azure.storage.blob.aio import BlobServiceClient

async def get_best_source(model_identifier: str, vm_region: str) -> dict:
    account_url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"

    async with DefaultAzureCredential() as credential:
        async with BlobServiceClient(account_url=account_url, credential=credential) as client:
            bc = client.get_blob_client(
                container="model-cache",
                blob=f"{vm_region}/{model_identifier}.tar.lz4",
            )
            try:
                await bc.get_blob_properties()   # ověření existence
                url = await _generate_sas_url(blob_name, "read")
                return {"source": "blob", "download_url": url}
            except ResourceNotFoundError:
                return {"source": "ollama"}
```

**Generování SAS URL bez storage klíče (user-delegation key):**
```python
async def _generate_sas_url(blob_name: str, permission: str) -> str:
    # User-delegation key — žádný storage account key neprochází kódem
    delegation_key = await client.get_user_delegation_key(
        key_start_time=datetime.now(UTC) - timedelta(minutes=5),
        key_expiry_time=datetime.now(UTC) + timedelta(hours=1),
    )
    sas = generate_blob_sas(
        account_name=STORAGE_ACCOUNT_NAME,
        container_name="model-cache",
        blob_name=blob_name,
        user_delegation_key=delegation_key,
        permission=BlobSasPermissions(read=(permission == "read")),
        expiry=datetime.now(UTC) + timedelta(hours=2),
    )
    return f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net/model-cache/{blob_name}?{sas}"
```

---

## 5. Azure Cosmos DB — synchronní klient

```python
# az-llm-aks/api/routes/models.py
from azure.cosmos import CosmosClient, exceptions
from azure.identity import DefaultAzureCredential
import os

_cosmos_client: CosmosClient | None = None

def get_container():
    global _cosmos_client
    if _cosmos_client is None:
        key = os.environ.get("COSMOS_KEY")
        # Pokud není klíč, použij DefaultAzureCredential (Workload Identity)
        credential = key if key else DefaultAzureCredential()
        _cosmos_client = CosmosClient(
            url=os.environ["COSMOS_ENDPOINT"],
            credential=credential,
        )
    db = _cosmos_client.get_database_client("az-llm-aks")
    return db.get_container_client("models")

# CRUD operace
def list_models():
    container = get_container()
    return list(container.query_items(
        "SELECT * FROM c",
        enable_cross_partition_query=True
    ))

def get_model(model_id: str):
    try:
        return container.read_item(item=model_id, partition_key=model_id)
    except exceptions.CosmosResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Model not found")

def create_model(model: dict):
    container.create_item(body=model)

def update_model(model_id: str, updates: dict):
    item = container.read_item(item=model_id, partition_key=model_id)
    item.update(updates)
    container.replace_item(item=model_id, body=item)
```

---

## 6. Azure Cosmos DB — async klient s lazy singleton

```python
# az-spot-orchestrator/db/cosmos.py
from azure.cosmos import PartitionKey
from azure.cosmos.aio import ContainerProxy, CosmosClient
from azure.identity.aio import DefaultAzureCredential

_client: CosmosClient | None = None

def _get_client() -> CosmosClient:
    global _client
    if _client is None:
        # Fallback: pokud není klíč, použij AAD (Workload Identity / Managed Identity)
        credential = settings.cosmos_key if settings.cosmos_key else DefaultAzureCredential()
        _client = CosmosClient(url=settings.cosmos_endpoint, credential=credential)
    return _client

def get_models_container() -> ContainerProxy:
    return _get_client().get_database_client("az-spot-orchestrator").get_container_client("llm-models")

# Dotaz s parametry (SQL-like syntax)
async def find_available_in_region(model_identifier: str) -> list:
    container = get_models_container()
    results = []
    async for item in container.query_items(
        query="SELECT * FROM c WHERE c.model_identifier = @model_id AND c.status = @status",
        parameters=[
            {"name": "@model_id", "value": model_identifier},
            {"name": "@status",   "value": "available"},
        ],
    ):
        results.append(item)
    return results
```

**Startup check — ověření konektivity:**
```python
async def setup_cosmos() -> None:
    try:
        client = _get_client()
        async for _ in client.list_databases():
            break
        # Vytvoření kontejnerů pokud neexistují
        db = client.get_database_client("az-spot-orchestrator")
        await db.create_container_if_not_exists(
            id="system-messages",
            partition_key=PartitionKey(path="/id"),
        )
        logger.info("Cosmos DB ready")
    except Exception as exc:
        logger.warning("Cosmos DB check failed: %s", exc)
```

---

## 7. Management SDK — Compute a Network

Management SDK slouží ke **správě samotných Azure zdrojů** (VMs, VNets, NSG...).

```python
# az-spot-orchestrator/services/azure_client.py
from contextlib import asynccontextmanager
from azure.identity.aio import DefaultAzureCredential
from azure.mgmt.compute.aio import ComputeManagementClient
from azure.mgmt.network.aio import NetworkManagementClient

@asynccontextmanager
async def compute_client():
    async with DefaultAzureCredential() as credential:
        async with ComputeManagementClient(
            credential,
            subscription_id,
            connection_timeout=10,
            read_timeout=30,
        ) as client:
            yield client

@asynccontextmanager
async def network_client():
    async with DefaultAzureCredential() as credential:
        async with NetworkManagementClient(credential, subscription_id) as client:
            yield client
```

**Použití — kontrola dostupnosti VM SKU v regionech:**
```python
# az-spot-orchestrator/temporal/activities/azure.py
async def check_sku_availability(vm_size: str, regions: list[str]) -> list[str]:
    restricted: set[str] = set()

    async with compute_client() as comp:
        skus = comp.resource_skus.list(filter=f"name eq '{vm_size}'")
        async for sku in skus:
            for restriction in sku.restrictions or []:
                reason = getattr(restriction, "reason_code", None)
                if reason in ("NotAvailableForSubscription", "QuotaId"):
                    restricted.add(sku.locations[0])

    return [r for r in regions if r not in restricted]
```

**Použití — quota vCPU přes Management SDK:**
```python
# az-llm-aks/api/routes/inventory.py
from azure.mgmt.compute import ComputeManagementClient

def get_spot_vcpu_limit(region: str) -> int | None:
    credential = DefaultAzureCredential()
    client = ComputeManagementClient(credential, SUBSCRIPTION_ID)
    for usage in client.usage.list(location=region):
        if (getattr(usage.name, "value", None) or "").lower() == "lowprioritycores":
            return usage.limit
    return None
```

---

## 8. Management SDK — Resource a Storage Management

```python
# azure-penny/live_resources.py
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient

credential = DefaultAzureCredential()

# Výpis všech resource groups
resource_client = ResourceManagementClient(credential, SUBSCRIPTION_ID)
for rg in resource_client.resource_groups.list():
    print(rg.name, rg.location)

# Výpis všech VM SKU (pro pricing)
compute_client = ComputeManagementClient(credential, SUBSCRIPTION_ID)
for sku in compute_client.resource_skus.list(filter="location eq 'eastus'"):
    print(sku.name, sku.resource_type)

# Výpis storage účtů v resource group
storage_client = StorageManagementClient(credential, SUBSCRIPTION_ID)
for sa in storage_client.storage_accounts.list_by_resource_group("my-rg"):
    print(sa.name, sa.primary_location)
```

---

## 9. Zpracování výjimek — azure-core

Všechny Azure SDK balíčky sdílejí výjimky z `azure.core.exceptions`:

```python
from azure.core.exceptions import (
    ResourceNotFoundError,      # HTTP 404
    ResourceExistsError,        # HTTP 409 Conflict
    HttpResponseError,          # Obecná HTTP chyba (obsahuje status_code)
    AzureError,                 # Základní třída pro všechny Azure výjimky
)

# Cosmos DB
from azure.cosmos import exceptions as cosmos_exc

try:
    item = container.read_item(item=model_id, partition_key=model_id)
except cosmos_exc.CosmosResourceNotFoundError:
    raise HTTPException(status_code=404)

# Blob Storage
try:
    await blob_client.get_blob_properties()
except ResourceNotFoundError:
    return {"source": "ollama"}   # fallback

# Obecné — idempotentní operace
try:
    await db.create_container_if_not_exists(id="messages", partition_key=...)
except ResourceExistsError:
    pass  # kontejner už existuje — ok
```

---

## 10. Vzory z praxe

### Lazy singleton
```python
_client: SomeClient | None = None

def get_client() -> SomeClient:
    global _client
    if _client is None:
        _client = SomeClient(url=..., credential=DefaultAzureCredential())
    return _client
```

### Async context manager pro každý request
```python
@asynccontextmanager
async def compute_client():
    async with DefaultAzureCredential() as cred:
        async with ComputeManagementClient(cred, subscription_id) as client:
            yield client

# Použití
async with compute_client() as comp:
    result = await comp.virtual_machines.get(rg, vm_name)
```

### Credential fallback (klíč nebo AAD)
```python
key = os.environ.get("COSMOS_KEY")
credential = key if key else DefaultAzureCredential()
client = CosmosClient(url=endpoint, credential=credential)
```

---

## Shrnutí — Data plane vs Management plane

| | Data plane | Management plane |
|--|-----------|-----------------|
| **Příklady** | Blob, Cosmos, Service Bus | Compute, Network, Storage mgmt |
| **Balíčky** | `azure-storage-blob`, `azure-cosmos` | `azure-mgmt-compute`, `azure-mgmt-network` |
| **K čemu** | Čtení/zápis dat | Vytváření/mazání zdrojů |
| **Auth endpoint** | `*.blob.core.windows.net` | `management.azure.com` |
| **Typická role** | Storage Blob Data Contributor | Contributor / Owner |

**Doporučení pro produkci:**
- Nikdy neposílat klíče do kódu — vždy `DefaultAzureCredential`
- V Kubernetes použít Workload Identity (OIDC) + pod annotations
- Na VM/Container App použít Managed Identity (zero secrets)
- Async klient (`*.aio`) pro FastAPI / asyncio aplikace
