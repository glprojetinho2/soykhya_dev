from reportlab.pdfgen import canvas
import subprocess
import sys
from utils import *
from config import *
import argparse

parser = argparse.ArgumentParser(description="Faça etiquetas sem ter de usar bloatware")
parser.add_argument("nf", type=int, help="Número da nota fiscal.")
parser.add_argument(
    "--transportadora",
    "-t",
    action="store_true",
    help="Usar outra transportadora na etiqueta.",
)
parser.add_argument(
    "--volumes",
    "-v",
    action="store_true",
    help="Usar outra quantidade de volumes na etiqueta.",
)

args = parser.parse_args()

_nota = wrapper.soyquery(
    f"select qtdvol, vlrnota, p.nomeparc, t.nomeparc nometransp, cid.nomecid, observacao from tgfcab c join tgfpar p on c.codparc = p.codparc join tsicid cid on cid.codcid = p.codcid join tgfpar t on t.codparc = c.codparctransp where c.numnota={args.nf} and tipmov = 'V' and statusnota='L'"
)
assert len(_nota) != 0, f"Nenhuma nota encontrada"
nota = _nota[0]
if len(_nota) > 1:
    for i in range(1, len(_nota) + 1):
        print(f"{i}) {_nota[i-1]["NOMEPARC"]} (Valor: R${_nota[i-1]["VLRNOTA"]})")
    escolha = int(input("Escolha uma das notas acima: "))

    if escolha < len(_nota) and escolha >= 0:
        nota = _nota[escolha - 1]
    else:
        print("Alternativa inválida.")
        sys.exit(1)

print(f"Iniciando criação de etiqueta para a nota {args.nf}.")
print(f"Empresa: {nota["NOMEPARC"]}")
print()
cidade = nota["NOMECID"]
print(f"Cidade da nota: {cidade}")
observacao_nota = nota["OBSERVACAO"]
if observacao_nota is not None:
    print(f"Observação: {observacao_nota}")
    cidade = input(
        "Nome da cidade de entrega. Se a cidade da nota já está correta, só aperta 'Enter': "
    )
    if len(cidade.strip()) == 0:
        cidade = nota["NOMECID"]

transportadora = nota["NOMETRANSP"]
if args.transportadora:
    transportadora = input("Transportadora: ")
volumes = nota["QTDVOL"]
if args.volumes:
    volumes = int(input("Volumes: "))
largura = 300
altura = largura * 89 / 111

c = canvas.Canvas("etiqueta.pdf", (largura, altura))
for i in range(int(nota["QTDVOL"])):
    c.setFont("Helvetica", 32)
    c.drawString(largura * 0.2, altura * 0.85, f"NF: {args.nf}")
    c.setFont("Helvetica", 16)
    c.drawString(largura * 0.1, altura * 0.70, f"Cliente: {nota["NOMEPARC"]}")
    c.drawString(largura * 0.1, altura * 0.55, f"Cidade: {cidade}")
    c.drawString(largura * 0.1, altura * 0.40, f"Transp: {transportadora}")
    c.drawString(largura * 0.1, altura * 0.25, f"Volumes: {volumes}")
    c.showPage()
c.save()
subprocess.run(["lp", "-d", "elgin", "etiqueta.pdf"])
