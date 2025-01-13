import boto3
import json
import uuid
import logging


"""
This script is used to generate a JSON template containing all permissions assigned to specific accounts in AWS SSO (AWS Single Sign-On). It performs the following operations:

1. Logging configuration: Configures logging to display messages in the terminal and save them to a file called `sso_permissions_log.txt`.

2. Creation of boto3 clients: Creates clients for the AWS SSO Admin, Identity Store, and Organizations services.

3. Definition of global variables: Defines the Identity Store ID and cache dictionaries to avoid repeated API calls.

4. Helper functions:
    - `list_permission_sets(instance_arn, max_results=50)`: Lists all Permission Sets associated with an AWS SSO instance.
    - `get_permission_assignments(account_id, instance_arn, permission_set_arn=None, max_results=50)`: Retrieves the permissions assigned to a specific account in AWS SSO.
    - `get_principal_name(principal_id, principal_type, identity_store_id=idp_store_id)`: Receives the principal_id and principal_type (USER or GROUP) and returns the principal's name in the AWS Identity Center.
    - `get_permission_set_name(instance_arn, permission_set_arn)`: Retrieves the name of a Permission Set from its ARN.
    - `list_accounts()`: Lists all accounts associated with AWS Organizations or SSO.

5. Main function:
    - `main()`: Defines the ARN of the AWS SSO instance, retrieves the organization's accounts, lists all Permission Sets, and for each Permission Set and account, retrieves the assigned permissions and adds them to the final template. The generated template is displayed in the log.

This script is useful for auditing and documenting the permissions assigned in AWS SSO, facilitating access management and control in multi-account environments.
"""

# Logging configuration to display in the terminal and save to a file
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(),  # Exibe no terminal
                        logging.FileHandler('sso_permissions_log.txt', mode='w')  # Grava no arquivo
                    ])

# Create client for the SSO and Identity Store service
client = boto3.client('sso-admin')
idp_store_client = boto3.client('identitystore')
organizations_client = boto3.client('organizations')

idp_store_id = "d-12345678"  # ID do Identity Store do AWS SSO

# Cache dictionaries to avoid repeated API calls
principal_name_cache = {}
permission_set_name_cache = {}

def list_permission_sets(instance_arn, max_results=50):
    """
    List all Permission Sets associated with AWS SSO instance.
    """
    permission_sets = []
    next_token = ''

    while True:
        try:
            params = {
                'InstanceArn': instance_arn,
                'MaxResults': max_results,
                'NextToken': next_token
            }

            response = client.list_permission_sets(**params)
            permission_sets.extend(response['PermissionSets'])

            next_token = response.get('NextToken')
            if not next_token:
                break

        except client.exceptions.ClientError as e:
            logging.error(f" Error retrieving Permission Sets for the instance {instance_arn}: {e}")
            break

    return permission_sets


def get_permission_assignments(account_id, instance_arn, permission_set_arn=None, max_results=50):
    """
    Retrieves the permissions assigned to a specific account in AWS SSO.
    """
    assignments = []
    next_token = ''

    while True:
        try:
            params = {
                'AccountId': account_id,
                'InstanceArn': instance_arn,
                'MaxResults': max_results,
                'PermissionSetArn': permission_set_arn,
                'NextToken': next_token
            }

            response = client.list_account_assignments(**params)

            for assignment in response['AccountAssignments']:
                principal_name = get_principal_name(assignment['PrincipalId'], assignment['PrincipalType'])
                assignment_data = {
                    "SID": f"{str(uuid.uuid4())}",
                    "Target": [account_id],
                    "PrincipalType": assignment['PrincipalType'],
                    "PrincipalId": principal_name,
                    "PermissionSetName": get_permission_set_name(instance_arn, assignment['PermissionSetArn'])
                }
                assignments.append(assignment_data)

            next_token = response.get('NextToken')
            if not next_token:
                break

        except client.exceptions.ClientError as e:
            logging.error(f"Error retrieving permissions for the account {account_id}: {e}")
            break

    return assignments


def get_principal_name(principal_id, principal_type, identity_store_id=idp_store_id):
    """
    Receives the principal_id and principal_type (USER or GROUP) and returns the principal's name (user or group) in the AWS Identity Center (IAM Identity Store)
    """
    # Checks if the principal's name has already been stored in the cache
    if principal_id in principal_name_cache:
        return principal_name_cache[principal_id]

    try:
        if principal_type == 'USER':
            response = idp_store_client.describe_user(
                IdentityStoreId=identity_store_id,
                UserId=principal_id
            )
            principal_name = response['UserName']

        elif principal_type == 'GROUP':
            response = idp_store_client.describe_group(
                IdentityStoreId=identity_store_id,
                GroupId=principal_id
            )
            principal_name = response['DisplayName']

        else:
            raise ValueError("O principal_type must have 'USER' or 'GROUP'.")

        # Store the principal name in the cache
        principal_name_cache[principal_id] = principal_name
        return principal_name

    except idp_store_client.exceptions.ResourceNotFoundException as e:
        logging.error(f"{principal_type} with ID {principal_id} not found. Error details: {e}")
        raise

    except Exception as e:
        logging.error(f"Error of the search principal name (ID: {principal_id}, tipo: {principal_type}): {e}")
        raise


def get_permission_set_name(instance_arn, permission_set_arn):
    """
    Get the Permission Set name from an ARN.
    """
    # Checks if the permission set name has already been stored in the cache
    if permission_set_arn in permission_set_name_cache:
        return permission_set_name_cache[permission_set_arn]

    try:
        response = client.describe_permission_set(
            InstanceArn=instance_arn,
            PermissionSetArn=permission_set_arn
        )
        permission_set_name = response['PermissionSet']['Name']

        # Stores the permission set name in the cache
        permission_set_name_cache[permission_set_arn] = permission_set_name
        return permission_set_name

    except Exception as e:
        logging.error(f"Error of get the Permission Set (ARN: {permission_set_arn}): {e}")
        raise


def list_accounts():
    """
    Lists all accounts associated with AWS Organizations or SSO.
    """
    accounts = []
    next_token = ''

    while True:
        try:
            response = organizations_client.list_accounts(NextToken=next_token) if next_token else organizations_client.list_accounts()
            accounts.extend(response['Accounts'])

            next_token = response.get('NextToken')
            if not next_token:
                break

        except organizations_client.exceptions.ClientError as e:
            logging.error(f"Error of get organization account: {e}")
            break

    return accounts


def main():
    # Set the instance ARN of AWS SSO
    instance_arn = "arn:aws:sso:::instance/ssoins-12345678abc"

    # Get organization accounts
    accounts = list_accounts()

    # List all Permission Sets
    permission_sets = list_permission_sets(instance_arn)

    # Data Structure for the final template
    end_template = {"Assignments": []}

    posicion = 0
    for permission_set_arn in permission_sets:
        logging.info(f"Obtaining results for PermissionSet: {permission_set_arn}")

        for account in accounts:
            account_id = account['Id']
            posicion += 1
            logging.info(f"{posicion} - Obtaining results for account: {account_id}")

            # 
            assignments = get_permission_assignments(account_id, instance_arn, permission_set_arn)

            # Retrieve the permissions assigned to the account, filtered by PermissionSetArn.
            end_template["Assignments"].extend(assignments)

    # Show generated template
    logging.info("Generated Template:")
    logging.info(json.dumps(end_template, indent=4))

    # Save in json file
    with open("templates/assignments/template_associacoes.json", "w") as file:
        json.dump(end_template, file, indent=4)


if __name__ == '__main__':
    main()
