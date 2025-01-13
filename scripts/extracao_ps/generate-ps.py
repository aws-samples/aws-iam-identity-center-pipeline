import boto3
import json


"""
Este script interage com o AWS SSO Admin para listar e obter detalhes sobre os Permission Sets e gerar arquivos de Permission Sets 
para a pipeline. Ele realiza as seguintes operações:

1. Importação de bibliotecas: Importa as bibliotecas `boto3` e `json`.

2. Inicialização do cliente AWS SSO Admin: Inicializa o cliente boto3 para interagir com o serviço AWS SSO Admin.

3. Funções auxiliares:
    - `list_permission_sets(instance_arn)`: Lista todos os Permission Sets associados a uma instância do AWS SSO utilizando um paginador.
    - `get_permission_set_details(instance_arn, permission_set_arn)`: Obtém os detalhes de um Permission Set específico a partir de seu ARN.
    - `get_managed_policies(instance_arn, permission_set_arn)`: Obtém as políticas gerenciadas associadas a um Permission Set específico.

4. Função principal:
    - `process_permission_set(instance_arn, permission_set_arn)`: Processa um Permission Set específico, obtendo seus detalhes, políticas
    gerenciadas e política personalizada.
    - `main()`: Lista e processa todos os Permission Sets associados a uma instância do AWS SSO, salvando os resultados em um arquivo JSON.
    
Este script é útil para gerenciar e auditar os Permission Sets no AWS SSO, facilitando a administração de permissões em ambientes 
multi-conta.
"""

# Inicializar o cliente do AWS SSO Admin
client = boto3.client('sso-admin')


# Função para listar todos os permission sets
def list_permission_sets(instance_arn):
    paginator = client.get_paginator('list_permission_sets')
    permission_sets = []
    for page in paginator.paginate(InstanceArn=instance_arn):
        permission_sets.extend(page['PermissionSets'])
    return permission_sets


# Função para obter detalhes de um permission set
def get_permission_set_details(instance_arn, permission_set_arn):
    response = client.describe_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )
    return response['PermissionSet']


# Função para obter as políticas gerenciadas associadas a um permission set
def get_managed_policies(instance_arn, permission_set_arn):
    response = client.list_managed_policies_in_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )
    return response['AttachedManagedPolicies']


# Função para obter a política personalizada associada a um permission set
def get_custom_policy(instance_arn, permission_set_arn):
    response = client.get_inline_policy_for_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )
    return response.get('InlinePolicy', {})


# Função para processar um permission set
def process_permission_set(instance_arn, permission_set_arn):
    details = get_permission_set_details(instance_arn, permission_set_arn)
    
    # Extrair as informações necessárias
    name = details.get("Name")
    description = details.get("Description")
    session_duration = details.get("SessionDuration")
    managed_policies = get_managed_policies(instance_arn, permission_set_arn)
    custom_policy = get_custom_policy(instance_arn, permission_set_arn)
    
    # Formatar no modelo da pipeline
    formatted_permission_set = {
        "Name": name,
        "Description": description,
        "SessionDuration": session_duration,
        "ManagedPolicies": [policy['Arn'] for policy in managed_policies],
        "CustomPolicy": json.loads(custom_policy) if custom_policy else {}
    }
    
    return formatted_permission_set


# Função principal para listar e processar todos os permission sets
def main():
    # Substitua pelo ARN da instância do AWS SSO
    instance_arn = 'arn:aws:sso:::instance/ssoins-12345678abc'

    permission_sets = list_permission_sets(instance_arn)
    formatted_permission_sets = []
    
    for permission_set_arn in permission_sets:
        formatted_permission_set = process_permission_set(instance_arn, permission_set_arn)
        formatted_permission_sets.append(formatted_permission_set)
    
    # Salvar os permission sets formatados em um novo arquivo JSON
    with open('templates/permissionsets/formatted_permission_sets.json', 'w') as file:
        json.dump(formatted_permission_sets, file, indent=4)
    
    print("Permission sets processados e salvos em formatted_permission_sets.json")


# Executar a função principal
if __name__ == "__main__":
    main()
