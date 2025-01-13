import boto3
import json


"""
This script interacts with AWS SSO Admin to list and obtain details about Permission Sets and generate Permission Set files 
for the pipeline. It performs the following operations:

1. Importing libraries: Imports the `boto3` and `json` libraries.

2. Initializing the AWS SSO Admin client: Initializes the boto3 client to interact with the AWS SSO Admin service.

3. Helper functions:
    - `list_permission_sets(instance_arn)`: Lists all Permission Sets associated with an SSO instance using a paginator.
    - `get_permission_set_details(instance_arn, permission_set_arn)`: Gets the details of a specific Permission Set by its ARN.
    - `get_managed_policies(instance_arn, permission_set_arn)`: Gets the managed policies associated with a specific Permission Set.

4. Main function:
    - `process_permission_set(instance_arn, permission_set_arn)`: Processes a specific Permission Set, obtaining its details, managed
    policies, and custom policy.
    - `main()`: Lists and processes all Permission Sets associated with an SSO instance, saving the results in a JSON file.
    
This script is useful for managing and auditing Permission Sets in AWS SSO, facilitating permission administration in multi-account 
environments.
"""

# Inicialization of the AWS SSO Admin client
client = boto3.client('sso-admin')


# Function to list all permission sets
def list_permission_sets(instance_arn):
    paginator = client.get_paginator('list_permission_sets')
    permission_sets = []
    for page in paginator.paginate(InstanceArn=instance_arn):
        permission_sets.extend(page['PermissionSets'])
    return permission_sets


# Function for get permissionset details
def get_permission_set_details(instance_arn, permission_set_arn):
    response = client.describe_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )
    return response['PermissionSet']


# Function to retrieve the managed policies associated with a permission set
def get_managed_policies(instance_arn, permission_set_arn):
    response = client.list_managed_policies_in_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )
    return response['AttachedManagedPolicies']


# Function to get the custom policy associated with a permission set
def get_custom_policy(instance_arn, permission_set_arn):
    response = client.get_inline_policy_for_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )
    return response.get('InlinePolicy', {})


# Function for processing permissionset
def process_permission_set(instance_arn, permission_set_arn):
    details = get_permission_set_details(instance_arn, permission_set_arn)
    
    # Extract necessary information
    name = details.get("Name")
    description = details.get("Description")
    session_duration = details.get("SessionDuration")
    managed_policies = get_managed_policies(instance_arn, permission_set_arn)
    custom_policy = get_custom_policy(instance_arn, permission_set_arn)
    
    # Format the permission set pipeline model
    formatted_permission_set = {
        "Name": name,
        "Description": description,
        "SessionDuration": session_duration,
        "ManagedPolicies": [policy['Arn'] for policy in managed_policies],
        "CustomPolicy": json.loads(custom_policy) if custom_policy else {}
    }
    
    return formatted_permission_set


# Main function to list and process all permission sets
def main():
    # Substitute to ARN of AWS SSO instance
    instance_arn = 'arn:aws:sso:::instance/ssoins-12345678abc'

    permission_sets = list_permission_sets(instance_arn)
    formatted_permission_sets = []
    
    for permission_set_arn in permission_sets:
        formatted_permission_set = process_permission_set(instance_arn, permission_set_arn)
        formatted_permission_sets.append(formatted_permission_set)
    
    # Save the formatted permission sets in a new JSON file
    with open('templates/permissionsets/formatted_permission_sets.json', 'w') as file:
        json.dump(formatted_permission_sets, file, indent=4)
    
    print("Permission sets processed and saved in formatted_permission_sets.json")


if __name__ == "__main__":
    main()
