import boto3


"""
This script lists the unused Permission Sets in AWS SSO. It performs the following operations:

1. Importing libraries: Imports the `boto3` library.

2. Configuring the SSO Admin and Organizations client: Initializes the boto3 clients to interact with AWS SSO Admin
    and AWS Organizations services.

3. Helper functions:
     - `list_accounts()`: Lists all accounts in the organization, returning a list of account IDs.
     - `list_permission_sets(instance_arn)`: Lists all Permission Sets associated with an AWS SSO instance.

4. Main function:
     - `main()`: Defines the ARN of the AWS SSO instance, gets the list of accounts, lists all Permission Sets,
        and checks if each Permission Set is associated with any account. The unused Permission Sets are displayed in the terminal.

This script is useful for identifying Permission Sets that are not being used, facilitating the management and control of
permissions in multi-account environments.
"""

# Configuring the SSO Admin and Organizations client
client = boto3.client('sso-admin', region_name='us-east-1')
org_client = boto3.client('organizations')


def list_accounts():
    accounts = []
    account_ids = []
    
    # List accounts in the organization
    response = org_client.list_accounts()

    # Add accounts to the list
    accounts.extend(response['Accounts'])

    # Pagination
    while 'NextToken' in response:
        response = org_client.list_accounts(NextToken=response['NextToken'])
        accounts.extend(response['Accounts'])
    
    for account in accounts:
        account_ids.append(account['Id'])

    return account_ids


def list_permission_sets(instance_arn):
    """Lists all Permission Sets of an AWS Identity Center instance."""
    response = client.list_permission_sets(InstanceArn=instance_arn)
    return response['PermissionSets']


def list_account_assignments(instance_arn, account_id, permission_set_arn):
    """Checks if a Permission Set is associated with a specific account."""
    response = client.list_account_assignments(
        InstanceArn=instance_arn,
        AccountId=account_id,
        PermissionSetArn=permission_set_arn
    )

    return response['AccountAssignments']


def main():
    instance_arn = 'arn:aws:sso:::instance/ssoins-12345678abc'
    accounts = list_accounts()
    permission_sets = list_permission_sets(instance_arn)

    unused_permission_sets = []

    # For each PermissionSet, check if it is associated with any account
    for permission_set in permission_sets:
        permission_set_arn = permission_set
        used = False

        for account_id in accounts:
            associations = list_account_assignments(instance_arn, account_id, permission_set_arn)
            
            # If the PermissionSet is associated, mark it as used
            if associations:
                used = True
                break

        if not used:
            unused_permission_sets.append(permission_set_arn)
    
    print("Unused PermissionSets:")
    for ps in unused_permission_sets:
        print(ps)


if __name__ == '__main__':
    main()
