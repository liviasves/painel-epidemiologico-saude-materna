terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aiven = {
      source  = "aiven/aiven"
      version = ">= 4.0.0, < 5.0.0"
    }
  }
}

provider "aiven" {
  api_token = var.aiven_api_token
}

resource "aiven_pg" "banco" {
  project                = var.aiven_project
  service_name           = var.service_name
  plan                   = var.plan
  cloud_name             = var.cloud_name
  termination_protection = false
}