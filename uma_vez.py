from utils import *
from config import *

consulta = wrapper.soyquery(
    "select codprod, descrprod from tgfpro where lower(descrprod) like '%lona anti-chama%'"
)
produtos = [x["CODPROD"] for x in consulta]
print(json.dumps(consulta, indent=4))
mudancas = [
    {
        "pk": {"CODPROD": p},
        "mudanca": {"USOPROD": "V", "CODIPI": 1, "TEMIPIVENDA": "S", "CSTIPISAI": "50"},
    }
    for p in produtos
]
print(json.dumps(mudancas, indent=4))
input("Consumar mudanças?")
wrapper.soysave("Produto", mudancas)
