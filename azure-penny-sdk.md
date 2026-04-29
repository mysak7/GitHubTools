# azure-penny — Azure SDK

Projekt: serverless cost management dashboard — čte Cost Management exporty z Blob Storage, servuje přes FastAPI na Azure Container Apps se scale-to-zero.
Repo: `azure-penny` — `storage.py`, `live_resources.py`

---

## Použité SDK balíčky

```
azure-identity          # DefaultAzureCredential
azure-storage-blob      # BlobServiceClient
azure-mgmt-resource     # ResourceManagementClient
azure-mgmt-compute      # ComputeManagementClient
azure-mgmt-storage      # StorageManagementClient
```

---

## 1. Autentifikace — Managed Identity s client_id

```python
# storage.py
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

# AZURE_CLIENT_ID = User Assigned Managed Identity přiřazená Container Appu přes Terraform
credential = DefaultAzureCredential(
    managed_identity_client_id=AZURE_CLIENT_ID or None
)
account_url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
_blob_client = BlobServiceClient(account_url=account_url, credential=credential)
```

`managed_identity_client_id` — nutné u User Assigned Managed Identity (systémová MI client_id nepotřebuje).
Lokálně `DefaultAzureCredential` automaticky použije `az login`.

---

## 2. Blob Storage — lazy singleton klient

```python
# storage.py
_blob_client: BlobServiceClient | None = None

def get_blob_service_client() -> BlobServiceClient:
    global _blob_client
    if _blob_client is None:
        credential = DefaultAzureCredential(
            managed_identity_client_id=AZURE_CLIENT_ID or None
        )
        account_url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
        _blob_client = BlobServiceClient(account_url=account_url, credential=credential)
        log.info("BlobServiceClient initialised for account: %s", STORAGE_ACCOUNT_NAME)
    return _blob_client
```

Singleton — jeden klient pro celý životní cyklus Container App instance.

---

## 3. Čtení Parquet souboru z Blob do pandas DataFrame

```python
import io
import pandas as pd
from azure.storage.blob import BlobServiceClient

def load_parquet_from_blob(container: str, blob_name: str) -> pd.DataFrame:
    client = get_blob_service_client()
    blob = client.get_blob_client(container=container, blob=blob_name)
    data = blob.download_blob().readall()          # bytes
    return pd.read_parquet(io.BytesIO(data))       # DataFrame
```

`io.BytesIO` — obalí bytes do file-like objektu, který pandas umí číst.

---

## 4. Listing blobů — discovery Cost Management exportů

```python
def list_cost_exports(container: str, prefix: str = "") -> list[str]:
    client = get_blob_service_client()
    ctr = client.get_container_client(container)
    return [
        blob.name
        for blob in ctr.list_blobs(name_starts_with=prefix)
        if blob.name.endswith(".parquet") or blob.name.endswith(".csv")
    ]
```

Azure Cost Management exportuje do struktury: `{scope}/{date}/{filename}.parquet`.

---

## 5. Management SDK — inventář ARM zdrojů

```python
# live_resources.py
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient

_resource_mgmt_client: ResourceManagementClient | None = None
_compute_mgmt_client: ComputeManagementClient | None = None

def _get_resource_mgmt_client() -> ResourceManagementClient:
    global _resource_mgmt_client
    if _resource_mgmt_client is None:
        credential = DefaultAzureCredential(
            managed_identity_client_id=AZURE_CLIENT_ID or None
        )
        _resource_mgmt_client = ResourceManagementClient(credential, AZURE_SUBSCRIPTION_ID)
    return _resource_mgmt_client

def _get_compute_mgmt_client() -> ComputeManagementClient:
    global _compute_mgmt_client
    if _compute_mgmt_client is None:
        credential = DefaultAzureCredential(
            managed_identity_client_id=AZURE_CLIENT_ID or None
        )
        _compute_mgmt_client = ComputeManagementClient(credential, AZURE_SUBSCRIPTION_ID)
    return _compute_mgmt_client
```

---

## 6. Výpis všech ARM zdrojů v subscription

```python
# live_resources.py — _fetch_resource_inventory()
def _fetch_resource_inventory() -> list[dict]:
    rc = _get_resource_mgmt_client()
    all_res = list(rc.resources.list())
    log.info("ARM inventory: %d resources found", len(all_res))
    return [
        {
            "id": r.id,
            "name": r.name,
            "type": r.type,
            "location": r.location,
            "resource_group": r.id.split("/resourceGroups/")[1].split("/")[0],
        }
        for r in all_res
    ]
```

`rc.resources.list()` — stránkovaný iterátor přes všechny zdroje v subscription (cross-RG).

---

## 7. VM power state přes Compute Management

```python
# live_resources.py
def get_vm_power_state(rg: str, vm_name: str) -> str:
    cc = _get_compute_mgmt_client()
    # expand="instanceView" je nutné pro power state — základní GET ho nevrátí
    inst = cc.virtual_machines.get(rg, vm_name, expand="instanceView")
    statuses = inst.instance_view.statuses if inst.instance_view else []
    power = next(
        (s.display_status for s in statuses if s.code.startswith("PowerState/")),
        "Unknown",
    )
    return power  # "VM running", "VM deallocated", "VM stopped", ...
```

`expand="instanceView"` — bez tohoto parametru API nevrátí `PowerState`.

---

## 8. Azure Retail Prices API — ceny bez SDK

```python
# live_resources.py — pro ceny VM Spot/On-demand
import urllib.request, urllib.parse, json

def fetch_spot_price(vm_size: str, region: str) -> float | None:
    filter_str = (
        f"armRegionName eq '{region}'"
        f" and armSkuName eq '{vm_size}'"
        " and priceType eq 'Consumption'"
        " and contains(skuName,'Spot')"
    )
    url = (
        "https://prices.azure.com/api/retail/prices?api-version=2023-01-01-preview&$filter="
        + urllib.parse.quote(filter_str)
    )
    with urllib.request.urlopen(url, timeout=8) as resp:
        data = json.loads(resp.read())
    items = data.get("Items") or []
    return float(items[0]["retailPrice"]) if items else None
```

Azure Retail Prices API je veřejné, bez autentifikace — `urllib` stačí, SDK není potřeba.

---

## Architektura autentifikace v produkci

```
Container App
  └── User Assigned Managed Identity (UAMI)
        └── Role: Storage Blob Data Reader  →  Blob Storage (Cost Management exporty)
        └── Role: Reader                    →  Subscription (ARM resource inventory)

Terraform přiřadí UAMI k Container Appu:
  identity { type = "UserAssigned", identity_ids = [azurerm_user_assigned_identity.app.id] }

Aplikace:
  DefaultAzureCredential(managed_identity_client_id=UAMI_CLIENT_ID)
  → žádné secrets, žádné connection stringy v kódu ani v env vars
```
