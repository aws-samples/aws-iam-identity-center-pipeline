import os
import json

def carregar_grupos():
    grupos = []
    grupos_dir = '../../templates/groups/'

    if not os.path.exists(grupos_dir):
        print(f"[WARN] Directory {grupos_dir} not found.")
        return []

    for filename in os.listdir(grupos_dir):
        if filename.endswith('.json'):
            path = os.path.join(grupos_dir, filename)
            with open(path, 'r') as f:
                try:
                    dados = json.load(f)
                    if isinstance(dados, list):
                        grupos.extend(dados)
                except Exception as e:
                    print(f"[ERRO] Failed to load {filename}: {e}")
    
    return grupos

def gerar_groups_json(grupos, output_path="groups.json"):
    with open(output_path, 'w') as f:
        json.dump(grupos, f, indent=2)

    if not grupos:
        print("[INFO] No groups found. Empty groups.json generated.")
    else:
        print("[INFO] groups.json generated successfully.")

def main():
    print("#######################################")
    print("#      Starting group processing      #")
    print("#######################################\n")
    
    grupos = carregar_grupos()
    gerar_groups_json(grupos)

if __name__ == "__main__":
    main()