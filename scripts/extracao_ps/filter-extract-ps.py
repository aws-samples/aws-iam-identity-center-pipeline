import json
import os


"""
Este script lê um arquivo JSON contendo Permission Sets formatados e gera arquivos separados para cada Permission Set. 
Ele realiza as seguintes operações:

1. Importação de bibliotecas: Importa as bibliotecas `json` e `os`.

2. Função principal:
    - `generate_permission_set_files(input_file, output_directory)`: Lê o arquivo `formatted_permission_sets.json`, garante que o diretório 
    de saída exista, e para cada Permission Set, gera um arquivo JSON separado no diretório de saída.

3. Atenção aos nomes dos arquivo templates e diretórios

Este script é útil para organizar e separar os Permission Sets em arquivos individuais, facilitando a gestão e o controle de permissões em ambientes multi-conta.
"""

# Função para ler o arquivo formatted_permission_sets.json e gerar arquivos separados
def generate_permission_set_files(input_file, output_directory):
    # Certifique-se de que o diretório de saída existe
    os.makedirs(output_directory, exist_ok=True)
    
    # Ler o arquivo formatted_permission_sets.json
    with open(input_file, 'r') as file:
        permission_sets = json.load(file)
    
    # Para cada permission set, gerar um arquivo separado
    for permission_set in permission_sets:
        name = permission_set['Name']
        output_file = os.path.join(output_directory, f"{name}.json")
        
        with open(output_file, 'w') as outfile:
            json.dump(permission_set, outfile, indent=4)
        
        print(f"Arquivo gerado: {output_file}")


# Executar a função principal
if __name__ == "__main__":
    # Caminho do arquivo de entrada e diretório de saída
    input_file = 'templates/permissionsets/formatted_permission_sets.json'
    output_directory = 'templates/permissionsets/'

    # Executar a função para gerar os arquivos separados
    generate_permission_set_files(input_file, output_directory)
