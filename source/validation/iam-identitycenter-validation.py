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
## | AWS SSO Templates Validation
## +-----------------------------------

import boto3
import botocore
import json
import argparse
import sys
import os
import logging
import re

"""
Arguments used by the script
--sso-arn: AWS SSO instance ARN. It can be found at AWS SSO > Settings > ARN
--ps-folder: Folder where the permission set files are. Default: '../templates/assignments/'
"""

# Setting arguments
parser = argparse.ArgumentParser(description='AWS SSO Assignment Management')
parser.add_argument('--ps-folder', action="store", dest='psFolder')
parser.add_argument('--assignments-folder', action="store", dest='asFolder')
args = parser.parse_args()

# Logging configuration
logging.basicConfig(format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.DEBUG)
log = logging.getLogger()
log.setLevel(logging.INFO)

def list_permission_set_folder():
    perm_set_dict = {
        eachFile: json.loads(open(os.path.join(args.psFolder, eachFile)).read())
        for eachFile in os.listdir(args.psFolder)
    }
    log.info('Permission Sets successfully loaded from repository files')
    return perm_set_dict


def list_assingment_folder():
    assigments_file = os.listdir(args.asFolder)
    assig_dic = {
        'Assignments': [
            assignment
            for eachFile in assigments_file
            for assignment in json.loads(open(os.path.join(args.asFolder, eachFile)).read())['Assignments']
        ]
    }
    log.info('Assignments successfully loaded from repository files')
    return assig_dic

def validate_unique_permissionset_name():
    list_of_permission_set_name = []
    for permissionSet in permissionsetTemplates:
        list_of_permission_set_name.append(permissionsetTemplates[permissionSet]['Name'])
        
    if len(list_of_permission_set_name) > len(set(list_of_permission_set_name)):
        log.error("There are Permission Set templates with the same name. Please check your templates.")
        exit (1)
    
    log.info("No permission sets with the same name were detected.")
    return True

def validate_unique_assignment_sids():
    list_of_sids = []
    for eachAssignment in assignmentsTemplates['Assignments']:
        list_of_sids.append(eachAssignment['SID'])
    
    if len(list_of_sids) > len(set(list_of_sids)):
        log.error("There are Assignment templates with the same SID. Please check your templates.")
        exit (1)    
    log.info("No asignment templates with the same SID were detected.") 
    return True

def validate_json_policy_format():
    log.info("Analyzing each one of the permission set custom policies.") 
    client = boto3.client('accessanalyzer')
    
    for eachPermissionSet in permissionsetTemplates:
        if 'CustomPolicy' in json.dumps(permissionsetTemplates[eachPermissionSet]):
            thereIsCustomPolicy = json.dumps(permissionsetTemplates[eachPermissionSet]['CustomPolicy'])
            if len(thereIsCustomPolicy) > 2:
                log.info(f"[{eachPermissionSet}] Analyzing custom policy") 
                response = client.validate_policy(locale='EN', policyDocument=json.dumps(permissionsetTemplates[eachPermissionSet]['CustomPolicy']), policyType='IDENTITY_POLICY')
                results = response["findings"]
                
                while "NextToken" in response:
                    response = client.validate_policy(locale='PT_BR', policyDocument=json.dumps(permissionsetTemplates[eachPermissionSet]['CustomPolicy']), policyType='IDENTITY_POLICY', NextToken=response["NextToken"])
                    results.extend(response["findings"])

                for eachFinding in results:
                    if eachFinding['findingType'] == 'ERROR':
                        log.error(f"[{eachPermissionSet}] An error was found in the custom policy: " + str(eachFinding['findingDetails']))
                        exit(1)
                    if eachFinding['findingType'] == 'WARNING':
                        log.warning(f"[{eachPermissionSet}] An issue was found in the custom policy: " + str(eachFinding['findingDetails']))
            else:
                log.info(f"[{eachPermissionSet}] There is no Custom Policy in the permission set. Skipping")

def validate_managed_policies_arn():
    log.info("Analyzing each one of the permission set managed policies.") 
    client = boto3.client('iam')
    for eachPermissionSet in permissionsetTemplates:
        log.info(f"[{eachPermissionSet}] Analyzing AWS managed policies from permission set")

        try:
            for eachManagedPolicy in permissionsetTemplates[eachPermissionSet]['ManagedPolicies']:
                response = client.get_policy(
                    PolicyArn=eachManagedPolicy
                )
        except Exception as error:
            log.error(f"[{eachPermissionSet}] An issue was found in the managed policy. Reason: " + str(error))
            exit (1)

    for eachPermissionSet in permissionsetTemplates:
        log.info(f"[{eachPermissionSet}] Analyzing permission boundary policies from permission set")

        try:
            if ('PermissionBoundary' in permissionsetTemplates[eachPermissionSet]) and (permissionsetTemplates[eachPermissionSet]['PermissionBoundary']):
                if permissionsetTemplates[eachPermissionSet]['PermissionBoundary']['PolicyType'] == 'AWS':
                    response = client.get_policy(
                        PolicyArn=permissionsetTemplates[eachPermissionSet]['PermissionBoundary']['Policy']
                    )
                else:
                    if 'arn:aws' in permissionsetTemplates[eachPermissionSet]['PermissionBoundary']['Policy']:
                        print("dd")
                        log.error(f"[{eachPermissionSet}] Looks like you are using an AWS ARN instead of the name of the policy you want as Permission Boundary. Please review your template")
                        exit (1)
        except Exception as error:
            log.error(f"[{eachPermissionSet}] An issue was found in the AWS managed permission boundary policy. Reason: " + str(error))
            exit (1)            
                

def main():
    print("########################################")
    print("# Starting AWS SSO Template Validation #")
    print("########################################\n")
    
    # Check arguments exists
    if args.asFolder is None or args.psFolder is None:
        print ("Usage: python " + str(sys.argv[0]) +  " --ps-folder <PERMISSIONSET_FOLDER> --assignments-folder <ASSIGNMENTS_FOLDER>")
        print ("Example: python " + str(sys.argv[0]) +  " --ps-folder '../templates/permissionsets/' --assignments-folder '../templates/assignments/'")
        exit()

    
    # Load templates files from folder to global variables
    global permissionsetTemplates
    global assignmentsTemplates
    permissionsetTemplates = list_permission_set_folder()
    assignmentsTemplates = list_assingment_folder()


    # List of controls that will be validated
    validate_unique_permissionset_name()
    validate_unique_assignment_sids()
    validate_json_policy_format()
    validate_managed_policies_arn()
    
    log.info('Congrats! All templates were evaluated without errors! :)')
main()