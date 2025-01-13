import json
from collections import defaultdict


"""
Este script otimiza um arquivo JSON de associações de permissões, agrupando as associações por `PrincipalId` e `PermissionSetName`. Ele realiza as seguintes operações:

1. Importação de bibliotecas: Importa as bibliotecas `json` e `defaultdict` da coleção padrão do Python.

2. Carregamento do JSON: Carrega o arquivo JSON localizado em `templates/assignments/template_associacoes.json`.

3. Agrupamento de associações: Agrupa as associações por `PrincipalId` e `PermissionSetName` utilizando um `defaultdict` aninhado. Cada grupo contém:
    - `SID`: Identificador da associação.
    - `Target`: Lista de alvos associados.
    - `PrincipalType`: Tipo do principal (USER ou GROUP).
    - `PrincipalId`: Identificador do principal.
    - `PermissionSetName`: Nome do Permission Set.

4. Criação de uma nova lista de associações otimizadas: Inicializa uma lista vazia para armazenar as associações otimizadas.

5. Atenção aos nomes dos templates que estão sendo utilizados: `template_associacoes.json` e `optimized_template_associacoes.json`. Se necessário, ajuste os nomes dos arquivos.

Este script é útil para reduzir a redundância e otimizar a estrutura de dados das associações de permissões, facilitando a gestão e o controle de acesso em ambientes multi-conta.
"""

# Carregar o JSON
with open('templates/assignments/template_associacoes.json', 'r') as file:
    data = json.load(file)

# Agrupar por PrincipalId e PermissionSetName
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

# Criar uma nova lista de associações otimizadas
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

# Salvar o JSON otimizado
optimized_data = {"Assignments": optimized_assignments}

with open('templates/assignments/optimized_template_associacoes.json', 'w') as file:
    json.dump(optimized_data, file, indent=4)
