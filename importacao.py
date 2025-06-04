from utils import *
import typing
import xml.dom.minidom
from rich import print
import xml.etree.ElementTree as ET
import argparse
from config import *
from enum import Enum


class RegimeTributario(Enum):
    SIMPLES_NACIONAL = 0
    NORMAL = 1


class CST(Enum):
    TRIBUTADA_INTEGRALMENTE = "00"
    TRIBUTADA_E_COM_ST = "10"
    COM_REDUCAO_DA_BC = "20"
    ISENTA_OU_NÃO_TRIBUTADA_E_COM_ST = "30"
    ISENTA = "40"
    NAO_TRIBUTADA = "41"
    COM_SUSPENSAO = "50"
    COM_DIFERIMENTO = "51"
    ICMS_COBRADO_ANTERIORMENTE_POR_ST = "60"
    COM_REDUCAO_DA_BC_E_ST = "70"
    OUTRAS = "90"


class CSOSN(Enum):
    NAO_E_SIMPLES_NACIONAL = "0"
    TRIBUTADA_PELO_SN_COM_PERMISSAO_DE_CREDITO = "101"
    TRIBUTADA_PELO_SN_SEM_PERMISSAO_DE_CREDITO = "102"
    ISENCAO_DO_ICMS_NO_SN_PARA_FAIXA_DE_RECEITA_BRUTA = "103"
    TRIBUTADA_PELO_SN_COM_PERMISSAO_DE_CREDITO_E_COM_ST = "201"
    TRIBUTADA_PELO_SN_SEM_PERMISSAO_DE_CREDITO_E_COM_ST = "202"
    ISENCAO_DO_ICMS_NO_SN_PARA_FAIXA_DE_RECEITA_BRUTA_E_COM_ST = "203"
    IMUNE = "300"
    NAO_TRIBUTADA_PELO_SN = "400"
    ICMS_COBRADO_ANTERIORMENTE_POR_ST_SUBSTITUIDO_OU_POR_ANTECIPACAO = "500"
    OUTRO = "900"


def margem_lucro(
    regime_tributario: RegimeTributario, cst: CST, aliquota_icms: float, csosn: CSOSN
) -> float:
    """
    Retorna a margem de lucro associada com os argumentos.
    """
    if regime_tributario == RegimeTributario.SIMPLES_NACIONAL:
        if csosn in [CSOSN("201"), CSOSN("202"), CSOSN("203"), CSOSN("500")]:
            return 30
        else:
            return 41.5
    elif regime_tributario == RegimeTributario.NORMAL:
        if cst == CST.TRIBUTADA_INTEGRALMENTE:
            if aliquota_icms == 4:
                return 40.25
        elif cst == CST.TRIBUTADA_E_COM_ST:
            return 41
        elif cst in [
            CST.ICMS_COBRADO_ANTERIORMENTE_POR_ST,
            CST.ISENTA_OU_NÃO_TRIBUTADA_E_COM_ST,
        ]:
            return 30
        elif cst == CST.COM_REDUCAO_DA_BC_E_ST:
            return 41.5
    return 35.7


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

    def icms(
        self,
        x: dict[str, str | dict[str, str | dict[str, str | dict[str, str]]]],
        observacao: str | None = None,
    ):
        assert isinstance(x["impostos"], dict)
        assert isinstance(x["impostos"]["ICMS"], dict)
        assert isinstance(x["NCM"], str)
        impostos = x["impostos"]["ICMS"]
        assert (
            isinstance(impostos["ALIQSTSUPORTADA"], str)
            or impostos["ALIQSTSUPORTADA"] is None
        )
        assert isinstance(impostos["ALIQFCP"], str) or impostos["ALIQFCP"] is None
        assert isinstance(impostos["REDBASE"], str) or impostos["REDBASE"] is None
        assert isinstance(impostos["CST"], str) or impostos["CST"] is None

        def pedir_observacao():
            # nonlocal observacao
            if observacao is not None:
                return wrapper.soysave(
                    "ObservacaoNotasFiscais",
                    [{"mudanca": {"CODOBSPADRAO": "", "OBSERVACAO": observacao}}],
                )[0]["CODOBSPADRAO"]

            obs_correta = input(
                """\
Digita a observação correta. Há um limite de 255 caracteres.
Caso não queiras criar uma regra nova, aperta enter sem ter digitado nada:\
"""
            )
            if obs_correta.strip() == "":
                return None
            assert len(obs_correta) < 256
            codigo_observacao = wrapper.soysave(
                "ObservacaoNotasFiscais",
                [{"mudanca": {"CODOBSPADRAO": "", "OBSERVACAO": obs_correta}}],
            )[0]["CODOBSPADRAO"]
            return codigo_observacao

        uforig = self.config_uf_empresa["xml"]
        ufdest = self.config_uf_parceiro["xml"]

        if uforig == ufdest:
            uforig = self.wrapper.soyquery(
                f"select coduf from tsiufs where uf='{uforig}'"
            )[0]["CODUF"]
            ufdest = uforig
        else:
            uforig = self.wrapper.soyquery(
                f"select coduf from tsiufs where uf='{uforig}'"
            )[0]["CODUF"]
            ufdest = self.wrapper.soyquery(
                f"select coduf from tsiufs where uf='{ufdest}'"
            )[0]["CODUF"]

        aliquota = float(impostos["ALIQSTSUPORTADA"] or 0) - float(
            impostos["ALIQFCP"] or 0
        )
        aliquota_frete = aliquota if aliquota != 4 else 0

        regras: list[dict[str, dict[str, int | float | str]]] = []
        for tipo_de_restricao in ["N", "H"]:
            regras.append(
                {
                    "mudanca": {
                        "REDBASEESTRANGEIRA": 0,
                        "ALIQUOTA": aliquota,
                        "REDBASE": impostos["REDBASE"] or 0,
                        "ALIQFRETE": aliquota_frete,
                        "CODTRIB": impostos["CST"],
                    },
                    "pk": {
                        "UFORIG": uforig,
                        "SEQUENCIA": 1,
                        "UFDEST": ufdest,
                        "TIPRESTRICAO": tipo_de_restricao,
                        "TIPRESTRICAO2": "H",
                        "CODRESTRICAO": -1,
                        "CODRESTRICAO2": x["NCM"],
                    },
                }
            )
        r = regras[0]
        regras_existentes = self.wrapper.soyquery(
            f"""
        select * from tgficm i
        join tgfobs o on o.codobspadrao=i.codobspadrao
        where uforig = {r["pk"]["UFORIG"]}
        and ufdest = {r["pk"]["UFDEST"]}
        and tiprestricao in ('N', 'H')
        and codrestricao2 = '{r["pk"]["CODRESTRICAO2"]}'
        """
        )
        if len(regras_existentes) > 0:
            r_e = regras_existentes[0]
            if (
                float(r["mudanca"]["ALIQUOTA"]) == float(r_e["ALIQUOTA"])
                and float(r["mudanca"]["REDBASE"]) == float(r_e["REDBASE"])
                and int(r["mudanca"]["CODTRIB"]) == int(r_e["CODTRIB"])
            ):
                return None
            else:
                print(
                    f"""\
Já existe uma regra de ICMS para o NCM {r_e["CODRESTRICAO2"]}.
Tu terás duas opções: manter a regra atual ou sobrescrevê-la.
Regra que será criada <=> Regra existente
{r["mudanca"]["ALIQUOTA"]} <=> {r_e["ALIQUOTA"]} Alíquota
{r["mudanca"]["REDBASE"]} <=> {r_e["REDBASE"]} Redução
{r["mudanca"]["CODTRIB"]} <=> {r_e["CODTRIB"]} CST
**********OBSERVAÇÃO DA NOTA*********************
{self.observacao}
**********OBSERVAÇÃO DA REGRA EXISTENTE**********
{regras_existentes[0]["OBSERVACAO"]}
*************************************************\
"""
                )
                cod_observacao = pedir_observacao()
                if cod_observacao is None:
                    return None
                for regra in regras:
                    regra["mudanca"].update({"CODOBSPADRAO": cod_observacao})
        else:
            print(
                f"""\
Tu terás agora a opção de criar uma nova regra de icms.
**********OBSERVAÇÃO DA NOTA**********
{self.observacao}
**************************************\
"""
            )
            cod_observacao = pedir_observacao()
            if cod_observacao is None:
                return None
            for regra in regras:
                regra["mudanca"].update({"CODOBSPADRAO": cod_observacao})
        regras_criadas = wrapper.soysave(
            "AliquotaICMS",
            regras,
        )

        return regras_criadas

    def ajustar_produtos(self, observacao: str | None = None):
        p_config = self.produtos_config
        p_xml = self.produtos_xml
        for c in p_config:
            x = [a for a in p_xml if str(a["CODPROD"]) == str(c["CODPRODXML"])][0]
            ipi = float(x["impostos"]["IPI"]["VALOR"])
            _ipi_codigo = self.wrapper.soyquery(
                f"select CODIPI from tgfipi where percentual={str(ipi)}"
            )
            ipi_cadastrado = len(_ipi_codigo) > 0
            if not ipi_cadastrado:
                novo_ipi = self.wrapper.soysave(
                    "AliquotaIPI",
                    [
                        {
                            "mudanca": {
                                "CODIPI": "",
                                "PERCENTUAL": ipi,
                                "DESCRICAO": f"IPI %{ipi}",
                            }
                        }
                    ],
                )
                ipi_codigo = novo_ipi[0]["CODIPI"]
            else:
                ipi_codigo = _ipi_codigo[0]["CODIPI"]
            mudanca = {
                "NCM": x["NCM"],
                "ORIGPROD": x["impostos"]["ICMS"]["ORIGEM"],
                "TEMIPICOMPRA": ("S" if ipi > 0 else "N"),
                "CODIPI": ipi_codigo,
            }
            if int(x["impostos"]["ICMS"]["CST"]) in [70, 60, 10]:
                # TODO: criar uma regra decente de imposto aqui
                mudanca["GRUPOICMS"] = 1000

            csosn = x["impostos"]["ICMS"]["CSOSN"] or "0"
            cst = x["impostos"]["ICMS"]["CST"] or "1"
            aliquota = x["impostos"]["ICMS"]["ALIQUOTA"] or 0
            regime = 1 if csosn is None else 0
            margem = margem_lucro(
                RegimeTributario(regime), CST(cst), float(aliquota), CSOSN(csosn)
            )
            mudanca["MARGLUCRO"] = margem

            ja_existe_codbarra = (
                len(
                    self.wrapper.soyquery(
                        f"select 1 from tgfbar where codbarra='{x["CODBARRA"]}'"
                    )
                )
                > 0
            )
            self.icms(x, observacao)
            if not ja_existe_codbarra:
                self.wrapper.soysave(
                    "CodigoBarras",
                    [{"mudanca": {"CODPROD": c["CODPROD"], "CODBARRA": x["CODBARRA"]}}],
                )
            self.wrapper.soysave(
                "Produto",
                [
                    {
                        "pk": {"CODPROD": c["CODPROD"]},
                        "mudanca": mudanca,
                    }
                ],
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
    def observacao(self) -> str | None:
        el = self.__xml.find("NFe")
        assert el is not None
        el = el.find("infNFe")
        assert el is not None
        el = el.find("infAdic")
        if el is not None:
            el = el.find("infCpl")
            if el is not None:
                return el.text
        return None

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
    def produtos_xml(
        self,
    ) -> list[dict[str, str | dict[str, str | dict[str, str | None]] | None]]:
        produtos = []

        def se_existir(pai: ET.Element, nome: str) -> str | None:
            iterador = list(pai.iter(nome))
            if len(iterador) > 0:
                return iterador[0].text
            else:
                return None

        for det in self.__xml.iter("det"):
            produto_elemento = det.find("prod")
            assert produto_elemento is not None
            produto: dict[str, str | dict[str, str | dict[str, str | None]] | None] = {}
            produto["CODPROD"] = se_existir(produto_elemento, "cProd")
            produto["CODBARRA"] = se_existir(produto_elemento, "cEAN")
            produto["DESCRPROD"] = se_existir(produto_elemento, "xProd")
            produto["NCM"] = se_existir(produto_elemento, "NCM")
            produto["CODCFO"] = se_existir(produto_elemento, "CFOP")
            produto["CODVOL"] = se_existir(produto_elemento, "uCom")
            produto["QTDNEG"] = se_existir(produto_elemento, "qCom")
            produto["VLRUNIT"] = se_existir(produto_elemento, "vUnCom")
            produto["VLRTOT"] = se_existir(produto_elemento, "vProd")
            produto["CODBARRATRIB"] = se_existir(produto_elemento, "cEANTrib")
            produto["CODVOLTRIB"] = se_existir(produto_elemento, "uTrib")
            produto["QTDNEGTRIB"] = se_existir(produto_elemento, "qTrib")
            produto["VLRUNITTRIB"] = se_existir(produto_elemento, "vUnTrib")
            produto["SEQUENCIA"] = se_existir(produto_elemento, "nItemPed")
            produto["INDTOT"] = se_existir(produto_elemento, "indTot")

            imposto_elemento = det.find("imposto")
            assert imposto_elemento is not None
            icms = {}
            icms_elemento = imposto_elemento.find("ICMS")
            assert icms_elemento is not None
            icms["CST"] = se_existir(icms_elemento, "CST")
            icms["ORIGEM"] = se_existir(icms_elemento, "orig")
            icms["MODBC"] = se_existir(icms_elemento, "modBC")
            icms["REDBASE"] = se_existir(icms_elemento, "pRedBC")
            icms["BASE"] = se_existir(icms_elemento, "vBC")
            icms["ALIQUOTA"] = se_existir(icms_elemento, "pICMS")
            icms["VALOR"] = se_existir(icms_elemento, "vICMS")
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
                tributacao = ipi_elemento.find("IPITrib")
                if tributacao is not None:
                    ipi["CST"] = se_existir(tributacao, "CST")
                    ipi["VALOR"] = se_existir(tributacao, "vIPI")

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
    def divergencia_pedidos(self) -> bool:
        cabecalho = self.__config.find("cabecalho")
        if cabecalho is None:
            return False
        return bool(cabecalho.attrib.get("DIVERGENCIAPEDIDOS"))

    @property
    def divergencia_itens(self) -> bool:
        cabecalho = self.__config.find("cabecalho")
        if cabecalho is None:
            return False
        return bool(cabecalho.attrib.get("DIVERGENCIAITENS"))

    @property
    def divergencia_financeiro(self) -> bool:
        cabecalho = self.__config.find("cabecalho")
        if cabecalho is None:
            return False
        return bool(cabecalho.attrib.get("DIVERGENCIAFINANCEIRO"))

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
        self.wrapper.validar_importacao(
            self.nuarquivo,
            config,
            False,
            [],
            [],
            False,
            False,
            Impostos_Financeiro.DO_ARQUIVO,
            Impostos_Financeiro.DO_ARQUIVO,
            False,
            False,
        )

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


def comando_importar(
    danfe: str,
    ocs: str | None = None,
    escolha_importacao: int | None = None,
    associacoes_codigo: str | None = None,
    associacoes_sequencia: str | None = None,
    associacoes_ordem: bool | None = None,
):
    if len(danfe) == 43:
        _imp = wrapper.soyquery(
            f"select * from tgfixn i join tgfpar p on i.codparc=p.codparc where chaveacesso={danfe}"
        )
    else:
        _imp = wrapper.soyquery(
            f"select * from tgfixn i join tgfpar p on i.codparc=p.codparc where numnota={danfe}"
        )

    if len(_imp) == 0:
        print("Nenhuma nota encontrada.")
        return
    elif len(_imp) > 1:
        importacoes_resumidas = []
        a = 1
        for i in _imp:
            i.update({"Número": a})
            a = a + 1
            importacoes_resumidas.append(
                escolher_chaves(i, ["Número", "CHAVEACESSO", "NOMEPARC", "VLRNOTA"])
            )
        print("Mais de uma nota encontrada. Escolha uma destas:")
        wrapper.printar_tabela(importacoes_resumidas, ["TGFIXN", "TGFPAR"])
        if escolha_importacao is None:
            escolha_importacao = int(
                input("Usa um número da coluna 'Números' para selecionar uma nota: ")
            )
        chave_acesso = [
            x for x in importacoes_resumidas if x["Número"] == escolha_importacao
        ][0]["CHAVEACESSO"]
        _imp = [x for x in _imp if x["CHAVEACESSO"] == chave_acesso]

    imp = ImportacaoXML(_imp[0], wrapper)

    if imp.erro:
        print(
            f"[bold red]Chave de acesso: {imp.cru["CHAVEACESSO"]}\n{imp.erro}[/bold red]"
        )
    produtos_fusao = []
    a = 0
    for px in imp.produtos_xml:
        a = a + 1
        for pc in imp.produtos_config:
            if pc["CODPRODXML"] == px["CODPROD"]:
                produto_fusao = {
                    "Número": a,
                    "CODBARRA": px["CODBARRA"],
                    "CODPROD": px["CODPROD"],
                    "CODVOL": px["CODVOL"],
                    "DESCRPROD": px["DESCRPROD"],
                    "VLRUNIT": px["VLRUNIT"],
                    "QTDNEG": px["QTDNEG"],
                    "Cód. Produto no Soynkhya": pc["CODPROD"],
                    "Descrição no Soynkhya": pc["DESCRPROD"],
                }
                produtos_fusao.append(produto_fusao)
    wrapper.printar_tabela(
        produtos_fusao, ["TGFITE", "TGFBAR", "TGFPRO"], titulo="Itens do XML"
    )
    produtos_ocs = None
    if ocs is not None:
        produtos_ocs = wrapper.soyquery(
            f"""
            select c.nunota, i.codprod, descrprod, i.codvol, vlrunit, qtdneg, codparc
            from tgfite i
            join tgfpro p on i.codprod=p.codprod
            join tgfcab c on c.nunota=i.nunota
            where i.nunota in ({ocs})
            """
        )
        wrapper.printar_tabela(
            produtos_ocs, ["TGFITE", "TGFPRO"], titulo="Itens das OCs"
        )
        assert len(produtos_ocs) >= len(
            produtos_fusao
        ), "Há menos produtos nas OCs do que na importação."
        for p in produtos_ocs:
            assert str(imp.parceiro) == str(
                p["CODPARC"]
            ), f"A OC {str(p["NUNOTA"])} tem {str(p["CODPARC"])} como parceiro. Esse não é o fornecedor que está na importação (Código {str(imp.parceiro)})."

    if not associacoes_codigo and not associacoes_ordem and not associacoes_sequencia:
        return {"importacao": imp}
    if associacoes_codigo:
        _associacoes = associacoes_codigo.split(",")
        assert len(_associacoes) == len(
            produtos_fusao
        ), f"O quantidade de códigos associados deve ser {len(produtos_fusao)}, não {len(_associacoes)}."

        associacoes = []
        for codigo, produto in zip(_associacoes, produtos_fusao):
            codigo = codigo.strip()
            if codigo == "*":
                assert isinstance(produto["Cód. Produto no Soynkhya"], str)
                codigo = produto["Cód. Produto no Soynkhya"]
            else:
                assert codigo.isdigit(), f"O código {codigo} não é um número inteiro."
            associacoes.append(codigo)

        assoyciacoes = []
        for associacao, produto in zip(associacoes, produtos_fusao):
            assoc_bd = wrapper.soyquery(
                f"select codprod, codvol unidade, descrprod from tgfpro where codprod={associacao}"
            )
            assert len(assoc_bd) == 1, f"Item {associacao} não existe no sistema."
            assoyciacoes.append(
                {
                    "CODPROD": assoc_bd[0]["CODPROD"],
                    "UNIDADE": assoc_bd[0]["UNIDADE"],
                    "CODPRODXML": produto["CODPROD"],
                    "DESCRPROD": assoc_bd[0]["DESCRPROD"],
                }
            )
    elif associacoes_sequencia or associacoes_ordem:
        assert (
            ocs and produtos_ocs
        ), "Só é possível associar sequencialmente quando o usuário informa OCs que têm produtos."
        if associacoes_sequencia:
            assert produtos_ocs, "Era pra ser impossível tu veres esta mensagem."
            _associacoes = associacoes_sequencia.split(",")
            assert len(_associacoes) == len(
                produtos_fusao
            ), f"O quantidade de associações deve ser {len(produtos_fusao)}, não {len(_associacoes)}."
        elif associacoes_ordem:
            _associacoes = [str(i + 1) for i in range(len(produtos_fusao))]
        assoyciacoes = []
        for id, associacao in enumerate(_associacoes):
            prod_assoc = produtos_ocs[int(associacao) - 1]
            assoyciacoes.append(
                {
                    "CODPROD": prod_assoc["CODPROD"],
                    "UNIDADE": prod_assoc["CODVOL"],
                    "CODPRODXML": produtos_fusao[id]["CODPROD"],
                    "DESCRPROD": prod_assoc["DESCRPROD"],
                }
            )

    imp.associar(assoyciacoes)
    return {"importacao": imp}


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

    importar_parser = subparsers.add_parser("importar", help="Importa nota.")
    importar_parser.add_argument("danfe", type=int, help="Número da nota.")
    importar_parser.add_argument(
        "-o", "--ocs", type=int, help="Número das ordens de compra."
    )
    importar_parser.add_argument(
        "-c", "--codigo", type=str, help="Associação por código (i.e. '7777,1234,*')."
    )
    importar_parser.add_argument(
        "-s",
        "--sequencia",
        type=str,
        help="Associação por sequência dos itens nas OCs (i.e. '3,1,2').",
    )
    importar_parser.add_argument(
        "-o",
        "--ordem",
        action="store_true",
        help="Associação na ordem das OCs.",
    )

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
    if args.comando == "importar":
        comando_importar(
            args.danfe,
            args.ocs,
            None,
            args.codigo,
            args.sequencia,
            args.ordem,
        )
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
