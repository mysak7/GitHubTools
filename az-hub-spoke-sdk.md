# az-hub-spoke — Azure SDK

Projekt: enterprise Hub-and-Spoke síť v Azure (Terraform + CLI bootstrap)
Repo: `az-hub-spoke`

---

## Python SDK v tomto projektu

Projekt `az-hub-spoke` **nepoužívá Python Azure SDK**. Celá infrastruktura je deklarativní Terraform (`azurerm` provider) a jednorázový bootstrap přes Azure CLI.

---

## Proč ne SDK?

| Vrstva | Nástroj | Důvod |
|--------|---------|-------|
| Síťová infrastruktura (VNet, Firewall, Bastion) | Terraform `azurerm` | Deklarativní, idempotentní, state management |
| Bootstrap (storage pro tfstate) | Azure CLI | Jednorázový skript, žádná aplikace |
| Runtime aplikace | — | Projekt nemá backend aplikaci |

---

## Co Terraform `azurerm` provider dělá místo SDK

```hcl
# modules/hub_network/main.tf
resource "azurerm_virtual_network" "hub" {
  name                = "vnet-hub-${var.prefix}-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = [var.hub_address_space]
  tags                = local.tags
}

resource "azurerm_subnet" "firewall" {
  name                 = "AzureFirewallSubnet"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.hub.name
  address_prefixes     = [var.firewall_subnet_prefix]
}
```

```hcl
# modules/firewall/main.tf
resource "azurerm_firewall" "main" {
  name                = "afw-${var.prefix}-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku_name            = "AZFW_VNet"
  sku_tier            = "Standard"
  firewall_policy_id  = azurerm_firewall_policy.main.id
  tags                = var.tags

  ip_configuration {
    name                 = "ipconfig"
    subnet_id            = var.firewall_subnet_id
    public_ip_address_id = azurerm_public_ip.firewall.id
  }
}
```

```hcl
# modules/peering/main.tf — obousměrný VNet Peering
resource "azurerm_virtual_network_peering" "hub_to_spoke" {
  name                      = "peer-hub-to-${var.spoke_name}"
  resource_group_name       = var.hub_resource_group_name
  virtual_network_name      = var.hub_vnet_name
  remote_virtual_network_id = var.spoke_vnet_id
  allow_forwarded_traffic   = true
  allow_gateway_transit     = true
}

resource "azurerm_virtual_network_peering" "spoke_to_hub" {
  name                      = "peer-${var.spoke_name}-to-hub"
  resource_group_name       = var.spoke_resource_group_name
  virtual_network_name      = var.spoke_vnet_name
  remote_virtual_network_id = var.hub_vnet_id
  allow_forwarded_traffic   = true
  use_remote_gateways       = false
}
```

```hcl
# modules/private_dns/main.tf
resource "azurerm_private_dns_zone" "blob" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = var.resource_group_name
}

resource "azurerm_private_dns_zone_virtual_network_link" "hub" {
  name                  = "link-hub"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.blob.name
  virtual_network_id    = var.hub_vnet_id
  registration_enabled  = false
}
```

---

## Kdy použít SDK vs Terraform

Pokud by projekt měl runtime komponentu (API, worker), použil by SDK takto:

```python
# Hypotetická aplikace nasazená do tohoto Hub-Spoke prostředí
from azure.identity import DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient

credential = DefaultAzureCredential()   # Managed Identity na VM v spoke subnetu
client = NetworkManagementClient(credential, subscription_id)

# Výpis VNet peeringu
for peering in client.virtual_network_peerings.list(rg_name, vnet_name):
    print(peering.name, peering.peering_state)
```

Pro infrastrukturní projekty bez runtime aplikace je **Terraform + CLI dostačující** a vhodnější než SDK.
