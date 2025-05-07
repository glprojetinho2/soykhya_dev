from utils import *
from config import *
import math
from datetime import datetime, timedelta
import time
import typing
import os
import sys
import requests
import argparse
import zipfile
import os


def upload(nugdg: int, caminho_do_zip: str):
    wrapper.upload("ARQUIVO_COMPONENTE", caminho_do_zip)
    wrapper.pegar_corpo(
        wrapper.soyrequest(
            "DynaGadgetBuilderSP.atualizarComponente",
            {"param": {"chave": "ARQUIVO_COMPONENTE", "nugdg": nugdg}},
        )
    )


toml_chaves = {
    "TITULO": "titulo",
    "DESCRICAO": "descricao",
    "CATEGORIA": "categoria",
    "ATIVO": "ativo",
    "LAYOUT": "layout",
    "GDGASSINADO": "assinado",
    "EVOCARD": "cartao_inteligente_layout",
}


class ComponenteBI:
    def __init__(self, nugdg: int):
        self.componente_pasta = os.path.join(COMPONENTES_PASTA, str(nugdg))
        self.toml_caminho = os.path.join(self.componente_pasta, "config.toml")
        self.html_caminho = os.path.join(self.componente_pasta, "html5.zip")
        self.xml_caminho = os.path.join(self.componente_pasta, "componente.xml")
        self.html_pasta = os.path.join(self.componente_pasta, "html5")
        self.nugdg = nugdg
        componente = wrapper.soyquery(
            f"select length(html5) as tamanho, config, titulo, dhalter, descricao, categoria, ativo, layout, gdgassinado, evocard from tsigdg where nugdg = {nugdg}"
        )[0]
        tamanho_pedaco = 1000
        self.configuracao = componente["CONFIG"]
        self.zip: bytes | None = None
        if componente["TAMANHO"] is not None:
            tamanho_clob = int(componente["TAMANHO"])
            select_partes = []
            for i in range(math.floor(tamanho_clob / tamanho_pedaco) + 1):
                select_partes.append(
                    f"UTL_RAW.CAST_TO_VARCHAR2(UTL_RAW.CAST_TO_RAW(DBMS_LOB.SUBSTR(html5, {tamanho_pedaco}, {tamanho_pedaco * i + 1}))) AS a{i}"
                )
            partes = [
                x
                for x in wrapper.soyquery(
                    f"select {", ".join(select_partes)} from tsigdg where nugdg = {nugdg}"
                )[0].values()
                if x
            ]
            clob = "".join(partes)
            binario = bytes.fromhex(clob)
            self.zip = binario
        self.titulo: str = componente["TITULO"]
        self.descricao: str | None = componente.get("DESCRICAO")
        self.categoria: str | None = componente["CATEGORIA"]
        self.ativo: str = componente["ATIVO"]
        self.layout: str | None = componente["LAYOUT"]
        self.assinado: str | None = componente["GDGASSINADO"]
        self.cartao_inteligente_layout: str | None = componente["EVOCARD"]

    def gravar(self) -> str:
        """
        Grava o componente e retorna o seu diretório no servidor
        da Soynkhya.
        """
        with open(self.xml_caminho, "r") as f_cfg:
            xml_cfg = f_cfg.read()
        with open(self.toml_caminho, "r", encoding="utf-8") as t_cfg:
            toml_cfg = toml.loads(t_cfg.read())
        mudanca: dict[str, str | int | float | None] = {"CONFIG": xml_cfg}
        mudanca.update(
            {chave: toml_cfg.get(toml_chaves[chave]) for chave in toml_chaves.keys()}
        )
        mudanca.update({"DHALTER": ""})
        componente_atualizado = wrapper.soysave(
            "Gadget", [{"pk": {"NUGDG": self.nugdg}, "mudanca": mudanca}]
        )[0]

        def data_para_diretorio_base(data: str | int | float | None) -> str:
            assert data
            assert isinstance(data, str)
            if "/" in data:
                data_alteracao = datetime.strptime(str(data), "%d/%m/%Y %H:%M:%S")
            else:
                data_alteracao = datetime.strptime(str(data), "%d%m%Y %H:%M:%S")
            data_formatada = data_alteracao.strftime("%Y%m%d%H%M%S")
            return f"html5component/{self.nugdg}_{data_formatada}"

        diretorio_base = data_para_diretorio_base(componente_atualizado["DHALTER"])
        zipar_pasta(
            self.html_pasta,
            self.html_caminho,
            {
                "{{BASE_DIR}}": diretorio_base,
                "{{DOMINIO}}": DOMINIO,
            },
        )
        upload(self.nugdg, self.html_caminho)

        def atualiza_diretorio_ate_dar_certo():
            nonlocal diretorio_base
            real_data_formatada = wrapper.soyquery(
                f"select dhalter from tsigdg where nugdg={self.nugdg}"
            )[0]["DHALTER"]
            real_diretorio_base = data_para_diretorio_base(real_data_formatada)
            if diretorio_base != real_diretorio_base:
                diretorio_base = data_para_diretorio_base(
                    wrapper.soysave(
                        "Gadget",
                        [{"pk": {"NUGDG": self.nugdg}, "mudanca": {"DHALTER": ""}}],
                    )[0]["DHALTER"]
                )
                zipar_pasta(
                    self.html_pasta,
                    self.html_caminho,
                    {
                        "{{BASE_DIR}}": diretorio_base,
                        "{{DOMINIO}}": DOMINIO,
                    },
                )
                upload(self.nugdg, self.html_caminho)
                atualiza_diretorio_ate_dar_certo()

        atualiza_diretorio_ate_dar_certo()

        return diretorio_base

    @classmethod
    def remover(cls, confirmar: bool, *pks):
        for pk in pks:
            _resultado = wrapper.soyquery(f"select * from tsigdg where nugdg = {pk}")
            if len(_resultado) == 0:
                print(f"Não há componente com a pk igual a {pk}")
                sys.exit(1)
            resultado = _resultado[0]
            if confirmar:
                print(json.dumps(resultado, indent=4))
                resposta = input("Desejas remover o registro acima? [s/N]: ")
                if resposta == "s":
                    wrapper.soyremove("Gadget", [{"NUGDG": pk}])
                    nao_restou_nada = (
                        wrapper.soyquery(
                            f"select count(*) bruh from tsigdg where nugdg = {pk}"
                        )[0]["BRUH"]
                        == 0
                    )
                    assert nao_restou_nada, "Não foi possível deletar componente"
            else:
                wrapper.soyremove("Gadget", [{"NUGDG": pk}])

    @classmethod
    def novo(
        cls,
    ) -> typing.Self:
        """
        Cria um componente de BI.
        """
        html_padrao = os.path.join("html_padrao.zip")
        componente = wrapper.soysave(
            "Gadget",
            [
                {
                    "mudanca": {
                        "NUGDG": "",
                        "TITULO": "Título Interessante",
                        "DESCRICAO": "Descrição interessante",
                        "CONFIG": f"""\
    <gadget>
      <level id="02C" description="Principal">
        <container orientacao="V" tamanhoRelativo="100">
          <html5component id="html5_02D" entryPoint="index.html"></html5component>
        </container>
      </level>
    </gadget>""",
                    }
                }
            ],
        )[0]
        id = componente["NUGDG"]
        upload(id, html_padrao)

        resultado = cls(id)
        resultado.editar()
        # folguinha pro sistema fraco
        time.sleep(1)
        # pro {{BASE_DIR}} e outras variáveis serem substituídas,
        # esta linha é necessária
        resultado.gravar()
        return resultado

    def editar(self):
        os.makedirs(self.componente_pasta, exist_ok=True)
        if self.zip is not None:
            os.makedirs(self.html_pasta, exist_ok=True)
            with open(self.html_caminho, "wb") as f:
                f.write(self.zip)
            with zipfile.ZipFile(self.html_caminho, "r") as zip_arquivo:
                zip_arquivo.extractall(self.html_pasta)

        substituicao_recursiva(
            self.html_pasta, r"html5component/\d+_\d+", "{{BASE_DIR}}"
        )
        with open(self.toml_caminho, "w") as toml_file:
            toml_str = f"""\
{toml_chaves["TITULO"]}= "{self.titulo}"
{"" if self.descricao else "# "}{toml_chaves["DESCRICAO"]}= "{self.descricao or "Descricao"}"
{"" if self.categoria else "# "}{toml_chaves["CATEGORIA"]}= "{self.categoria or "Contabilidade"}"
{toml_chaves["ATIVO"]}= "{self.ativo}"
{"" if self.layout else "# "}{toml_chaves["LAYOUT"]}= "{self.layout or "T"}"
{"" if self.assinado else "# "}{toml_chaves["GDGASSINADO"]}= "{self.assinado or "N"}"
# Caso o seja um cartão inteligente
{"" if self.cartao_inteligente_layout else "# "}{toml_chaves["EVOCARD"]}= "{self.cartao_inteligente_layout or "col1;row1"}"\
"""
            toml_file.write(toml_str)

        with open(self.xml_caminho, "w") as xml_file:
            xml_file.write(self.configuracao)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Faça componentes BI sem ter contato com o Soynkhya :)"
    )
    subparsers = parser.add_subparsers(dest="comando")

    editar_parser = subparsers.add_parser("editar", help="Edita componente.")
    editar_parser.add_argument("id", type=int, help="Id do componente.")

    lista_parser = subparsers.add_parser("lista", help="Lista componentes.")

    novo_parser = subparsers.add_parser("novo", help="Cria um novo componente.")

    gravar_parser = subparsers.add_parser(
        "gravar", help="Grava alterações feitas no componente."
    )
    gravar_parser.add_argument("id", type=int, help="Id do componente.")

    remover_parser = subparsers.add_parser("remover", help="Remove um componente.")
    remover_parser.add_argument("pks", nargs="*", help="pks dos componentes")

    args = parser.parse_args()

    try:
        nugdg = args.id
        componente = ComponenteBI(nugdg)
    except AttributeError:
        pass

    if args.comando == "gravar":
        componente.gravar()
        print("Componente gravado com sucesso.")

    elif args.comando == "novo":
        novo_componente = ComponenteBI.novo()
        print(f"Componente {novo_componente.nugdg} criado.")
        print(f"Componente {novo_componente.nugdg} importado com sucesso.")

    elif args.comando == "editar":
        componente.editar()
        print(f"Componente {nugdg} importado com sucesso.")

    elif args.comando == "remover":
        ComponenteBI.remover(True, *args.pks)

    elif args.comando == "lista":
        lista = wrapper.soyquery(
            f"select nugdg, titulo, descricao, config from tsigdg order by nugdg asc"
        )
        print(json.dumps(lista, indent=4))
