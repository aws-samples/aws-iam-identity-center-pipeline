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
import traceback

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



def list_all_accounts():
    client = boto3.client('organizations')

    response = client.list_accounts()
    results = response["Accounts"]
    while "NextToken" in response:
        response = client.list_accounts(NextToken=response["NextToken"]) 
        results.extend(response["Accounts"])

    accounts = []
    for eachAccount in results:
        if eachAccount['Status'] == 'ACTIVE':
            accounts.append(eachAccount['Id'])
    
    return accounts

def list_active_accounts_in_ou_not_nested(ou_id):
    client = boto3.client('organizations')

    def get_active_accounts_in_ou(ou_id):
        active_accounts = []
        paginator = client.get_paginator('list_accounts_for_parent')
        
        for page in paginator.paginate(ParentId=ou_id):
            for account in page['Accounts']:
                if account['Status'] == 'ACTIVE':
                    active_accounts.append(account['Id'])
        
        return active_accounts
    
    return get_active_accounts_in_ou(ou_id)

def list_accounts_in_ou_nested(ou_id):
    client = boto3.client('organizations')
    def get_accounts_in_ou(ou_id):
        accounts = []
        paginator = client.get_paginator('list_accounts_for_parent')
        
        for page in paginator.paginate(ParentId=ou_id):
            for account in page['Accounts']:
                if account["Status"] == "ACTIVE":
                    accounts.append(account['Id'])
        
        return accounts
    
    def get_nested_ous(ou_id):
        ous = []
        paginator = client.get_paginator('list_organizational_units_for_parent')
        
        for page in paginator.paginate(ParentId=ou_id):
            for ou in page['OrganizationalUnits']:
                ous.append(ou['Id'])
        
        return ous
    
    def list_all_accounts_recursive(ou_id):
        all_accounts = get_accounts_in_ou(ou_id)
        nested_ous = get_nested_ous(ou_id)
        
        for nested_ou_id in nested_ous:
            all_accounts.extend(list_all_accounts_recursive(nested_ou_id))
        
        return all_accounts

    return list_all_accounts_recursive(ou_id)

def list_accounts_in_ou(ouid):
    client = boto3.client('organizations', config=config, aws_access_key_id=credentials['AccessKeyId'], aws_secret_access_key=credentials['SecretAccessKey'], aws_session_token=credentials['SessionToken'])
    root_id = client.list_roots()['Roots'][0]['Id']
    
    try:
        account_list = []
        if 'ou-' in ouid:
            if ':*' in ouid:
                log.info(f"[OU: {ouid}] Nested association found (:*). Listing accounts inside nested OUs.")
                account_list = list_accounts_in_ou_nested(str(ouid.split(":")[0]))
            else:
                account_list = list_active_accounts_in_ou_not_nested(ouid)
        elif root_id in ouid or 'Root' in ouid:
            account_list = list_all_accounts()      
        else:
            log.error('Target is not in valid format.')
            exit (1)
                
    except Exception as error:
        log.error('It was not possible to list accounts from Organization Unit. Reason: ' + str(error))
        log.error(traceback.format_exc())
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
        log.error(traceback.format_exc())

def resolve_targets(eachCurrentAssignments):
    try:
        account_list = []
        log.info(f"[SID: {eachCurrentAssignments['SID']}] Resolving target in accounts")
        for eachTarget in eachCurrentAssignments['Target']:
            pattern = re.compile(r'\d{12}') # Regex for AWS Account Id
            if pattern.match(eachTarget.split(":")[1]):
                account_list.append(eachTarget.split(":")[1])
            else:
                account_list.extend(list_accounts_in_ou(eachTarget.split(":", 1)[1]))                
        return account_list
    except Exception as error:
        log.error(f"[SID: {eachCurrentAssignments['SID']}] It was not possible to resolve the targets from assignment. Reason: " + str(error))
        log.error(traceback.format_exc())


def create_assignment_file(permissionSetsArn,repositoryAssignments):
    log.info('Creating assignment file')
    
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
        log.error(traceback.format_exc())
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
    
    log.info('Association file created.')
main()