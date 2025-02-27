import unittest
import random
from utils import *
from config import *
from botao import *
from bi import *


class TestBI(unittest.TestCase):
    def test_gravacao(self):
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
                "CONFIG": '<gadget>\n      <level id="02C" description="Principal">\n        <container orientacao="V" tamanhoRelativo="100">\n          <html5component id="html5_02D" entryPoint="index.html"></html5component>\n        </container>\n      </level>\n    </gadget>',
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
        componente.remover(False, componente.nugdg)

    def test_adicao_e_remocao(self):
        componente = ComponenteBI.novo()
        componente.remover(False, componente.nugdg)

    def test_multiplas_remocoes(self):
        pks = []
        for i in range(3):
            pks.append(ComponenteBI.novo().nugdg)
        ComponenteBI.remover(False, *pks)

    def test_edicao_com_html(self):
        nugdg = wrapper.soyquery(
            "select nugdg from tsigdg where html5 is not null fetch first 1 rows only"
        )[0]["NUGDG"]
        componente = ComponenteBI(nugdg)
        componente.editar()
        componente.remover(False, nugdg)

    def test_edicao_sem_html(self):
        nugdg = wrapper.soyquery(
            "select nugdg from tsigdg where html5 is null fetch first 1 rows only"
        )[0]["NUGDG"]
        componente = ComponenteBI(nugdg)
        componente.editar()
        componente.remover(False, nugdg)


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


if __name__ == "__main__":
    unittest.main()
