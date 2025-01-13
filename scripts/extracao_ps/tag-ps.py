import boto3


"""
Este script interage com o AWS SSO Admin para listar Permission Sets e suas tags. Ele realiza as seguintes operações:

1. Importação de bibliotecas: Importa a biblioteca `boto3`.

2. Inicialização do cliente AWS SSO Admin: Inicializa o cliente boto3 para interagir com o serviço AWS SSO Admin.

3. Funções auxiliares:
    - `list_permission_sets(instance_arn)`: Lista todos os Permission Sets associados a uma instância do AWS SSO utilizando um paginador.
    - `list_tags_for_permission_set(instance_arn, permission_set_arn)`: Obtém as tags associadas a um Permission Set específico.
    - `get_permission_set_name(instance_arn, permission_set_arn)`: Obtém o nome de um Permission Set específico a partir de seu ARN.

    4. Função principal:
    - `main()`: Lista todos os Permission Sets associados a uma instância do AWS SSO, verifica se possuem 
    a tag SSOPipeline com valor true e, caso contrário, solicita a adição da tag. O script exibe os Permission Sets
    que não possuem a tag e solicita confirmação para adicionar a tag.
    
Este script é útil para gerenciar e auditar os Permission Sets e suas tags no AWS SSO, facilitando a administração 
de permissões em ambientes multi-conta.
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


# Função para obter as tags de um permission set
def list_tags_for_permission_set(instance_arn, permission_set_arn):
    response = client.list_tags_for_resource(
        InstanceArn=instance_arn,
        ResourceArn=permission_set_arn
    )

    return response['Tags']


# Função para obter o nome de um permission set
def get_permission_set_name(instance_arn, permission_set_arn):
    response = client.describe_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )

    return response['PermissionSet']['Name']


# Função para adicionar a tag SSOPipeline a um permission set
def tag_permission_set(instance_arn, permission_set_arn):
    client.tag_resource(
        InstanceArn=instance_arn,
        ResourceArn=permission_set_arn,
        Tags=[
            {
                'Key': 'SSOPipeline',
                'Value': 'true'
            }
        ]
    )


# Função principal
def main():
    instance_arn = 'arn:aws:sso:::instance/ssoins-12345678abc'  # Substitua pelo seu ARN de instância
    permission_sets = list_permission_sets(instance_arn)  # Lista de PermissionSets

    permission_sets_to_tag = []
    aws_permission_sets_to_tag = []

    # Para cada PermissionSet, verifica as tags
    for permission_set_arn in permission_sets:
        name = get_permission_set_name(instance_arn, permission_set_arn)
        
        tags = list_tags_for_permission_set(instance_arn, permission_set_arn)
        has_ssopipeline_tag = any(tag['Key'] == 'SSOPipeline' and tag['Value'] == 'true' for tag in tags)

        if not has_ssopipeline_tag:
            if name.startswith('AWS'):
                aws_permission_sets_to_tag.append((permission_set_arn, name))
            else:
                permission_sets_to_tag.append((permission_set_arn, name))

    # Mostrar os permission sets que não possuem a tag SSOPipeline com valor true
    print("Permission sets que não possuem a tag SSOPipeline com valor true:")
    
    for permission_set_arn, name in permission_sets_to_tag:
        print(f"{name} ({permission_set_arn})")

    # Solicitar confirmação para adicionar a tag aos permission sets sem prefixo AWS
    confirm = input("Deseja adicionar a tag SSOPipeline=true a todos esses permission sets? (yes/no): ")

    if confirm.lower() == 'yes':
        for permission_set_arn, name in permission_sets_to_tag:
            tag_permission_set(instance_arn, permission_set_arn)
            print(f"Tag adicionada ao permission set: {name} ({permission_set_arn})")

    # Mostrar os permission sets com prefixo AWS que não possuem a tag SSOPipeline com valor true
    print("\nPermission sets com prefixo AWS que não possuem a tag SSOPipeline com valor true:")
    
    for permission_set_arn, name in aws_permission_sets_to_tag:
        print(f"{name} ({permission_set_arn})")

    # Solicitar confirmação para adicionar a tag aos permission sets com prefixo AWS
    confirm_aws = input("Deseja adicionar a tag SSOPipeline=true a todos esses permission sets com prefixo AWS? (yes/no): ")

    if confirm_aws.lower() == 'yes':
        for permission_set_arn, name in aws_permission_sets_to_tag:
            tag_permission_set(instance_arn, permission_set_arn)
            print(f"Tag adicionada ao permission set com prefixo AWS: {name} ({permission_set_arn})")


if __name__ == "__main__":
    main()
