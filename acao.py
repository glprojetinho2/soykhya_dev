from utils import *
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
import json
import toml
import sys
import os
import re
import argparse

SCRIPTS_PASTA = "scripts/"


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
testar_parser.add_argument("valores", nargs="*", help="Valores dos parâmetros.")

novo_parser = subparsers.add_parser("novo", help="Cria um novo botão.")

lista_parser = subparsers.add_parser("lista", help="Lista botões.")

args = parser.parse_args()


def editar(id: int):
    botao_cru = soyquery(f"select * from tsibta where tipo = 'SC' and idbtnacao = {id}")
    assert len(botao_cru) != 0, "Nenhum botão encontrado com o id " + str(id)
    assert isinstance(botao_cru[0], dict), "Botão cru não é um dicionário"
    botao = BotaoJS(botao_cru[0])
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
    novo_botao_cru = BotaoJS.config_from_toml(javascript, config_toml)
    id_botao = novo_botao_cru.pop("IDBTNACAO")
    mudanca = [{"pk": {"IDBTNACAO": id_botao}, "mudanca": novo_botao_cru}]
    novo_botao_cru["IDBTNACAO"] = id_botao

    soysave("BotaoAcao", mudanca)

    checagem_query = soyquery(f"select * from tsibta where idbtnacao = {id_botao}")[0]
    assert not isinstance(checagem_query, str), checagem_query

    assert (
        checagem_query == novo_botao_cru
    ), f"""\
Não foi possível atualizar o botão.
Diferença: {set(checagem_query.items()) ^ set(novo_botao_cru.items())}
Banco: {json.dumps(checagem_query, indent=4)}
Local: {json.dumps(novo_botao_cru, indent=4)}\
"""


if args.comando == "editar":
    id = args.id
    botao_pasta = os.path.join(SCRIPTS_PASTA, f"{id}")
    if os.path.exists(botao_pasta):
        desfazer = input(
            f"Queres realmente desfazer as alterações que fizeste no botão {id}? [s/N]"
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

elif args.comando == "testar":
    id = args.id
    try:
        gravar(id)
    except FileNotFoundError:
        print("Estás tentando gravar um botão de ação que não foi importado.")
        sys.exit(1)
    botao_cru = soyquery(f"select * from tsibta where tipo = 'SC' and idbtnacao = {id}")
    assert len(botao_cru) != 0, "Nenhum botão encontrado com o id " + str(id)
    assert isinstance(botao_cru[0], dict), "Botão cru não é um dicionário"
    with open("auth", "a"):
        pass
    with open("auth", "r") as file:
        codigo_autorizacao = file.read()
    botao = BotaoJS(botao_cru[0])
    try:
        botao.autorizar(codigo_autorizacao)
    except AutorizacaoFalhou as e:
        print(
            f"Autorização do botão {e.id} falhou com o código '{e.codigo_autorizacao}'."
        )
        requisitar_codigo()
        print("Novo código de autorização requisitado por e-mail.")
        codigo = input("Coloque aqui um novo código de autorização: ")
        assert len(codigo) > 0, "Digite algum código."
        with open("auth", "w") as file:
            file.write(codigo)
        botao.autorizar(codigo)

    parametros = botao.get_parametros()
    if len(parametros) != len(args.valores):
        print("Número errado de argumentos. Ei-los aqui dispostos:")
        for i in range(len(parametros)):
            print(
                f"{i+1} -> {parametros[i]["label"]} [Tipo: '{parametros[i]["paramType"]}']"
            )
    print("Botão chamado com os seguintes valores:")
    for parametro, valor in zip(parametros, args.valores):
        print(f"{parametro["label"]} = '{valor}'")
    print()
    print("Resultado:")
    resultado = botao.ativar(args.valores)
    print(json.dumps(resultado, indent=2))


elif args.comando == "novo":
    resposta = soysave(
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
                    "CONFIG": '<actionConfig><runScript entityName="CabecalhoNota" refreshType="NONE" txManual="false"><![CDATA[mensagem = "Tudo certo";]]></runScript><params><promptParam label="Parâmetro 1" name="PARAM1" required="true" saveLast="false" paramType="S"/><promptParam label="Parâmetro 2" name="PARAM2" required="true" saveLast="false" paramType="DH"/></params></actionConfig>',
                },
            },
        ],
    )
    id = resposta[0]["IDBTNACAO"]
    editar(id)
    print(f"Botão {id} criado e importado.")


elif args.comando == "lista":
    botao_cru = soyquery(
        f"select * from tsibta where tipo = 'SC' order by idbtnacao asc"
    )
    print(json.dumps(botao_cru, indent=4))


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
