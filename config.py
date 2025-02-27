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
        with open(self.path, "w") as f:
            toml.dump(config, f)
        self.dominio = config["dominio"]
        self.codigo_autorizacao = config["codigo_autorizacao"]

    def gravar(self):
        conteudo = {
            "dominio": self.dominio,
            "codigo_autorizacao": self.codigo_autorizacao,
        }
        with open(self.path, "w") as f:
            toml.dump(conteudo, f)


CONFIG = Config()
DOMINIO = CONFIG.dominio
URL = f"https://{DOMINIO}/mge/service.sbr"

wrapper = Soywrapper(
    URL, sankhya_cookies["mge"], sankhya_cookies["mgecom"], sankhya_cookies["mgefin"]
)
