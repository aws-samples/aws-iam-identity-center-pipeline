#!/usr/bin/env python3
import argparse
import json
import logging
import sys
import uuid
from collections import defaultdict
from pathlib import Path

import boto3
from botocore.config import Config

LOG = logging.getLogger("identity-extract")


def repo_root():
    return Path(__file__).resolve().parents[2]


def templates_path(*parts):
    return repo_root().joinpath("templates", *parts)


def ensure_parent_dir(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def configure_logging(level, log_file=None):
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, mode="w"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


def boto3_session(profile=None, region=None):
    if profile:
        return boto3.Session(profile_name=profile, region_name=region)
    return boto3.Session(region_name=region)


def make_config():
    return Config(retries={"max_attempts": 1000, "mode": "adaptive"})


# ----------------------
# Shared AWS helpers
# ----------------------

def list_accounts(org_client):
    accounts = []
    paginator = org_client.get_paginator("list_accounts")
    for page in paginator.paginate():
        accounts.extend(page.get("Accounts", []))
    return accounts


def list_permission_sets(sso_client, instance_arn):
    paginator = sso_client.get_paginator("list_permission_sets")
    permission_sets = []
    for page in paginator.paginate(InstanceArn=instance_arn):
        permission_sets.extend(page.get("PermissionSets", []))
    return permission_sets


# ----------------------
# Assignments
# ----------------------

def get_principal_name(identity_client, identity_store_id, principal_id, principal_type, cache):
    if principal_id in cache:
        return cache[principal_id]

    if principal_type == "USER":
        response = identity_client.describe_user(
            IdentityStoreId=identity_store_id,
            UserId=principal_id,
        )
        principal_name = response["UserName"]
    elif principal_type == "GROUP":
        response = identity_client.describe_group(
            IdentityStoreId=identity_store_id,
            GroupId=principal_id,
        )
        principal_name = response["DisplayName"]
    else:
        raise ValueError("principal_type must be USER or GROUP")

    cache[principal_id] = principal_name
    return principal_name


def get_permission_set_name(sso_client, instance_arn, permission_set_arn, cache):
    if permission_set_arn in cache:
        return cache[permission_set_arn]

    response = sso_client.describe_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn,
    )
    name = response["PermissionSet"]["Name"]
    cache[permission_set_arn] = name
    return name


def list_account_assignments(sso_client, instance_arn, account_id, permission_set_arn):
    assignments = []
    paginator = sso_client.get_paginator("list_account_assignments")
    for page in paginator.paginate(
        InstanceArn=instance_arn,
        AccountId=account_id,
        PermissionSetArn=permission_set_arn,
    ):
        assignments.extend(page.get("AccountAssignments", []))
    return assignments


def optimize_assignments(data):
    grouped = defaultdict(
        lambda: defaultdict(
            lambda: {
                "SID": None,
                "Target": [],
                "PrincipalType": None,
                "PrincipalId": None,
                "PermissionSetName": None,
            }
        )
    )

    for assignment in data.get("Assignments", []):
        principal_id = assignment["PrincipalId"]
        permission_set_name = assignment["PermissionSetName"]
        if grouped[principal_id][permission_set_name]["SID"] is None:
            grouped[principal_id][permission_set_name]["SID"] = assignment["SID"]
        grouped[principal_id][permission_set_name]["Target"].extend(assignment["Target"])
        grouped[principal_id][permission_set_name]["PrincipalType"] = assignment["PrincipalType"]
        grouped[principal_id][permission_set_name]["PrincipalId"] = principal_id
        grouped[principal_id][permission_set_name]["PermissionSetName"] = permission_set_name

    optimized = []
    for principal_id, permissions in grouped.items():
        for permission_set_name, details in permissions.items():
            optimized.append(
                {
                    "SID": details["SID"],
                    "Target": details["Target"],
                    "PrincipalType": details["PrincipalType"],
                    "PrincipalId": details["PrincipalId"],
                    "PermissionSetName": details["PermissionSetName"],
                }
            )

    return {"Assignments": optimized}


def cmd_assignments_extract(args):
    configure_logging(args.log_level, args.log_file)
    session = boto3_session(args.profile, args.region)
    sso_client = session.client("sso-admin", config=make_config())
    identity_client = session.client("identitystore", config=make_config())
    org_client = session.client("organizations", config=make_config())

    principal_cache = {}
    permission_set_cache = {}

    accounts = list_accounts(org_client)
    permission_sets = list_permission_sets(sso_client, args.instance_arn)

    output = {"Assignments": []}
    counter = 0

    for permission_set_arn in permission_sets:
        LOG.info("Processing PermissionSet: %s", permission_set_arn)
        for account in accounts:
            account_id = account["Id"]
            counter += 1
            LOG.info("%s - Account: %s", counter, account_id)

            assignments = list_account_assignments(
                sso_client, args.instance_arn, account_id, permission_set_arn
            )

            for assignment in assignments:
                principal_name = get_principal_name(
                    identity_client,
                    args.identity_store_id,
                    assignment["PrincipalId"],
                    assignment["PrincipalType"],
                    principal_cache,
                )
                output["Assignments"].append(
                    {
                        "SID": str(uuid.uuid4()),
                        "Target": [account_id],
                        "PrincipalType": assignment["PrincipalType"],
                        "PrincipalId": principal_name,
                        "PermissionSetName": get_permission_set_name(
                            sso_client,
                            args.instance_arn,
                            assignment["PermissionSetArn"],
                            permission_set_cache,
                        ),
                    }
                )

    output = optimize_assignments(output)
    ensure_parent_dir(args.output)
    with open(args.output, "w") as fh:
        json.dump(output, fh, indent=4)

    LOG.info("Assignments saved to %s", args.output)


def cmd_assignments_optimize(args):
    with open(args.input, "r") as fh:
        data = json.load(fh)

    optimized = optimize_assignments(data)
    ensure_parent_dir(args.output)
    with open(args.output, "w") as fh:
        json.dump(optimized, fh, indent=4)


def cmd_assignments_filter_controltower(args):
    with open(args.input, "r") as fh:
        data = json.load(fh)

    filtered = [
        assignment
        for assignment in data.get("Assignments", [])
        if not any(args.keyword in str(value) for value in assignment.values())
    ]

    ensure_parent_dir(args.output)
    with open(args.output, "w") as fh:
        json.dump({"Assignments": filtered}, fh, indent=4)


# ----------------------
# Permission sets
# ----------------------

def get_permission_set_details(sso_client, instance_arn, permission_set_arn):
    response = sso_client.describe_permission_set(
        InstanceArn=instance_arn, PermissionSetArn=permission_set_arn
    )
    return response["PermissionSet"]


def get_managed_policies(sso_client, instance_arn, permission_set_arn):
    response = sso_client.list_managed_policies_in_permission_set(
        InstanceArn=instance_arn, PermissionSetArn=permission_set_arn
    )
    return response.get("AttachedManagedPolicies", [])


def get_custom_policy(sso_client, instance_arn, permission_set_arn):
    response = sso_client.get_inline_policy_for_permission_set(
        InstanceArn=instance_arn, PermissionSetArn=permission_set_arn
    )
    return response.get("InlinePolicy", {})


def cmd_permissionsets_export(args):
    session = boto3_session(args.profile, args.region)
    sso_client = session.client("sso-admin", config=make_config())

    permission_sets = list_permission_sets(sso_client, args.instance_arn)
    formatted = []

    for permission_set_arn in permission_sets:
        details = get_permission_set_details(sso_client, args.instance_arn, permission_set_arn)
        custom_policy = get_custom_policy(sso_client, args.instance_arn, permission_set_arn)
        managed_policies = get_managed_policies(sso_client, args.instance_arn, permission_set_arn)

        formatted.append(
            {
                "Name": details.get("Name"),
                "Description": details.get("Description"),
                "SessionDuration": details.get("SessionDuration"),
                "ManagedPolicies": [policy["Arn"] for policy in managed_policies],
                "CustomPolicy": json.loads(custom_policy) if custom_policy else {},
            }
        )

    ensure_parent_dir(args.output)
    with open(args.output, "w") as fh:
        json.dump(formatted, fh, indent=4)

    write_permission_set_files(formatted, args.output_dir)
    try:
        Path(args.output).unlink()
    except FileNotFoundError:
        pass

    print(f"Permission sets written to {args.output_dir}")


def write_permission_set_files(permission_sets, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for permission_set in permission_sets:
        name = permission_set["Name"]
        output_file = output_dir / f"{name}.json"
        with open(output_file, "w") as out:
            json.dump(permission_set, out, indent=4)
        print(f"Generated file: {output_file}")


def cmd_permissionsets_list_unused(args):
    session = boto3_session(args.profile, args.region)
    sso_client = session.client("sso-admin", config=make_config())
    org_client = session.client("organizations", config=make_config())

    accounts = [a["Id"] for a in list_accounts(org_client)]
    permission_sets = list_permission_sets(sso_client, args.instance_arn)

    unused = []
    for permission_set_arn in permission_sets:
        used = False
        for account_id in accounts:
            assignments = list_account_assignments(
                sso_client, args.instance_arn, account_id, permission_set_arn
            )
            if assignments:
                used = True
                break
        if not used:
            unused.append(permission_set_arn)

    if args.format == "json":
        print(json.dumps(unused, indent=2))
    else:
        print("Unused PermissionSets:")
        for ps in unused:
            print(ps)


def cmd_permissionsets_fill_description(args):
    directory = Path(args.dir)
    for file_path in directory.glob("*.json"):
        with open(file_path, "r") as fh:
            data = json.load(fh)

        if "Description" in data and (data["Description"] is None or data["Description"] == ""):
            data["Description"] = args.value
            with open(file_path, "w") as fh:
                json.dump(data, fh, indent=4)
            print(f"Updated: {file_path}")


def list_tags_for_permission_set(sso_client, instance_arn, permission_set_arn):
    response = sso_client.list_tags_for_resource(
        InstanceArn=instance_arn, ResourceArn=permission_set_arn
    )
    return response.get("Tags", [])


def get_permission_set_name_simple(sso_client, instance_arn, permission_set_arn):
    response = sso_client.describe_permission_set(
        InstanceArn=instance_arn, PermissionSetArn=permission_set_arn
    )
    return response["PermissionSet"]["Name"]


def tag_permission_set(sso_client, instance_arn, permission_set_arn, key, value):
    sso_client.tag_resource(
        InstanceArn=instance_arn,
        ResourceArn=permission_set_arn,
        Tags=[{"Key": key, "Value": value}],
    )


def cmd_permissionsets_tag(args):
    session = boto3_session(args.profile, args.region)
    sso_client = session.client("sso-admin", config=make_config())

    permission_sets = list_permission_sets(sso_client, args.instance_arn)
    to_tag = []

    for permission_set_arn in permission_sets:
        name = get_permission_set_name_simple(sso_client, args.instance_arn, permission_set_arn)
        if not args.include_aws_prefix and name.startswith("AWS"):
            continue

        tags = list_tags_for_permission_set(sso_client, args.instance_arn, permission_set_arn)
        has_tag = any(tag.get("Key") == args.tag_key and tag.get("Value") == args.tag_value for tag in tags)
        if not has_tag:
            to_tag.append((permission_set_arn, name))

    if not to_tag:
        print("All permission sets already have the tag.")
        return

    print("Permission sets missing tag:")
    for permission_set_arn, name in to_tag:
        print(f"{name} ({permission_set_arn})")

    if not args.apply:
        print("Run again with --apply to add the tag.")
        return

    for permission_set_arn, name in to_tag:
        tag_permission_set(sso_client, args.instance_arn, permission_set_arn, args.tag_key, args.tag_value)
        print(f"Tagged: {name}")


# ----------------------
# OUs
# ----------------------

def list_nested_ou_ids(org_client, parent_ou_id):
    nested_ou_ids = [parent_ou_id]

    def list_ou_children(parent_id):
        paginator = org_client.get_paginator("list_organizational_units_for_parent")
        for page in paginator.paginate(ParentId=parent_id):
            for ou in page.get("OrganizationalUnits", []):
                nested_ou_ids.append(ou["Id"])
                list_ou_children(ou["Id"])

    list_ou_children(parent_ou_id)
    return nested_ou_ids


def cmd_ous_list_nested(args):
    session = boto3_session(args.profile, args.region)
    org_client = session.client("organizations", config=make_config())

    nested = list_nested_ou_ids(org_client, args.ou_id)
    output = json.dumps(nested, indent=2)

    if args.output:
        ensure_parent_dir(args.output)
        with open(args.output, "w") as fh:
            fh.write(output)
    else:
        print(output)


# ----------------------
# CLI wiring
# ----------------------

def build_parser():
    parser = argparse.ArgumentParser(prog="identity-extract")
    shared_parser = argparse.ArgumentParser(add_help=False)
    shared_parser.add_argument("--profile", help="AWS profile name")
    shared_parser.add_argument("--region", help="AWS region")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # assignments extract
    assignments = subparsers.add_parser("assignments", help="Assignments related commands")
    assignments_sub = assignments.add_subparsers(dest="subcommand", required=True)

    extract = assignments_sub.add_parser(
        "extract",
        help="Extract assignments from Identity Center",
        parents=[shared_parser],
    )
    extract.add_argument("--instance-arn", required=True)
    extract.add_argument("--identity-store-id", required=True)
    extract.add_argument(
        "--output",
        default=str(templates_path("assignments", "template_assignments.json")),
    )
    extract.add_argument("--log-file")
    extract.add_argument("--log-level", default="INFO")
    extract.set_defaults(func=cmd_assignments_extract)

    optimize = assignments_sub.add_parser(
        "optimize",
        help="Optimize assignments JSON",
        parents=[shared_parser],
    )
    optimize.add_argument(
        "--input",
        default=str(templates_path("assignments", "template_assignments.json")),
    )
    optimize.add_argument(
        "--output",
        default=str(templates_path("assignments", "optimized_template_assignments.json")),
    )
    optimize.set_defaults(func=cmd_assignments_optimize)

    filter_ct = assignments_sub.add_parser(
        "filter-controltower",
        help="Remove ControlTower-related assignments",
        parents=[shared_parser],
    )
    filter_ct.add_argument(
        "--input",
        default=str(templates_path("assignments", "template_assignments.json")),
    )
    filter_ct.add_argument(
        "--output",
        default=str(templates_path("assignments", "filtered_template_assignments.json")),
    )
    filter_ct.add_argument("--keyword", default="ControlTower")
    filter_ct.set_defaults(func=cmd_assignments_filter_controltower)

    # permission sets
    permissionsets = subparsers.add_parser("permissionsets", help="Permission set commands")
    permissionsets_sub = permissionsets.add_subparsers(dest="subcommand", required=True)

    ps_export = permissionsets_sub.add_parser(
        "export",
        help="Export permission sets",
        parents=[shared_parser],
    )
    ps_export.add_argument("--instance-arn", required=True)
    ps_export.add_argument(
        "--output",
        default=str(templates_path("permissionsets", "formatted_permission_sets.json")),
    )
    ps_export.add_argument(
        "--output-dir",
        default=str(templates_path("permissionsets")),
    )
    ps_export.set_defaults(func=cmd_permissionsets_export)

    ps_unused = permissionsets_sub.add_parser(
        "list-unused",
        help="List unused permission sets",
        parents=[shared_parser],
    )
    ps_unused.add_argument("--instance-arn", required=True)
    ps_unused.add_argument("--format", choices=["text", "json"], default="text")
    ps_unused.set_defaults(func=cmd_permissionsets_list_unused)

    ps_fill = permissionsets_sub.add_parser(
        "fill-description",
        help="Fill empty permission set descriptions",
        parents=[shared_parser],
    )
    ps_fill.add_argument(
        "--dir",
        default=str(templates_path("permissionsets")),
    )
    ps_fill.add_argument("--value", default="ps-description")
    ps_fill.set_defaults(func=cmd_permissionsets_fill_description)

    ps_tag = permissionsets_sub.add_parser(
        "tag",
        help="Tag permission sets",
        parents=[shared_parser],
    )
    ps_tag.add_argument("--instance-arn", required=True)
    ps_tag.add_argument("--tag-key", default="SSOPipeline")
    ps_tag.add_argument("--tag-value", default="true")
    ps_tag.add_argument("--include-aws-prefix", action="store_true")
    ps_tag.add_argument("--apply", action="store_true")
    ps_tag.set_defaults(func=cmd_permissionsets_tag)

    # ous
    ous = subparsers.add_parser("ous", help="OU related commands")
    ous_sub = ous.add_subparsers(dest="subcommand", required=True)

    ous_list = ous_sub.add_parser(
        "list-nested",
        help="List nested OU IDs",
        parents=[shared_parser],
    )
    ous_list.add_argument("--ou-id", required=True)
    ous_list.add_argument("--output")
    ous_list.set_defaults(func=cmd_ous_list_nested)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    # Normalize log level if provided
    if hasattr(args, "log_level"):
        args.log_level = getattr(logging, args.log_level.upper(), logging.INFO)

    args.func(args)


if __name__ == "__main__":
    main()
