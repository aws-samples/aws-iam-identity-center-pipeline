Execute os scripts na ordem que estão listados, ajustando-os com os path, ids e nomes corretos dos arquivos. Dentro de cada um deles tem uma explicação de como funciona.

1. extracao_assignments/

    * Basicamente, ele varre o console em busca das atribuições das contas, consolida os que possuem o mesmo grupo + PS e remove alguns blocos referentes a recursos do Control Tower. Com isso sempre conseguiremos aplicar um sync com o console caso haja necessidade(muito embora a ideia é que isso não seja mais necessário)

    * generate-account-assignments.py
    * optimization-asssignments-json.py
    * remove-controltower-blocks.py

2. extracao_Ous/

    * list_ou_nested.py

3. extracao_ps/

    * list-ps-unused.py
    * generate-ps.py
    * filter-extract-ps.py
    * change-ps-description.py
    * tag-ps.py