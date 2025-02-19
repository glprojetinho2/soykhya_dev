import browsercookie
import xml.etree.ElementTree as ET
import requests
import argparse
import toml
import json
from typing import Dict, Any, List

cookiejar = browsercookie.firefox()
# TODO: excluir os inúteis
sankhya_cookies = {"mge": "", "mgefin": "", "mgecom": ""}
for __i in cookiejar:
    if __i.name == "JSESSIONID":
        sankhya_cookies[__i.path.strip("/")] = __i.value

COOKIES_MGE = {"JSESSIONID": sankhya_cookies["mge"]}
URL = "https://soldasul.sankhyacloud.com.br/mge/service.sbr"
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Connection": "keep-alive",
    "Content-Type": "application/json; charset=UTF-8",
}


class ErroDoSoynkhya(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class AutorizacaoFalhou(Exception):
    def __init__(self, id: int, codigo_autorizacao: str):
        self.id = id
        self.codigo_autorizacao = codigo_autorizacao
        self.message = (
            f"Não foi possível autorizar {id} com o código '{codigo_autorizacao}'"
        )
        super().__init__(self.message)


class BotaoJS:
    def __init__(self, botao_cru: dict[str, Any]):
        assert botao_cru["TIPO"] == "SC", "Botão não foi feito em Javascript"
        assert botao_cru["CONFIG"] is not None, "Botão sem configuração"
        self.id: int = botao_cru["IDBTNACAO"]
        self.instancia: str = botao_cru["NOMEINSTANCIA"]
        self.filtro_de_telas: str | None = botao_cru["RESOURCEID"]
        self.descricao: str = botao_cru["DESCRICAO"]
        self.configuracao = ET.fromstring(botao_cru["CONFIG"])
        runScript = self.configuracao.find("runScript")
        assert runScript is not None, "runScript in None"
        self.tipo_atualizacao = runScript.attrib["refreshType"]
        self.controle_transacao = runScript.attrib["txManual"]
        self.script = runScript.text or ""
        self.modulo: int | None = botao_cru["CODMODULO"]
        self.ordem: int | None = botao_cru["ORDEM"]
        self.controla_acesso: str = botao_cru["CONTROLAACESSO"]  # "S" ou "N"
        self.tecla_de_atalho: str | None = botao_cru["TECLAATALHO"]

    def get_parametros(self) -> list[dict[str, str]]:
        return [x.attrib for x in self.configuracao.iter("promptParam")]

    def config_to_toml(self) -> str:
        """
        Coloca todas as informações presentes neste botão num toml,
        exceto o javascript.
        """
        config = f"""
# NÃO MUDE ESTE VALOR
id = {self.id}
instancia = "{self.instancia}"
"""
        if self.modulo:
            config += f"""\
modulo = "{self.modulo}"
"""
        else:
            config += f"""\
# modulo = "{self.modulo}"
"""

        if self.filtro_de_telas:
            config += f"""\
# Determina as telas que mostrarão o botão.
filtro_de_telas = "{self.filtro_de_telas}"
"""
        else:
            config += f"""\
# Determina as telas que mostrarão o botão.
# filtro_de_telas = "{self.filtro_de_telas}"
"""

        if self.ordem:
            config += f"""\
ordem = "{self.ordem}"
"""
        else:
            config += f"""\
# ordem = "{self.ordem}"
"""

        config += f"""
# Nome do botão.
descricao = "{self.descricao}"
# Pode ser "S" ou "N"
controla_acesso = "{self.controla_acesso}"
"""
        if self.tecla_de_atalho:
            config += f"""
tecla_de_atalho = "{self.tecla_de_atalho}"
"""
        else:
            config += f"""
# tecla_de_atalho = "{self.tecla_de_atalho}"
"""

        config += f"""\
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
    def config_from_toml(cls, javascript: str, config_toml: str):
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
            "IDBTNACAO": config_obj["id"],
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

    def ativar(self, args: list[str | int]):
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
        r = soyrequest(
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
        r = soyrequest(
            "ACSP.icl", {"tipo": "BTA", "ids": [{"id": self.id}], "codigo": codigo}
        )
        status = r.json()["status"]
        if status == "0":
            raise AutorizacaoFalhou(self.id, codigo)
        return r


def requisitar_codigo():
    soyrequest("ACSP.ecl", {"tipo": "BTA"})


def soyrequest(servico: str, corpo_requisicao: dict[str, Any]):
    data = {"serviceName": servico, "requestBody": corpo_requisicao}
    params = {
        "serviceName": servico,
        "outputType": "json",
    }
    r = requests.post(
        URL,
        params=params,
        cookies=COOKIES_MGE,
        headers=HEADERS,
        json=data,
    )
    return r


def soysave(entidade: str, mudancas: list[dict[str, dict[str, str]]]):
    """
    Wrapper pro DataSP.save.
    `mudancas` tem o seguinte formato: [{
        "pk": {"IDBTNACAO": "1"},
        "mudanca": {
            "DESCRICAO": "Outro nome"
        }
    },
    {
        "pk": {"IDBTNACAO": "2"},
        "mudanca": {
            "CONFIG": "<actionConfig><runScript entityName=\"CabecalhoNota\" refreshType=\"NONE\" txManual=\"false\"><![CDATA[console.log(\"wow\")]]></runScript><params></params></actionConfig>",
        }
    }]
    O DataSP.save pode também ser usado para criar linhas no banco de dados.
    """
    fields = chaves_das_mudancas(mudancas)
    records = mudancas_para_records(mudancas)

    r = soyrequest(
        "DatasetSP.save",
        {
            "entityName": entidade,
            "fields": fields,
            "records": records,
        },
    )
    # Formato da resposta:
    # {
    #   "serviceName":"DatasetSP.save",
    #   "status":"1",
    #   "pendingPrinting":"false"
    #   "transactionId":"BRUH"
    #   "responseBody":{"total":"2", "result":[["CAMPO1", "CAMPO2"], ["CAMPO1", "CAMPO2"]]}
    # }
    try:
        response = r.json()
    except json.JSONDecodeError:
        return r.text
    assert response.get(
        "responseBody"
    ), f"Resposta sem corpo: {json.dumps(response, indent=4)}"
    assert response["responseBody"].get(
        "result"
    ), f"Corpo sem 'result': {json.dumps(response, indent=4)}"
    lista_valores = response["responseBody"]["result"]
    resultados = []
    for valores in lista_valores:
        resultados.append(dict(zip(fields, valores)))
    return resultados


def soyquery(query: str) -> list[dict[str, Any]] | str:
    """
    Faz uma consulta ao banco de dados da Soynkhya
    >>> soyquery("select nunota from tgfcab where nunota in (1, 2)")
    [
      {'NUNOTA': 1},
      {'NUNOTA': 2}
    ]
    """
    # exemplo de resultado com a query
    # 'select nunota from tgfcab where nunota = 7777':
    # {
    #     "serviceName": "DbExplorerSP.executeQuery",
    #     "status": "1",
    #     "pendingPrinting": "false",
    #     "transactionId": "FFDFFAFF4FFFFFAFFFF2FF3FFF4FFFFF",
    #     "responseBody": {
    #         "fieldsMetadata": [
    #             {
    #                  "name": "NUNOTA",
    #                  "description": "NUNOTA",
    #                  "order": 1,
    #                  "userType": "I"
    #             }
    #         ],
    #         "rows": [[7777]],
    #         "burstLimit": False,
    #         "timeQuery": "3ms",
    #         "timeResultSet": "1ms",
    #     },
    # }
    r = soyrequest("DbExplorerSP.executeQuery", {"sql": query})
    try:
        response = r.json()
    except json.JSONDecodeError:
        return r.text
    if "responseBody" not in response:
        raise ErroDoSoynkhya(json.dumps(response, indent=4))
    response_body = response["responseBody"]
    fields_metadata = response_body["fieldsMetadata"]
    # aqui estão os resultados de fato
    rows = response_body["rows"]
    result = []
    for row in rows:
        dict_version = {}
        for index in range(len(row)):
            dict_version[fields_metadata[index]["name"]] = row[index]
        result.append(dict_version)
    return result


def flatten(lst: list[Any]):
    flat_list = []
    for item in lst:
        if isinstance(item, list):
            flat_list.extend(flatten(item))
        else:
            flat_list.append(item)
    return flat_list


def chaves_das_mudancas(mudancas_com_pk: list[dict[str, dict[str, str]]]) -> list[str]:
    """
    self.assertEqual(
        chaves_das_mudancas(
            [
                {
                    "pk": {"IDBTNACAO": "131"},
                    "mudanca": {"DESCRICAO": ""},
                },
                {
                    "foreignKey": {
                        "NOMEINSTANCIA": "Bruh",
                    },
                    "mudanca": {"RESOURCEID": ""},
                },
            ]
        ),
        ["DESCRICAO", "RESOURCEID"],
    )
    """
    mudancas = [x["mudanca"] for x in mudancas_com_pk]
    keys = flatten([list(mudanca.keys()) for mudanca in mudancas])
    return keys


def mudancas_para_records(
    mudancas_com_pk: list[dict[str, dict[str, str]]],
) -> list[dict[str, dict[str, str]]]:
    fields = chaves_das_mudancas(mudancas_com_pk)
    records = []
    for mudanca in mudancas_com_pk:
        mudanca_item = mudanca.pop("mudanca")
        elemento_corpo = mudanca
        elemento_corpo["values"] = {}
        for chave, valor in mudanca_item.items():
            indice = str(fields.index(chave))
            elemento_corpo["values"][indice] = valor
        records.append(elemento_corpo)
    return records


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
