from reportlab.pdfgen import canvas
import subprocess
import sys
from utils import *
from config import *
import argparse


def emitir_etiquetas(nf: int, transportadora=None, volumes=None, usar_parceiro=None):
    _nota = wrapper.soyquery(
        f"""
        select qtdvol, vlrnota, p.nomeparc, t.nomeparc nometransp, d.nomeparc nomeparcdest, d.codparc codparcdest, destcid.nomecid nomeciddest, cid.nomecid, observacao
         from tgfcab c
         join tgfpar p on c.codparc = p.codparc
         join tsicid cid on cid.codcid = p.codcid
         join tgfpar t on t.codparc = c.codparctransp
         join tgfpar d on d.codparc = c.codparcdest
         join tsicid destcid on destcid.codcid = d.codcid
         where c.numnota={nf} and tipmov = 'V' and statusnota='L'
        """
    )
    assert len(_nota) != 0, f"Nenhuma nota encontrada"
    nota = _nota[0]
    if len(_nota) > 1:
        for i in range(1, len(_nota) + 1):
            print(f"{i}) {_nota[i-1]["NOMEPARC"]} (Valor: R${_nota[i-1]["VLRNOTA"]})")
        escolha = int(input("Escolha uma das notas acima: "))

        if escolha <= len(_nota) and escolha >= 0:
            nota = _nota[escolha - 1]
        else:
            print("Alternativa inválida.")
            sys.exit(1)

    print(f"Iniciando criação de etiqueta para a nota {nf}.")
    print(f"Empresa: {nota["NOMEPARC"]}")
    print(f"Cidade da empresa: {nota["NOMECID"]}")
    print(f"Parceiro Destino: {nota["NOMEPARCDEST"]}")
    print(f"Cidade Destino: {nota.get("AD_CIDADE_DESTINO") or "Vazio"}")

    volumes = volumes or nota["QTDVOL"]
    print(f"Quantidade de volumes: {volumes}")

    cidade = nota["NOMECID"]
    parceiro = nota["NOMEPARC"]
    if not usar_parceiro:
        if str(nota["CODPARCDEST"]) != "0":
            parceiro = nota["NOMEPARCDEST"]
            cidade = nota["NOMECIDDEST"]
    print(f"Cidade do destinatário: {cidade}")
    print()
    observacao_nota = nota["OBSERVACAO"]
    if observacao_nota is not None:
        print(f"Observação: {observacao_nota}")
        _cidade = input(
            "Nome da cidade de entrega. Se a cidade da nota já está correta, só aperta 'Enter': "
        )
        if not len(_cidade.strip()) == 0:
            cidade = _cidade

    transportadora = transportadora or nota["NOMETRANSP"]

    largura = 300
    altura = largura * 89 / 111

    c = canvas.Canvas("etiqueta.pdf", (largura, altura))
    for i in range(int(volumes)):
        c.setFont("Helvetica", 32)
        c.drawString(largura * 0.2, altura * 0.85, f"NF: {nf}")
        c.setFont("Helvetica", 16)
        if len(nota["NOMEPARC"]) > 20:
            c.setFont("Helvetica", 12)
        c.drawString(largura * 0.1, altura * 0.70, f"Cliente: {parceiro}")
        c.drawString(largura * 0.1, altura * 0.55, f"Cidade: {cidade}")
        if len(transportadora) > 20:
            c.setFont("Helvetica", 12)
        c.drawString(largura * 0.1, altura * 0.40, f"Transp: {transportadora}")
        c.setFont("Helvetica", 16)
        c.drawString(largura * 0.1, altura * 0.25, f"Volumes: {volumes}")
        c.setFont("Helvetica", 12)
        c.drawString(largura * 0.8, altura * 0.15, f"{i+1}/{volumes}")
        c.showPage()
    c.save()
    subprocess.run(["lp", "-d", "elgin", "etiqueta.pdf"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Faça etiquetas sem ter de usar bloatware"
    )
    parser.add_argument("nf", type=int, help="Número da nota fiscal.")
    parser.add_argument(
        "--transportadora",
        "-t",
        help="Usar outra transportadora na etiqueta.",
    )
    parser.add_argument(
        "--volumes",
        "-v",
        help="Usar outra quantidade de volumes na etiqueta.",
    )
    parser.add_argument(
        "--parceiro",
        "-p",
        action="store_true",
        help="Usar informações do parceiro, ignorando o destinatário.",
    )

    args = parser.parse_args()
    emitir_etiquetas(args.nf, args.transportadora, args.volumes, args.parceiro)
