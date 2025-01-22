import json


"""
This script removes blocks from a JSON file of permission assignments that contain the word "ControlTower" in any value. It performs the following operations:

Importing libraries: Imports the json library from Python's standard collection.

Loading the JSON: Loads the JSON file located at templates/assignments/optimized_template_assignments_updated.json.

Filtering the blocks: Filters the blocks that do not contain "ControlTower" in any value, creating a new list of filtered assignments.

Saving the filtered JSON: Saves the filtered JSON to a new file located at templates/assignments/filtered_template_associacoes.json.

This script is useful for removing specific assignments related to ControlTower, facilitating access management and control in multi-account environments.
"""

# Load JSON file
with open('templates/assignments/optimized_template_assignments_updated.json', 'r') as file:
    data = json.load(file)

# Filter the blocks that do not contain "ControlTower" in any value
filtered_assignments = [
    assignment for assignment in data['Assignments']
    if not any("ControlTower" in str(value) for value in assignment.values())
]

# Save filtered JSON to a new file
filtered_data = {"Assignments": filtered_assignments}

with open('templates/assignments/filtered_template_assignments.json', 'w') as file:
    json.dump(filtered_data, file, indent=4)
