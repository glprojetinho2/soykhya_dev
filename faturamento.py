from utils import *
import typing
from etiquetas import emitir_etiquetas
from datetime import datetime
from rich.console import Console
from rich.table import Table
import argparse
from config import *
import urllib3
from urllib3.exceptions import InsecureRequestWarning

urllib3.disable_warnings(InsecureRequestWarning)


class ErroNaNota(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class LiberacaoPendente(Exception):
    def __init__(self, liberacoes: dict[str, str | float | int | None]):
        self.liberacoes = liberacoes
        super().__init__(
            "\n".join(
                [
                    f"Evento {liberacao["EVENTO"]} pendente para a nota {liberacao["NUCHAVE"]}."
                    for liberacao in liberacoes
                ]
            )
        )


def nome_conferente(nome: str | None) -> str | None:
    if (isinstance(nome, str) and len(nome) == 0) or nome is None:
        return None
    if nome in CONFIG.conferentes:
        return CONFIG.conferentes[nome]
    return nome.upper()


classificacao_icms = {
    "T": "Usar a da TOP",
    "R": "Revendedor",
    "C": "Consumidor Final Não Contribuinte",
    "P": "Produtor Rural",
    "X": "Consumidor Final Contribuinte",
    "I": "Isento de ICMS",
}

eventos_liberacao = {
    1: "Desconto Tipo Negociação",
    2: "Desconto Produto",
    3: "Limite de Crédito",
    4: "Prazo",
    5: "Prazo Médio Máximo",
    6: "Prazo Máximo",
    7: "Prazo Cad. Parceiro",
    8: "Atraso",
    9: "Tempo Inativo",
    10: "Estoque",
    11: "Evento descontinuado",
    12: "Frete CIF",
    13: "Valor Mínimo Tipo Negoc.",
    14: "Valor Máximo Tipo Negoc.",
    15: "Limite Créd. Mensal",
    16: "Metas de Despesa",
    17: "Procedure de Validação de Desconto",
    18: "Confirmação de Nota",
    19: "Lucro Mínimo",
    20: "Lançamento de Compras p/Contrato",
    21: "Fórmula Desc.Máx.Tipo Negociação",
    22: "Quantidade máxima de títulos vencidos",
    23: "Bonificação",
    24: "Autorização de Pagamento",
    25: "Desconto por Item da Nota",
    26: "Limite de Crédito p/ Média Negociações",
    27: "Fórmula Desc.Máx.Tipo Negoc. por Item",
    28: "Limite de Bonificação por Projeto",
    29: "Desconto no Financeiro",
    30: "Perdão de Multa no Financeiro",
    31: "Perdão de Juros no Financeiro",
    32: "Descontos Financeiros por Parceiro",
    33: "Antecipação de Orçamento",
    34: "Suplementação de Orçamento",
    35: "Transferência de Orçamento",
    36: "EPI Antes do Vencimento",
    37: "EPI Sem Devolução",
    38: "Características de Análises de Laudo",
    39: "Quantidade de Parcelas na Renegociação",
    40: "Solicitação de Compra p/produto em Estoque",
    41: "Confirmação de Nota com análise dos itens",
    42: "Limite de Crédito por Grupo de Tip.Título",
    43: "Desconto em Medição de Contrato",
    44: "Liberação exigida pela TOP",
    45: "Liberação para Laudo de matéria prima",
    46: "Liberação de conferência de impostos",
    47: "Liberação de desvios em pesagens",
    48: "Margem de Contribuição Mínima",
    49: "Desconto de Frete",
    50: "Desconto de Grande Carga",
    51: "Desconto Progressivo Extra",
    52: "Despesas de CPR",
    53: "Capacidade Produção Diária em M3",
    54: "Orçamento por Intervalo único",
    55: "Liberação de grupo de autorização",
    56: "Variação percentual no custo pedido/nota",
    57: "Variação no prazo médio de compra",
    58: "Variação na quantidade Pedido/Nota",
    59: "Validação de prazo Pedido/Nota",
    60: "Validação da quantidade de pedidos pendentes no estoque",
    61: "Liberação de data de validade menor que o previsto.",
    62: "Liberação Comercial",
    63: "Liberação Financeira",
    64: "Corte/divergência de pedido (Conferência)",
    65: "Variação no valor Pedido/Nota",
    66: "Desconto do item abaixo do calculado",
    67: "Excede Estoque Máximo",
    68: "Variação do vlr. unit. orig./dest.",
    69: "Desconto de frete do pedido/nota",
    70: "Acréscimo do valor unitário ref. ao último custo",
    71: "Liberação de Limite de Venda por Parceiro",
    72: "Tolerância na variação de peso do pedido excedida (WMS)",
    73: "Variação do frete sobre Conhecimento Transporte",
    74: "Venda mínima por Parceiro/Cidade/Região",
    75: "Diferença entre NCM, CEST: Origem ou FCI",
    76: "Diferença de impostos",
    77: "Análise de crédito expirada",
    78: "Liberação de agrupamento mínimo",
    79: "Fechamento Fiscal Contábil",
    80: "Desvio no consumo de material",
    81: "Desvio na quantidade apontada de PA",
    82: "Pendências Financeiras maiores que o Estoque Disponivel",
    83: "Liberação de Laudo de Classificação p/ Armazenagem",
    84: "Liberação para Destinação de Verba",
    85: "Diferença entre NCM",
    86: "Diferença entre CEST",
    87: "Diferença entre Origem",
    88: "Diferença entre FCI,",
}


def frete(codigo: int) -> str:
    assert codigo in [0, 1, 2]
    if codigo == 0:
        return "C"
    elif codigo == 1:
        return "F"
    elif codigo == 2:
        return "S"
    else:
        raise Exception("bruh")


def emitir_etiquetas_escolhendo_transportadora(nf: int, transportadora: int | None):
    """
    Emite etiquetas com as informações da nota.
    A transportadora de código `transportadora` será usada na etiqueta
    caso esse código seja especificado.
    """
    print("Emitindo etiquetas.")
    if transportadora:
        nome_transportadora = wrapper.soyquery(
            f"select nomeparc from tgfpar where codparc={args.transportadora}"
        )[0]["NOMEPARC"]
        emitir_etiquetas(nf, nome_transportadora, args.volumes)
    else:
        emitir_etiquetas(nf, None, args.volumes)


class NotaExistenteEmOutraTOP(Exception):
    def __init__(self, numero_pedido: int, tops: list[int]):
        tops_str = [str(top) for top in list(set(tops))]
        self.message = (
            f"Pedido {numero_pedido} já tinha pedido na(s) top(s) {", ".join(tops_str)}"
        )
        super().__init__(self.message)


def faturar_se_nao_houver_nota(pedido: dict[str, str | int | None], top: int) -> int:
    """
    Fatura um pedido para uma top de destino caso já não haja nota
    vinculada ao mesmo pedido.
    O retorno é o número da nota.
    """
    assert pedido["NUNOTA"] is not None
    notas = wrapper.soyquery(
        f"""
select distinct c.statusnfe, v.nunota, c.codtipoper
from tgfcab c
join tgfvar v on c.nunota = v.nunota
where nunotaorig={pedido["NUNOTA"]}
"""
    )
    if len(notas) > 0:
        notas_da_top = [nota for nota in notas if int(nota["CODTIPOPER"]) == int(top)]
        assert (
            len(notas_da_top) <= 1
        ), f"Mais de uma nota com a top {top} para o pedido {pedido["NUNOTA"]}"
        if len(notas_da_top) == 0:
            tops = [nota["CODTIPOPER"] for nota in notas]
            raise NotaExistenteEmOutraTOP(int(pedido["NUNOTA"]), tops)
        else:
            nota_da_top = notas_da_top[0]
            return int(nota_da_top["NUNOTA"])
    else:
        return int(wrapper.faturar_documento([int(pedido["NUNOTA"])], top)["nota"])


def aprovar_nota(
    info_nota: dict[str, Any], tipo_entrega=None, liberador: int | None = None
):
    """
    Valida nota e tenta aprová-la na SEFAZ.
    """
    if tipo_entrega in CONFIG.sempre_tem_transportadora:
        print(f"Tipo da entrega: {tipo_entrega}.")
        assert (
            str(info_nota["CODPARCTRANSP"]) != "0"
            and info_nota["CODPARCTRANSP"] is not None
        ), "Pedido sem transportadora."
    if info_nota["STATUSNOTA"] != "L":
        print(f"Confirmando nota.")
        confirmacao = wrapper.confirmar_documento([int(info_nota["NUNOTA"])])

        if len(confirmacao["liberacoes"]) > 0:
            chaves = {
                "NUCHAVE": "Chave",
                "EVENTO": "Evento",
                "CODUSULIB": "Liberador",
                "REPROVADO": "Reprovado",
                "VLRLIMITE": "Limite",
                "VLRATUAL": "Solicitado",
                "VLRLIBERADO": "Liberado",
                "OBSERVACAO": "Observação",
            }
            tabela_liberacao = Table(title="Liberações Pendentes")
            liberacoes = confirmacao["liberacoes"]
            for coluna in chaves.values():
                tabela_liberacao.add_column(coluna)
            for liberacao in liberacoes:

                def embelezar(chave, valor):
                    if chave == "EVENTO":
                        return eventos_liberacao[valor]
                    return str(valor)

                tabela_liberacao.add_row(
                    *[embelezar(chave, liberacao[chave]) for chave in chaves.keys()]
                )
            console = Console()
            console.print(tabela_liberacao)
            codigo_liberador = None
            if liberador is None:
                print("****************************")
                liberadores = CONFIG.liberadores
                for liberador_possivel in liberadores:
                    print(
                        f"{liberador_possivel["nome"]} = {liberador_possivel["abreviado"]}"
                    )
                escolha = input("Escolha um dos liberadores acima: ")
                for liberador_possivel in liberadores:
                    if escolha == liberador_possivel["abreviado"]:
                        codigo_liberador = int(liberador_possivel["codigo"])
                assert codigo_liberador is not None, "Escolha um liberador da lista."
                print("****************************")
            else:
                codigo_liberador = liberador
            for liberacao in liberacoes:
                wrapper.soysave(
                    "LiberacaoLimite",
                    [
                        {
                            "pk": liberacao,
                            "mudanca": {"CODUSULIB": codigo_liberador},
                        }
                    ],
                )
            raise LiberacaoPendente(liberacoes)

        erros_da_nf(info_nota)
    elif info_nota["STATUSNFE"] != "A":
        wrapper.gerar_lote([int(info_nota["NUNOTA"])])
        erros_da_nf(info_nota)
        status = wrapper.soyquery(
            f"select statusnfe from tgfcab where nunota={info_nota["NUNOTA"]}"
        )[0]["STATUSNFE"]
        assert (
            status == "A"
        ), "Gerar lote não foi o suficiente para faturar a nota, porém a nota não contém erros."
    else:
        print("Nota já estava confirmada e aprovada na SEFAZ.")


def mostrar_informacoes_do_documento(info_nota: dict[str, str | float | int | None]):
    tabela_nota = Table(title="Informações da nota")
    colunas_nota = {
        "NUNOTA": "Núm. Único",
        "NUMNOTA": "NF",
        "PESOBRUTO": "Peso Bruto",
        "QTDVOL": "Qtd. de Volumes",
        "CIF_FOB": "CIF ou FOB",
        "CODPARCTRANSP": "Transportadora",
        "AD_CONFERENTE": "Conferente",
        "VLRNOTA": "Valor da Nota",
    }
    for coluna in colunas_nota.values():
        tabela_nota.add_column(coluna)
    valores_nota = [str(info_nota[coluna]) for coluna in colunas_nota.keys()]
    tabela_nota.add_row(*valores_nota)

    tabela_cliente = Table(title="Cliente")
    colunas_cliente = {
        "CODPARC": "Código",
        "NOMEPARC": "Nome",
        "IDENTINSCESTAD": "Insc. Estadual",
        "CLASSIFICMS": "Classificação ICMS",
    }
    parceiro_nota = wrapper.soyquery(
        f"select {", ".join(colunas_cliente.keys())} from tgfpar where codparc = {info_nota["CODPARC"]}"
    )

    for coluna in colunas_cliente.values():
        tabela_cliente.add_column(coluna)
    for parceiro in parceiro_nota:

        valores_itens = []
        for coluna in colunas_cliente.keys():
            valor = str(parceiro[coluna.split(".")[-1]])
            if coluna == "CLASSIFICMS":
                valores_itens.append(classificacao_icms[valor])
            else:
                valores_itens.append(valor)
        tabela_cliente.add_row(*valores_itens)

    colunas_itens = {
        "i.CODPROD": "Código",
        "DESCRPROD": "Descrição",
        "QTDNEG": "Quantidade",
        "i.CODVOL": "Unidade",
        "VLRUNIT": "Vlr. Unitário",
        "VLRTOT": "Vlr. Total",
        "CODTRIB": "CST",
        "NCM": "NCM",
        "IDALIQICMS": "Id da Alíq. de ICMS",
        "ALIQICMS": "Alíquota de ICMS",
        "CSTIPI": "CST do IPI",
        "VLRIPI": "Valor do IPI",
        "ALIQIPI": "Alíquota do IPI",
    }
    produtos_nota = wrapper.soyquery(
        f"""
        select {", ".join(colunas_itens.keys())}
        from tgfite i
        join tgfpro p on i.codprod = p.codprod
        where nunota = {info_nota["NUNOTA"]}
        """
    )
    tabela_itens = Table(title="Itens da nota")
    for coluna in colunas_itens.values():
        tabela_itens.add_column(coluna)
    for produto in produtos_nota:
        valores_itens = [
            str(produto[coluna.split(".")[-1]]) for coluna in colunas_itens.keys()
        ]
        tabela_itens.add_row(*valores_itens)

    console = Console()
    console.print(tabela_nota)
    console.print(tabela_cliente)
    console.print(tabela_itens)


def erros_da_nf(info_nota: dict[str, str | float | int | None]):
    """
    Dá um erro caso haja algum impedimento na nota.
    """
    erro_nfe = wrapper.soyquery(
        f"select ocorrencias from tgfact where nunota={info_nota["NUNOTA"]}"
    )
    if len(erro_nfe) > 0:
        mostrar_informacoes_do_documento(info_nota)
        raise ErroNaNota("\n".join([erro["OCORRENCIAS"] for erro in erro_nfe]))


def nota_triangular(
    numero_pedido: int,
    volumes: int,
    peso: float,
    cif_fob: str,
    conferente: str | None = None,
    _destinatario: int | None = None,
    transportadora: int | None = None,
    impressoes=False,
    liberador: int | None = None,
):
    pedido = wrapper.soyquery(f"select * from tgfcab where nunota = {numero_pedido}")[0]
    tipo_entrega = pedido.get(CONFIG.campo_tipo_entrega.upper())

    if str(pedido["CODPARCDEST"]) == "0":
        destinatario = _destinatario or input(
            "Digite o código da pessoa física que receberá a mercadoria:"
        )
        int(destinatario)
    else:
        destinatario = pedido["CODPARCDEST"]

    nunota_triangular = faturar_se_nao_houver_nota(pedido, CONFIG.top_nfe_triangular)
    # Mudanças na nota
    mensagem_triangular = wrapper.soyquery(
        f"""select 
         concat('DESTINADA A PESSOA FISICA ', concat(concat(concat(nomeparc, ' CPF:'), cgc_cpf), ' NF EMITIDA NOS TERMOS DO LIVRO II ART 59 DO DEC 3769997.')) msg from tgfpar
         where codparc = {destinatario}"""
    )[0]["MSG"]
    if mensagem_triangular in pedido["OBSERVACAO"]:
        observacao_nova = pedido["OBSERVACAO"]
    else:
        observacao_nova = f"{pedido["OBSERVACAO"]}|{mensagem_triangular}"
    mudanca = {
        "OBSERVACAO": observacao_nova,
        "CODPARCDEST": destinatario,
        "CIF_FOB": cif_fob,
        "PESOBRUTO": peso,
        "QTDVOL": volumes,
        "CODPARCTRANSP": transportadora or pedido["CODPARCTRANSP"],
    }
    if conferente is not None:
        mudanca.update(
            {
                "AD_CONFERENTE": conferente,
                "AD_HORARIO_CONFERENCIA": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            }
        )
    wrapper.soysave(
        "CabecalhoNota",
        [
            {
                "pk": {"NUNOTA": nunota_triangular},
                "mudanca": mudanca,
            }
        ],
    )
    # Fim das mudanças na nota
    info_nota = wrapper.soyquery(
        f"select * from tgfcab where nunota = {nunota_triangular}"
    )[0]
    print(f"Nota de venda: {nunota_triangular}.")
    aprovar_nota(info_nota, tipo_entrega, liberador=liberador)
    info_nota = wrapper.soyquery(
        f"select * from tgfcab where nunota = {nunota_triangular}"
    )[0]

    assert nunota_triangular != 0
    mostrar_informacoes_do_documento(info_nota)
    numero_remessa = info_nota["NUREM"]
    assert numero_remessa is not None and numero_remessa != 0, "Nota sem remessa."
    wrapper.soysave(
        "CabecalhoNota",
        [
            {
                "pk": {"NUNOTA": numero_remessa},
                "mudanca": mudanca,
            }
        ],
    )
    remessa = wrapper.soyquery(f"select * from tgfcab where nunota={numero_remessa}")[0]
    aprovar_nota(remessa, tipo_entrega, liberador=liberador)
    if impressoes:
        print(f"Imprimindo tudo.")
        wrapper.imprimir_notas(
            [numero_remessa, numero_remessa, nunota_triangular, nunota_triangular]
        )
        if tipo_entrega in CONFIG.emitir_etiquetas:
            emitir_etiquetas_escolhendo_transportadora(
                remessa["NUMNOTA"], transportadora
            )


def nota_de_venda(
    numero_pedido: int,
    volumes: int,
    peso: float,
    cif_fob: str,
    conferente: str | None = None,
    transportadora: int | None = None,
    impressoes=False,
    liberador: int | None = None,
):
    pedido = wrapper.soyquery(f"select * from tgfcab where nunota = {numero_pedido}")[0]

    tipo_entrega = pedido.get(CONFIG.campo_tipo_entrega.upper())

    nunota = faturar_se_nao_houver_nota(pedido, CONFIG.top_venda_nfe)

    mudanca = {
        "PESOBRUTO": peso,
        "QTDVOL": volumes,
        "CIF_FOB": cif_fob,
        "CODPARCTRANSP": transportadora or pedido["CODPARCTRANSP"],
    }
    if conferente is not None:
        mudanca.update(
            {
                "AD_CONFERENTE": conferente,
                "AD_HORARIO_CONFERENCIA": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            }
        )
    wrapper.soysave(
        "CabecalhoNota",
        [
            {
                "pk": {"NUNOTA": nunota},
                "mudanca": mudanca,
            }
        ],
    )
    print(f"Gerada a nota {nunota}.")
    info_nota = wrapper.soyquery(f"select * from tgfcab where nunota = {nunota}")[0]
    aprovar_nota(info_nota, liberador=liberador)
    info_nota = wrapper.soyquery(f"select * from tgfcab where nunota = {nunota}")[0]
    print(f"Imprimindo nota {nunota} (nf={info_nota["NUMNOTA"]}).")
    mostrar_informacoes_do_documento(info_nota)

    if impressoes:
        wrapper.imprimir_notas([nunota, nunota])
        if tipo_entrega in CONFIG.emitir_etiquetas:
            emitir_etiquetas_escolhendo_transportadora(
                info_nota["NUMNOTA"], transportadora
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seja um faturista sem tocar no Soynkhya :)"
    )
    subparsers = parser.add_subparsers(dest="comando")

    triangular_parser = subparsers.add_parser("tri", help="Emite nota triangular.")
    triangular_parser.add_argument(
        "numero_pedido", type=int, help="Número único do pedido faturado."
    )
    triangular_parser.add_argument(
        "volumes", type=int, help="Quantidade de volumes da nota."
    )
    triangular_parser.add_argument("peso", type=float, help="Peso bruto da nota.")
    triangular_parser.add_argument(
        "frete", type=int, help="Tipo de frete. CIF=0, FOB=1 e 2 elimina o frete."
    )
    triangular_parser.add_argument(
        "conferente",
        help="Nome do conferente. Podes definir atalhos para esses nomes na configuração.",
    )
    triangular_parser.add_argument(
        "--transportadora",
        "-t",
        type=int,
        help="Código da transportadora a ser usada na nota.",
    )
    triangular_parser.add_argument(
        "--volumes",
        "-v",
        type=int,
        help="Usar outra quantidade de volumes na etiqueta (caso ela seja emitida).",
    )
    triangular_parser.add_argument(
        "--destinatario",
        "-d",
        type=str,
        help="Pessoa física que receberá a mercadoria.",
    )

    cancelar_parser = subparsers.add_parser("cancelar", help="Cancela nota.")
    cancelar_parser.add_argument("nf", type=int, help="NF a ser cancelada.")
    cancelar_parser.add_argument(
        "--justificativa", "-j", type=str, help="Justificativa do cancelamento."
    )

    excluir_parser = subparsers.add_parser("excluir", help="Cancela nota.")
    excluir_parser.add_argument("nunota", type=int, help="Documento que será excluído.")

    nfe_parser = subparsers.add_parser("nfe", help="Fatura nota de venda.")
    nfe_parser.add_argument(
        "numero_pedido", type=int, help="Número único do pedido faturado."
    )
    nfe_parser.add_argument("volumes", type=int, help="Quantidade de volumes da nota.")
    nfe_parser.add_argument("peso", type=float, help="Peso bruto da nota.")
    nfe_parser.add_argument(
        "frete", type=int, help="Tipo de frete. CIF=0, FOB=1 e 2 elimina o frete."
    )
    nfe_parser.add_argument(
        "conferente",
        help="Nome do conferente. Podes definir atalhos para esses nomes na configuração. O valor desse argumento populará o campo 'AD_CONFERENTE' do pedido.",
    )
    nfe_parser.add_argument(
        "--transportadora",
        "-t",
        type=int,
        help="Código da transportadora a ser usada na nota.",
    )
    nfe_parser.add_argument(
        "--volumes",
        "-v",
        help="Usar outra quantidade de volumes na etiqueta (caso ela seja emitida).",
    )

    args = parser.parse_args()

    if args.comando == "tri":
        numero_pedido = args.numero_pedido
        volumes = args.volumes
        peso = args.peso
        cif_fob = frete(args.frete)
        conferente = nome_conferente(args.conferente)
        nota_triangular(
            numero_pedido, volumes, peso, cif_fob, conferente, impressoes=True
        )

    elif args.comando == "excluir":
        wrapper.soyremove("CabecalhoNota", [{"NUNOTA": args.nunota}])
        print("Pronto.")

    elif args.comando == "cancelar":
        _nunota = wrapper.soyquery(
            f"select nunota from tgfcab where statusnfe='A' and numnota={args.nf}"
        )
        if len(_nunota) == 0:
            print(f"Nenhuma nota aprovada encontrada com o número {args.nf}")
        else:
            nunota_triangular = _nunota[0]["NUNOTA"]
            justificativa = args.justificativa or "erro na emissão"
            print(wrapper.cancelar_nota([nunota_triangular], justificativa))
            print(f"Nota {args.nf} cancelada com a justificativa '{justificativa}'.")

    elif args.comando == "nfe":
        numero_pedido = args.numero_pedido
        volumes = args.volumes
        peso = args.peso
        cif_fob = frete(args.frete)
        conferente = nome_conferente(args.conferente)
        nota_de_venda(
            numero_pedido, volumes, peso, cif_fob, conferente, impressoes=True
        )
