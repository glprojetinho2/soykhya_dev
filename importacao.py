from utils import *
import xml.etree.ElementTree as ET
from config import *


class ImportacaoXML:
    def __init__(self, importacao_crua: dict[str, Any], wrapper: Soywrapper):
        self.cru = importacao_crua
        self.wrapper = wrapper
        assert self.cru["CONFIG"] is not None
        self.__config = ET.fromstring(self.cru["CONFIG"])

    @property
    def divergencia_pedidos(self):
        return bool(self.__config.find("cabecalho").attrib.get("DIVERGENCIAPEDIDOS"))

    @property
    def divergencia_itens(self):
        return bool(self.__config.find("cabecalho").attrib.get("DIVERGENCIAITENS"))

    @property
    def parceiro(self) -> int | None:
        """
        Código do parceiro no Soynkhya.
        """
        return self.__nota_e_xml("codParc", True)["nota"]

    @property
    def empresa(self) -> int | None:
        """
        Código da empresa (CODEMP) no Soynkhya.
        """
        return self.__nota_e_xml("codParc", True)["nota"]

    @property
    def cgcEmp(self):
        return self.__nota_e_xml("cgcEmp")

    @property
    def ieEmp(self):
        return self.__nota_e_xml("ieEmp")

    @property
    def nomeEmp(self):
        return self.__nota_e_xml("nomeEmp")

    @property
    def endEmp(self):
        return self.__nota_e_xml("endEmp")

    @property
    def nroEmp(self):
        return self.__nota_e_xml("nroEmp")

    @property
    def bairroEmp(self):
        return self.__nota_e_xml("bairroEmp")

    @property
    def cidadeEmp(self):
        return self.__nota_e_xml("cidadeEmp")

    @property
    def ufEmp(self):
        return self.__nota_e_xml("ufEmp")

    @property
    def cepEmp(self):
        return self.__nota_e_xml("cepEmp")

    @property
    def paisEmp(self):
        return self.__nota_e_xml("paisEmp")

    @property
    def foneEmp(self):
        return self.__nota_e_xml("foneEmp")

    @property
    def ieParc(self):
        return self.__nota_e_xml("ieParc")

    @property
    def nomeParc(self):
        return self.__nota_e_xml("nomeParc")

    @property
    def endParc(self):
        return self.__nota_e_xml("endParc")

    @property
    def nroParc(self):
        return self.__nota_e_xml("nroParc")

    @property
    def bairroParc(self):
        return self.__nota_e_xml("bairroParc")

    @property
    def cidadeParc(self):
        return self.__nota_e_xml("cidadeParc")

    @property
    def ufParc(self):
        return self.__nota_e_xml("ufParc")

    @property
    def cepParc(self):
        return self.__nota_e_xml("cepParc")

    @property
    def paisParc(self):
        return self.__nota_e_xml("paisParc")

    @property
    def foneParc(self):
        return self.__nota_e_xml("foneParc")

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


bruh = wrapper.soyquery(
    "select * from tgfixn where numnota between 7777 and 10000 and config is not null"
)
for i in bruh:
    assert not isinstance(i, str)
    # print(i["CONFIG"])
    importacao = ImportacaoXML(i, wrapper)
    dado = importacao.endParc
    print(dado)
