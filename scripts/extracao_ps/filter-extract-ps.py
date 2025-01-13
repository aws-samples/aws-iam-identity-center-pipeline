import json
import os


"""
This script reads a JSON file containing formatted Permission Sets and generates separate files for each Permission Set.
It performs the following operations:

1. Importing libraries: Imports the `json` and `os` libraries.

2. Main function:
    - `generate_permission_set_files(input_file, output_directory)`: Reads the `formatted_permission_sets.json` file, ensures the output 
    directory exists, and for each Permission Set, generates a separate JSON file in the output directory.

3. Attention to the names of the template files and directories.

This script is useful for organizing and separating Permission Sets into individual files, making it easier to manage and control permissions in multi-account environments.
"""

# Function to read the formatted_permission_sets.json file and generate separate files
def generate_permission_set_files(input_file, output_directory):
    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)
    
    # Read the formatted_permission_sets.json file
    with open(input_file, 'r') as file:
        permission_sets = json.load(file)
    
    # For each permission set, generate a separate file
    for permission_set in permission_sets:
        name = permission_set['Name']
        output_file = os.path.join(output_directory, f"{name}.json")
        
        with open(output_file, 'w') as outfile:
            json.dump(permission_set, outfile, indent=4)
        
        print(f"Generated file: {output_file}")


if __name__ == "__main__":
    # Path of the input file and output directory
    input_file = 'templates/permissionsets/formatted_permission_sets.json'
    output_directory = 'templates/permissionsets/'

    # Execute the function to generate the separate files
    generate_permission_set_files(input_file, output_directory)
