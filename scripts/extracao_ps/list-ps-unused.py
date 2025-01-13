import boto3


"""
Este script lista os Permission Sets não utilizados no AWS SSO. Ele realiza as seguintes operações:

1. Importação de bibliotecas: Importa as bibliotecas `boto3`.

2. Configuração do cliente SSO Admin e Organizations: Inicializa os clientes boto3 para interagir com os serviços AWS SSO Admin
 e AWS Organizations.

3. Funções auxiliares:
    - `list_accounts()`: Lista todas as contas na organização, retornando uma lista de IDs de contas.
    - `list_permission_sets(instance_arn)`: Lista todos os Permission Sets associados a uma instância do AWS SSO.

4. Função principal:
    - `main()`: Define o ARN da instância do AWS SSO, obtém a lista de contas, lista todos os Permission Sets 
    e verifica se cada Permission Set está associado a alguma conta. Os Permission Sets não utilizados são exibidos no terminal.

Este script é útil para identificar Permission Sets que não estão sendo utilizados, facilitando a gestão e o controle de 
permissões em ambientes multi-conta.
"""

# Configuração do cliente SSO Admin e ORG
client = boto3.client('sso-admin', region_name='us-east-1')  # Defina a região apropriada
org_client = boto3.client('organizations')


def list_accounts():
    accounts = []
    account_ids = []
    
    # Listar contas na organização
    response = org_client.list_accounts()

    # Adicionar contas à lista
    accounts.extend(response['Accounts'])

    # Verificar se há mais contas (paginação)
    while 'NextToken' in response:
        response = org_client.list_accounts(NextToken=response['NextToken'])
        accounts.extend(response['Accounts'])
    
    for account in accounts:
        account_ids.append(account['Id'])

    return account_ids


def list_permission_sets(instance_arn):
    """Lista todos os PermissionSets de uma instância do AWS Identity Center."""
    response = client.list_permission_sets(InstanceArn=instance_arn)
    return response['PermissionSets']


def list_account_assignments(instance_arn, account_id, permission_set_arn):
    """Verifica se um PermissionSet está associado a uma conta específica."""
    response = client.list_account_assignments(
        InstanceArn=instance_arn,
        AccountId=account_id,
        PermissionSetArn=permission_set_arn
    )

    return response['AccountAssignments']


def main():
    instance_arn = 'arn:aws:sso:::instance/ssoins-12345678abc'  # Substitua pelo seu ARN de instância
    accounts = list_accounts()
    permission_sets = list_permission_sets(instance_arn)  # Lista de PermissionSets

    unused_permission_sets = []

    # Para cada PermissionSet, verifica se ele está associado a alguma conta
    for permission_set in permission_sets:
        permission_set_arn = permission_set  # ARN do PermissionSet
        used = False  # Flag para verificar se o PermissionSet está sendo utilizado

        for account_id in accounts:
            associations = list_account_assignments(instance_arn, account_id, permission_set_arn)
            
            # Se o PermissionSet estiver associado, marque como utilizado
            if associations:
                used = True
                break

        if not used:
            unused_permission_sets.append(permission_set_arn)
    
    print("PermissionSets não utilizados:")
    for ps in unused_permission_sets:
        print(ps)


if __name__ == '__main__':
    main()
