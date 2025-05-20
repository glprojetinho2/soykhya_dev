import unittest
import random
import tempfile
import pytest
import zipfile
import os
from utils import *
from importacao import *
from faturamento import *
from config import *
from botao import *
from bi import *


def importacao_teste(nome: str) -> ImportacaoXML:
    importacao_crua = wrapper.soyquery(
        f"select * from tgfixn where xml like '%SOYNKHYA: {nome.upper()}%'"
    )
    assert len(importacao_crua) <= 1, "Mais de uma importação."
    if len(importacao_crua) == 1:
        importacao = ImportacaoXML(importacao_crua[0], wrapper)
        importacao.processar()
        return importacao
    else:
        for _, __, arquivos in os.walk("xmls_teste/"):
            for arquivo in arquivos:
                print(arquivo)
                try:
                    ImportacaoXML.novo("xmls_teste/" + arquivo)
                except:
                    pass
                importacoes_cruas = wrapper.soyquery(
                    f"select * from tgfixn where xml like '%SOYNKHYA:%'"
                )
                cnpj_empresa_padrao = wrapper.soyquery(
                    f"select cgc from tsiemp where codemp={CONFIG.codigo_empresa_padrao}"
                )[0]["CGC"]
                top = wrapper.soyquery(
                    "select codtipoper from tgfcab where tipmov='C' and statusnota='L' group by codtipoper order by count(codtipoper) desc fetch first 1 rows only"
                )[0]["CODTIPOPER"]
                wrapper.soysave(
                    "ImportacaoXMLNotas",
                    [
                        {
                            "pk": {"NUARQUIVO": i["NUARQUIVO"]},
                            "mudanca": {
                                "XML": str(i["XML"]).replace(
                                    "{{EMPRESA}}", cnpj_empresa_padrao
                                ),
                                "CODTIPOPER": top,
                                "CNPJDEST": cnpj_empresa_padrao,
                            },
                        }
                        for i in importacoes_cruas
                    ],
                )
        importacao_crua = wrapper.soyquery(
            f"select * from tgfixn where xml like '%SOYNKHYA: {nome.upper()}%'"
        )
        assert len(importacao_crua) == 1
        importacao = ImportacaoXML(importacao_crua[0], wrapper)
        importacao.processar()
        return importacao


def gerar_configuracao_dos_testes():
    pass


class TestImportacao(unittest.TestCase):
    def test_ajuste_produtos(self):
        importacao = importacao_teste("simples")
        produto = produto_normal()
        ncm = "84716052"
        _ipi_sojado = wrapper.soyquery(f"select CODIPI from tgfipi where percentual>0")
        wrapper.soysave(
            "Produto",
            [
                {
                    "pk": {"CODPROD": produto},
                    "mudanca": {
                        "NCM": ncm,
                        "ORIGPROD": 7,
                        "TEMIPICOMPRA": "S",
                        "CODIPI": _ipi_sojado[0]["CODIPI"],
                    },
                }
            ],
        )
        top = wrapper.soyquery(
            "select codtipoper from tgfcab where tipmov='O' and statusnota='L' group by codtipoper order by count(codtipoper) desc fetch first 1 rows only"
        )[0]["CODTIPOPER"]
        pedido = criar_documento(
            int(top),
            {"CODPARC": importacao.cru["CODPARC"]},
            [
                {
                    "CODPROD": produto,
                    "CODVOL": "UN",
                    "QTDNEG": 2,
                }
            ],
        )
        wrapper.confirmar_documento([int(pedido["NUNOTA"])])
        importacao.associar([{"CODPRODXML": 1, "CODPROD": produto, "UNIDADE": "UN"}])
        importacao.ajustar_produtos()
        produto_atualizado = wrapper.soyquery(
            f"select * from tgfpro where codprod={produto}"
        )[0]

        self.assertEqual(produto_atualizado["NCM"], "95059000")
        self.assertEqual(produto_atualizado["ORIGPROD"], "0")
        self.assertEqual(produto_atualizado["TEMIPICOMPRA"], "N")

    def test_ajuste_muda_ipi(self):
        pass

    def test_produtos_xml(self):
        for x in wrapper.soyquery(
            "select * from tgfixn where config is not null and tipo='N' fetch first 100 rows only"
        ):
            importacao = ImportacaoXML(x, wrapper)
            print("******************")
            print(x["NUARQUIVO"])
            print(x["XML"])
            print(json.dumps(importacao.produtos_xml, indent=4))
            print("******************")

    def test_associacao_e_ligacao(self):
        importacao = importacao_teste("simples")
        top = wrapper.soyquery(
            "select codtipoper from tgfcab where tipmov='O' and statusnota='L' group by codtipoper order by count(codtipoper) desc fetch first 1 rows only"
        )[0]["CODTIPOPER"]

        produto_qualquer = wrapper.soyquery(
            "select codprod, codvol unidade from tgfpro where descrprod not like '%SOYNKHYA%' and ativo = 'S' fetch first 1 rows only"
        )[0]
        outro_produto_qualquer = wrapper.soyquery(
            f"select codprod, codvol unidade from tgfpro where codprod <> {produto_qualquer["CODPROD"]} and descrprod not like '%SOYNKHYA%' and ativo = 'S' fetch first 1 rows only"
        )[0]
        produto_qualquer.update({"CODPRODXML": "1"})
        outro_produto_qualquer.update({"CODPRODXML": "1"})
        importacao.associar(
            [produto_qualquer],
        )
        print(json.dumps(importacao.produtos_config, indent=4))
        importacao = importacao.atualizar()
        self.assertEqual(
            importacao.produtos_config[0]["CODPROD"], str(produto_qualquer["CODPROD"])
        )
        self.assertEqual(
            importacao.produtos_config[0]["UNIDADE"], str(produto_qualquer["UNIDADE"])
        )

        # Criação da ordem de compra
        top = wrapper.soyquery(
            "select codtipoper from tgfcab where tipmov='O' and statusnota='L' group by codtipoper order by count(codtipoper) desc fetch first 1 rows only"
        )[0]["CODTIPOPER"]

        pedido = criar_documento(
            int(top),
            {"CODPARC": importacao.cru["CODPARC"]},
            [
                {
                    "CODPROD": outro_produto_qualquer["CODPROD"],
                    "CODVOL": "UN",
                    "QTDNEG": 2,
                }
            ],
        )
        wrapper.confirmar_documento([int(pedido["NUNOTA"])])

        importacao.associar(
            [outro_produto_qualquer],
        )
        importacao = importacao.atualizar()
        importacao.ligar_pedidos_mais_antigos()
        importacao = importacao.atualizar()
        self.assertEqual(
            importacao.produtos_config[0]["CODPROD"],
            str(outro_produto_qualquer["CODPROD"]),
        )
        self.assertEqual(
            importacao.produtos_config[0]["UNIDADE"],
            str(outro_produto_qualquer["UNIDADE"]),
        )
        self.assertNotEqual(float(importacao.produtos_ligados[0]["QTDLIGADA"]), 0)


@pytest.fixture(scope="session", autouse=True)
def limpar():
    yield
    notas_aprovadas = wrapper.soyquery(
        "select nunota from tgfcab where observacao like '%SOYNKHYA: %' and statusnfe='A'"
    )

    wrapper.cancelar_nota(
        [int(nota["NUNOTA"]) for nota in notas_aprovadas],
        "Nota era apenas um teste.",
    )
    total_de_documentos = len(
        wrapper.soyquery(
            """select nunota, statusnfe from tgfcab c
where observacao like '%SOYNKHYA: %'"""
        )
    )
    documentos_excluidos = 0
    while documentos_excluidos != total_de_documentos:
        documentos = wrapper.soyquery(
            """select nunota, statusnfe, statusnota from tgfcab c
where observacao like '%SOYNKHYA: %' and
(select count(*) from tgfvar where nunotaorig=c.nunota) = 0"""
        )
        if len(documentos) == 0:
            break
        documentos_nao_confirmados = [
            str(r["NUNOTA"]) for r in documentos if r["STATUSNOTA"] != "L"
        ]
        if len(documentos_nao_confirmados) > 0:
            liberacoes = wrapper.soyquery(
                f"select * from tsilib where nuchave in ({", ".join(documentos_nao_confirmados)}) and dhlib is null"
            )
            if len(liberacoes) > 0:
                liberacao_exemplo = wrapper.soyquery(
                    "select codusulib, evento, tabela from tsilib where dhlib is not null order by dhlib desc fetch first 1 rows only"
                )[0]
                ja_liberado = {
                    "VLRTOTAL": 1,
                    "VLRATUAL": 1,
                    "VLRLIBERADO": 1,
                    "VLRLIMITE": 1,
                    "DHLIB": "03/03/2022 21:20:12",
                }
                ja_liberado.update(liberacao_exemplo)
                wrapper.soysave(
                    "LiberacaoLimite",
                    [
                        {
                            "pk": liberacao,
                            "mudanca": ja_liberado,
                        }
                        for liberacao in liberacoes
                    ],
                )
            wrapper.confirmar_documento(documentos_nao_confirmados)
        documentos_nunota = [str(x["NUNOTA"]) for x in documentos]
        produtos = wrapper.soyquery(
            f"select nunota, i.codprod, sequencia, i.codemp from tgfite i join tgfest e on i.codprod=e.codprod join tgfpro p on i.codprod=p.codprod where nunota in ({", ".join(documentos_nunota)}) and p.descrprod like '%SOYNKHYA%'"
        )
        wrapper.soysave(
            "ItemNota",
            [
                {
                    "pk": {
                        "NUNOTA": produto["NUNOTA"],
                        "SEQUENCIA": produto["SEQUENCIA"],
                    },
                    "mudanca": {
                        "QTDNEG": 1,
                        "VLRUNIT": 0.0000001,
                        "VLRTOT": 0.0000001,
                        "CODCFO": 5102,
                        "CODVOL": "UN",
                    },
                }
                for produto in produtos
            ],
        )

        nota_mudanca = wrapper.soyquery(
            "select codparc from tgfpar where classificms='C' fetch first 1 rows only"
        )[0]
        wrapper.soysave(
            "CabecalhoNota",
            [
                {
                    "pk": documento,
                    "mudanca": nota_mudanca,
                }
                for documento in documentos
                if documento["STATUSNFE"] is not None and documento["STATUSNFE"] != "A"
            ],
        )
        documentos_lote = [
            int(documento["NUNOTA"])
            for documento in documentos
            if documento["STATUSNFE"] is not None and documento["STATUSNFE"] != "A"
        ]
        if len(documentos_lote) > 0:
            wrapper.gerar_lote(documentos_lote)
        # print(
        #     "\n".join(
        #         [
        #             x["OCORRENCIAS"]
        #             for x in wrapper.soyquery(
        #                 f"select ocorrencias from tgfact where nunota in ({", ".join(documentos_nunota)}) order by dhocor desc"
        #             )
        #         ]
        #     )
        # )
        wrapper.cancelar_nota(
            documentos_nunota,
            "Nota era apenas um teste.",
        )
        wrapper.soyremove(
            "CabecalhoNota",
            wrapper.soyquery(
                """select nunota from tgfcab c
where observacao like '%SOYNKHYA: %' and
(select count(*) from tgfvar where nunotaorig=c.nunota) = 0"""
            ),
        )
        documentos_excluidos_anteriormente = documentos_excluidos
        documentos_excluidos += len(documentos)
        assert documentos_excluidos > documentos_excluidos_anteriormente
    componentes = wrapper.soyquery(
        "select nugdg from tsigdg where titulo = 'TESTE GRAVAÇÃO'"
    )
    wrapper.soyremove("Gadget", componentes)


# limpar()


def parceiro_anti_sefaz() -> int:
    """
    Retorna o código de um contribuinte sem inscrição estadual.
    O intuito desse parceiro é fazer com que a SEFAZ rejeite as notas
    que o tiverem como remetente.
    """
    nome = "SOYNKHYAANTISEFAZ"
    pesquisa = wrapper.soyquery(f"select codparc from tgfpar where nomeparc='{nome}'")
    if len(pesquisa) > 0:
        return int(pesquisa[0]["CODPARC"])
    parceiro = wrapper.soysave(
        "Parceiro",
        [
            {
                "mudanca": {
                    "CODPARC": "",
                    "CGC_CPF": "58602581000111",
                    "TIPPESSOA": "J",
                    "CLIENTE": "S",
                    "IDENTINSCESTAD": "bruh",
                    "NOMEPARC": nome,
                    "CLASSIFICMS": "X",
                    "CODCID": 1,
                }
            }
        ],
    )
    return int(parceiro[0]["CODPARC"])


def cliente() -> int:
    """
    Retorna o código de um cliente.
    """
    nome = "SOYNKHYACLIENTE"
    pesquisa = wrapper.soyquery(f"select codparc from tgfpar where nomeparc='{nome}'")
    if len(pesquisa) > 0:
        return int(pesquisa[0]["CODPARC"])
    parceiro = wrapper.soysave(
        "Parceiro",
        [
            {
                "mudanca": {
                    "CODPARC": "",
                    "CGC_CPF": "02819864000165",
                    "TIPPESSOA": "J",
                    "CLIENTE": "S",
                    "FORNECEDOR": "S",
                    "IDENTINSCESTAD": "",
                    "CLASSIFICMS": "C",
                    "NOMEPARC": nome,
                    "CODCID": 1,
                }
            }
        ],
    )
    return int(parceiro[0]["CODPARC"])


def criar_documento(
    top: int,
    parametros_extras: dict[str, str | float | int | None] = {},
    itens: list[dict[str, str | float | int | None]] = [],
):
    """
    Cria um documento de venda e retorna o seu número único.
    """

    def mais_comum(campo: str):
        return wrapper.soyquery(
            f"select {campo} from tgfcab group by {campo} order by count({campo}) desc fetch first 1 rows only"
        )[0][campo.upper()]

    codigo_natureza_operacao = mais_comum("codnat")
    codigo_centro_custo = mais_comum("codcencus")
    codigo_tipo_negociacao = mais_comum("codtipvenda")
    mudanca = {
        "NUNOTA": "",
        "NUMNOTA": "0",
        "CODTIPOPER": top,
        "CODEMP": CONFIG.codigo_empresa_padrao,
        "CODPARC": cliente(),
        "CODCENCUS": codigo_centro_custo,
        "CODNAT": codigo_natureza_operacao,
        "CODTIPVENDA": codigo_tipo_negociacao,
        "OBSERVACAO": f"SOYNKHYA: {top}",
    }
    mudanca.update(parametros_extras)
    novo_pedido = wrapper.soysave(
        "CabecalhoNota",
        [{"mudanca": mudanca}],
    )
    assert len(novo_pedido) == 1
    nunota = novo_pedido[0]["NUNOTA"]
    if len(itens) == 0:
        wrapper.soysave(
            "ItemNota",
            [
                {
                    "mudanca": {
                        "NUNOTA": nunota,
                        "CODPROD": 1,
                        "SEQUENCIA": 1,
                        "CODVOL": "UN",
                        "QTDNEG": 2,
                        "USOPROD": "R",
                        "VLRUNIT": 1,
                    }
                }
            ],
        )
    else:
        mudancas = [{"mudanca": dict({"NUNOTA": nunota}, **item)} for item in itens]
        wrapper.soysave(
            "ItemNota",
            mudancas,
        )
    return wrapper.soyquery(f"select * from tgfcab where nunota = {nunota}")[0]


def produto_normal():
    """
    O produto cujo código será retornado não deve ser em si um problema
    em um faturamento ou em uma confirmação de documento.
    """
    nomes = [
        "SOYNKHYAPRODUTONORMAL1",
        "SOYNKHYAPRODUTONORMAL2",
        "SOYNKHYAPRODUTONORMAL3",
    ]
    nome = random.choice(nomes)
    _produto = wrapper.soyquery(f"select codprod from tgfpro where descrprod='{nome}'")
    if len(_produto) == 0:
        grupo_nome = "SOYNKHYAGRUPONORMAL"
        _grupo = wrapper.soyquery(
            f"select codgrupoprod from tgfgru where descrgrupoprod='{grupo_nome}'"
        )
        if len(_grupo) == 0:
            codigo = wrapper.soyquery(
                "select max(codgrupoprod)+100 a from tgfgru where analitico='N'"
            )[0]["A"]
            print(codigo)
            _grupo = wrapper.soysave(
                "GrupoProduto",
                [
                    {
                        "mudanca": {
                            "CODGRUPOPROD": codigo,
                            "DESCRGRUPOPROD": grupo_nome,
                            "ANALITICO": "S",
                            "GRAU": 2,
                            "LIMCURVA_B": 0,
                            "LIMCURVA_C": 0,
                            "COMCURVA_A": 0,
                            "COMCURVA_B": 0,
                            "COMCURVA_C": 0,
                            "VALEST": "N",
                            "ATIVO": "S",
                            "CODNAT": 0,
                            "CODCENCUS": 0,
                            "CODPROJ": 0,
                            "SOLCOMPRA": "N",
                            "PEDIRLIB": "N",
                            "APRPRODVDA": "S",
                            "AGRUPALOCVALEST": "S",
                            "PERCCMTNAC": 0,
                            "PERCCMTIMP": 0,
                            "PERCCMTFED": 0,
                            "PERCCMTEST": 0,
                            "PERCCMTMUN": 0,
                            "DHALTER": "28/03/2025 16:57:05",
                            "CODUSU": 12,
                            "CALRUPTURAESTOQUE": "N",
                        },
                    }
                ],
            )
        grupo = _grupo[0]["CODGRUPOPROD"]
        _produto = wrapper.soysave(
            "Produto",
            [
                {
                    "mudanca": {
                        "CODPROD": "",
                        "DESCRPROD": nome,
                        "CODGRUPOPROD": grupo,
                        "CODVOL": "UN",
                        "CODIPI": 0,
                        "CODFORMPREC": 1,
                        "MARGLUCRO": 42,
                        "DECVLR": 4,
                        "DECQTD": 4,
                        "DESCMAX": 100,
                        "PESOBRUTO": 0,
                        "PESOLIQ": 0,
                        "ALERTAESTMIN": "S",
                        "PROMOCAO": "N",
                        "TEMICMS": "S",
                        "TEMISS": "N",
                        "TEMIPIVENDA": "N",
                        "TEMIPICOMPRA": "N",
                        "TEMIRF": "N",
                        "TEMINSS": "N",
                        "PERCINSS": 0,
                        "REDBASEINSS": 0,
                        "USOPROD": "R",
                        "ORIGPROD": "0",
                        "TIPSUBST": "N",
                        "TIPLANCNOTA": "A",
                        "TIPCONTEST": "N",
                        "ATIVO": "S",
                        "APRESDETALHE": "N",
                        "CODMOEDA": 0,
                        "GRUPOICMS": 0,
                        "LOCAL": "N",
                        "DTALTER": "01/04/2025 10:47:59",
                        "USALOCAL": "S",
                        "CODVOLCOMPRA": "UN",
                        "HRDOBRADA": "N",
                        "ICMSGERENCIA": "N",
                        "CODNAT": 0,
                        "CODCENCUS": 0,
                        "CODPROJ": 0,
                        "TEMCIAP": "N",
                        "IMPLAUDOLOTE": "N",
                        "DIMENSOES": "N",
                        "PADRAO": "S",
                        "SOLCOMPRA": "N",
                        "CONFERE": "S",
                        "REMETER": "N",
                        "ARREDPRECO": 0,
                        "TEMCOMISSAO": "S",
                        "COMPONOBRIG": "N",
                        "AP1RCTEGO": "N",
                        "CALCULOGIRO": "G",
                        "UNIDADE": "MM",
                        "CONFCEGAPESO": "N",
                        "GRUPOPIS": "TODOS",
                        "GRUPOCOFINS": "TODOS",
                        "GRUPOCSSL": "TODOS",
                        "CSTIPISAI": 99,
                        "UTILIZAWMS": "N",
                        "BALANCA": "N",
                        "RECEITUARIO": "N",
                        "EXIGEBENEFIC": "N",
                        "GERAPLAPROD": "N",
                        "PRODUTONFE": 0,
                        "TIPGTINNFE": 0,
                        "NCM": "82054000",
                        "FLEX": "S",
                        "QTDNFLAUDOSINT": 0,
                        "TIPCONTESTWMS": "N",
                        "LISTALPM": "N",
                        "ONEROSO": "N",
                        "REFMERCMED": "N",
                        "TERMOLABIL": "N",
                        "CONTROLADO": "N",
                        "IDENCORRELATO": "N",
                        "IDENCOSME": "N",
                        "PRODFALTA": "N",
                        "STATUSMED": 0,
                        "MVAAJUSTADO": 0,
                        "INFPUREZA": "N",
                        "USASTATUSLOTE": "N",
                        "USACODBARRASQTD": "N",
                        "VALCAPM3": "N",
                        "CSTIPIENT": 0,
                        "IMPORDEMCORTE": "N",
                        "TEMCREDPISCOFINSDEPR": "N",
                        "UTILSMARTCARD": "N",
                        "RECUPAVARIA": "N",
                        "APRESFORM": "S",
                        "CODBARCOMP": "N",
                        "TEMMEDICAO": "N",
                        "CODLOCALPADRAO": 0,
                        "PERMCOMPPROD": "S",
                        "DTVALDIF": "X",
                        "DESCVENCONSUL": "N",
                        "TIPOCONTAGEM": "D",
                        "CALCDIFAL": "S",
                        "STATUSNCM": "N",
                    }
                }
            ],
        )
    produto = _produto[0]["CODPROD"]
    return int(produto)


def produto_liberacao():
    """
    O produto cujo código será retornado poderá gerar um evento
    de liberação por estoque insuficiente.
    """
    grupo_nome = "SOYNKHYAGRUPOLIB"
    _grupo = wrapper.soyquery(
        f"select codgrupoprod from tgfgru where descrgrupoprod='{grupo_nome}'"
    )
    if len(_grupo) == 0:
        _grupo = wrapper.soysave(
            "GrupoProduto",
            [
                {
                    "mudanca": {
                        "CODGRUPOPROD": "770000",
                        "DESCRGRUPOPROD": grupo_nome,
                        "ANALITICO": "N",
                        "GRAU": 2,
                        "LIMCURVA_B": 0,
                        "LIMCURVA_C": 0,
                        "COMCURVA_A": 0,
                        "COMCURVA_B": 0,
                        "COMCURVA_C": 0,
                        "VALEST": "G",
                        "ATIVO": "S",
                        "CODNAT": 0,
                        "CODCENCUS": 0,
                        "CODPROJ": 0,
                        "SOLCOMPRA": "N",
                        "PEDIRLIB": "S",
                        "APRPRODVDA": "S",
                        "AGRUPALOCVALEST": "S",
                        "PERCCMTNAC": 0,
                        "PERCCMTIMP": 0,
                        "PERCCMTFED": 0,
                        "PERCCMTEST": 0,
                        "PERCCMTMUN": 0,
                        "DHALTER": "28/03/2025 16:57:05",
                        "CODUSU": 12,
                        "CALRUPTURAESTOQUE": "N",
                    }
                }
            ],
        )
    grupo = _grupo[0]["CODGRUPOPROD"]
    produto_nome = "SOYNKHYAPRODUTOLIB"
    _produto = wrapper.soyquery(
        f"select codprod from tgfpro where descrprod='{produto_nome}'"
    )

    if len(_produto) == 0:
        _produto = wrapper.soysave(
            "Produto",
            [
                {
                    "mudanca": {
                        "CODPROD": "",
                        "DESCRPROD": produto_nome,
                        "CODGRUPOPROD": grupo,
                        "CODVOL": "UN",
                        "CODIPI": 0,
                        "CODFORMPREC": 1,
                        "MARGLUCRO": 42,
                        "DECVLR": 4,
                        "DECQTD": 4,
                        "DESCMAX": 100,
                        "PESOBRUTO": 0,
                        "PESOLIQ": 0,
                        "ALERTAESTMIN": "S",
                        "PROMOCAO": "N",
                        "TEMICMS": "S",
                        "TEMISS": "N",
                        "TEMIPIVENDA": "N",
                        "TEMIPICOMPRA": "N",
                        "TEMIRF": "N",
                        "TEMINSS": "N",
                        "PERCINSS": 0,
                        "REDBASEINSS": 0,
                        "USOPROD": "R",
                        "ORIGPROD": "0",
                        "TIPSUBST": "N",
                        "TIPLANCNOTA": "A",
                        "TIPCONTEST": "N",
                        "ATIVO": "S",
                        "APRESDETALHE": "N",
                        "CODMOEDA": 0,
                        "GRUPOICMS": 0,
                        "LOCAL": "N",
                        "DTALTER": "01/04/2025 10:47:59",
                        "USALOCAL": "S",
                        "CODVOLCOMPRA": "UN",
                        "HRDOBRADA": "N",
                        "ICMSGERENCIA": "N",
                        "CODNAT": 0,
                        "CODCENCUS": 0,
                        "CODPROJ": 0,
                        "TEMCIAP": "N",
                        "IMPLAUDOLOTE": "N",
                        "DIMENSOES": "N",
                        "PADRAO": "S",
                        "SOLCOMPRA": "N",
                        "CONFERE": "S",
                        "REMETER": "N",
                        "ARREDPRECO": 0,
                        "TEMCOMISSAO": "S",
                        "COMPONOBRIG": "N",
                        "AP1RCTEGO": "N",
                        "CALCULOGIRO": "G",
                        "UNIDADE": "MM",
                        "CONFCEGAPESO": "N",
                        "GRUPOPIS": "TODOS",
                        "GRUPOCOFINS": "TODOS",
                        "GRUPOCSSL": "TODOS",
                        "CSTIPISAI": 99,
                        "UTILIZAWMS": "N",
                        "BALANCA": "N",
                        "RECEITUARIO": "N",
                        "EXIGEBENEFIC": "N",
                        "GERAPLAPROD": "N",
                        "PRODUTONFE": 0,
                        "TIPGTINNFE": 0,
                        "NCM": "82054000",
                        "FLEX": "S",
                        "QTDNFLAUDOSINT": 0,
                        "TIPCONTESTWMS": "N",
                        "LISTALPM": "N",
                        "ONEROSO": "N",
                        "REFMERCMED": "N",
                        "TERMOLABIL": "N",
                        "CONTROLADO": "N",
                        "IDENCORRELATO": "N",
                        "IDENCOSME": "N",
                        "PRODFALTA": "N",
                        "STATUSMED": 0,
                        "MVAAJUSTADO": 0,
                        "INFPUREZA": "N",
                        "USASTATUSLOTE": "N",
                        "USACODBARRASQTD": "N",
                        "VALCAPM3": "N",
                        "CSTIPIENT": 0,
                        "IMPORDEMCORTE": "N",
                        "TEMCREDPISCOFINSDEPR": "N",
                        "UTILSMARTCARD": "N",
                        "RECUPAVARIA": "N",
                        "APRESFORM": "S",
                        "CODBARCOMP": "N",
                        "TEMMEDICAO": "N",
                        "CODLOCALPADRAO": 0,
                        "PERMCOMPPROD": "S",
                        "DTVALDIF": "X",
                        "DESCVENCONSUL": "N",
                        "TIPOCONTAGEM": "D",
                        "CALCDIFAL": "S",
                        "STATUSNCM": "N",
                    }
                }
            ],
        )
    produto = _produto[0]["CODPROD"]
    return int(produto)


class TestPedidos(unittest.TestCase):
    def test_carta_correcao(self):
        pedido = criar_documento(CONFIG.top_pedido)
        wrapper.confirmar_documento([pedido["NUNOTA"]])
        nota = wrapper.faturar_documento([pedido["NUNOTA"]], CONFIG.top_venda_nfe)[
            "nota"
        ]
        wrapper.confirmar_documento([nota])
        texto_esperado = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        wrapper.carta_de_correcao(int(nota), texto_esperado)
        texto_real = wrapper.texto_carta_de_correcao(nota)
        print(
            wrapper.soyquery("select numnota from tgfcab where nunota = " + str(nota))
        )
        # wrapper.imprimir_carta_de_correcao(nota)
        self.assertEqual(texto_esperado, texto_real)
        input("bruh")

    def test_nfe_de_venda_com_evento_de_liberacao(self):
        produto = produto_liberacao()
        pedido = criar_documento(
            CONFIG.top_pedido,
            itens=[
                {
                    "CODPROD": produto,
                    "SEQUENCIA": "0",
                    "CODVOL": "UN",
                    "VLRUNIT": 99999999,
                    "VLRTOT": 9999999,
                    "QTDNEG": 99999999,
                    "VLRUNIT": 0.1,
                }
            ],
        )
        wrapper.confirmar_documento([pedido["NUNOTA"]])
        with self.assertRaises(LiberacaoPendente):
            nota_de_venda(pedido["NUNOTA"], 1, 1, "C", None, None, False, 0)

    def test_nfe_triangular_com_evento_de_liberacao(self):
        produto = produto_liberacao()
        pedido = criar_documento(
            CONFIG.top_pedido,
            itens=[
                {
                    "CODPROD": produto,
                    "SEQUENCIA": "0",
                    "CODVOL": "UN",
                    "QTDNEG": 99999999,
                    "VLRUNIT": 0.1,
                }
            ],
        )
        wrapper.confirmar_documento([pedido["NUNOTA"]])
        cliente_nota = cliente()
        with self.assertRaises(LiberacaoPendente):
            nota_triangular(
                pedido["NUNOTA"], 1, 1, "C", None, cliente_nota, None, False, 0
            )

    def test_nfe_de_venda_com_erro_na_sefaz(self):
        codigo_parceiro = parceiro_anti_sefaz()
        pedido = criar_documento(CONFIG.top_pedido, {"CODPARC": codigo_parceiro})
        wrapper.confirmar_documento([pedido["NUNOTA"]])
        with self.assertRaises(ErroDoSoynkhya):
            nota_de_venda(pedido["NUNOTA"], 1, 1, "C", None, None)
        nota = wrapper.soyquery(
            f"select * from tgfcab where nunota = (select distinct nunota from tgfvar where nunotaorig={pedido["NUNOTA"]})"
        )[0]
        self.assertNotEqual(nota["STATUSNFE"], "A")
        wrapper.soysave(
            "CabecalhoNota",
            [{"pk": {"NUNOTA": nota["NUNOTA"]}, "mudanca": {"CODPARC": cliente()}}],
        )
        nota_de_venda(pedido["NUNOTA"], 1, 1, "C", None, None)

    def test_nfe_triangular_com_erro_na_sefaz(self):
        codigo_parceiro = parceiro_anti_sefaz()
        pedido = criar_documento(CONFIG.top_pedido, {"CODPARC": codigo_parceiro})
        wrapper.confirmar_documento([pedido["NUNOTA"]])
        cliente_nota = cliente()
        with self.assertRaises(ErroDoSoynkhya):
            nota_triangular(pedido["NUNOTA"], 1, 1, "C", None, cliente_nota)
        nota = wrapper.soyquery(
            f"select * from tgfcab where nunota = (select distinct nunota from tgfvar where nunotaorig={pedido["NUNOTA"]})"
        )[0]
        self.assertNotEqual(nota["STATUSNFE"], "A")
        wrapper.soysave(
            "CabecalhoNota",
            [{"pk": {"NUNOTA": nota["NUNOTA"]}, "mudanca": {"CODPARC": cliente_nota}}],
        )
        nota_triangular(pedido["NUNOTA"], 1, 1, "C", None, cliente_nota)

    def test_faturar_triangular(self):
        pedido = criar_documento(CONFIG.top_pedido)
        wrapper.confirmar_documento([pedido["NUNOTA"]])
        volumes = 222
        peso = 1.3
        frete = "C"
        conferente = "AAAAAAAAAAAAAAAAAAA"
        transportadora = wrapper.soyquery(
            "select codparc from tgfpar where transportadora = 'S' fetch first 1 rows only"
        )[0]["CODPARC"]
        nota_triangular(
            pedido["NUNOTA"],
            volumes,
            peso,
            frete,
            conferente,
            CONFIG.codigo_empresa_padrao,
            transportadora,
        )
        nf_venda = wrapper.soyquery(
            f"select * from tgfcab where nunota = (select distinct nunota from tgfvar where nunotaorig={pedido["NUNOTA"]}) and codtipoper = {CONFIG.top_nfe_triangular}"
        )[0]
        remessa = wrapper.soyquery(
            f"select * from tgfcab where nunota = {nf_venda["NUREM"]}"
        )[0]
        for nota in [nf_venda, remessa]:
            # Nota precisa estar confirmada
            self.assertEqual(nota["STATUSNOTA"], "L")
            # Nota precisa estar aprovada
            self.assertEqual(nota["STATUSNFE"], "A")
            self.assertEqual(float(nota["PESOBRUTO"]), peso)
            self.assertEqual(int(nota["QTDVOL"]), volumes)
            self.assertEqual(nota["CIF_FOB"], frete)
            if "AD_CONFERENTE" in nota:
                self.assertEqual(nota["AD_CONFERENTE"], conferente)
        self.assertEqual(
            int(nf_venda["CODPARCDEST"]), int(CONFIG.codigo_empresa_padrao)
        )
        self.assertEqual(int(nf_venda["CODTIPOPER"]), int(CONFIG.top_nfe_triangular))

    def test_faturar_nota_de_venda(self):
        pedido = criar_documento(CONFIG.top_pedido)
        wrapper.confirmar_documento([pedido["NUNOTA"]])
        volumes = 222
        peso = 1.3
        frete = "C"
        conferente = "AAAAAAAAAAAAAAAAAAA"
        nota_de_venda(pedido["NUNOTA"], volumes, peso, frete, conferente)
        nota = wrapper.soyquery(
            f"select * from tgfcab where nunota = (select distinct nunota from tgfvar where nunotaorig={pedido["NUNOTA"]})"
        )[0]
        # Nota precisa estar confirmada
        self.assertEqual(nota["STATUSNOTA"], "L")
        # Nota precisa estar aprovada
        self.assertEqual(nota["STATUSNFE"], "A")
        self.assertEqual(int(nota["CODTIPOPER"]), int(CONFIG.top_venda_nfe))
        self.assertEqual(float(nota["PESOBRUTO"]), peso)
        self.assertEqual(int(nota["QTDVOL"]), volumes)
        self.assertEqual(nota["CIF_FOB"], frete)
        if "AD_CONFERENTE" in nota:
            self.assertEqual(nota["AD_CONFERENTE"], conferente)

    def test_excluir(self):
        pass

    def test_confirmacao_pedido(self):
        # print(
        #     wrapper.soyrequest(
        #         "PersonalizedFilter.getEntityStructure",
        #         {"entity": {"name": "CabecalhoNota"}},
        #     ).json()
        # )

        for nunotas in [
            [criar_documento(CONFIG.top_orcamento)["NUNOTA"]],
            [
                criar_documento(CONFIG.top_orcamento)["NUNOTA"],
                criar_documento(CONFIG.top_orcamento)["NUNOTA"],
            ],
        ]:
            print(wrapper.mgecom)
            resposta = wrapper.confirmar_documento(nunotas)
            self.assertEqual(int(resposta["confirmados"]), len(nunotas))
            self.assertEqual(int(resposta["nao_confirmados"]), 0)
            self.assertEqual(int(resposta["total"]), len(nunotas))
            confirmada = wrapper.soyquery(
                f"select count(*) as confirmadas from tgfcab where nunota in ({",".join(nunotas)}) and statusnota='L'"
            )[0]["CONFIRMADAS"] == len(nunotas)
            self.assertTrue(confirmada)

    def test_faturamento(self):
        nunota = criar_documento(CONFIG.top_orcamento)["NUNOTA"]
        print(json.dumps(wrapper.confirmar_documento([nunota]), indent=4))
        resposta = wrapper.faturar_documento([nunota], CONFIG.top_pedido)

        print(resposta)

    def test_dict_para_aliquota(self):
        print(
            json.dumps(
                dict_para_aliquota(
                    {
                        "origem": "RS",
                        "destino": "nordeste",
                        "aliquota": 17,
                        "reducao": 0,
                        "restricao1": ["N", "X"],
                        "restricao2": "H",
                        "codigo_restricao2": "85159000",
                        "cst": 70,
                        "observacao": "Lei bostileira feita pra te roubar.",
                        "outorga": 0,
                    }
                ),
                indent=4,
            )
        )


class TestBI(unittest.TestCase):
    def test_gravacao(self):
        self.maxDiff = None
        componente = ComponenteBI.novo()
        xml_caminho = os.path.join(
            COMPONENTES_PASTA, str(componente.nugdg), "componente.xml"
        )
        xml = "çç"
        with open(xml_caminho, "w") as __x:
            __x.write(xml)
        toml_caminho = os.path.join(
            COMPONENTES_PASTA, str(componente.nugdg), "config.toml"
        )
        toml = f"""\
titulo= "Teste gravação"
descricao= "Teste"
categoria= "Gravacao"
ativo= "N"
layout= "T"
assinado= "N"
# Caso o componente seja um cartão inteligente
# cartao_inteligente_layout= "col1;row1"\
"""
        with open(toml_caminho, "w") as __t:
            __t.write(toml)
        componente.gravar()
        bruh = wrapper.soyquery(
            f"select * from tsigdg where nugdg = {componente.nugdg}"
        )[0]
        bruh["NUGDG"] = 1
        bruh["DHALTER"] = ""
        self.assertEqual(
            bruh,
            {
                "NUGDG": 1,
                "TITULO": "TESTE GRAVAÇÃO",
                "DESCRICAO": "Teste",
                "CONFIG": "çç",
                "THUMBNAIL": None,
                "CATEGORIA": "Gravacao",
                "ATIVO": "N",
                "CODUSUINC": 57,
                "CODUSU": 57,
                "DHALTER": "",
                "URLCOMPONENTE": None,
                "HTML5": "binary",
                "LAYOUT": "T",
                "GDGASSINADO": "N",
                "EVOCARD": None,
                "APVNC": None,
            },
        )

    def test_adicao_e_remocao(self):
        componente = ComponenteBI.novo()

    def test_multiplas_remocoes(self):
        pks = []
        for i in range(3):
            pks.append(ComponenteBI.novo().nugdg)

    def test_edicao_com_html(self):
        nugdg = wrapper.soyquery(
            "select nugdg from tsigdg where html5 is not null fetch first 1 rows only"
        )[0]["NUGDG"]
        componente = ComponenteBI(nugdg)
        componente.editar()

    def test_edicao_sem_html(self):
        nugdg = wrapper.soyquery(
            "select nugdg from tsigdg where html5 is null fetch first 1 rows only"
        )[0]["NUGDG"]
        componente = ComponenteBI(nugdg)
        componente.editar()


class TestBotao(unittest.TestCase):
    def test_config_from_toml(self):
        self.maxDiff = None
        toml_cru = """\
instancia = "Produto"
# modulo = "None"
# Determina as telas que mostrarão o botão.
filtro_de_telas = "br.com.sankhya.core.cad.produtos"
# ordem = "None"

# Nome do botão.
descricao = "Estoque"
# Pode ser "S" ou "N"
controla_acesso = "N"

# tecla_de_atalho = "None"
# Tipo de atualização. Valores possíveis:
# "NONE" = Não recarregar nada
# "ALL" = Recarregar toda a grade
# "SEL" = Recarregar os registros selecionados
# "PARENT" = Recarregar o registro pai (quando ele existir)
# "MASTER" = Recarregar o registro principal (quando ele existir)
tipo_atualizacao = "NONE"
# Controle manual de transações. Pode ser `false` ou `true`
controle_transacao = "false"
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
[[parametros]]
label = "Cód. Produto"
name = "CODPROD"
required = "true"
saveLast = "false"
paramType = "I"

[[parametros]]
label = "Estoque"
name = "ESTOQUE"
required = "true"
saveLast = "false"
paramType = "D"
precision = "4"\
"""
        self.assertEqual(
            BotaoJS.config_from_toml(1, "bruh", toml_cru),
            {
                "CODMODULO": None,
                "CONFIG": '<actionConfig><runScript entityName="Produto" refreshType="NONE" '
                'txManual="false">bruh</runScript><params><promptParam label="Cód. '
                'Produto" name="CODPROD" required="true" saveLast="false" '
                'paramType="I" /><promptParam label="Estoque" name="ESTOQUE" '
                'required="true" saveLast="false" paramType="D" precision="4" '
                "/></params></actionConfig>",
                "CONTROLAACESSO": "N",
                "DESCRICAO": "Estoque",
                "IDBTNACAO": 1,
                "NOMEINSTANCIA": "Produto",
                "ORDEM": None,
                "RESOURCEID": "br.com.sankhya.core.cad.produtos",
                "TECLAATALHO": None,
                "TIPO": "SC",
            },
        )

    def test_config_from_toml_deveria_dar_erro(self):
        config_toml = toml.loads(
            """\
id = 777
instancia = "AAA"
filtro_de_telas = "AAA"
descricao = "bruh 20"
controla_acesso = "N"
tipo_atualizacao = "NONE"
controle_transacao = "false"
[[parametros]]
label = "a"
name = "a"
required = "true"
saveLast = "false"
paramType = "I"
"""
        )
        mudancas = ("controla_acesso", "tipo_atualizacao")
        mudancas_parametro = ("required", "saveLast", "paramType")
        for mudanca in mudancas:
            clone_toml = config_toml
            clone_toml[mudanca] = "BRUH"
            with self.assertRaises(AssertionError):
                BotaoJS.config_from_toml(777, "bruh", toml.dumps(clone_toml))

        for mudanca in mudancas_parametro:
            clone_toml = config_toml
            clone_toml["parametros"][0][mudanca] = "BRUH"
            with self.assertRaises(AssertionError):
                BotaoJS.config_from_toml(777, "bruh", toml.dumps(clone_toml))

    def test_config_to_toml(self):
        botao_cru = {
            "IDBTNACAO": 1,
            "NOMEINSTANCIA": "CabecalhoNota",
            "RESOURCEID": "bruh",
            "DESCRICAO": "Teste",
            "TIPO": "SC",
            "CONFIG": """\
<actionConfig>
<runScript entityName="CabecalhoNota" refreshType="NONE" txManual="false">
console.log("bruh");
</runScript>
<params>
<promptParam label="um" name="um" required="true" saveLast="false" paramType="ENTITY" entityName="Ncm" />
<promptParam label="dois" name="dois" required="true" saveLast="false" paramType="S" />
<promptParam label="tres" name="tres" required="true" saveLast="false" paramType="D" />
</params>
</actionConfig>
""",
            "CODMODULO": None,
            "ORDEM": None,
            "CONTROLAACESSO": "N",
            "TECLAATALHO": None,
        }
        botao = BotaoJS(botao_cru, wrapper)
        config = botao.config_to_toml()
        config_toml = toml.loads(config)
        self.assertEqual(
            config_toml,
            {
                "controla_acesso": "N",
                "controle_transacao": "false",
                "descricao": "Teste",
                "filtro_de_telas": "bruh",
                "instancia": "CabecalhoNota",
                "parametros": [
                    {
                        "entityName": "Ncm",
                        "label": "um",
                        "name": "um",
                        "paramType": "ENTITY",
                        "required": "true",
                        "saveLast": "false",
                    },
                    {
                        "label": "dois",
                        "name": "dois",
                        "paramType": "S",
                        "required": "true",
                        "saveLast": "false",
                    },
                    {
                        "label": "tres",
                        "name": "tres",
                        "paramType": "D",
                        "required": "true",
                        "saveLast": "false",
                    },
                ],
                "tipo_atualizacao": "NONE",
            },
        )


class TestUtils(unittest.TestCase):
    def test_chave_das_mudancas(self):
        self.assertEqual(
            chaves_das_mudancas(
                [
                    {
                        "pk": {"IDBTNACAO": "131"},
                        "mudanca": {"DESCRICAO": ""},
                    },
                    {
                        "pk": {"IDBTNACAO": "130"},
                        "mudanca": {"RESOURCEID": ""},
                    },
                ]
            ),
            ["DESCRICAO", "RESOURCEID"],
        )

    def test_mudancas_para_records(self):
        self.assertEqual(
            mudancas_para_records(
                [
                    {
                        "pk": {"IDBTNACAO": "131"},
                        "mudanca": {"DESCRICAO": "descricao"},
                    },
                    {
                        "pk": {"IDBTNACAO": "130"},
                        "mudanca": {"RESOURCEID": "resourceid"},
                    },
                ]
            ),
            [
                {"pk": {"IDBTNACAO": "131"}, "values": {"0": "descricao"}},
                {"pk": {"IDBTNACAO": "130"}, "values": {"1": "resourceid"}},
            ],
        )
        self.assertEqual(
            mudancas_para_records(
                [
                    {
                        "foreignKey": {"NOMEINSTANCIA": "131"},
                        "mudanca": {"DESCRICAO": "descricao"},
                    },
                    {
                        "pk": {"IDBTNACAO": "130"},
                        "mudanca": {"RESOURCEID": "resourceid"},
                    },
                ]
            ),
            [
                {"foreignKey": {"NOMEINSTANCIA": "131"}, "values": {"0": "descricao"}},
                {"pk": {"IDBTNACAO": "130"}, "values": {"1": "resourceid"}},
            ],
        )

    def test_mudancas_para_records_nao_muda_argumento(self):
        mudancas = [
            {
                "pk": {"IDBTNACAO": "131"},
                "mudanca": {"DESCRICAO": "descricao"},
            },
            {
                "pk": {"IDBTNACAO": "130"},
                "mudanca": {"RESOURCEID": "resourceid"},
            },
        ]
        esperado = copy.deepcopy(mudancas)
        mudancas_para_records(mudancas)
        print(esperado)
        self.assertEqual(mudancas, esperado)

    def test_parametro_para_acionamento(self):
        resultado = parametro_para_acionamento(
            {
                "label": "Data",
                "name": "DATA",
                "required": "true",
                "saveLast": "false",
                "paramType": "DT",
            },
            777,
        )
        self.assertEqual(resultado, {"$": 777, "paramName": "DATA", "type": "D"})

    def test_zipar_pasta(self):
        with tempfile.TemporaryDirectory() as tempdir:
            os.makedirs(os.path.join(tempdir, "pasta"), exist_ok=True)
            with open(os.path.join(tempdir, "um.txt"), "w") as f1:
                f1.write("SUBSTITUIR")
            with open(os.path.join(tempdir, "pasta", "dois.txt"), "w") as f2:
                f2.write("SUBSTITUIR")
            zip_caminho = os.path.join(tempdir, "output.zip")
            zipar_pasta(
                tempdir,
                zip_caminho,
                {"SUBSTITUIR": "SUBSTITUÍDO"},
            )
            zip_pasta = os.path.join(tempdir, "output")
            with zipfile.ZipFile(zip_caminho, "r") as zip_arquivo:
                zip_arquivo.extractall(zip_pasta)
            um = os.path.join(zip_pasta, "um.txt")
            dois = os.path.join(zip_pasta, "pasta", "dois.txt")
            with open(um, "r") as ff1:
                self.assertEqual(ff1.read(), "SUBSTITUÍDO")
            with open(dois, "r") as ff2:
                self.assertEqual(ff2.read(), "SUBSTITUÍDO")


class TestDados(unittest.TestCase):
    def test_nomes_colunas(self):
        colunas = wrapper.nome_colunas("LiberacaoLimite")
        self.assertEqual(colunas["ANTECIPACAO"], "Antecipação")
