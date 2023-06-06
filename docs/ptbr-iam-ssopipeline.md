## AWS Single Sign On Pipeline (access-as-a-code)
Este pipeline tem como objetivo gerenciar permissões do Identity Center e suas associações como código usando templates JSON. Neste pipeline é possível:
* Criar, apagar e atualizar Permission Sets como código
* Criar, atualizar ou apagar associações dos Permission Sets nas contas AWS ou nas Organization Units do AWS Organization com usuários do seu IdP

Este pipeline considera novas contas criadas, fazendo com que novas contas herdem as permissões estabelecidas como código. 


## Sobre os templates
Este pipeline gerencia as permissões via templates JSON. Existem dois tipos de templates:

### Template Permission Set
Este template JSON permite gerenciar o Permission Set. Cada arquivo representa um permission set no AWS Identity Center. Os campos que precisam ser preenchidos são:

```
{
    "Name": "ProductionAccess",
    "Description": "Production access in AWS",
    "SessionDuration": "PT4H",
    "ManagedPolicies": [
        "arn:aws:iam::aws:policy/job-function/ViewOnlyAccess"
    ],
    "CustomPolicy": {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ProductionAllowAccess",
                "Effect": "Allow",
                "Action": [
                    "ec2:*",
                ],
                "Resource": "*"
            }
        ]
    }
}
```

* **Name**
    * Tipo: String
    * Pode ser alterado depois de criado: : Não
    * Descrição: Nome do permission set no Identity Center. Este campo precisa ser único e não pode ser alterado
* **Description**
    * Tipo: String
    * Pode ser alterado depois de criado: : Sim
    * Descrição: Descrição do permission set
* **SessionDuration**
    * Tipo: String
    * Pode ser alterado depois de criado: : Sim
    * Descrição: Duração da sessão da role no formato  ISO-8601 
* **ManagedPolicies**
    * Tipo: List (string)
    * Pode ser alterado depois de criado: : Sim
    * Descrição: Lista de managed policies ARN
* **CustomPolicy**
    * Tipo: String (JSON)
    * Pode ser alterado depois de criado: : Sim
    * Descrição: Inline policy

### Assignment Templates
Este template JSON permite gerenciar o relacionamento entre Principal vs. Account vs. PermissionSet. Os seguintes campos precisam ser preenchidos:
```
{
    "Assignments": [
        {
            "SID": "Assingment01",
            "Target": [
                "ou-ag00-uv9hvcz2"
            ],
            "PrincipalType": "GROUP",
            "PrincipalId": "LAB-NetworkAdministrator@domain.internal",
            "PermissionSetName": "NetworkAdministrator"
        }
    ]
}
```

* **SID**
    * Tipo: String
    * Pode ser alterado depois de criado: : Não
    * Descrição: Identificador único do assignment. Precisa ser único e não pode ser alterado.
* **Target**
    * Tipo: List (string)
    * Pode ser alterado depois de criado: : Sim
    * Descrição: Alvo da associação. Suporta conta, OU ou RootID (para associar em todas as contas)
* **PrinicipalType**
    * Tipo: String
    * Pode ser alterado depois de criado: : Não
    * Descrição: Tipo do principal do IdP. Pode ser GROUP ou USER
* **PrinicipalId**
    * Tipo: String
    * Pode ser alterado depois de criado: : Não
    * Descrição: Nome do usuário na IdentityStore quer receberá o assigment.

## Instruções gerais
* Este pipeline irá gerenciar (criar, atualizar, deletar) somente Permission Sets com a tag **SSOPipeline:true**
* Você pode ter multiplos arquivos de templates na mesma pasta
* Quando você exclui um template, o pipeline irá excluir os assignments / permission sets
* Se você excluir um elemento da lista de "Assignments" do arquivo template de assignments, o pipeline irá excluir a permissão refernete aquele bloco
* Não é possível excluir um permission set associado a uma conta AWS
* Não é possível criar permission sets com o mesmo nome
* Não é possível criar assignments com o mesmo SID

## Arquitetura do pipeline
O pipeline é sensibilizado nas duas condições;
* **Commit no CodeCommit**: toda vez que um novo commit é feito nos arquivos de template
* **Conta criada / movimentada**: toda vez que uma nova conta é criada no Control Tower ou movimetada de OU

### Estágios do pipeline
* **Source**: Código fonte
* **TemplateValidation**: Valida os templates da pasta /templates/, incluindo:
    * Sintaxe das custom inline policies (JSON)
    * Se os SIDs são únicos
    * Se os nomes dos permissions sets são únicos
    * Se as ARNs das managed policies são válidas
* **Approval**: Aprovação manual para promover as mudanças
* **PermissionSet**: Implementa mudanças dos permission set
* **PermissionSet**: Implementa mudanças dos assignments (principal vs. target vs. permissionSet)


![Architecture](pictures/iam-ssopipeline.png)