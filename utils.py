import json
import zipfile
import os
import requests
from typing import Any
from enum import Enum
import re

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Connection": "keep-alive",
    "Content-Type": "application/json; charset=UTF-8",
}


class ErroDoSoynkhya(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def substituicao_recursiva(pasta: str, padrao_regex: str, substituicao: str):
    for raiz, _, arquivos in os.walk(pasta):
        for nome in arquivos:
            caminho = os.path.join(raiz, nome)
            try:
                with open(caminho, "r") as f:
                    conteudo = f.read()

                conteudo_atualizado = re.sub(padrao_regex, substituicao, conteudo)

                if conteudo_atualizado != conteudo:
                    with open(caminho, "w") as f:
                        f.write(conteudo_atualizado)
            except Exception as e:
                print(f"Error processing {caminho}: {e}")


def chaves_das_mudancas(
    mudancas: list[dict[str, dict[str, str | float | int | None]]],
) -> list[str]:
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
    mudancas = [x["mudanca"] for x in mudancas]
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


def lista(item):
    return item if isinstance(item, list) else [item]


def mudancas_para_records(
    mudancas: list[dict[str, dict[str, str | float | int | None]]],
) -> list[dict[str, dict[str, str | float | int | None]]]:
    fields = chaves_das_mudancas(mudancas)
    records = []
    for mudanca in mudancas:
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


class TipoImpressao(Enum):
    NOTA = 1
    BOLETO = 3


class TipoObjetoBD(Enum):
    TABELA = "T"
    FUNCAO = "F"
    PROCEDURE = "P"
    TRIGGER = "R"
    VIEW = "V"


class Soywrapper:
    """
    Classe contendo wrappers para requests que o Soynkhya faz.
    """

    def __init__(self, url, jsessionid_mge, jsessionid_mgecom, jsessionid_mgefin):
        self.mge = {"JSESSIONID": jsessionid_mge}
        self.mgefin = {"JSESSIONID": jsessionid_mgefin}
        self.mgecom = {"JSESSIONID": jsessionid_mgecom}
        self.url = url

    def erro(self, mensagem: str | dict[Any, Any]):
        print(f"mge: {self.mge["JSESSIONID"][:5]}...")
        print(f"mgecom: {self.mgecom["JSESSIONID"][:5]}...")
        print(f"mgefin: {self.mgefin["JSESSIONID"][:5]}...")
        print(f"url: {self.url}")
        raise ErroDoSoynkhya(json.dumps(mensagem, indent=4, ensure_ascii=False))

    def pegar_corpo(self, r: requests.Response) -> dict[str, Any]:
        """
        Retorna o "responseBody" de uma resposta. Se houver algum erro na resposta,
        ele bloquerá o processo.
        """
        try:
            resposta = r.json()
        except json.JSONDecodeError:
            raise self.erro(r.text)
        if "statusMessage" in resposta:
            raise self.erro(resposta["statusMessage"])
        try:
            resposta = resposta["responseBody"]
        except KeyError:
            self.erro(resposta)
        return resposta

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
        return self.pegar_corpo(r)

    def soysave(
        self,
        entidade: str,
        mudancas: list[dict[str, dict[str, str | float | int | None]]],
    ) -> list[dict[str, str | float | int | None]]:
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
        response = self.pegar_corpo(r)
        lista_valores = response["result"]
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
            raise self.erro(
                f"""\
Query: {query}
{r.text}"""
            )
        if "responseBody" not in response:
            raise self.erro(
                f"""\
Query: {query}
{r.text}"""
            )
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
                self.url + f"/mge/service.sbr",
                params=params,
                cookies=self.mge,
                headers=HEADERS,
                json=data,
            )
        elif cookie == "mgefin":
            r = requests.post(
                self.url + f"/mgefin/service.sbr",
                params=params,
                cookies=self.mgefin,
                headers=HEADERS,
                json=data,
            )
        elif cookie == "mgecom":
            r = requests.post(
                self.url + f"/mgecom/service.sbr",
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
        assert "responseBody" in r, json.dumps(r, indent=4, ensure_ascii=False)
        return r["responseBody"]["config"]

    def upload(self, chave: str, caminho: str, tipo="application/zip"):
        with open(caminho, "rb") as __upload_f:
            files = {"arquivo": ("arquivo", __upload_f, tipo)}
            requests.get(
                f"{self.url}/mge/sessionUpload.mge",
                cookies=self.mge,
                params={
                    "sessionkey": chave,
                    "fitem": "S",
                    "isHtml5": "S",
                },
            )
            requests.post(
                f"{self.url}/mge/sessionUpload.mge",
                cookies=self.mge,
                params={"salvar": "S"},
                files=files,
            )

    def importar_arquivo(
        self,
        configuracao: dict[str, dict[str, str]],
    ):
        corpo = {
            "chave": {
                "fileKey": "IMPORTACAO_XML_ZIPXML",
                "multiplosAvisos": "true",
                "paramsNFeEmissaoPropria": configuracao,
                "paramsNFe": configuracao,
                "paramsCte": configuracao,
            }
        }
        r = self.soyrequest("ImportacaoXMLNotasSP.importarArquivo", corpo).json()
        return r

    def info_objeto_bd(self, nome: str, tipo: TipoObjetoBD):
        r = self.soyrequest(
            "DbExplorerSP.getObjectDetails",
            {"dbObject": {"name": nome, "type": tipo.value}},
        )
        resposta = self.pegar_corpo(r)
        assert "objectDetails" in resposta
        detalhes = resposta["objectDetails"]
        if tipo == TipoObjetoBD.TABELA:
            colunas = [
                {
                    "nome": coluna[0],
                    "pk": coluna[1],
                    "tipo": coluna[2],
                    "tamanho": coluna[3],
                    "casas_decimais": coluna[4],
                    "nulo": coluna[5],
                    "padrao": coluna[6],
                }
                for coluna in detalhes["colunas"]
            ]
            return colunas
        elif tipo == TipoObjetoBD.VIEW:
            colunas = [
                {
                    "nome": coluna[0],
                    "pk": coluna[1],
                    "tipo": coluna[2],
                    "tamanho": coluna[3],
                    "casas_decimais": coluna[4],
                    "nulo": coluna[5],
                    "padrao": coluna[6],
                }
                for coluna in detalhes["colunas"]
            ]
            return {"colunas": colunas, "sql": detalhes["viewSql"]}
        elif tipo == TipoObjetoBD.PROCEDURE:
            return detalhes["code"]
        elif tipo == TipoObjetoBD.FUNCAO:
            return detalhes["code"]
        elif tipo == TipoObjetoBD.TRIGGER:
            return detalhes["code"]

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

    def editar_liberacao(self, mudancas: list[dict[str, str]]):
        """
        Exemplo de mudanças:
        [
            {
                "chave": 154746,
                "tabela": "TGFCAB",
                "evento": 3,
                "sequencia": 0,
                "solicitante": 57,
                "liberador": 18,
                "seqCascata": 0,
                "enviaNotif": "S",
                "hashLiberacao": "beb835ba59f263fbd68de5fcf6f331d5",
                "nucll": "",
            }
        ]
        """
        return self.soyrequest(
            "LiberacaoAlcadaSP.editarLiberacoes",
            {"liberacoes": {"liberacao": mudancas}},
        ).json()

    def faturar_documento(
        self,
        notas: list[int],
        codigo_tipo_operacao: int,
        ignorar_estoque_insuficiente=True,
        parametros_low_level={},
    ) -> dict[str, Any]:
        """
        Fatura documento para o código destino especificado (`codigo_tipo_operacao`).
        Exemplo de resposta:
        ```json
        {
            "usuario": "22",
            "movimento": "P",
            "valor_nota_faturada": "0",
            "numero_nota_faturada": "0",
            "nota": "153773"
        }
        ```
        """
        # {
        #     "serviceName": "SelecaoDocumentoSP.faturar",
        #     "status": "1",
        #     "pendingPrinting": "false",
        #     "transactionId": "7043379C69B14CEF87F31B35D4E0BCC8",
        #     "responseBody": {
        #         "codUsuLogado": {
        #             "$": "57"
        #         },
        #         "notas": {
        #             "tipMov": "V",
        #             "vlrNotaFat": "1862.49",
        #             "numNotaFat": "0",
        #             "nota": {
        #                 "$": "153541"
        #             }
        #         }
        #     }
        # }
        notas_soynkhya = [{"$": nota} for nota in notas]
        corpo = {
            "codTipOper": codigo_tipo_operacao,
            "dtFaturamento": "",
            "serie": "4",
            "dtSaida": "",
            "hrSaida": "",
            "tipoFaturamento": "FaturamentoNormal",
            "dataValidada": True,
            "notasComMoeda": {},
            "nota": notas_soynkhya,
            "codEmp": 2,
            "codLocalDestino": "",
            "conta2": 0,
            "faturarTodosItens": True,
            "umaNotaParaCada": "false",
            "ehWizardFaturamento": True,
            "dtFixaVenc": "",
            "ehPedidoWeb": False,
            "nfeDevolucaoViaRecusa": False,
            "isFaturamentoDanfeSeguranca": False,
        }
        if ignorar_estoque_insuficiente:
            produtos = [
                produto["CODPROD"]
                for produto in self.soyquery(
                    f"select codprod from tgfite where nunota in ({",".join([str(nota) for nota in notas])})"
                )
            ]
            corpo.update(
                {
                    "txProperties": {
                        "prop": [
                            {
                                "name": f"central.notas.pode.efetivar_{codigo}",
                                "value": "true",
                            }
                            for codigo in produtos
                        ]
                    },
                }
            )

        corpo.update(parametros_low_level)
        r = self.soyrequest(
            "SelecaoDocumentoSP.faturar",
            {
                "notas": corpo,
            },
            cookie="mgecom",
        )
        try:
            resposta = self.pegar_corpo(r)
            return {
                "nota": resposta["notas"]["nota"]["$"],
                "usuario": resposta["codUsuLogado"]["$"],
                "movimento": resposta["notas"]["tipMov"],
                "valor_nota_faturada": resposta["notas"]["vlrNotaFat"],
                "numero_nota_faturada": resposta["notas"]["numNotaFat"],
            }
        except json.JSONDecodeError:
            raise self.erro(r.text)

    def estrutura_de_entidade(self, entidade: str):
        r = self.soyrequest(
            "PersonalizedFilter.getEntityStructure", {"entity": {"name": entidade}}
        )
        return self.pegar_corpo(r)

    def nome_colunas(self, entidade: str):
        estrutura = self.estrutura_de_entidade(entidade)
        resultado = {}
        for info in estrutura["entity"]["field"]:
            resultado[info["name"]] = info["description"]
        return resultado
    def _imprimir_transacao(self, transacao: str):
        url = f"https://localhost:9196/.localPrinting?params={self.mgecom["JSESSIONID"]}|{transacao}"
        headers = {
            "Origin": self.url,
            "Referer": f"{self.url}/mgecom/SelecaoDocumento.xhtml5",
            "Accept": "*/*",
        }
        requests.get(url, headers=headers, verify=False)

    def imprimir_carta_de_correcao(self, nota):
        r = self.soyrequest(
            "ServicosNfeSP.imprimeCartaCorrecao",
            {"notas": {"nota": [{"$": nota}]}},
            "mgecom",
        )
        self.pegar_corpo(r)
        transacao = r.json()["transactionId"]
        self._imprimir_transacao(transacao)

    def imprimir_notas(
        self,
        notas: list[int],
        tipo=TipoImpressao.NOTA,
        pedido_web=False,
        portal_caixa=False,
        gerar_pdf=False,
    ) -> dict[str, Any]:
        nota_requisicao = [
            {"nuNota": nunota, "tipoImp": tipo.value, "impressaoDanfeSimplicado": False}
            for nunota in notas
        ]
        corpo = {
            "notas": {
                "pedidoWeb": pedido_web,
                "portalCaixa": portal_caixa,
                "gerarpdf": gerar_pdf,
                "nota": nota_requisicao,
            },
        }
        resposta = self.soyrequest("ImpressaoNotasSP.imprimeDocumentos", corpo).json()
        if not gerar_pdf:
            transacao = resposta["transactionId"]
            self._imprimir_transacao(transacao)
        return transacao

    def gerar_lote(self, notas: list[int]):
        notas_soynkhya = [{"$": nota} for nota in notas]
        r = self.soyrequest(
            "ServicosNfeSP.gerarLote",
            {
                "notas": {
                    "retNotasReprovadas": True,
                    "nunota": notas_soynkhya,
                    "habilitaClientEvent": "S",
                    "visAutOcorrencias": True,
                    "habilitaClientEvent": "S",
                    "visAutOcorrencias": True,
                    "txProperties": {
                        "prop": [
                            {"name": "br.com.utiliza.dtneg.servidor", "value": True}
                        ]
                    },
                    "confirmaGeracaoXmlRejeitado": "S",
                }
            },
            cookie="mgecom",
        )
        return self.pegar_corpo(r)

    def confirmar_documento(
        self, notas: list[int], parametros_low_level={}
    ) -> dict[str, Any]:
        """
        Exemplo de resposta:
        {
        }
        """
        # Exemplo de resposta:
        # {
        #     "serviceName": "ServicosNfeSP.confirmarNotas",
        #     "status": "1",
        #     "pendingPrinting": "false",
        #     "transactionId": "9D4C0E19E447612CF472BF400706EDE8",
        #     "responseBody": {
        #         "resumoConfirmacao": {
        #             "docsConfirmados": "1",
        #             "docsNaoConfirmados": "0",
        #             "totalDocs": "1",
        #             "confirmados": {
        #                 "nota": {
        #                     "$": "Documento n\u00ba 153804 foi confirmado com sucesso.\n--------------------------------------------------------------------------------------------------------\n\n",
        #                     "nuNota": "153804"
        #                 }
        #             }
        #         }
        #     }
        # }
        # o "nota" pode ser uma lista (??????????????????????)
        notas_soynkhya = [{"$": nota} for nota in notas]
        corpo = {
            "confirmacaoPortal": True,
            "aprovarNFeNFSe": False,
            "compensarNotaAutomaticamente": False,
            "confirmacaoCentralNota": True,
            "pedidoWeb": False,
            "resourceID": "br.com.sankhya.mgecom.mov.selecaodedocumento",
            "atualizaPrecoItemPedCompra": False,
            "ownerServiceCall": "SelecaoDocumento",
            "nunota": notas_soynkhya,
            "txProperties": {
                "prop": [
                    {
                        "name": "br.com.utiliza.dtneg.servidor",
                        "value": False,
                    },
                    {
                        "name": "central.notas.pode.compensar",
                        "value": False,
                    },
                ]
            },
        }
        corpo.update(parametros_low_level)
        r = self.soyrequest(
            "ServicosNfeSP.confirmarNotas",
            {
                "notas": corpo,
            },
            cookie="mgecom",
        )
        try:
            resposta = self.pegar_corpo(r)
            try:
                resposta = resposta["resumoConfirmacao"]
                liberacoes = []
                if "eventosLiberacao" in resposta:
                    liberacoes = self.soyquery(
                        f"select * from vsilib where nuchave in ({", ".join([str(nota) for nota in notas])})"
                    )
                mensagens = []
                if "confirmados" in resposta:
                    for elemento in lista(resposta["confirmados"]["nota"]):
                        mensagens.append(
                            {"documento": elemento["nuNota"], "mensagem": elemento["$"]}
                        )

                if "naoConfirmados" in resposta:
                    for elemento in lista(resposta["naoConfirmados"]["nota"]):
                        mensagens.append(
                            {"documento": elemento["nuNota"], "mensagem": elemento["$"]}
                        )

                return {
                    "confirmados": resposta["docsConfirmados"],
                    "nao_confirmados": resposta["docsNaoConfirmados"],
                    "total": resposta["totalDocs"],
                    "mensagens": mensagens,
                    "liberacoes": liberacoes,
                }
            except KeyError:
                self.erro(resposta)
        except json.JSONDecodeError:
            raise self.erro(r.text)
        raise self.erro(r.text)

    def cancelar_nota(
        self, notas: list[int], justificativa: str, pode_cancelar_remessa=True
    ):
        notas_soynkhya = [{"$": nota} for nota in notas]
        r = self.soyrequest(
            "CACSP.cancelarNota",
            {
                "notasCanceladas": {
                    "nunota": notas_soynkhya,
                    "nota": notas_soynkhya,
                    "justificativa": justificativa,
                    "txProperties": {
                        "prop": [
                            {
                                "name": "pode.cancelar.notas.remessa",
                                "value": pode_cancelar_remessa,
                            }
                        ]
                    },
                },
            },
            cookie="mgecom",
        )
        return self.pegar_corpo(r)

    def texto_carta_de_correcao(self, nota: int):
        r = self.soyrequest(
            "ServicosNfeSP.getTextoCartaCorrecao",
            {
                "notas": {"nunota": {"$": nota}},
            },
            "mgecom",
        )
        return self.pegar_corpo(r)["carta"]["texto"]["$"]

    def carta_de_correcao(self, nota: int, texto: str):
        """
        Envia uma carta de correção para a `nota` com um `texto`.
        """
        r = self.soyrequest(
            "ServicosNfeSP.enviarCartaCorrecao",
            {
                "carta": {
                    "nota": {"$": nota},
                    "texto": {"$": texto},
                }
            },
            "mgecom",
        )
        resposta = self.pegar_corpo(r)
        assert resposta == {}, self.erro(r)

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
        )
        return self.pegar_corpo(r)


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
