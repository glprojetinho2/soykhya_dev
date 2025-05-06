import browsercookie
import toml
from utils import *

cookiejar = browsercookie.firefox()
sankhya_cookies = {"mge": "", "mgefin": "", "mgecom": "", "mgecom-bff": ""}
SCRIPTS_PASTA = "scripts/"
COMPONENTES_PASTA = "componentes/"
for __i in cookiejar:
    if __i.name == "JSESSIONID":
        valor = __i.value
        if sankhya_cookies.get(__i.path.strip("/")) == "":
            sankhya_cookies[__i.path.strip("/")] = valor


class Config:
    def __init__(self):
        self.path = "config.toml"
        # para garantir que o arquivo está criado
        # antes de qualquer operação
        with open(self.path, "a") as f:
            f.write("")
        config = toml.load(self.path)
        if "dominio" not in config:
            dominio = input("Domínio ('suaempresa.sankhyacloud.com.br'):")
            config["dominio"] = dominio
        if "codigo_autorizacao" not in config:
            config["codigo_autorizacao"] = ""
        if "top_orcamento" not in config:
            top_pedido = input("Top de orcamento:")
            int(top_pedido)
            config["top_orcamento"] = top_pedido
        if "top_pedido" not in config:
            top_pedido = input("Top de pedido de venda:")
            int(top_pedido)
            config["top_pedido"] = top_pedido
        if "top_venda_nfe" not in config:
            top_venda_nfe = input("Top de nota fiscal de venda:")
            int(top_venda_nfe)
            config["top_venda_nfe"] = top_venda_nfe
        if "top_nfe_triangular" not in config:
            top_nfe_triangular = input("Top de nota triangular:")
            int(top_nfe_triangular)
            config["top_nfe_triangular"] = top_nfe_triangular
        if "codigo_empresa_padrao" not in config:
            codigo_empresa_padrao = input(
                "O código da empresa padrao será usado para faturar pedidos nos testes etc. Digita-o: "
            )
            int(codigo_empresa_padrao)
            config["codigo_empresa_padrao"] = codigo_empresa_padrao
        if "conferentes" not in config:
            config["conferentes"] = {}
        if "separadores" not in config:
            config["separadores"] = {}
        if "liberadores" not in config:
            config["liberadores"] = []
        else:
            for liberador in config["liberadores"]:
                assert "nome" in liberador, "Veja se há um liberador sem nome."
                assert (
                    "abreviado" in liberador
                ), "Veja se há um liberador sem nome abreviado."
                assert "codigo" in liberador, "Veja se há um liberador sem código."

        with open(self.path, "w") as f:
            toml.dump(config, f)

        self.dominio = config["dominio"]
        self.codigo_autorizacao = config["codigo_autorizacao"]
        self.top_orcamento = config["top_orcamento"]
        self.top_pedido = config["top_pedido"]
        self.top_venda_nfe = config["top_venda_nfe"]
        self.top_nfe_triangular = config["top_nfe_triangular"]
        self.codigo_empresa_padrao = config["codigo_empresa_padrao"]
        self.conferentes = config["conferentes"]
        self.separadores = config["separadores"]
        self.campo_tipo_entrega = None
        self.emitir_etiquetas = []
        self.sempre_tem_transportadora = []
        self.liberadores = config["liberadores"]
        if "faturamento" in config:
            f = config["faturamento"]
            self.campo_tipo_entrega = f.get("campo_tipo_entrega")
            self.emitir_etiquetas = f.get("emitir_etiquetas") or []
            self.sempre_tem_transportadora = f.get("sempre_tem_transportadora") or []

    def atualizar_codigo(self, codigo):
        self.codigo_autorizacao = codigo
        config = toml.load(self.path)
        config.update(
            {
                "codigo_autorizacao": self.codigo_autorizacao,
            }
        )
        with open(self.path, "w") as f:
            toml.dump(config, f)


CONFIG = Config()
DOMINIO = CONFIG.dominio
URL = f"https://{DOMINIO}"

wrapper = Soywrapper(
    URL, sankhya_cookies["mge"], sankhya_cookies["mgecom"], sankhya_cookies["mgefin"]
)
