import browsercookie
import xml.etree.ElementTree as ET
import requests
import argparse
import toml
import os
import json
import configparser
from utils import *
from typing import Dict, Any, List


class AutorizacaoFalhou(Exception):
    def __init__(self, id: int, codigo_autorizacao: str):
        self.id = id
        self.codigo_autorizacao = codigo_autorizacao
        self.message = (
            f"Não foi possível autorizar {id} com o código '{codigo_autorizacao}'"
        )
        super().__init__(self.message)


class BotaoJS:
    def __init__(self, botao_cru: dict[str, Any], wrapper: Soywrapper):
        self.wrapper = wrapper
        self.cru = botao_cru
        assert botao_cru["TIPO"] == "SC", "Botão não foi feito em Javascript"
        assert botao_cru["CONFIG"] is not None, "Botão sem configuração"
        self.__runScript = self.configuracao.find("runScript")
        assert self.__runScript is not None, "runScript é None"

    @property
    def modulo(self) -> int | None:
        return self.cru["CODMODULO"]

    @property
    def ordem(self) -> int | None:
        return self.cru["ORDEM"]

    @property
    def controla_acesso(self) -> str:
        return self.cru["CONTROLAACESSO"]  # "S" ou "N"

    @property
    def tecla_de_atalho(self) -> str | None:
        return self.cru["TECLAATALHO"]

    @property
    def tipo_atualizacao(self):
        return self.__runScript.attrib["refreshType"]

    @property
    def controle_transacao(self):
        return self.__runScript.attrib["txManual"]

    @property
    def script(self):
        return self.__runScript.text or ""

    @property
    def instancia(self) -> str:
        return self.cru["NOMEINSTANCIA"]

    @property
    def filtro_de_telas(self) -> str | None:
        return self.cru["RESOURCEID"]

    @property
    def descricao(self) -> str:
        return self.cru["DESCRICAO"]

    @property
    def configuracao(self):
        return ET.fromstring(self.cru["CONFIG"])

    @property
    def id(self):
        return self.cru["IDBTNACAO"]

    def get_parametros(self) -> list[dict[str, str]]:
        return [x.attrib for x in self.configuracao.iter("promptParam")]

    def config_to_toml(self) -> str:
        """
        Coloca todas as informações presentes neste botão num toml,
        exceto o javascript.
        """
        config = f"""\
instancia = "{self.instancia}"
{"" if self.modulo else "# "}modulo = "{self.modulo}"
# Determina as telas que mostrarão o botão.
{"" if self.filtro_de_telas else "# "}filtro_de_telas = "{self.filtro_de_telas}"
# Nome do botão.
descricao = "{self.descricao}"
# Pode ser "S" ou "N"
controla_acesso = "{self.controla_acesso}"
{"" if self.ordem else "# "}ordem = "{self.ordem}"
{"" if self.tecla_de_atalho else "# "}tecla_de_atalho = "{self.tecla_de_atalho}"
# Tipo de atualização. Valores possíveis:
# "NONE" = Não recarregar nada
# "ALL" = Recarregar toda a grade
# "SEL" = Recarregar os registros selecionados
# "PARENT" = Recarregar o registro pai (quando ele existir)
# "MASTER" = Recarregar o registro principal (quando ele existir)
tipo_atualizacao = "{self.tipo_atualizacao}"
# Controle manual de transações. Pode ser `false` ou `true`
controle_transacao = "{self.controle_transacao}"
# [[parametros]]
# label = "Nome bonitinho"
# name = "NOME_USADO_NO_CODIGO"
# required = "true" ou "false"
# saveLast = "true" ou "false"
# paramType = "I" = Inteiro, "S" = Texto, "D" = Decimal, "DT" = Data,
# "DH" = Data e hora, "B" = Boolean, "ENTITY" = Linha no banco de dados
# "OS" = Opções
# Se o paramType for "ENTITY", o campo abaixo é obrigatório
# entityName="Nome da entidade"
# Se o paramType for "D", o campo abaixo é obrigatório
# precision = 4 # número de casas decimais
# Se o paramType for "OS", o campo abaixo é obrigatório
# options = "opções"
"""
        parametros = self.get_parametros()

        parametros_toml = toml.dumps({"parametros": parametros}).strip()
        config += parametros_toml
        return config.strip()

    @classmethod
    def config_from_toml(cls, id: str, javascript: str, config_toml: str):
        """
        Reconstitui um botão de ação.
        """
        config_obj = toml.loads(config_toml)
        assert config_obj["controla_acesso"] in ("S", "N")
        assert config_obj["controle_transacao"] in ("false", "true")
        assert config_obj["tipo_atualizacao"] in (
            "NONE",
            "ALL",
            "SEL",
            "PARENT",
            "MASTER",
        )
        for parametro in config_obj["parametros"]:
            assert parametro["paramType"] in (
                "I",
                "S",
                "D",
                "DT",
                "DH",
                "B",
                "ENTITY",
                "OS",
            )
            if parametro["paramType"] == "ENTITY":
                assert (
                    "entityName" in parametro
                ), f"""
'{parametro["label"]}' precisa de um valor para 'entityName'.
"""
            elif parametro["paramType"] == "D":
                assert (
                    "precision" in parametro
                ), f"""\
'{parametro["label"]}' precisa de um valor para 'precision'.
Esse valor determinará o número de casas decimais consideradas pelo campo.\
"""
            elif parametro["paramType"] == "OS":
                assert (
                    "options" in parametro
                ), f"""
'{parametro["label"]}' precisa de um valor para 'options'.\
"""
            assert parametro["required"] in ("false", "true")
            assert parametro["saveLast"] in ("false", "true")

        actionConfig = ET.Element("actionConfig")

        runScript = ET.SubElement(actionConfig, "runScript")
        runScript.attrib = {
            "entityName": config_obj["instancia"],
            "refreshType": config_obj["tipo_atualizacao"],
            "txManual": config_obj["controle_transacao"],
        }
        runScript.text = javascript

        params = ET.SubElement(actionConfig, "params")
        for parametro in config_obj["parametros"]:
            parametro_str = {key: str(value) for key, value in parametro.items()}
            ET.SubElement(params, "promptParam", parametro_str)
        config_xml = ET.tostring(actionConfig, encoding="unicode")
        return {
            "IDBTNACAO": id,
            "NOMEINSTANCIA": config_obj["instancia"],
            "RESOURCEID": config_obj.get("filtro_de_telas"),
            "DESCRICAO": config_obj["descricao"],
            "TIPO": "SC",
            "CONFIG": config_xml,
            "CODMODULO": config_obj.get("modulo"),
            "ORDEM": config_obj.get("ordem"),
            "CONTROLAACESSO": config_obj["controla_acesso"],
            "TECLAATALHO": config_obj.get("tecla_de_atalho"),
        }

    def ativar(self, args: list[str | int | None]):
        """
        Ativa o botão com os argumentos especificados no `args`.
        Talvez seja necessário autorizar o uso do botão com o método
        `autorizar`.
        """
        parametros = self.get_parametros()
        id = self.id
        assert len(parametros) == len(
            args
        ), "Número de parâmetros diferente do número de valores."
        params = []
        for parametro, valor in zip(parametros, args):
            params.append(parametro_para_acionamento(parametro, valor))
        r = self.wrapper.soyrequest(
            "ActionButtonsSP.executeScript",
            {
                "runScript": {
                    "actionID": id,
                    "masterEntityName": "CabecalhoNota",
                    "params": {"param": params},
                },
            },
        )
        try:
            response = r.json()
        except json.JSONDecodeError:
            return r.text
        return response

    def autorizar(self, codigo: str):
        """
        Autoriza o uso do botão.
        """
        r = self.wrapper.soyrequest(
            "ACSP.icl", {"tipo": "BTA", "ids": [{"id": self.id}], "codigo": codigo}
        )
        status = r.json()["status"]
        if status == "0":
            raise AutorizacaoFalhou(self.id, codigo)
        return r


def requisitar_codigo(wrapper: Soywrapper):
    wrapper.soyrequest("ACSP.ecl", {"tipo": "BTA"})


def parametro_para_acionamento(
    param: dict[str, str], valor: str | int
) -> dict[str, str | int]:
    equivalencia = {
        "I": "I",
        "S": "S",
        "D": "F",
        "DT": "D",
        "DH": "D",
        "B": "S",
        "ENTITY": "S",
        "OS": "OS",
        "S": "S",
        "DH": "D",
    }
    return {
        "type": equivalencia[param["paramType"]],
        "paramName": param["name"],
        "$": valor,
    }
