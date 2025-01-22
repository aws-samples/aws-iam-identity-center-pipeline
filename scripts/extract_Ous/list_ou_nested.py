import boto3
import argparse
import json


"""
This script lists the IDs of nested Organizational Units (OUs) in AWS Organizations. It performs the following operations:

1. Importing libraries: Imports the `boto3`, `argparse`, and `json` libraries.

2. Initializing the AWS Organizations client: Initializes the boto3 client to interact with the AWS Organizations service.

3. Helper functions:
    - `list_nested_ou_ids(parent_ou_id)`: Lists the IDs of nested OUs starting from a given parent OU. Uses a paginator 
    to iterate through all nested OUs and adds their IDs to a list.

4. Main function:
    - `main()`: Receives the parent OU ID as a parameter, calls the `list_nested_ou_ids` function to get the IDs of nested OUs 
    and prints the resulting list in JSON format with indentation.

This script is useful for identifying and listing all nested OUs within a specific OU, facilitating the management of 
organizational structures in AWS Organizations.
"""

# Initialize the AWS Organizations client
client = boto3.client('organizations')


def list_nested_ou_ids(parent_ou_id):
    nested_ou_ids = [parent_ou_id]

    def list_ou_children(parent_id):
        paginator = client.get_paginator("list_organizational_units_for_parent")
        for page in paginator.paginate(ParentId=parent_id):
            for ou in page["OrganizationalUnits"]:
                nested_ou_ids.append(ou["Id"])
                list_ou_children(ou["Id"])

    list_ou_children(parent_ou_id)
    return nested_ou_ids


def main():
    parser = argparse.ArgumentParser(description="List nested OU IDs.")
    parser.add_argument("ou_id", type=str, help="The ID of the parent OU.")
    args = parser.parse_args()

    nested_ou_ids = list_nested_ou_ids(args.ou_id)
    print(json.dumps(nested_ou_ids, indent=2))


if __name__ == "__main__":
    main()
