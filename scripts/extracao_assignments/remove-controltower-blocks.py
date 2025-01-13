import json


"""
Este script remove blocos de um arquivo JSON de associações de permissões que contêm a palavra "ControlTower" em qualquer valor. Ele realiza as seguintes operações:

1. Importação de bibliotecas: Importa a biblioteca `json` da coleção padrão do Python.

2. Carregamento do JSON: Carrega o arquivo JSON localizado em `templates/assignments/optimized_template_associacoes_updated.json`.

3. Filtragem dos blocos: Filtra os blocos que não contêm "ControlTower" em qualquer valor, criando uma nova lista de associações filtradas.

4. Salvamento do JSON filtrado: Salva o JSON filtrado em um novo arquivo localizado em `templates/assignments/filtered_template_associacoes.json`.

Este script é útil para remover associações específicas relacionadas ao ControlTower, facilitando a gestão e o controle de acesso em ambientes multi-conta.
"""

# Carregar o JSON
with open('templates/assignments/optimized_template_associacoes_updated.json', 'r') as file:
    data = json.load(file)

# Filtrar os blocos que não contêm "ControlTower" em qualquer valor
filtered_assignments = [
    assignment for assignment in data['Assignments']
    if not any("ControlTower" in str(value) for value in assignment.values())
]

# Salvar o JSON filtrado
filtered_data = {"Assignments": filtered_assignments}

with open('templates/assignments/filtered_template_associacoes.json', 'w') as file:
    json.dump(filtered_data, file, indent=4)
