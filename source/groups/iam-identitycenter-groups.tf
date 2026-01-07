terraform {
  required_providers {
    aws = {}
  }
  backend "s3" {
  }
}

locals {
  groups = jsondecode(file("${path.module}/groups.json"))
}

data "aws_ssoadmin_instances" "this" {}

resource "aws_identitystore_group" "this" {
  for_each          = { for g in local.groups : g.DisplayName => g }
  display_name      = each.value.DisplayName
  description       = each.value.Description
  identity_store_id = data.aws_ssoadmin_instances.this.identity_store_ids[0]
}
