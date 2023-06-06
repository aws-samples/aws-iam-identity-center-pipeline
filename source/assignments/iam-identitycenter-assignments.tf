# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


data "aws_region" "current" {}
data "aws_ssoadmin_instances" "sso" {}

terraform {
  required_providers {
    aws = {}
  }
  backend "s3" {
  }
}

locals {
  assignment_file = jsondecode(file("assignments.json"))
}

resource "aws_ssoadmin_account_assignment" "assignment" {
  for_each = {for t in local.assignment_file : t.Sid => t}
  instance_arn = tolist(data.aws_ssoadmin_instances.sso.arns)[0]
  permission_set_arn = "${each.value.PermissionSetName}"
  principal_id       = "${each.value.PrincipalId}"
  principal_type     = "${each.value.PrincipalType}"
  target_id          = "${each.value.Target}"
  target_type = "AWS_ACCOUNT"
}