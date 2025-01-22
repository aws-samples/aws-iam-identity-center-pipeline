import os
import json


"""
This script updates the description of Permission Sets in JSON files. It performs the following operations:

1. Importing libraries: Imports the `os` and `json` libraries.

2. Directory definition: Defines the directory containing the JSON files of the Permission Sets.

3. Main function:
    - `process_permission_sets(directory)`: Iterates through all JSON files in the specified directory, checks if the 
    `Description` field is empty or null, and updates the field with "ps-description". The changes are saved in the file itself.

This script is useful to ensure that all Permission Sets have a standard description, facilitating the management and 
control of permissions in multi-account environments.
"""

# JSON template file directory
directory = 'templates/permissionsets/'


# Function to process each JSON file
def process_permission_sets(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r') as file:
                data = json.load(file)
            
            # Check and replace the Description field
            if 'Description' in data and (data['Description'] is None or data['Description'] == ''):
                data['Description'] = "ps-description"
                print(f"Updating file: {file_path}")
                
                # Save changes in the file
                with open(file_path, 'w') as file:
                    json.dump(data, file, indent=4)


if __name__ == "__main__":
    process_permission_sets(directory)

