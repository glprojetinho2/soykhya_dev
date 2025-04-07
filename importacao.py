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


class ImportacaoXML:

    def __init__(self, importacao_crua: dict[str, Any], wrapper: Soywrapper):
        self.cru = importacao_crua
        self.nuarquivo = self.cru["NUARQUIVO"]
        self.wrapper = wrapper
        assert self.cru["CONFIG"] is not None
        self.__config = ET.fromstring(self.cru["CONFIG"])
        assert self.cru["XML"] is not None
        self.__xml = ET.fromstring(self.cru["XML"])

    def produtos(self):  # -> list[ProdutoXML]
        resultado = []
        for produto in self.__xml.iter("det"):
            resultado.append(produto.attrib)
        return resultado

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
    def erro(self) -> str | None:
        if "validacoes" == self.__config.tag:
            return " ".join(
                [elem.text for elem in self.__config.iter() if elem.text is not None]
            ).strip()
        else:
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
        description="Seja um faturista sem tocar no Soynkhya :)"
    )
    parser.add_argument("argumento")
    args = parser.parse_args()

    wrapper.imprimir_notas(
        [
            wrapper.soyquery(
                f"select nunota from tgfcab where numnota={args.argumento} and statusnota='L' and codtipoper=1101"
            )[0]["NUNOTA"]
        ],
        TipoImpressao.BOLETO,
    )

# wrapper.processar(bruh["NUARQUIVO"], config, False)
# print(
#     wrapper.soyquery(
#         "select config from tgfixn where nuarquivo = " + str(bruh["NUARQUIVO"])
#     )[0]["CONFIG"]
# )

# print(xml.dom.minidom.parseString(bruh["XML"]).toprettyxml(indent=" "))
# print(wrapper.processar(bruh["NUARQUIVO"], config, False))
