import json
import zipfile
import os
import requests
from typing import Any
from enum import Enum

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Connection": "keep-alive",
    "Content-Type": "application/json; charset=UTF-8",
}


class ErroDoSoynkhya(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


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


def flatten(lst: list[Any]):
    flat_list = []
    for item in lst:
        if isinstance(item, list):
            flat_list.extend(flatten(item))
        else:
            flat_list.append(item)
    return flat_list


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


class Impostos_Financeiro(Enum):
    """
    Donde tirar os impostos/financeiro.
    """

    DO_ARQUIVO = "X"
    DO_SISTEMA = "S"
    NAO_INFORMADO = "N"


class Soywrapper:
    """
    Classe contendo wrappers para requests que o Soynkhya faz.
    """

    def __init__(self, url, jsessionid_mge, jsessionid_mgefin, jsessionid_mgecom):
        self.mge = {"JSESSIONID": jsessionid_mge}
        self.mgefin = {"JSESSIONID": jsessionid_mgefin}
        self.mgecom = {"JSESSIONID": jsessionid_mgecom}
        self.url = url

    def erro(self, mensagem: str):
        print(f"mge: {self.mge["JSESSIONID"][:5]}...")
        print(f"mgecom: {self.mgecom["JSESSIONID"][:5]}...")
        print(f"mgefin: {self.mgefin["JSESSIONID"][:5]}...")
        print(f"url: {self.url}")
        raise ErroDoSoynkhya(mensagem)

    def soyremove(self, entidade: str, pks: list[dict[str, str]]):
        """
        Para remover um botão de ação com id 10:
        ```
        wrapper.soyremove("BotaoAcao", [{"IDBTNACAO": 10}])
        ```
        """
        r = self.soyrequest(
            "DatasetSP.removeRecord",
            {
                "crudListener": "br.com.sankhya.modelcore.crudlisteners.GadgetCRUDListener",
                "entityName": entidade,
                "pks": pks,
            },
        )
        try:
            return r.json()
        except json.JSONDecodeError:
            raise self.erro(r.text)

    def soysave(self, entidade: str, mudancas: list[dict[str, dict[str, str | int]]]):
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

        r = self.soyrequest(
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
            raise self.erro(r.text)
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

    def soyquery(self, query: str) -> list[dict[str, Any]]:
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
        r = self.soyrequest("DbExplorerSP.executeQuery", {"sql": query})
        try:
            response = r.json()
        except json.JSONDecodeError:
            print("Query: ", query)
            raise self.erro(r.text)
        if "responseBody" not in response:
            print("Query: ", query)
            raise self.erro(json.dumps(response, indent=4))
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

    def soyrequest(
        self,
        servico: str,
        corpo_requisicao: dict[str, Any],
        cookie="mge",
        parametros_adicionais={},
    ):
        data = {"serviceName": servico, "requestBody": corpo_requisicao}
        params = {
            "serviceName": servico,
            "outputType": "json",
        }
        params.update(parametros_adicionais)
        assert cookie in ("mge", "mgefin", "mgecom")
        if cookie == "mge":
            r = requests.post(
                self.url,
                params=params,
                cookies=self.mge,
                headers=HEADERS,
                json=data,
            )
        elif cookie == "mgefin":
            r = requests.post(
                self.url,
                params=params,
                cookies=self.mgefin,
                headers=HEADERS,
                json=data,
            )
        elif cookie == "mgecom":
            r = requests.post(
                self.url,
                params=params,
                cookies=self.mgecom,
                headers=HEADERS,
                json=data,
            )

        return r

    def soyconfig(self, chave: str) -> dict[str, dict[str, str]]:
        """
        Com a chave "br.com.sankhya.cac.ImportacaoXMLNota.config", por exemplo,
        conseguimos a configuração usada nos lançamentos efetuados pelo
        'Portal de Importação de XML'. Tu poderias usar essa configuração
        para fazer requisições ao serviço "ImportacaoXMLNotasSP.validarImportacao".
        {
            "tipoDeNegociacao": {
                "$": "4"
            },
            [...]
            "qtdDiasDtExtemporanea": {
                "$": "0"
            },
            "CODUSUIMP": {}
        }
        """
        r = self.soyrequest(
            "SystemUtilsSP.getConf",
            {
                "config": {
                    "chave": chave,
                    "tipo": "T",
                }
            },
        ).json()
        assert "responseBody" in r, json.dumps(r, indent=4)
        return r["responseBody"]["config"]

    def processar(
        self,
        nuarquivo: int,
        configuracao: dict[str, dict[str, str]],
        reprocessar: bool,
        numero_pedido_frete: int = 0,
        valor_pedido_frete: int = 0,
    ):
        """
        Wrapper pra requisição "ImportacaoXMLNotasSP.processarArquivo"
        Use o `soyconfig` para obter a configuração. Altere alguma coisa
        caso seja necessário.
        """
        nr = str(numero_pedido_frete)
        vlr = str(valor_pedido_frete)
        if nr == 0:
            nr = ""
        if vlr == 0:
            vlr = ""
        corpo = {
            "params": {
                "tela": "PORTALIMPORTACAOXML",
                "reprocessar": reprocessar,
                "NUARQUIVO": [{"$": nuarquivo}],
                "paramsCte": configuracao,
                "pedidoFreteLigado": {
                    "nroPedidoFrete": nr,
                    "vlrPedidoFrete": vlr,
                },
                "paramsNFe": configuracao,
                "paramsNFeEmissaoPropria": configuracao,
                "multiplosAvisos": "true",
            }
        }
        r = self.soyrequest("ImportacaoXMLNotasSP.processarArquivo", corpo).json()
        return r

    def validar_importacao(
        self,
        nuarquivo: int,
        configuracao: dict[str, dict[str, str]],
        reprocessar: bool,
        produtos_parceiro: list[dict[str, str]],
        pedidos_ligados: list[dict[str, str]],
        ligar_antigos: bool,
        revalidar_pedidos_ligados: bool,
        impostos: Impostos_Financeiro,
        financeiro: Impostos_Financeiro,
        item_alterado: bool,
        algum_item_do_xml_tem_lote_med: bool,
    ):
        """
        produtos_parceiro = [
            {
                "CODPARC": "1338",
                "CODPRODXML": "2",
                "PRODUTOXML": "Broca 2",
                "UNIDADEXML": "UN",
                "CONTROLE": "",
                "CODPROD": 15438,
                "DESCRPROD": "JFTVTIPNJOVNTBMWBUPS",
                "UNIDADE": "BG",
                "CODBARRAPARC": "AVEREGINACAELORUM44",
            },
            [...]
        ]
        pedidos_ligados =  [{
            "PRODUTO": 15438,
            "SEQUENCIA": 1,
            "DESCRPROD": "Broca 2",
            "CONTROLE": "",
            "QTDALIGAR": 1,
            "VLRUNIT": 0,
            "QTDLIGADA": 0,
            "QTDRESTANTE": 1,
            "ligacao": [
                {
                    "NUNOTA": 123019,
                    "NUMNOTA": 95963,
                    "SEQUENCIA": 1,
                    "DTMOV": "01/01/2023 09:36:16",
                    "QTDPENDENTE": 998,
                    "QTDLIG": 0,
                    "VLRUNIT": 0.002,
                    "QTDPENDENTEUNPAD": 998,
                    "CODTIPVENDA": 256,
                    "CODVOL": "BG",
                    "CODCENCUS": 102002,
                    "CODNAT": 1010000,
                    "CODPROJ": 0,
                    "DESCRTIPVENDA": "SEM FINANCEIRO",
                    "CODVEND": 42,
                    "OBSERVACAO": "ddddddddddddddddddd"
                },
                [...]
            ]},
            [...]
            ]
        """
        r = self.soyrequest(
            "ImportacaoXMLNotasSP.validarImportacao",
            {
                "params": {
                    "nuArquivo": nuarquivo,
                    "codParceiro": {},
                    "filtraSomentePedidos": False,
                    "importarDadosDoInterm": False,
                    "paramsNFe": configuracao,
                    "paramsNFeEmissaoPropria": configuracao,
                    "validacoes": {
                        "simulacaoFinanceiro": False,
                        "produtosParceiro": {
                            "ITEMALTERADO": item_alterado,
                            "ALGUMITEMDOXMLTEMLOTEMED": algum_item_do_xml_tem_lote_med,
                            "produtoParceiro": produtos_parceiro,
                        },
                        "pedidosLigados": {
                            "item": pedidos_ligados,
                            "ligarAntigos": ligar_antigos,
                            "revalidarPedidosLigados": revalidar_pedidos_ligados,
                        },
                        "impostos": {"USOIMPOSTOS": impostos.value},
                        "financeiro": {"USOFINANCEIRO": financeiro.value},
                    },
                    "reprocessar": reprocessar,
                }
            },
        ).json()
        return r


def zipar_pasta(pasta: str, output: str, substituicoes: dict[str, str]):
    """
    Compacta uma pasta fazendo substituições em todos os seus arquivos.
    Exemplo:
    ```python
    zipar_pasta("caminho", "output.zip", {"termo": "substituição"})
    ```
    """
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as arquivo_zip:
        for raiz, diretorios, caminhos in os.walk(pasta):
            for caminho in caminhos:
                caminho_maior = os.path.join(raiz, caminho)
                with open(caminho_maior, "r") as f:
                    conteudo = f.read()
                for pesquisa, substituto in substituicoes.items():
                    conteudo = conteudo.replace(pesquisa, substituto)
                caminho_relativo = os.path.relpath(caminho_maior, pasta)
                arquivo_zip.writestr(caminho_relativo, conteudo)
