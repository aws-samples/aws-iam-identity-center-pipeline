import boto3
import argparse
import json


"""
Este script lista os IDs das Organizational Units (OUs) aninhadas no AWS Organizations. Ele realiza as seguintes operações:

1. Importação de bibliotecas: Importa as bibliotecas `boto3`, `argparse` e `json`.

2. Inicialização do cliente AWS Organizations: Inicializa o cliente boto3 para interagir com o serviço AWS Organizations.

3. Funções auxiliares:
    - `list_nested_ou_ids(parent_ou_id)`: Lista os IDs das OUs aninhadas a partir de um OU pai fornecido. Utiliza um paginador 
    para percorrer todas as OUs aninhadas e adiciona seus IDs a uma lista.

4. Função principal:
    - `main()`: Recebe o ID da OU pai como parâmetro, chama a função `list_nested_ou_ids` para obter os IDs das OUs aninhadas 
    e imprime a lista resultante em formato JSON com indentação.

Este script é útil para identificar e listar todas as OUs aninhadas dentro de uma OU específica, facilitando a gestão de 
estruturas organizacionais do AWS Organizations.
"""

# Inicializar o cliente AWS Organizations
client = boto3.client('organizations')


def list_nested_ou_ids(parent_ou_id):
    nested_ou_ids = [parent_ou_id]

    def list_ou_children(parent_id):
        paginator = client.get_paginator("list_organizational_units_for_parent")
        for page in paginator.paginate(ParentId=parent_id):
            for ou in page["OrganizationalUnits"]:
                nested_ou_ids.append(ou["Id"])
                list_ou_children(ou["Id"])

    list_ou_children(parent_ou_id)
    return nested_ou_ids


def main():
    parser = argparse.ArgumentParser(description="List nested OU IDs.")
    parser.add_argument("ou_id", type=str, help="The ID of the parent OU.")
    args = parser.parse_args()

    nested_ou_ids = list_nested_ou_ids(args.ou_id)
    print(json.dumps(nested_ou_ids, indent=2))

if __name__ == "__main__":
    main()
