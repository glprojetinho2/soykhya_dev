from utils import *
from config import *
from typing import Dict, Any, List
import json
import tempfile
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
import sys
import os
import re
import argparse

parser = argparse.ArgumentParser(
    description="Faça botões de ação sem ter contato com o Soynkhya :)"
)
subparsers = parser.add_subparsers(dest="comando")


def estrutura(entidade: str):
    r = wrapper.estrutura_de_entidade(entidade)
    print(json.dumps(r, indent=2, ensure_ascii=False))


def dicionarios_para_tabela(dicionarios: list[dict[Any, Any]], nome_da_tabela: str):
    tabela = Table(title=nome_da_tabela)
    colunas = dicionarios[0].keys()
    for coluna in colunas:
        tabela.add_column(coluna)
    for dicionario in dicionarios:
        tabela.add_row(*[str(x) for x in dicionario.values()])
    return tabela


query_parser = subparsers.add_parser(
    "query", help="Realiza uma query no banco de dados."
)
query_parser.add_argument("query", type=str, help="Query em SQL.")
query_parser.add_argument(
    "--toml", "-t", action="store_true", help="Mostra os resultados como toml."
)

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
remover_parser = subparsers.add_parser(
    "remover", help="Remove alguma coisa do sistema."
)
remover_parser.add_argument("instancia", type=str, help="Nome exato da instância.")
remover_parser.add_argument(
    "pks",
    nargs="*",
    help="Chaves primárias da linha modificada. (e.g. 'NUCHAVE 1 TABELA TGFCAB EVENTO 10')",
)
info_parser = subparsers.add_parser(
    "info",
    help="Mostra informações sobre tabelas, views, funções, procedures e triggers.",
)
info_parser.add_argument("nome", type=str, help="Nome do objeto.")
info_parser.add_argument(
    "--tabela",
    "-t",
    action="store_true",
    help="Se o nome refere-se a uma tabela. (ESSE É O PADRÃO)",
)
info_parser.add_argument(
    "--view", "-v", action="store_true", help="Se o nome refere-se a uma view."
)
info_parser.add_argument(
    "--funcao", "-f", action="store_true", help="Se o nome refere-se a uma função."
)
info_parser.add_argument(
    "--procedure",
    "-p",
    action="store_true",
    help="Se o nome refere-se a uma procedure.",
)
info_parser.add_argument(
    "--trigger", "-r", action="store_true", help="Se o nome refere-se a um trigger."
)
extrair_parser = subparsers.add_parser(
    "extrair",
    help="Extrai código do DBExplorer.",
)
extrair_parser.add_argument(
    "--views",
    "-v",
    action="store_true",
    help="Extrai o código de todas as views do sistema.",
)
extrair_parser.add_argument(
    "--funcoes", "-f", action="store_true", help="Extrai todas as funções do sistema."
)
extrair_parser.add_argument(
    "--procedures",
    "-p",
    action="store_true",
    help="Extrai todas as procedures do sistema.",
)
extrair_parser.add_argument(
    "--triggers", "-r", action="store_true", help="Extrai todos os triggers do sistema."
)

estrutura_parser = subparsers.add_parser(
    "estrutura", help="Dá-te acesso à estrutura de uma entidade."
)
estrutura_parser.add_argument("entidade", help="Nome da entidade.")

args = parser.parse_args()

if args.comando == "query":
    if args.toml:
        for r in wrapper.soyquery(args.query):
            print("*********************************")
            print(toml.dumps(r))
    else:
        print(json.dumps(wrapper.soyquery(args.query), indent=4, ensure_ascii=False))

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

elif args.comando == "estrutura":
    estrutura(args.entidade)

elif args.comando == "remover":
    assert len(args.pks) % 2 == 0, "Chaves primárias devem estar dispostas em pares."
    chaves = args.pks[::2]
    valores = args.pks[1::2]
    a_remover = dict(zip(chaves, valores))
    wrapper.soyremove(args.instancia, [a_remover])
    print("Removido.")
elif args.comando == "info":
    bandeiras = [args.tabela, args.view, args.funcao, args.procedure, args.trigger]
    tipo = TipoObjetoBD.TABELA
    nome = args.nome.upper()
    console = Console()

    if bandeiras.count(True) > 1:
        print("Especifique um só tipo de objeto.")
    elif args.view:
        tipo = TipoObjetoBD.VIEW
        info = wrapper.info_objeto_bd(nome, tipo)
        sintaxe = Syntax(info["sql"], "sql")
        console.print(dicionarios_para_tabela(info["colunas"], "Colunas"))
        console.print(sintaxe)
    elif args.funcao:
        tipo = TipoObjetoBD.FUNCAO
        info = wrapper.info_objeto_bd(nome, tipo)
        console.print(Syntax(info, "sql"))
    elif args.procedure:
        tipo = TipoObjetoBD.PROCEDURE
        info = wrapper.info_objeto_bd(nome, tipo)
        console.print(Syntax(info, "sql"))
    elif args.trigger:
        tipo = TipoObjetoBD.TRIGGER
        info = wrapper.info_objeto_bd(nome, tipo)
        console.print(Syntax(info, "sql"))
    else:
        info = wrapper.info_objeto_bd(nome, tipo)
        console.print(dicionarios_para_tabela(info, "Colunas"))
elif args.comando == "extrair":
    tudo = wrapper.pegar_corpo(wrapper.soyrequest("DbExplorerSP.getInitData", {}))[
        "objectList"
    ]["itens"]
    objetos = []
    nome_do_tipo_de_objeto = ""
    artigo = "as"
    if args.views:
        tipo = TipoObjetoBD.VIEW
        nome_do_tipo_de_objeto = "views"
        objetos = [x["name"] for x in tudo if x["type"] == "V"]
    elif args.triggers:
        tipo = TipoObjetoBD.TRIGGER
        artigo = "os"
        nome_do_tipo_de_objeto = "triggers"
        objetos = [x["name"] for x in tudo if x["type"] == "R"]
    elif args.funcoes:
        tipo = TipoObjetoBD.FUNCAO
        nome_do_tipo_de_objeto = "funções"
        objetos = [x["name"] for x in tudo if x["type"] == "F"]
    elif args.procedures:
        tipo = TipoObjetoBD.PROCEDURE
        nome_do_tipo_de_objeto = "procedures"
        objetos = [x["name"] for x in tudo if x["type"] == "P"]
    else:
        exit(0)
    os.makedirs(nome_do_tipo_de_objeto, exist_ok=True)
    print(f"{len(objetos)} {nome_do_tipo_de_objeto} encontrad{artigo}.")
    errado = []
    for i in range(len(objetos)):
        nome = objetos[i]
        try:
            print(f"({i}/{len(objetos)})")
            info = wrapper.info_objeto_bd(nome, tipo)
            with open(f"{nome_do_tipo_de_objeto}/{nome}.sql", "w") as f:
                if "sql" in info and isinstance(info, dict):
                    f.write(info["sql"])
                else:
                    f.write(info)
        except AssertionError:
            errado.append(nome)
            print(f"o código de {nome} não pôde ser extraído.")
    if len(errado) > 0:
        print(
            f"{artigo.capitalize()} {nome_do_tipo_de_objeto} {", ".join(errado)} não foram extraídas."
        )
