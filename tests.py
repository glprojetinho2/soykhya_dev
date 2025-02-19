import unittest
import random
from utils import *


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

    def test_config_from_toml(self):
        self.maxDiff = None
        config_toml = """
id = 777
instancia = "AAA"
filtro_de_telas = "AAA"
descricao = "bruh 20"
controla_acesso = "N"
tipo_atualizacao = "NONE"
controle_transacao = "false"
[[parametros]]
label = "a"
name = "NUNOTA"
required = "true"
saveLast = "false"
paramType = "I"
[[parametros]]
label = "b"
name = "PENDENCIA"
required = "true"
saveLast = "false"
paramType = "S"
"""
        config = BotaoJS.config_from_toml('console.log("bruh")', config_toml)
        self.assertEqual(
            config,
            {
                "IDBTNACAO": 777,
                "NOMEINSTANCIA": "AAA",
                "RESOURCEID": "AAA",
                "DESCRICAO": "bruh 20",
                "TIPO": "SC",
                "CONFIG": '<actionConfig><runScript entityName="AAA" refreshType="NONE" txManual="false">console.log("bruh")</runScript><params><promptParam label="a" name="NUNOTA" required="true" saveLast="false" paramType="I" /><promptParam label="b" name="PENDENCIA" required="true" saveLast="false" paramType="S" /></params></actionConfig>',
                "CODMODULO": None,
                "ORDEM": None,
                "CONTROLAACESSO": "N",
                "TECLAATALHO": None,
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
                BotaoJS.config_from_toml("bruh", toml.dumps(clone_toml))

        for mudanca in mudancas_parametro:
            clone_toml = config_toml
            clone_toml["parametros"][0][mudanca] = "BRUH"
            with self.assertRaises(AssertionError):
                BotaoJS.config_from_toml("bruh", toml.dumps(clone_toml))

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

    def test_query(self):
        resultado = soyquery("select nunota from tgfcab where nunota < 1000")
        self.assertGreater(len(resultado), 0)


if __name__ == "__main__":
    unittest.main()
