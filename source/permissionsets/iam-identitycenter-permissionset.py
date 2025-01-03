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

## + -----------------------
## | AWS SSO Permission Set Managemnet
## +-----------------------------------

import boto3
import botocore
import json
import argparse
import sys
import os
import logging
from botocore.config import Config


# Logging configuration
logging.basicConfig(format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.DEBUG)
log = logging.getLogger()
log.setLevel(logging.INFO)

# Config to handle throttling
config = Config(
   retries = {
      'max_attempts': 1000,
      'mode': 'adaptive'
   }
)

# This method will return all permission sets in AWS SSO with the tag 'SSOPipeline'
def get_current_permissionset_list():
    client = boto3.client('sso-admin', config=config)
    perm_set_dict = {}

    response = client.list_permission_sets(InstanceArn=ssoInstanceArn)

    results = response["PermissionSets"]
    while "NextToken" in response:
        response = client.list_permission_sets(InstanceArn=ssoInstanceArn, NextToken=response["NextToken"]) 
        results.extend(response["PermissionSets"])

    for permission_set in results:
        response = client.list_tags_for_resource(InstanceArn=ssoInstanceArn,ResourceArn=permission_set)
        for eachTag in response['Tags']:
            if (eachTag['Key'] in 'SSOPipeline'):
                perm_description = client.describe_permission_set(InstanceArn=ssoInstanceArn,PermissionSetArn=permission_set)
                perm_set_dict[perm_description["PermissionSet"]["Name"]] = permission_set
    
    return perm_set_dict

# This method will return all permission sets in the folder specificied in the script argument (--ps-folder) in a single dictionary
def get_repository_permissionset_list():
    psFiles = os.listdir('../../templates/permissionsets/')
    perm_set_dict = {}

    for eachFile in psFiles:
        path = '../../templates/permissionsets/'+eachFile
        f = open(path)
        data = json.load(f)
        perm_set_dict[data['Name']] = data
        f.close()
    return perm_set_dict


#########################
## GENERAL INFORMATION ##
#########################
# This will update general information of permission set, like description and session duration
def update_general_information(permissionSet, permissionSetArn, client):
    log.info(f"[PS: {permissionSet['Name']}] " + "Updating General Information...")

    relay_state = permissionSet.get('RelayState', "https://console.aws.amazon.com/")
    
    try:
        response = client.update_permission_set(
            InstanceArn=ssoInstanceArn,
            PermissionSetArn=permissionSetArn,
            Description=permissionSet['Description'],
            SessionDuration=permissionSet['SessionDuration'],
            RelayState=relay_state
        )
        log.info(f"[PS: {permissionSet['Name']}] " + "Successfully upated general information")
    except Exception as e:
        log.error('It was not possible to update Permission Set general information. Reason: ' + str(e))
        exit(1)

###################
## INLINE POLICY ##
###################
# Updates inline policy or delete it
def update_inline_policy(permissionSet, permissionSetArn, client):
    log.info(f"[PS: {permissionSet['Name']}] " + "Updating Inline Policy...")
    
    # Update inline policy
    if ('CustomPolicy' in permissionSet) and (permissionSet['CustomPolicy']):
        try:
            response = client.put_inline_policy_to_permission_set(
                InstanceArn=ssoInstanceArn,
                PermissionSetArn=permissionSetArn,
                InlinePolicy=json.dumps(permissionSet['CustomPolicy'])
            )
            log.info(f"[PS: {permissionSet['Name']}] " + "Successfully upated inline permissions")
        except Exception as e:
            log.error('It was not possible to update inline permission. Reason: ' + str(e))
            exit(1)
    
    # Delete inline policy
    else:
        try:
            response = client.delete_inline_policy_from_permission_set(
                InstanceArn=ssoInstanceArn,
                PermissionSetArn=permissionSetArn
            )
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'ResourceNotFoundException':
                log.info(f"[PS: {permissionSet['Name']}] " + "Not Inline policy found")   
            else:
                log.error(f"[PS: {permissionSet['Name']}] " + "It was not possible deleting Inline Policy. Reason: " + str(error))   
                exit(1)                     

##########################
## AWS MANAGED POLICIES ##
##########################
def update_aws_managed_policies(permissionSet, permissionSetArn, client):
    log.info(f"[PS: {permissionSet['Name']}] " + "Updateing on AWS Managed Policies...")
    
    # List AWS Managed Policies
    response = client.list_managed_policies_in_permission_set(
        InstanceArn=ssoInstanceArn,
        PermissionSetArn=permissionSetArn,
    )
    currentManagedPolicies = response['AttachedManagedPolicies']

    if ('ManagedPolicies' in permissionSet) and (permissionSet['ManagedPolicies']):
        # Add new AWS managed policies
        for eachManagedPolicy in permissionSet['ManagedPolicies']:
            try:        
                response = client.attach_managed_policy_to_permission_set(
                    InstanceArn=ssoInstanceArn,
                    PermissionSetArn=permissionSetArn,
                    ManagedPolicyArn=eachManagedPolicy
                )
                log.info(f"[PS: {permissionSet['Name']}] " + "Successfully added managed policy: " + str(eachManagedPolicy))
            except botocore.exceptions.ClientError as error:
                if error.response['Error']['Code'] == 'ConflictException':
                    log.info(f"[PS: {permissionSet['Name']}] " + "Managed policy was already attached: " + str(eachManagedPolicy))
                else:
                    log.error('It was not possible to add managed policies. Reason: ' + str(error))
                    exit(1)

        # Remove AWS managed policies that were removed from repository
        for eachManagedPolicy in currentManagedPolicies:
            try:
                if eachManagedPolicy['Arn'] not in permissionSet['ManagedPolicies']:
                    log.info(f"[PS: {permissionSet['Name']}] " + "Managed policy needs to be removed from Permission Set: " + str(eachManagedPolicy['Arn']))
                    response = client.detach_managed_policy_from_permission_set(
                        InstanceArn=ssoInstanceArn,
                        PermissionSetArn=permissionSetArn,
                        ManagedPolicyArn=eachManagedPolicy['Arn']
                    )                
            except Exception as error:
                log.error(f"[PS: {permissionSet['Name']}] " + 'It was not possible remove managed policies. Reason: ' + str(error))
                exit(1)
    
    else:
        # Remove AWS managed policies that were removed from repository
        for eachManagedPolicy in currentManagedPolicies:
            try:
                log.info(f"[PS: {permissionSet['Name']}] " + "Managed policy needs to be removed from Permission Set: " + str(eachManagedPolicy['Arn']))
                response = client.detach_managed_policy_from_permission_set(
                    InstanceArn=ssoInstanceArn,
                    PermissionSetArn=permissionSetArn,
                    ManagedPolicyArn=eachManagedPolicy['Arn']
                )                
            except Exception as error:
                log.error(f"[PS: {permissionSet['Name']}] " + 'It was not possible remove managed policies. Reason: ' + str(error))
                exit(1)


###############################
## CUSTOMER MANAGED POLICIES ##
###############################
def update_customer_managed_policies(permissionSet, permissionSetArn, client):
    log.info(f"[PS: {permissionSet['Name']}] " + "Updating Customer Managed Policies...")
    
    # List Customer Managed Policies
    response = client.list_customer_managed_policy_references_in_permission_set(
        InstanceArn=ssoInstanceArn,
        PermissionSetArn=permissionSetArn,
    )
        
    currentCustomerManagedPolicies = response['CustomerManagedPolicyReferences']

    # This part will check if the field CustomerManagedPolicies exist in templates. Otherwise, will ignore this feature.
    if ('CustomerManagedPolicies' in permissionSet) and (permissionSet['CustomerManagedPolicies']):


        # Add customer managed policies
        for eachManagedPolicy in permissionSet['CustomerManagedPolicies']:
            try:
                customerManagedPolicy = {'Name': 'customerManagedPolicy', 'Path': '/'}
                customerManagedPolicy['Name'] = eachManagedPolicy
                response = client.attach_customer_managed_policy_reference_to_permission_set(
                    InstanceArn=ssoInstanceArn,
                    PermissionSetArn=permissionSetArn,
                    CustomerManagedPolicyReference=customerManagedPolicy
                )
                log.info(f"[PS: {permissionSet['Name']}] " + "Successfully added Customer Managed Policy: " + str(eachManagedPolicy))
            except botocore.exceptions.ClientError as error:
                if error.response['Error']['Code'] == 'ConflictException':
                    log.info(f"[PS: {permissionSet['Name']}] " + "Customer Managed Policy was already attached: " + str(eachManagedPolicy))
                else:
                    log.error('It was not possible to add Customer Managed Policy. Reason: ' + str(error))
                    exit(1)

        # Remove customer managed policies
        for eachManagedPolicy in currentCustomerManagedPolicies:
            try:
                if eachManagedPolicy['Name'] not in permissionSet['CustomerManagedPolicies']:
                    customerManagedPolicy = {'Name': 'customerManagedPolicy', 'Path': '/'}
                    customerManagedPolicy['Name'] = eachManagedPolicy['Name']
                    log.info(f"[PS: {permissionSet['Name']}] " + "Customer Managed Policy needs to be removed from Permission Set: " + str(eachManagedPolicy['Name']))
                    response = client.detach_customer_managed_policy_reference_from_permission_set(
                        InstanceArn=ssoInstanceArn,
                        PermissionSetArn=permissionSetArn,
                        CustomerManagedPolicyReference=customerManagedPolicy
                    )                
            except Exception as error:
                log.error(f"[PS: {permissionSet['Name']}] " + 'It was not possible remove managed policies. Reason: ' + str(error))
                exit(1)

    else:
        for eachManagedPolicy in currentCustomerManagedPolicies:
            try:                
                customerManagedPolicy = {'Name': 'customerManagedPolicy', 'Path': '/'}
                customerManagedPolicy['Name'] = eachManagedPolicy['Name']
                log.info(f"[PS: {permissionSet['Name']}] " + "Customer Managed Policy needs to be removed from Permission Set: " + str(eachManagedPolicy['Name']))
                response = client.detach_customer_managed_policy_reference_from_permission_set(
                    InstanceArn=ssoInstanceArn,
                    PermissionSetArn=permissionSetArn,
                    CustomerManagedPolicyReference=customerManagedPolicy
                )                
            except Exception as error:
                log.error(f"[PS: {permissionSet['Name']}] " + 'It was not possible remove managed policies. Reason: ' + str(error))
                exit(1)   
    
#########################
## PERMISSION BOUNDARY ##
#########################
def update_permission_boundary(permissionSet, permissionSetArn, client):
    log.info(f"[PS: {permissionSet['Name']}] " + "Updating Permission Boundary...")
    if ('PermissionBoundary' in permissionSet) and (permissionSet['PermissionBoundary']):
        # Update Permission Boundary
        try:
            if permissionSet['PermissionBoundary']['PolicyType'] == 'AWS':
                boundary = {'ManagedPolicyArn': 'managedpolicy'}
                boundary['ManagedPolicyArn'] = permissionSet['PermissionBoundary']['Policy']
            else:
                boundary = {'CustomerManagedPolicyReference': {'Name': 'policy', 'Path': '/'}}
                boundary['CustomerManagedPolicyReference']['Name'] = permissionSet['PermissionBoundary']['Policy']
            
            response = client.put_permissions_boundary_to_permission_set(
                InstanceArn=ssoInstanceArn,
                PermissionSetArn=permissionSetArn,
                PermissionsBoundary=boundary
            )
            log.info(f"[PS: {permissionSet['Name']}] " + "Successfully attached Permission Boundary")
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'ConflictException':
                log.info(f"[PS: {permissionSet['Name']}] " + "Permission Boundary was already attached.")
            else:
                log.error('It was not possible to attach Permission Boundary. Reason: ' + str(error))
                exit(1)
    else:
        # Try to delete boundary
        log.info(f"[PS: {permissionSet['Name']}] " + "No Permission Boundary found in code, thus it will be delete from permission set")
        try:
            response = client.delete_permissions_boundary_from_permission_set(
                InstanceArn=ssoInstanceArn,
                PermissionSetArn=permissionSetArn,
            )
            log.info(f"[PS: {permissionSet['Name']}] " + "Permission Boundary deleted")
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'ResourceNotFoundException':
                log.info(f"[PS: {permissionSet['Name']}] " + "No Permission Boundary found, nothing to delete.")
            else:
                log.error('It was not possible to delete Permission Boundary. Reason: ' + str(error))
                exit(1)

############################
## UPDATE PERMISSION SETS ##
############################
def update_permission_set(permissionSet, permissionSetArn):
    client = boto3.client('sso-admin', config=config)
    
    # GENERAL INFORMATION
    update_general_information(permissionSet, permissionSetArn, client)

    # INLINE POLICY
    update_inline_policy(permissionSet, permissionSetArn, client)

    # AWS MANAGED POLICIES
    update_aws_managed_policies(permissionSet, permissionSetArn, client)
    
    # CUSTOMER MANAGED POLICIES
    update_customer_managed_policies(permissionSet, permissionSetArn, client)
         
    # PERMISSION BOUNDARY
    update_permission_boundary(permissionSet, permissionSetArn, client)            

    # PROVISION IN ALL ACCOUNTS
    try:
        response = client.provision_permission_set(
            InstanceArn=ssoInstanceArn,
            PermissionSetArn=permissionSetArn,
            TargetType='ALL_PROVISIONED_ACCOUNTS'
        )
        log.info(f"[PS: {permissionSet['Name']}] " + "Re-provisioning permission set in all accounts. It might take a while and will happen in parallel.")
    except Exception as error:
        log.error('It was not possible to provision the permission set in all accounts. Reason: ' + str(error))
        exit (1)

    return True

###########################
## CREATE PERMISSION SET ## 
###########################
# This method will create a permission set according to the template in the 'templates/permissionsets/' with the tag 'SSOPipeline:true'
def create_permission_set(permissionSet):
    client = boto3.client('sso-admin', config=config)
    
    # Create permission set
    try:
        response = client.create_permission_set(
            Name=permissionSet['Name'],
            Description=permissionSet['Description'],
            InstanceArn=ssoInstanceArn,
            SessionDuration=permissionSet['SessionDuration'],
            Tags=[
                {
                    'Key': 'SSOPipeline',
                    'Value': 'true'
                },
            ]
        )
        log.info(f"[PS: {permissionSet['Name']}] " + "Successfully created the Permission Set")
    except Exception as e:
        log.error('It was not possible to create the Permission Set. Reason: ' + str(e))
        exit(1)

    permissionSetArn = response['PermissionSet']['PermissionSetArn']
    update_permission_set(permissionSet, permissionSetArn)

###########################
## DELETE PERMISSION SET ## 
###########################
# This method will delete the permission set that was deleted from the folder 'templates/permissionsets/' of the repository
def delete_permission_set(permissionSetArn, permissionSetName):
    client = boto3.client('sso-admin', config=config)
    
    # Update general information
    try:
        response = client.delete_permission_set(
            InstanceArn=ssoInstanceArn,
            PermissionSetArn=permissionSetArn
        )
        log.info(f"[PS: {permissionSetName}] " + "Permission Set was deleted: " + str(permissionSetArn))
    except Exception as e:
        log.error(f"[PS: {permissionSetName}] " + 'It was not possible to delete Permission Set. Reason: ' + str(e))
        exit(1)
    
    return True

# This method will compare both current permission sets (implemented in the AWS SSO with the tag SSOpipeline) 
# with the permission sets in the repository and modify, create or delete what is required. The repository will always be the source of truth.
def define_permissionset_change(currentPermissionSets, repositoryPermissionSets):
    # Loop for UPDATE and CREATE permission sets
    for eachRepositoryPermissionSet in repositoryPermissionSets:
        if repositoryPermissionSets[eachRepositoryPermissionSet]['Name'] in currentPermissionSets:
            log.info(f"[PS: {repositoryPermissionSets[eachRepositoryPermissionSet]['Name']}] " + "Permission set already exists in AWS SSO, so it will be UPDATED.")
            update_permission_set(repositoryPermissionSets[eachRepositoryPermissionSet], currentPermissionSets[repositoryPermissionSets[eachRepositoryPermissionSet]['Name']])
        else:
            log.info(f"[PS: {repositoryPermissionSets[eachRepositoryPermissionSet]['Name']}] " + "Permission set doesn\'t exist in AWS SSO, so it will be CREATED.")
            create_permission_set(repositoryPermissionSets[eachRepositoryPermissionSet])
    
    # Loop for DELETE permission sets
    for eachCurrentPermissionSet in currentPermissionSets:
        if eachCurrentPermissionSet not in repositoryPermissionSets:
            log.info(f"[PS: {eachCurrentPermissionSet}] " + " Permission set was not found in the repository, so it will be DELETED")
            delete_permission_set(currentPermissionSets[eachCurrentPermissionSet], eachCurrentPermissionSet)


def main():
    print("##########################################")
    print("# Starting AWS SSO Permission Set Script #")
    print("##########################################\n")
    

    # Put the SSOInstanceArn in a global variable to be used latter on in the code
    global ssoInstanceArn

    # Get Identity Store and SSO Instance ARN
    sso_client = boto3.client('sso-admin', config=config)
    response = sso_client.list_instances()
    ssoInstanceArn = response['Instances'][0]['InstanceArn']

    currentPermissionSets = get_current_permissionset_list()    
    repositoryPermissionSets = get_repository_permissionset_list()

    define_permissionset_change(currentPermissionSets, repositoryPermissionSets)
    log.info('Congrats! Permission sets script finished without errors! :)')
    
main()