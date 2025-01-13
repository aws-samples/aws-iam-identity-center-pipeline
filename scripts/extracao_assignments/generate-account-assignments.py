import boto3
import json
import uuid
import logging


"""
Este script é utilizado para gerar um template JSON contendo todas as permissões atribuídas a contas específicas no AWS SSO (AWS Single Sign-On). Ele realiza as seguintes operações:

1. Configuração de logging: Configura o logging para exibir mensagens no terminal e salvar em um arquivo chamado `sso_permissions_log.txt`.

2. Criação de clientes boto3: Cria clientes para os serviços AWS SSO Admin, Identity Store e Organizations.

3. Definição de variáveis globais: Define o ID do Identity Store e dicionários de cache para evitar chamadas repetidas à API.

4. Funções auxiliares:
    - `list_permission_sets(instance_arn, max_results=50)`: Lista todos os Permission Sets associados a uma instância do AWS SSO.
    - `get_permission_assignments(account_id, instance_arn, permission_set_arn=None, max_results=50)`: Obtém as permissões atribuídas a uma conta específica no AWS SSO.
    - `get_principal_name(principal_id, principal_type, identity_store_id=idp_store_id)`: Recebe o principal_id e principal_type (USER ou GROUP) e retorna o nome do principal no AWS Identity Center.
    - `get_permission_set_name(instance_arn, permission_set_arn)`: Obtém o nome de um Permission Set a partir de seu ARN.
    - `list_accounts()`: Lista todas as contas associadas ao AWS Organizations ou SSO.

5. Função principal:
    - `main()`: Define o ARN da instância do AWS SSO, obtém as contas da organização, lista todos os Permission Sets, e para cada Permission Set e conta, 
    obtém as permissões atribuídas e as adiciona ao template final. O template gerado é exibido no log.

Este script é útil para auditar e documentar as permissões atribuídas no AWS SSO, facilitando a gestão e o controle de acesso em ambientes multi-conta.
"""

# Configuração do logging para exibir no terminal e salvar em arquivo
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(),  # Exibe no terminal
                        logging.FileHandler('sso_permissions_log.txt', mode='w')  # Grava no arquivo
                    ])

# Criar cliente para o serviço SSO e Identity Store
client = boto3.client('sso-admin')
idp_store_client = boto3.client('identitystore')
organizations_client = boto3.client('organizations')

idp_store_id = "d-12345678"  # ID do Identity Store do AWS SSO

# Dicionários de cache para evitar chamadas repetidas à API
principal_name_cache = {}
permission_set_name_cache = {}

def list_permission_sets(instance_arn, max_results=50):
    """
    Lista todos os Permission Sets associados a uma instância do AWS SSO.
    """
    permission_sets = []
    next_token = ''

    while True:
        try:
            params = {
                'InstanceArn': instance_arn,
                'MaxResults': max_results,
                'NextToken': next_token
            }

            response = client.list_permission_sets(**params)
            permission_sets.extend(response['PermissionSets'])

            next_token = response.get('NextToken')
            if not next_token:
                break

        except client.exceptions.ClientError as e:
            logging.error(f"Erro ao obter Permission Sets para a instância {instance_arn}: {e}")
            break

    return permission_sets


def get_permission_assignments(account_id, instance_arn, permission_set_arn=None, max_results=50):
    """
    Obtém as permissões atribuídas a uma conta específica no AWS SSO.
    """
    assignments = []
    next_token = ''

    while True:
        try:
            params = {
                'AccountId': account_id,
                'InstanceArn': instance_arn,
                'MaxResults': max_results,
                'PermissionSetArn': permission_set_arn,
                'NextToken': next_token
            }

            response = client.list_account_assignments(**params)

            for assignment in response['AccountAssignments']:
                principal_name = get_principal_name(assignment['PrincipalId'], assignment['PrincipalType'])
                assignment_data = {
                    "SID": f"{str(uuid.uuid4())}",
                    "Target": [account_id],
                    "PrincipalType": assignment['PrincipalType'],
                    "PrincipalId": principal_name,
                    "PermissionSetName": get_permission_set_name(instance_arn, assignment['PermissionSetArn'])
                }
                assignments.append(assignment_data)

            next_token = response.get('NextToken')
            if not next_token:
                break

        except client.exceptions.ClientError as e:
            logging.error(f"Erro ao obter permissões para a conta {account_id}: {e}")
            break

    return assignments


def get_principal_name(principal_id, principal_type, identity_store_id=idp_store_id):
    """
    Recebe o principal_id e principal_type (USER ou GROUP) e retorna o nome do principal
    (usuário ou grupo) no AWS Identity Center (IAM Identity Store).
    """
    # Verifica se o nome do principal já foi armazenado no cache
    if principal_id in principal_name_cache:
        return principal_name_cache[principal_id]

    try:
        if principal_type == 'USER':
            response = idp_store_client.describe_user(
                IdentityStoreId=identity_store_id,
                UserId=principal_id
            )
            principal_name = response['UserName']  # Recupera o username

        elif principal_type == 'GROUP':
            response = idp_store_client.describe_group(
                IdentityStoreId=identity_store_id,
                GroupId=principal_id
            )
            principal_name = response['DisplayName']  # Recupera o DisplayName para grupos

        else:
            raise ValueError("O principal_type deve ser 'USER' ou 'GROUP'.")

        # Armazena o nome do principal no cache
        principal_name_cache[principal_id] = principal_name
        return principal_name

    except idp_store_client.exceptions.ResourceNotFoundException as e:
        logging.error(f"{principal_type} com ID {principal_id} não encontrado. Detalhes do erro: {e}")
        raise

    except Exception as e:
        logging.error(f"Erro ao buscar nome do principal (ID: {principal_id}, tipo: {principal_type}): {e}")
        raise


def get_permission_set_name(instance_arn, permission_set_arn):
    """
    Obtém o nome de um Permission Set a partir de seu ARN.
    """
    # Verifica se o nome do permission set já foi armazenado no cache
    if permission_set_arn in permission_set_name_cache:
        return permission_set_name_cache[permission_set_arn]

    try:
        response = client.describe_permission_set(
            InstanceArn=instance_arn,
            PermissionSetArn=permission_set_arn
        )
        permission_set_name = response['PermissionSet']['Name']

        # Armazena o nome do permission set no cache
        permission_set_name_cache[permission_set_arn] = permission_set_name
        return permission_set_name

    except Exception as e:
        logging.error(f"Erro ao obter nome do Permission Set (ARN: {permission_set_arn}): {e}")
        raise


def list_accounts():
    """
    Lista todas as contas associadas ao AWS Organizations ou SSO.
    """
    accounts = []
    next_token = ''

    while True:
        try:
            response = organizations_client.list_accounts(NextToken=next_token) if next_token else organizations_client.list_accounts()
            accounts.extend(response['Accounts'])

            next_token = response.get('NextToken')
            if not next_token:
                break

        except organizations_client.exceptions.ClientError as e:
            logging.error(f"Erro ao obter contas da organização: {e}")
            break

    return accounts


def main():
    # Defina o ARN da instância do AWS SSO
    instance_arn = "arn:aws:sso:::instance/ssoins-12345678abc"

    # Obter as contas da organização
    accounts = list_accounts()

    # Listar todos os Permission Sets
    permission_sets = list_permission_sets(instance_arn)

    # Estrutura para armazenar os dados
    final_template = {"Assignments": []}

    posicao = 0
    for permission_set_arn in permission_sets:
        logging.info(f"Obtendo permissões para PermissionSet: {permission_set_arn}")

        for account in accounts:
            account_id = account['Id']
            posicao += 1
            logging.info(f"{posicao} - Obtendo permissões para a conta: {account_id}")

            # Obter as permissões atribuídas à conta, filtradas pelo PermissionSetArn
            assignments = get_permission_assignments(account_id, instance_arn, permission_set_arn)

            # Adiciona as permissões ao template final
            final_template["Assignments"].extend(assignments)

    # Exibir o template gerado
    logging.info("Template gerado:")
    logging.info(json.dumps(final_template, indent=4))

    # Se quiser salvar em um arquivo JSON
    with open("templates/assignments/template_associacoes.json", "w") as file:
        json.dump(final_template, file, indent=4)


if __name__ == '__main__':
    main()
