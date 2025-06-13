#!/bin/sh

function numnota() {
  python dados.py query "select nunota from tgfcab where numnota=$1" | jq -r ".[].NUNOTA"
}
 
function cotacao() {
  python dados.py query "
with tops_ven as (
select distinct codtipoper from tgftop top
where top.codcfo_saida in (5551, 5654, 5655, 5656, 5653, 5652, 5651, 5258, 5253, 5257, 5251, 5252, 5254, 5255, 5256, 5102, 5110, 5104, 5120, 5119, 5106, 5115, 5123, 5112, 5114, 5405, 5403, 5109, 5101, 5103, 5118, 5116, 5105, 5122, 5111, 5113, 5402, 5401, 5250, 5922)
), tops_pv as (
  select distinct codtipoper from tgftop top
  where top.tipmov='P'
  and (top.orcamento is null or top.orcamento = 'N')
  and top.codcfo_entrada=0
  and top.codcfo_saida=0
  and top.codcfo_entrada_fora=0
  and top.codcfo_saida_fora=0
)
select
remetente.cgc_cpf cnpj_remetente,
remetente.nomeparc nome_remetente,
(
select
concat(
tipo,
concat(concat(
' ',
nomeend
), concat(concat(
' ',
remetente.numend
),
concat(
' - ',
concat(nomecid, concat('/', u.uf))
))))
from tsiend
join tsicid c on c.codcid = remetente.codcid
join tsiufs u on c.uf = u.coduf
where codend=remetente.codend) endereco_coleta,
destinatario.cgc_cpf cnpj_destinatario,
destinatario.nomeparc nome_destinatario,
(
select
concat(
tipo,
concat(concat(
' ',
nomeend
), concat(concat(
' ',
destinatario.numend
),
concat(
' - ',
concat(nomecid, concat('/', u.uf))
))))
from tsiend
join tsicid c on c.codcid = destinatario.codcid
join tsiufs u on c.uf = u.coduf
where codend=destinatario.codend) endereco_destinatario,
triangular.cgc_cpf cpf_triangular,
triangular.nomeparc nome_triangular,
(
select
concat(
tipo,
concat(concat(
' ',
nomeend
), concat(concat(
' ',
triangular.numend
),
concat(
' - ',
concat(nomecid, concat('/', u.uf))
))))
from tsiend
join tsicid c on c.codcid = triangular.codcid
join tsiufs u on c.uf = u.coduf
where codend=triangular.codend) endereco_triangular,
(case CIF_FOB
when 'T' then 'Terceiros'
when 'R' then 'Transp. Próprio Remetente'
when 'S' then 'Sem Frete'
when 'D' then 'Transp. Próprio Destinatário'
when 'C' then 'CIF'
when 'F' then 'FOB'
else 'CIF'
end
) modalidade,
observacao,
qtdvol,
destinatario.cep destinatario_cep,
remetente.cep remetente_cep,
triangular.cep triangular_cep,
vlrnota
from tgfcab c
join tgfpar destinatario on destinatario.codparc = c.codparc
join tgfpar triangular on triangular.codparc = c.codparcdest
join tgfpar remetente on remetente.codparc = c.codemp
where nunota=$1
" | jq '.[0] | "CNPJ do remetente: \(.CNPJ_REMETENTE)\nNome do remetente: \(.NOME_REMETENTE)\nEndereço de coleta: \(.ENDERECO_COLETA) - CEP \(.REMETENTE_CEP)\n\nCNPJ do destinatário: \(.CNPJ_DESTINATARIO)\nNome do destinatário: \(.NOME_DESTINATARIO)\nEndereço de destino: \(.ENDERECO_DESTINATARIO) - CEP \(.DESTINATARIO_CEP)\nCPF do destinatário (P.F.): \(.CPF_TRIANGULAR)\nNome do destinatário (P.F.): \(.NOME_TRIANGULAR)\nEndereço de destino (P.F.): \(.ENDERECO_TRIANGULAR) - CEP \(.TRIANGULAR_CEP)\n\nQuantidade de volumes: xxxxxxxxxxxx\nPeso: xxxxxxxxxxxxxxx\nTipo de carga: xxxxxxxxxxxxxxxx\nValor da nota: R$ \(.VLRNOTA)\nModalidade: \(.MODALIDADE)\n\nMedidas:\nxxxxxxxxxxxxxxx\n\nObservação da nota:\n\(.OBSERVACAO)\n\nPor favor, forneça-nos as seguintes informações:\n1) Código único da cotação;\n2) Prazo para coleta;\n3) Prazo para entrega pós coleta;\n4) Valor do frete."' -r
}
