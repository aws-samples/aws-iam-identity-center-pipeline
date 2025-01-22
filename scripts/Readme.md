Run the scripts in the order they are listed, adjusting them with the correct paths, IDs, and file names. Inside each of them, there is an explanation of how it works.

1. extract_assignments/

    * Basically, it scans the console for account assignments, consolidates those with the same group + PS, and removes some blocks related to Control Tower resources. With this, we can always apply a sync with the console if necessary (although the idea is that this is no longer needed).

    * generate-account-assignments.py
    * optimization-asssignments-json.py
    * remove-controltower-blocks.py

2. extract_Ous/

    * list_ou_nested.py

3. extract_ps/

    * list-ps-unused.py
    * generate-ps.py
    * filter-extract-ps.py
    * change-ps-description.py
    * tag-ps.py