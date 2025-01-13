import boto3


"""
This script interacts with AWS SSO Admin to list Permission Sets and their tags. It performs the following operations:

1. Importing libraries: Imports the `boto3` library.

2. Initializing the AWS SSO Admin client: Initializes the boto3 client to interact with the AWS SSO Admin service.

3. Helper functions:
    - `list_permission_sets(instance_arn)`: Lists all Permission Sets associated with an AWS SSO instance using a paginator.
    - `list_tags_for_permission_set(instance_arn, permission_set_arn)`: Retrieves the tags associated with a specific Permission Set.
    - `get_permission_set_name(instance_arn, permission_set_arn)`: Retrieves the name of a specific Permission Set from its ARN.

4. Main function:
    - `main()`: Lists all Permission Sets associated with an AWS SSO instance, checks if they have the SSOPipeline tag with value true, and if not, prompts to add the tag. The script displays the Permission Sets that do not have the tag and asks for confirmation to add the tag.
    
This script is useful for managing and auditing Permission Sets and their tags in AWS SSO, facilitating permission administration in multi-account environments.
"""

# Inicialize AWS SSO Admin client
client = boto3.client('sso-admin')


# Function to list all permission sets
def list_permission_sets(instance_arn):
    paginator = client.get_paginator('list_permission_sets')
    permission_sets = []

    for page in paginator.paginate(InstanceArn=instance_arn):
        permission_sets.extend(page['PermissionSets'])
    
    return permission_sets


# Function to retrieve the tags of a permission set
def list_tags_for_permission_set(instance_arn, permission_set_arn):
    response = client.list_tags_for_resource(
        InstanceArn=instance_arn,
        ResourceArn=permission_set_arn
    )

    return response['Tags']


# Function to retrieve the name of a permission set
def get_permission_set_name(instance_arn, permission_set_arn):
    response = client.describe_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )

    return response['PermissionSet']['Name']


# Function to add the SSOPipeline tag to a permission set
def tag_permission_set(instance_arn, permission_set_arn):
    client.tag_resource(
        InstanceArn=instance_arn,
        ResourceArn=permission_set_arn,
        Tags=[
            {
                'Key': 'SSOPipeline',
                'Value': 'true'
            }
        ]
    )


def main():
    instance_arn = 'arn:aws:sso:::instance/ssoins-12345678abc'
    permission_sets = list_permission_sets(instance_arn)

    permission_sets_to_tag = []
    aws_permission_sets_to_tag = []

    # Check the tag in all PermissionSet
    for permission_set_arn in permission_sets:
        name = get_permission_set_name(instance_arn, permission_set_arn)
        
        tags = list_tags_for_permission_set(instance_arn, permission_set_arn)
        has_ssopipeline_tag = any(tag['Key'] == 'SSOPipeline' and tag['Value'] == 'true' for tag in tags)

        if not has_ssopipeline_tag:
            if name.startswith('AWS'):
                aws_permission_sets_to_tag.append((permission_set_arn, name))
            else:
                permission_sets_to_tag.append((permission_set_arn, name))

    # Display permission sets that do not have the SSOPipeline tag with value true
    print("Permission sets that do not have the SSOPipeline tag with value true:")
    
    for permission_set_arn, name in permission_sets_to_tag:
        print(f"{name} ({permission_set_arn})")

    # Request confirmation to add the tag to permission sets without the AWS prefix
    confirm = input("Do you want to add the SSOPipeline=true tag to all these permission sets? (yes/no): ")

    if confirm.lower() == 'yes':
        for permission_set_arn, name in permission_sets_to_tag:
            tag_permission_set(instance_arn, permission_set_arn)
            print(f"Tag adicionada ao permission set: {name} ({permission_set_arn})")

    # Display permission sets with AWS prefix that do not have the SSOPipeline tag with value true
    print("\nPermission sets with the AWS prefix that do not have the SSOPipeline tag with the value true:")
    
    for permission_set_arn, name in aws_permission_sets_to_tag:
        print(f"{name} ({permission_set_arn})")

    # Request confirmation to add the tag to permission sets with AWS prefix
    confirm_aws = input("Do you want to add the tag SSOPipeline=true to all these permission sets with the AWS prefix? (yes/no): ")

    if confirm_aws.lower() == 'yes':
        for permission_set_arn, name in aws_permission_sets_to_tag:
            tag_permission_set(instance_arn, permission_set_arn)
            print(f"Tag added in Permissionset with prefix AWS: {name} ({permission_set_arn})")


if __name__ == "__main__":
    main()
