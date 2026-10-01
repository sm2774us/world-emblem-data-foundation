terraform {
  required_version = ">= 1.9"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
  }
  # backend "azurerm" {}   # configure per environment (state in a locked-down storage account)
}

provider "azurerm" {
  features {}
  storage_use_azuread = true
}

variable "tenant_id" { type = string }

module "landing_zone" {
  source    = "../../modules/landing_zone"
  name      = "wedf-prod"
  location  = "eastus2"
  tenant_id = var.tenant_id
  tags      = { project = "world-emblem-data-foundation", env = "prod", owner = "data-platform" }
}

output "storage_account" { value = module.landing_zone.storage_account }
