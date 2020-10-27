terraform {
    required_version = ">= 0.13"

    required_providers {
        azurerm = {
            source  = "hashicorp/azurerm"
            version = "2.25.0"
        }
        external = {
            source  = "hashicorp/external"
            version = "1.2.0"
        }
    }
}

provider "azurerm" {
    version = "~> 2.0"
    features {}
}

provider "external" {
  version = "~> 1.2"
}

# Get info about currently activated subscription
data "azurerm_subscription" "current" {}

# Resource Group
resource "azurerm_resource_group" "rg" {
    name     = "Hub23"
    location = "westeurope"
}

# Container Registry
resource "azurerm_container_registry" "acr" {
    name                = "hub23registry"
    resource_group_name = azurerm_resource_group.rg.name
    location            = azurerm_resource_group.rg.location
    sku                 = "Standard"
}

# DNS Zone
resource "azurerm_dns_zone" "dns" {
    name                = "hub23.turing.ac.uk"
    resource_group_name = azurerm_resource_group.rg.name
}

# A Records in DNS Zone
resource "azurerm_dns_a_record" "binder_a_rec" {
    name                = "binder"
    zone_name           = azurerm_dns_zone.dns.name
    resource_group_name = azurerm_resource_group.rg.name
    ttl                 = 300
    target_resource_id  = "/subscriptions/ecaf0411-6ab5-4b62-8357-113228d6a259/resourceGroups/mc_hub23_hub23cluster_westeurope/providers/Microsoft.Network/publicIPAddresses/kubernetes-a5bd8ff872541442ca741cad811020fb"
}

resource "azurerm_dns_a_record" "hub_a_rec" {
    name                = "hub"
    zone_name           = azurerm_dns_zone.dns.name
    resource_group_name = azurerm_resource_group.rg.name
    ttl                 = 300
    target_resource_id  = "/subscriptions/ecaf0411-6ab5-4b62-8357-113228d6a259/resourceGroups/mc_hub23_hub23cluster_westeurope/providers/Microsoft.Network/publicIPAddresses/kubernetes-a5bd8ff872541442ca741cad811020fb"
}

# Key Vault
resource "azurerm_key_vault" "keyvault" {
    name                       = "hub23-keyvault"
    location                   = azurerm_resource_group.rg.location
    resource_group_name        = azurerm_resource_group.rg.name
    sku_name                   = "standard"
    tenant_id                  = data.azurerm_subscription.current.tenant_id
    soft_delete_enabled        = true
    soft_delete_retention_days = 90
}

# Virtual Network
resource "azurerm_virtual_network" "vnet" {
    name                = "hub23-vnet"
    location            = azurerm_resource_group.rg.location
    resource_group_name = azurerm_resource_group.rg.name
    address_space       = ["10.0.0.0/8"]
}

# Virtual Network Subnet
resource "azurerm_subnet" "subnet" {
    name                 = "hub23-subnet"
    resource_group_name  = azurerm_resource_group.rg.name
    virtual_network_name = azurerm_virtual_network.vnet.name
    address_prefixes     = ["10.240.0.0/16"]
}

# Extract secrets from the vault
data "external" "appId" {
    program = ["az", "keyvault", "secret", "show", "--vault-name", azurerm_key_vault.keyvault.name, "--name", "SP-appId", "--query", "{value: value}"]
}
output "appId" {
    description = "ID of the service principal used by the Kubernetes cluster"
    value       = data.external.appId.result.value
    sensitive   = true
}

data "external" "appKey" {
    program = ["az", "keyvault", "secret", "show", "--vault-name", azurerm_key_vault.keyvault.name, "--name", "SP-key", "--query", "{value: value}"]
}
output "appKey" {
    description = "Client key of the service principal used by the Kubernetes cluster"
    value       = data.external.appKey.result.value
    sensitive   = true
}

data "external" "sshKey" {
    program = ["az", "keyvault", "secret", "show", "--vault-name", azurerm_key_vault.keyvault.name, "--name", "ssh-key-Hub23cluster-public", "--query", "{value: value}"]
}
output "sshKey" {
    description = "Public ssh key used by the Kubernetes cluster"
    value       = data.external.sshKey.result.value
}
