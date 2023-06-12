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
## | AWS SSO Assignments Managemnet
## +-----------------------------------

import boto3
import json
import os
import logging
from botocore.config import Config
import re
import argparse

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

# Setting arguments
parser = argparse.ArgumentParser(description='AWS SSO Permission Set Management')
parser.add_argument('--org_role', action="store", dest='orgRole')
parser.add_argument('--mgmt_account', action="store", dest='mgmtAccount')

args = parser.parse_args()

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

def load_assignments_from_file():
    assigments_file = os.listdir('../../templates/assignments/')
    assig_dic = {}
    assignments_list = []
    

    for eachFile in assigments_file:
        path = '../../templates/assignments/'+eachFile
        f = open(path)
        data = json.load(f)
        assignments_list.extend(data['Assignments'])
        f.close()
    assig_dic['Assignments'] = assignments_list
    log.info('Assignments successfully loaded from repository files')
    return assig_dic



def resolve_ou_names(ouid, client):
    response = client.list_organizational_units_for_parent(ParentId=ouid)
    results = response['OrganizationalUnits']
    while "NextToken" in response:
        response = client.list_organizational_units_for_parent(ParentId=ouid, NextToken=response["NextToken"]) 
        results.extend(response["OrganizationalUnits"])
    
    if results:
        for eachOU in results:
            results.extend(resolve_ou_names(eachOU['Id'], client))
    
    return results

def list_accounts_in_ou(ouid):
    client = boto3.client('organizations', config=config, aws_access_key_id=credentials['AccessKeyId'], aws_secret_access_key=credentials['SecretAccessKey'], aws_session_token=credentials['SessionToken'])
    try:
        if 'ou-' in ouid:
            response = client.list_accounts_for_parent(ParentId=ouid)
            results = response["Accounts"]
            while "NextToken" in response:
                response = client.list_accounts_for_parent(ParentId=ouid, NextToken=response["NextToken"]) 
                results.extend(response["Accounts"])
        elif 'r-' in ouid:
            response = client.list_accounts()
            results = response["Accounts"]
            while "NextToken" in response:
                response = client.list_accounts(NextToken=response["NextToken"]) 
                results.extend(response["Accounts"])
        elif 'Root' in ouid:
            response = client.list_accounts()
            results = response["Accounts"]
            while "NextToken" in response:
                response = client.list_accounts(NextToken=response["NextToken"]) 
                results.extend(response["Accounts"])                
        else:
            results = []
            rootid = client.list_roots()['Roots'][0]['Id']
            log.info(f"{rootid} Trying to identify accounts for OU name")
            results = resolve_ou_names(rootid, client)
            for eachOu in results:
                if eachOu['Name'] == str(ouid):
                    newOuId = eachOu['Id']
                    log.info(f"[OU: {ouid}] Organization Unit ID found for OU name")
                    break
            response = client.list_accounts_for_parent(ParentId=newOuId)
            results = response["Accounts"]
            while "NextToken" in response:
                response = client.list_accounts_for_parent(ParentId=ouid, NextToken=response["NextToken"]) 
                results.extend(response["Accounts"])

    except Exception as error:
        log.error('It was not possible to list accounts from Organization Unit. Reason: ' + str(error))

    account_list = []
    for eachResult in results:
        if eachResult["Status"] == "ACTIVE":
            account_list.append(eachResult['Id'])
    return account_list

def lookup_principal_id(principalName, principalType):
    try:
        client = boto3.client('identitystore', config=config)
        if principalType == 'GROUP':
            response = client.list_groups(
                IdentityStoreId=identitystore,
                Filters=[
                    {
                        'AttributePath': 'DisplayName',
                        'AttributeValue': principalName
                    },
                ]
            )
            return response['Groups'][0]['GroupId']
        if principalType == 'USER':
            response = client.list_users(
                IdentityStoreId=identitystore,
                Filters=[
                    {
                        'AttributePath': 'UserName',
                        'AttributeValue': principalName
                    },
                ]
            )
            return response['Users'][0]['UserId']
    except Exception as error:
        log.error(f"[PR: {principalName}] [{principalType}]  It was not possible lookup target. Reason: " + str(error))

def resolve_targets(eachCurrentAssignments):
    client = boto3.client('sso-admin', config=config)
    try:
        account_list = []
        log.info(f"[SID: {eachCurrentAssignments['SID']}] Resolving target in accounts")
        for eachTarget in eachCurrentAssignments['Target']:
            pattern = re.compile(r'\d{12}') # Regex for AWS Account Id
            if pattern.match(eachTarget):
                account_list.append(eachTarget)
            else:
                account_list.extend(list_accounts_in_ou(eachTarget))                
        return account_list
    except Exception as error:
        log.error(f"[SID: {eachCurrentAssignments['SID']}] It was not possible to resolve the targets from assignment. Reason: " + str(error))



def list_permission_in_sso_for_user(permissionSet, eachRepositoryAssignments):
    
    account_list = []
    try:
        # List all accounts with specific permission set
        client = boto3.client('sso-admin', config=config)
        response = client.list_accounts_for_provisioned_permission_set(InstanceArn=ssoInstanceArn,PermissionSetArn=permissionSet)
        results = response["AccountIds"]
        while "NextToken" in response:
            response = client.list_accounts_for_provisioned_permission_set(InstanceArn=ssoInstanceArn,PermissionSetArn=permissionSet, NextToken=response["NextToken"])
            results.extend(response["AccountIds"])
        log.info(f"[SID: {eachRepositoryAssignments['SID']}] [PR: {eachRepositoryAssignments['PrincipalId']}] [{eachRepositoryAssignments['PrincipalType']}] Looking up principal ID")
        principalId = lookup_principal_id(eachRepositoryAssignments['PrincipalId'], eachRepositoryAssignments['PrincipalType'])

        # For each account, list assignments
        for eachAccount in response["AccountIds"]:
            assignmentsResponse = client.list_account_assignments(
                InstanceArn=ssoInstanceArn,
                AccountId=eachAccount,
                PermissionSetArn=permissionSet
            )

            # For each assingment, check if it is associated to a specific principalId
            for eachuser in assignmentsResponse['AccountAssignments']:
                if principalId == eachuser['PrincipalId']:
                    account_list.append(eachAccount)
    except Exception as error:
        log.error(f"[SID: {eachRepositoryAssignments['SID']}] It was not possible to list permissions for a specific user. Reason: " + str(error))

    return account_list



def create_assignment_file(permissionSetsArn,repositoryAssignments):
    log.info('Creating assignment file')
    client = boto3.client('sso-admin', config=config)
    
    try:
        for assignment in repositoryAssignments['Assignments']:
            accounts = resolve_targets(assignment)
            principalId = lookup_principal_id(assignment['PrincipalId'], assignment['PrincipalType'])
            
            for eachAccount in accounts:
                if eachAccount != managementAccount:
                    resolvedAssingmnets['Assignments'].append(
                        {
                            "Sid": str(eachAccount)+str(assignment['PrincipalId'])+str(assignment['PrincipalType'])+str(assignment['PermissionSetName']),
                            "PrincipalId": principalId,
                            "PrincipalType": assignment['PrincipalType'],
                            "PermissionSetName": permissionSetsArn[assignment['PermissionSetName']],
                            "Target": eachAccount
                        }
                    )                
        return True
    except Exception as error:
        log.error("Error: " + str(error))
        exit (1)

def main():
    print("#######################################")
    print("# Starting AWS SSO Assignments Script #")
    print("#######################################\n")
    
    # Put arguments in a global variable to be used latter on in the code
    global ssoInstanceArn
    global permissionSetsArn
    global identitystore
    global resolvedAssingmnets
    global managementAccount
    global credentials
    resolvedAssingmnets = {}
    resolvedAssingmnets['Assignments'] = []

    managementAccount = args.mgmtAccount

    # Assume role in management account
    mgmt_role = args.orgRole
    sts_client = boto3.client('sts', config=config)
    assumed_role_object=sts_client.assume_role(RoleArn=mgmt_role,RoleSessionName="identitycenter-pipeline")
    credentials=assumed_role_object['Credentials']

    # Get Identity Store and SSO Instance ARN
    sso_client = boto3.client('sso-admin', config=config)
    response = sso_client.list_instances()
    ssoInstanceArn = response['Instances'][0]['InstanceArn']
    identitystore = response['Instances'][0]['IdentityStoreId']
    
    permissionSetsArn = get_current_permissionset_list()

    repositoryAssignments = load_assignments_from_file()

    create_assignment_file(permissionSetsArn,repositoryAssignments)

    seen = []
    for eachSID in resolvedAssingmnets['Assignments']:
        if eachSID not in seen:
            seen.append(eachSID)

    with open('assignments.json', 'w') as convert_file:
        convert_file.write(json.dumps(seen))
    
    log.info('Association file successfully created.')
main()