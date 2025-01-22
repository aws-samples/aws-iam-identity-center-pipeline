import json
from collections import defaultdict


"""
This script optimizes a JSON file of permission assignments by grouping the assignments by PrincipalId and PermissionSetName. It performs the following operations:

Importing libraries: Imports the json and defaultdict libraries from Python's standard collection.

Loading the JSON: Loads the JSON file located at templates/assignments/template_assignments.json.

Grouping assignments: Groups the assignments by PrincipalId and PermissionSetName using a nested defaultdict. Each group contains:

SID: Assignment identifier.
Target: List of associated targets.
PrincipalType: Type of the principal (USER or GROUP).
PrincipalId: Principal's identifier.
PermissionSetName: Name of the Permission Set.
Creating a new list of optimized assignments: Initializes an empty list to store the optimized assignments.

Attention to the template names being used: template_assignments.json and optimized_template_assignments.json. If necessary, adjust the file names.

This script is useful for reducing redundancy and optimizing the data structure of permission assignments, facilitating access management and control in multi-account environments.
"""

# Load the JSON file
with open('templates/assignments/template_assignments.json', 'r') as file:
    data = json.load(file)

# Grouping for PrincipalId and PermissionSetName
grouped = defaultdict(lambda: defaultdict(lambda: {
    "SID": None,
    "Target": [],
    "PrincipalType": None,
    "PrincipalId": None,
    "PermissionSetName": None
}))

for assignment in data['Assignments']:
    principal_id = assignment['PrincipalId']
    permission_set_name = assignment['PermissionSetName']
    if grouped[principal_id][permission_set_name]["SID"] is None:
        grouped[principal_id][permission_set_name]["SID"] = assignment["SID"]
    grouped[principal_id][permission_set_name]["Target"].extend(assignment["Target"])
    grouped[principal_id][permission_set_name]["PrincipalType"] = assignment["PrincipalType"]
    grouped[principal_id][permission_set_name]["PrincipalId"] = principal_id
    grouped[principal_id][permission_set_name]["PermissionSetName"] = permission_set_name

# Create the new list of optimizations assignments
optimized_assignments = []

for principal_id, permissions in grouped.items():
    for permission_set_name, details in permissions.items():
        optimized_assignments.append({
            "SID": details["SID"],
            "Target": details["Target"],
            "PrincipalType": details["PrincipalType"],
            "PrincipalId": details["PrincipalId"],
            "PermissionSetName": details["PermissionSetName"]
        })

# Save optimized JSON file
optimized_data = {"Assignments": optimized_assignments}

with open('templates/assignments/optimized_template_assignments.json', 'w') as file:
    json.dump(optimized_data, file, indent=4)
