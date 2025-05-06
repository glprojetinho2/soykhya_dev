from utils import *
import typing
import xml.dom.minidom
import xml.etree.ElementTree as ET
import argparse
from config import *
from enum import Enum


class StatusImportacao(Enum):
    PENDENTE = 0
    IMPORTADO = 2
    COM_DIVERGENCIA = 4
    CONFIRMADO = 5


class ProdutoXML:
    def __init__(self):
        pass


class StatusXML(Enum):
    PENDENTE = 0
    CANCELADO = 1
    IMPORTADO = 2
    INVALIDO = 3
    COM_DIVERGENCIA = 4
    CONFIRMADO = 5


class ImportacaoXML:

    def __init__(self, importacao_crua: dict[str, Any], wrapper: Soywrapper):
        self.cru = importacao_crua
        self.nuarquivo = self.cru["NUARQUIVO"]
        self.wrapper = wrapper
        self.configuracao_importacao = self.wrapper.soyconfig(
            "br.com.sankhya.cac.ImportacaoXMLNota.config"
        )
        assert self.cru["CONFIG"] is not None
        self.__config = ET.fromstring(self.cru["CONFIG"])
        assert self.cru["XML"] is not None
        self.__xml = ET.fromstring(self.cru["XML"])

    def atualizar(self) -> typing.Self:
        return self.__class__(
            self.wrapper.soyquery(
                f"select * from tgfixn where nuarquivo={self.nuarquivo}"
            )[0],
            self.wrapper,
        )

    def ajustar_produtos(self):
        p_config = self.produtos_config
        p_xml = self.produtos_xml
        for c in p_config:
            x = [a for a in p_xml if str(a["CODPROD"]) == str(c["CODPRODXML"])][0]
            self.wrapper.soysave(
                "Produto",
                [{"pk": {"CODPROD": c["CODPROD"]}, "mudanca": {"NCM": x["NCM"]}}],
            )

    def associar(self, produtos: list[dict[str, str]]):
        """
        Associa produtos do Soynkhya a produtos do xml dentro da importação.
        produtos = [{
            "CODPRODXML": "1",
            "CODPROD": 18613,
            "UNIDADE": "UN",
        }, ...]
        """
        produtos_config = self.produtos_config
        nova_config: list[dict[str, str]] = []
        for produto in produtos:
            assert (
                "CODPRODXML" in produto
            ), f"Informa o código do produto {produto["CODPROD"]} no xml para que a associação possa prosseguir."
            assert "UNIDADE" in produto
            assert "CODPROD" in produto
            _produto_cfg = [
                x
                for x in produtos_config
                if str(x["CODPRODXML"]) == str(produto["CODPRODXML"])
            ]
            print(produtos_config)
            assert (
                len(_produto_cfg) == 1
            ), f"O produto {produto["CODPRODXML"]} não corresponde a nenhum produto do xml.\n{json.dumps(produtos_config, indent=4)}"
            produto_cfg = _produto_cfg[0]
            produto["CODPRODXML"]
            produto_cfg.update(produto)
            nova_config.append(produto_cfg)

        assert len(nova_config) == len(produtos)

        self.wrapper.validar_importacao(
            self.nuarquivo,
            self.configuracao_importacao,
            False,
            nova_config,
            [],
            False,
            False,
            self.impostos,
            self.financeiro,
            True,
            False,
        )

    def ligar_pedidos_mais_antigos(self):
        config = wrapper.soyconfig("br.com.sankhya.cac.ImportacaoXMLNota.config")
        self.wrapper.validar_importacao(
            self.nuarquivo,
            self.configuracao_importacao,
            False,
            self.produtos_config,
            self.produtos_ligados,
            True,
            False,
            self.impostos,
            self.financeiro,
            False,
            False,
        )

    def produtos(self):  # -> list[ProdutoXML]
        resultado = []
        for produto in self.__xml.iter("det"):
            resultado.append(produto.attrib)
        return resultado

    @property
    def impostos(self) -> Impostos_Financeiro:
        imposto_elemento = self.__config.find("impostos")
        assert imposto_elemento is not None
        if "USOIMPOSTOS" in imposto_elemento.attrib:
            return Impostos_Financeiro(imposto_elemento.attrib["USOIMPOSTOS"])
        return Impostos_Financeiro.NAO_INFORMADO

    @property
    def financeiro(self) -> Impostos_Financeiro:
        financeiro_elemento = self.__config.find("financeiro")
        assert financeiro_elemento is not None
        if "USOFINANCEIRO" in financeiro_elemento.attrib:
            return Impostos_Financeiro(financeiro_elemento.attrib["USOFINANCEIRO"])
        return Impostos_Financeiro.NAO_INFORMADO

    @property
    def produtos_xml(self):
        produtos = []

        def se_existir(pai: ET.Element, nome: str) -> str | None:
            iterador = list(pai.iter(nome))
            if len(iterador) > 0:
                return iterador[0].text
            else:
                return None

        for det in self.__xml.iter("det"):
            produto_elemento = det.find("prod")
            produto = {}
            produto["CODPROD"] = produto_elemento.find("cProd").text
            produto["CODBARRA"] = produto_elemento.find("cEAN").text
            produto["DESCRPROD"] = produto_elemento.find("xProd").text
            produto["NCM"] = produto_elemento.find("NCM").text
            produto["CODCFO"] = produto_elemento.find("CFOP").text
            produto["CODVOL"] = produto_elemento.find("uCom").text
            produto["QTDNEG"] = produto_elemento.find("qCom").text
            produto["VLRUNIT"] = produto_elemento.find("vUnCom").text
            produto["VLRTOT"] = produto_elemento.find("vProd").text
            produto["CODBARRATRIB"] = produto_elemento.find("cEANTrib").text
            produto["CODVOLTRIB"] = produto_elemento.find("uTrib").text
            produto["QTDNEGTRIB"] = produto_elemento.find("qTrib").text
            produto["VLRUNITTRIB"] = produto_elemento.find("vUnTrib").text
            produto["SEQUENCIA"] = se_existir(produto_elemento, "nItemPed")
            produto["INDTOT"] = produto_elemento.find("indTot").text

            imposto_elemento = det.find("imposto")
            icms = {}
            icms_elemento = imposto_elemento.find("ICMS")
            icms["CST"] = se_existir(icms_elemento, "CST")
            icms["ORIGEM"] = se_existir(icms_elemento, "orig")
            icms["MODBC"] = se_existir(icms_elemento, "modBC")
            icms["REDBASE"] = se_existir(icms_elemento, "pRedBC")
            icms["BASE"] = se_existir(icms_elemento, "vBC")
            icms["ALIQUOTA"] = se_existir(icms_elemento, "pICMS")
            icms["VLRICMS"] = se_existir(icms_elemento, "vICMS")
            icms["ALIQFCP"] = se_existir(icms_elemento, "pFCP")
            icms["VLRFCP"] = se_existir(icms_elemento, "vFCP")
            icms["BASEFCP"] = se_existir(icms_elemento, "vBCFCP")
            icms["MODBCST"] = se_existir(icms_elemento, "modBCST")
            icms["ALIQMVAST"] = se_existir(icms_elemento, "pMVAST")
            icms["REDBASEST"] = se_existir(icms_elemento, "pRedBCST")
            icms["BASEST"] = se_existir(icms_elemento, "vBCST")
            icms["ALIQICMSST"] = se_existir(icms_elemento, "pICMSST")
            icms["VLRICMSST"] = se_existir(icms_elemento, "vICMSST")
            icms["BASEFCPST"] = se_existir(icms_elemento, "vBCFCPST")
            icms["ALIQFCPST"] = se_existir(icms_elemento, "pFCPST")
            icms["VLRFCPST"] = se_existir(icms_elemento, "vFCPST")
            icms["VLRICMSDESONERADO"] = se_existir(icms_elemento, "vICMSDeson")
            icms["MOTIVODESONERACAO"] = se_existir(icms_elemento, "motDesICMS")
            icms["CSOSN"] = se_existir(icms_elemento, "CSOSN")
            icms["ALIQCREDITO"] = se_existir(icms_elemento, "pCredSN")
            icms["VALORCREDITO"] = se_existir(icms_elemento, "vCredICMSSN")
            icms["BASESTRETIDO"] = se_existir(icms_elemento, "vBCSTRet")
            icms["ALIQSTSUPORTADA"] = se_existir(icms_elemento, "pST")
            icms["VLRICMSSUBSTITUTO"] = se_existir(icms_elemento, "vICMSSubstituto")
            icms["VLRICMSSTRET"] = se_existir(icms_elemento, "vICMSSTRet")

            ipi = {}
            ipi_elemento = imposto_elemento.find("IPI")
            if ipi_elemento is not None:
                ipi["CST"] = se_existir(ipi_elemento, "IPITrib")

            produto["impostos"] = {"ICMS": icms, "IPI": ipi}
            produtos.append(produto)
        return produtos

    @property
    def produtos_config(self) -> list[dict[str, str]]:
        """
        Retorna informações presentes na aba "Produtos por Parceiro" da importação.
        Exemplo de retorno = [
            {
                "ALGUMITEMDOXMLTEMLOTEMED": "false",
                "CODPARC": "1338",
                "NOMEPARC": "JFTVTIPNJOVNTBMWBUPS EMITENTE",
                "CODPRODXML": "1",
                "PRODUTOXML": "botina 1",
                "UNIDADEXML": "UN",
                "QTDNEG": "1",
                "CODPROD": 2,
                "DESCRPROD": "SOYNKHYAPRODUTONORMAL3",
                "UNIDADE": "UN",
                "UNIDADELOTE": "",
                "CONTROLE": " ",
                "CODBARRAPARC": "AVEREGINACAELORUM89",
                "ERRO": "N",
                "FALTALOTE": "N",
                "TIPCONTEST": ""
            }
        ]
        """
        return [x.attrib for x in self.__config.iter("produto")]

    @property
    def produtos_ligados(self) -> list[dict[str, str | list[dict[str, str]]]]:
        """
        Retorna informações presentes na aba "Pedidos" da importação.
        Exemplo de retorno = [
            {
                "PRODUTO": "5",
                "SEQUENCIA": "1",
                "DESCRPROD": "botina 1",
                "CONTROLE": " ",
                "UNIDADE": "UN",
                "QTDALIGAR": "1",
                "VLRUNIT": "0",
                "QTDLIGADA": "0.0",
                "ligacao": [
                    {
                        "NUNOTA": "167361",
                        "NUMNOTA": "5503",
                        "SEQUENCIA": "1",
                        "DTMOV": "23/04/2025 13:38:57",
                        "QTDPENDENTE": "1",
                        "QTDLIG": "0",
                        "VLRUNIT": "0",
                        "QTDPENDENTEUNPAD": "1",
                        "CODTIPVENDA": "15",
                        "NUMCOTACAO": "",
                        "CODVOL": "UN",
                        "CODCENCUS": "102002",
                        "CODNAT": "1010000",
                        "CODPROJ": "0",
                        "DESCRTIPVENDA": "BB VENDA - 28 DIAS",
                        "DTPREVENTR": "",
                        "CODVEND": "0",
                        "OBSERVACAO": "SOYNKHYA: 1301"
                    },
                    ...
                ]
            }
        ]
        """
        resultado = []
        for produto in self.__config.iter("item"):
            atributos = produto.attrib
            atributos["ligacao"] = [x.attrib for x in produto.iter("ligacao")]
            resultado.append(atributos)
        return resultado

    @property
    def status(self) -> StatusXML:
        return StatusXML(int(self.cru["STATUS"]))

    @property
    def config_produtos(self) -> list[dict[str, str]]:
        """
        Exemplo de retorno:
        [
            {
                "ALGUMITEMDOXMLTEMLOTEMED": "false",
                "CODPARC": "777 {Código do parceiro (cliente)}",
                "NOMEPARC": "Nome do parceiro (cliente)",
                "CODPRODXML": "777 {Código do produto no xml}",
                "PRODUTOXML": "Nome do produto no xml",
                "UNIDADEXML": "UN {Unidade do produto no xml}",
                "QTDNEG": "8.0000 {Quantidade}",
                "CODPROD": "1195 {Código do produto no Soynkhya}",
                "DESCRPROD": "Nome do produto no Soynkhya",
                "UNIDADE": "UN {Unidade do produto no Soynkhya}",
                "UNIDADELOTE": "",
                "CONTROLE": " ",
                "CODBARRAPARC": "Código de barras do produto",
                "ERRO": "N",
            nova_importacao_crua = wrapper.soyquery(
                f"select * from tgfixn where nuarquivo={r["nuarquivo"]["$"]}"
            )
            assert (
                len(nova_importacao_crua) > 0
            ), "Importação foi criada, mas não está no banco de dados (????)"
            return cls(nova_importacao_crua[0], wrapper)
                "FALTALOTE": "N",
                "TIPCONTEST": ""
            },
            [...]
        ]
        """
        resultado = []
        for produto in self.__config.iter("produto"):
            resultado.append(produto.attrib)
        return resultado

    @property
    def divergencia_pedidos(self):
        return bool(self.__config.find("cabecalho").attrib.get("DIVERGENCIAPEDIDOS"))

    @property
    def divergencia_itens(self):
        return bool(self.__config.find("cabecalho").attrib.get("DIVERGENCIAITENS"))

    @property
    def divergencia_financeiro(self):
        return bool(self.__config.find("cabecalho").attrib.get("DIVERGENCIAFINANCEIRO"))

    @property
    def erro(self) -> str | None:
        cabecalho = self.__config.find("cabecalho")
        mensagem = ""
        if self.divergencia_pedidos:
            mensagem += "Divergência de pedidos ligados.\n"
        if self.divergencia_itens:
            mensagem += "Divergência de itens.\n"
        if self.divergencia_financeiro:
            mensagem += "Divergência de financeiro.\n"
        if (
            "validacoes" == self.__config.tag
            and self.__config.find("cabecalho") is None
        ):
            mensagem += " ".join(
                [elem.text for elem in self.__config.iter() if elem.text is not None]
            ).strip()
        if len(mensagem) > 0:
            return mensagem.strip()
        else:
            assert self.status != StatusXML.COM_DIVERGENCIA
            return None

    @property
    def parceiro(self) -> int | None:
        """
        Código do parceiro no Soynkhya.
        """
        _resultado = self.__nota_e_xml("codParc", True)["nota"]
        resultado = None
        if _resultado is not None:
            resultado = int(_resultado)
        return resultado

    @property
    def empresa(self) -> int | None:
        """
        Código da empresa (CODEMP) no Soynkhya.
        """
        _resultado = self.__nota_e_xml("codEmp", True)["nota"]
        resultado = None
        if _resultado is not None:
            resultado = int(_resultado)
        return resultado

    @property
    def config_cgc_empresa(self):
        return self.__nota_e_xml("cgcEmp")

    @property
    def config_inscricao_estadual_empresa(self):
        return self.__nota_e_xml("ieEmp")

    @property
    def config_nome_empresa(self):
        return self.__nota_e_xml("nomeEmp")

    @property
    def config_endereco_empresa(self):
        return self.__nota_e_xml("endEmp")

    @property
    def config_numero_empresa(self):
        return self.__nota_e_xml("nroEmp")

    @property
    def config_bairro_empresa(self):
        return self.__nota_e_xml("bairroEmp")

    @property
    def config_cidade_empresa(self):
        return self.__nota_e_xml("cidadeEmp")

    @property
    def config_uf_empresa(self):
        return self.__nota_e_xml("ufEmp")

    @property
    def config_cep_empresa(self):
        return self.__nota_e_xml("cepEmp")

    @property
    def config_pais_empresa(self):
        return self.__nota_e_xml("paisEmp")

    @property
    def config_fone_empresa(self):
        return self.__nota_e_xml("foneEmp")

    @property
    def config_inscricao_estadual_parc(self):
        return self.__nota_e_xml("ieParc")

    @property
    def config_nome_parceiro(self):
        return self.__nota_e_xml("nomeParc")

    @property
    def config_endereco_parceiro(self):
        return self.__nota_e_xml("endParc")

    @property
    def config_numero_parceiro(self):
        return self.__nota_e_xml("nroParc")

    @property
    def config_bairro_parceiro(self):
        return self.__nota_e_xml("bairroParc")

    @property
    def config_cidade_parceiro(self):
        return self.__nota_e_xml("cidadeParc")

    @property
    def config_uf_parceiro(self):
        return self.__nota_e_xml("ufParc")

    @property
    def config_cep_parceiro(self):
        return self.__nota_e_xml("cepParc")

    @property
    def config_pais_parceiro(self):
        return self.__nota_e_xml("paisParc")

    @property
    def config_fone_parceiro(self):
        return self.__nota_e_xml("foneParc")

    def processar(self):
        config = wrapper.soyconfig("br.com.sankhya.cac.ImportacaoXMLNota.config")
        print(wrapper.processar(self.nuarquivo, config, False))
        nova_importacao_crua = wrapper.soyquery(
            f"select * from tgfixn where nuarquivo={self.nuarquivo}"
        )
        return ImportacaoXML(nova_importacao_crua[0], self.wrapper)

    def __nota_e_xml(
        self, nome_da_tag: str, valores_numericos=False
    ) -> dict[str, str | int | None]:
        """
        Converte
        ```xml
        <nome_da_tag>
          <NOTA><![CDATA[nota]]></NOTA>
          <XML><![CDATA[xml]]></XML>
        </nome_da_tag>
        ```
        em
        ```json
        {
            "nota": "nota",
            "xml": "xml"
        }
        ```
        Se `valores_numericos` for `True`, os valores serão convertidos
        para `int`.
        """
        cabecalho = self.__config.find("cabecalho")
        assert cabecalho is not None
        cod_parc_tag = cabecalho.find(nome_da_tag)
        assert cod_parc_tag is not None
        _nota = cod_parc_tag.find("NOTA")
        nota: str | int | None = None
        if _nota is not None:
            nota = _nota.text
            if valores_numericos:
                if _nota.text is not None:
                    nota = int(_nota.text)
        _xml = cod_parc_tag.find("XML")
        xml: str | int | None = None
        if _xml is not None:
            xml = _xml.text
            if valores_numericos:
                if _xml.text is not None:
                    xml = int(_xml.text)
        return {"nota": nota, "xml": xml}

    @classmethod
    def novo(cls, caminho: str) -> typing.Self:
        config = wrapper.soyconfig("br.com.sankhya.cac.ImportacaoXMLNota.config")
        wrapper.upload("IMPORTACAO_XML_ZIPXML", caminho, "text/xml")
        resposta_importacao = wrapper.importar_arquivo(config)
        assert "responseBody" in resposta_importacao, json.dumps(
            resposta_importacao, indent=4
        )
        r = resposta_importacao["responseBody"]
        if "nuarquivo" in r:
            nova_importacao_crua = wrapper.soyquery(
                f"select * from tgfixn where nuarquivo={r["nuarquivo"]["$"]}"
            )
            assert (
                len(nova_importacao_crua) > 0
            ), "Importação foi criada, mas não está no banco de dados (????)"
            return cls(nova_importacao_crua[0], wrapper)
        assert (
            "statusMessage" not in resposta_importacao
        ), f"Mensagem de erro (status: {resposta_importacao["status"]}): {resposta_importacao["statusMessage"]}"

        assert "aviso" not in r, r["aviso"]["$"]
        raise Exception(json.dumps(resposta_importacao, indent=4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Importe notas sem interagir com o Soynkhya :)"
    )
    subparsers = parser.add_subparsers(dest="comando")

    editar_parser = subparsers.add_parser(
        "editar", help="Importa XML da nota de importação para que seja editado."
    )
    editar_parser.add_argument("nuarquivo", type=int, help="Id da importação.")

    gravar_parser = subparsers.add_parser(
        "gravar", help="Grava edição feita no xml duma importação."
    )
    gravar_parser.add_argument("nuarquivo", type=int, help="Id da importação.")

    args = parser.parse_args()

    if args.comando == "editar":
        importacao = wrapper.soyquery(
            f"select xml from tgfixn where nuarquivo = {args.nuarquivo}"
        )
        importacao_xml = importacao[0]["XML"]
        os.makedirs("importacoes", exist_ok=True)
        with open(os.path.join("importacoes", f"{args.nuarquivo}.xml"), "w") as f:
            f.write(importacao_xml)
        print("Sucesso.")
    if args.comando == "gravar":
        caminho = os.path.join("importacoes", f"{args.nuarquivo}.xml")
        os.path.exists(caminho)
        with open(caminho, "r") as f:
            importacao_xml = f.read()
            wrapper.soysave(
                "ImportacaoXMLNotas",
                [
                    {
                        "pk": {"NUARQUIVO": args.nuarquivo},
                        "mudanca": {"XML": importacao_xml},
                    }
                ],
            )
            print("Sucesso.")
    # wrapper.imprimir_notas(
    #     [
    #         wrapper.soyquery(
    #             f"select nunota from tgfcab where numnota={args.argumento} and statusnota='L' and codtipoper=1101"
    #         )[0]["NUNOTA"]
    #     ],
    #     TipoImpressao.BOLETO,
    # )

# wrapper.processar(bruh["NUARQUIVO"], config, False)
# print(
#     wrapper.soyquery(
#         "select config from tgfixn where nuarquivo = " + str(bruh["NUARQUIVO"])
#     )[0]["CONFIG"]
# )

# print(xml.dom.minidom.parseString(bruh["XML"]).toprettyxml(indent=" "))
# print(wrapper.processar(bruh["NUARQUIVO"], config, False))
