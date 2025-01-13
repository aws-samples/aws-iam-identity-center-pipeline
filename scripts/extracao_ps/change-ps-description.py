import os
import json


"""
Este script atualiza a descrição dos Permission Sets em arquivos JSON. Ele realiza as seguintes operações:

1. Importação de bibliotecas: Importa as bibliotecas `os` e `json`.

2. Definição do diretório: Define o diretório contendo os arquivos JSON dos Permission Sets.

3. Função principal:
    - `process_permission_sets(directory)`: Percorre todos os arquivos JSON no diretório especificado, verifica se o campo 
    `Description` está vazio ou nulo, e atualiza o campo com "ps-description". As alterações são salvas no próprio arquivo.

Este script é útil para garantir que todos os Permission Sets tenham uma descrição padrão, facilitando a gestão
 e o controle de permissões em ambientes multi-conta.
"""

# Diretório contendo os arquivos JSON
directory = 'templates/permissionsets/'


# Função para processar cada arquivo JSON
def process_permission_sets(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r') as file:
                data = json.load(file)
            
            # Verificar e substituir o campo Description
            if 'Description' in data and (data['Description'] is None or data['Description'] == ''):
                data['Description'] = "ps-description"
                print(f"Atualizando arquivo: {file_path}")
                
                # Salvar as alterações no arquivo
                with open(file_path, 'w') as file:
                    json.dump(data, file, indent=4)


if __name__ == "__main__":
    process_permission_sets(directory)

