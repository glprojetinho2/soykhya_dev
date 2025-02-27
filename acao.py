from utils import *
from botao import *
from config import *
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
import json
import toml
import sys
import os
import re
import argparse


parser = argparse.ArgumentParser(
    description="Faça botões de ação sem ter contato com o Soynkhya :)"
)
subparsers = parser.add_subparsers(dest="comando")

editar_parser = subparsers.add_parser("editar", help="Edita botão.")
editar_parser.add_argument("id", type=int, help="Id do botão.")

gravar_parser = subparsers.add_parser(
    "gravar", help="Grava alterações feitas no botão."
)
gravar_parser.add_argument("id", type=int, help="Id do botão.")

testar_parser = subparsers.add_parser(
    "testar",
    help=f"""\
Testa o botão de ação.
Alterações serão gravadas.""",
)
testar_parser.add_argument("id", type=int, help="Id do botão.")
testar_parser.add_argument(
    "valores",
    nargs="*",
    help="Valores dos parâmetros. Use None em campos opcionais para ignorá-los.",
)

ativar_parser = subparsers.add_parser(
    "ativar",
    help=f"""\
Ativa o botão de ação.""",
)
ativar_parser.add_argument("id", type=int, help="Id do botão.")
ativar_parser.add_argument(
    "valores",
    nargs="*",
    help="Valores dos parâmetros. Use None em campos opcionais para ignorá-los.",
)

novo_parser = subparsers.add_parser("novo", help="Cria um novo botão.")

lista_parser = subparsers.add_parser("lista", help="Lista botões.")

query_parser = subparsers.add_parser(
    "query", help="Realiza uma query no banco de dados."
)
query_parser.add_argument("query", type=str, help="Query em SQL.")

instancia_parser = subparsers.add_parser(
    "instancia", help="Mostra o nome das instâncias associadas a uma tabela."
)
instancia_parser.add_argument("tabela", type=str, help="Nome da tabela (e.g. TGFCAB)")

tabela_parser = subparsers.add_parser(
    "tabela", help="Mostra o nome da tabela associadas a uma instância."
)
tabela_parser.add_argument(
    "instancia", type=str, help="Nome parcial da instância (e.g. 'Cabecalho')"
)

remover_parser = subparsers.add_parser("remover", help="Remove um botões de ação.")
remover_parser.add_argument("pks", nargs="*", help="pks dos botões")

args = parser.parse_args()


def editar(id: int):
    botao_cru = wrapper.soyquery(
        f"select * from tsibta where tipo = 'SC' and idbtnacao = {id}"
    )
    assert len(botao_cru) != 0, "Nenhum botão encontrado com o id " + str(id)
    assert isinstance(botao_cru[0], dict), "Botão cru não é um dicionário"
    botao = BotaoJS(botao_cru[0], wrapper)
    botao_pasta = os.path.join(SCRIPTS_PASTA, f"{id}")
    os.makedirs(botao_pasta, exist_ok=True)
    javascript_caminho = os.path.join(botao_pasta, "codigo.js")
    config_caminho = os.path.join(botao_pasta, "config.toml")

    with open(javascript_caminho, "w") as file:
        file.write(botao.script)
    with open(config_caminho, "w") as file:
        file.write(botao.config_to_toml())


def gravar(id: int):
    botao_pasta = os.path.join(SCRIPTS_PASTA, f"{id}")
    os.makedirs(botao_pasta, exist_ok=True)
    javascript_caminho = os.path.join(botao_pasta, "codigo.js")
    config_caminho = os.path.join(botao_pasta, "config.toml")
    javascript = open(javascript_caminho, "r").read()
    config_toml = open(config_caminho, "r").read()
    novo_botao_cru = BotaoJS.config_from_toml(id, javascript, config_toml)
    id_botao = novo_botao_cru.pop("IDBTNACAO")
    mudanca = [{"pk": {"IDBTNACAO": id_botao}, "mudanca": novo_botao_cru}]
    novo_botao_cru["IDBTNACAO"] = id_botao

    wrapper.soysave("BotaoAcao", mudanca)

    checagem_query = wrapper.soyquery(
        f"select * from tsibta where idbtnacao = {id_botao}"
    )[0]
    assert not isinstance(checagem_query, str), checagem_query

    assert (
        checagem_query == novo_botao_cru
    ), f"""\
Não foi possível atualizar o botão.
Diferença: {set(checagem_query.items()) ^ set(novo_botao_cru.items())}
Banco: {json.dumps(checagem_query, indent=4)}
Local: {json.dumps(novo_botao_cru, indent=4)}\
"""


def ativar(botao: BotaoJS):
    print(f"Ativando botão '{botao.descricao}'.")
    parametros = botao.get_parametros()
    valores = [None if item == "None" else item for item in args.valores]
    if len(parametros) != len(valores):
        print("Número errado de argumentos. Ei-los aqui dispostos:")
        for i in range(len(parametros)):
            print(
                f"{i+1} -> {parametros[i]["label"]} [Tipo: '{parametros[i]["paramType"]}']"
            )
        sys.exit(1)
    print("Botão chamado com os seguintes valores:")
    for parametro, valor in zip(parametros, valores):
        print(f"{parametro["label"]} = '{valor}'")
    print()
    print("Resultado:")
    resultado = botao.ativar(valores)
    print("Mensagem: ", resultado.get("statusMessage"))
    print("Status: ", resultado.get("status"))


if args.comando == "editar":
    id = args.id
    botao_pasta = os.path.join(SCRIPTS_PASTA, f"{id}")
    if os.path.exists(botao_pasta):
        desfazer = input(
            f"Queres realmente desfazer as alterações que fizeste no botão {id}? [s/N]: "
        )
        if desfazer != "s":
            sys.exit(0)

    editar(id)
    print(f"Botão {id} importado.")


elif args.comando == "gravar":
    id = args.id
    try:
        gravar(id)
    except FileNotFoundError:
        print("Estás tentando gravar um botão de ação que não foi importado.")
        sys.exit(1)

elif args.comando == "ativar":
    id = args.id
    botao_cru = wrapper.soyquery(
        f"select * from tsibta where tipo = 'SC' and idbtnacao = {id}"
    )
    assert len(botao_cru) != 0, "Nenhum botão encontrado com o id " + str(id)
    assert isinstance(botao_cru[0], dict), "Botão cru não é um dicionário"
    codigo_autorizacao = CONFIG.codigo_autorizacao
    botao = BotaoJS(botao_cru[0], wrapper)
    ativar(botao)

elif args.comando == "testar":
    id = args.id
    try:
        gravar(id)
    except FileNotFoundError:
        print("Estás tentando testar um botão de ação que não foi importado.")
        sys.exit(1)
    botao_cru = wrapper.soyquery(
        f"select * from tsibta where tipo = 'SC' and idbtnacao = {id}"
    )
    assert len(botao_cru) != 0, "Nenhum botão encontrado com o id " + str(id)
    assert isinstance(botao_cru[0], dict), "Botão cru não é um dicionário"
    codigo_autorizacao = CONFIG.codigo_autorizacao
    botao = BotaoJS(botao_cru[0], wrapper)
    try:
        botao.autorizar(codigo_autorizacao)
    except AutorizacaoFalhou as e:
        print(
            f"Autorização do botão {e.id} falhou com o código '{e.codigo_autorizacao}'."
        )
        requisitar_codigo(wrapper)
        print("Novo código de autorização requisitado por e-mail.")
        codigo = input("Coloque aqui um novo código de autorização: ")
        assert len(codigo) > 0, "Digite algum código."
        CONFIG.codigo_autorizacao = codigo
        CONFIG.gravar()
        botao.autorizar(codigo)
    ativar(botao)

elif args.comando == "novo":
    resposta = wrapper.soysave(
        "BotaoAcao",
        [
            {
                "foreignKey": {
                    "NOMEINSTANCIA": "CabecalhoNota",
                },
                "mudanca": {
                    "IDBTNACAO": "",
                    "DESCRICAO": "Novo botão",
                    "TIPO": "SC",
                    "CONFIG": f"""<actionConfig><runScript entityName="CabecalhoNota" refreshType="NONE" txManual="false"><![CDATA[\
/// O erro da Soynkhya é horrível.
/// Vamos resolver.
function update(sql) {{
  try {{
    getQuery().update(sql);
  }} catch (e) {{
    mensagem = "Erro na linha: " + (e.lineNumber - 34) + "\\n";
    mensagem += e.message;
    mensagem += sql;
    throw mensagem
  }}
}}
]]></runScript><params><promptParam label="Parâmetro 1" name="PARAM1" required="true" saveLast="false" paramType="S"/><promptParam label="Parâmetro 2" name="PARAM2" required="true" saveLast="false" paramType="DH"/></params></actionConfig>""",
                },
            },
        ],
    )
    id = resposta[0]["IDBTNACAO"]
    editar(id)
    print(f"Botão {id} criado e importado.")


elif args.comando == "lista":
    botao_cru = wrapper.soyquery(
        f"select * from tsibta where tipo = 'SC' order by idbtnacao asc"
    )
    print(json.dumps(botao_cru, indent=4))

elif args.comando == "query":
    print(
        json.dumps(
            wrapper.soyquery(args.query),
            indent=4,
        )
    )

elif args.comando == "instancia":
    instancias = wrapper.soyquery(
        f"select nomeinstancia from tddins where nometab = '{args.tabela.upper()}'"
    )
    assert not isinstance(instancias, str)
    for instancia in instancias:
        print(instancia["NOMEINSTANCIA"])

elif args.comando == "tabela":
    instancias = wrapper.soyquery(
        f"select nometab, nomeinstancia from tddins where upper(nomeinstancia) like '%{args.instancia.upper()}%'"
    )
    assert not isinstance(instancias, str)
    for instancia in instancias:
        print(instancia["NOMETAB"], instancia["NOMEINSTANCIA"])

elif args.comando == "remover":
    for pk in args.pks:
        _resultado = wrapper.soyquery(
            f"select * from tsibta where tipo = 'SC' and idbtnacao = {pk}"
        )
        if len(_resultado) == 0:
            print(f"Não há botão com a pk igual a {pk}")
            sys.exit(1)
        resultado = _resultado[0]
        print(json.dumps(resultado, indent=4))
        resposta = input("Desejas remover o registro acima? [s/N]: ")
        if resposta == "s":
            wrapper.soyremove("BotaoAcao", [{"IDBTNACAO": pk}])
            nao_restou_nada = (
                wrapper.soyquery(
                    f"select count(*) bruh from tsibta where idbtnacao = {pk}"
                )[0]["BRUH"]
                == 0
            )
            assert nao_restou_nada, "Não foi possível deletar componente"

# params = list(root.iter("promptParam"))
# if len(params) > 0:
#     for param in params:
#         print(param.attrib)


# {
#     "IDBTNACAO": 1,
#     "NOMEINSTANCIA": "Instancia",
#     "RESOURCEID": "",
#     "DESCRICAO": "Exemplo",
#     "TIPO": "SC",
#     "CONFIG": "<actionConfig><runScript entityName=\"CabecalhoNota\" refreshType=\"NONE\" txManual=\"false\"><![CDATA[console.log("javascript")]]></runScript><params><promptParam label=\"PARAM\" name=\"PARAM\" required=\"true\" saveLast=\"false\" paramType=\"I\"/></params></actionConfig>",
#     "CODMODULO": null,
#     "ORDEM": null,
#     "CONTROLAACESSO": "N",
#     "TECLAATALHO": null
# }
