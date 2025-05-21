Trabalhe na linha de comando sem ter de interagir com o sistema hinduista Soynkhia (vulgo Sankhya).
# Uso
Assegura-te de que o `python` e o `pipenv` estão instalados.
Executa os seguintes comandos:
```bash
python -m pipenv shell
python dados.py -h
python acao.py -h
python bi.py -h
python faturamento.py -h
python importacao.py -h
```
Lê o manual e as mensagens de ajuda atentamente (RTFM) e começa a mourejar.

## ICMS

O cadastro de alíquotas de icms pode ser feito através de arquivos no formato TOML. Basta criar um arquivo nesse formato dentro da pasta `icms` que se acha na raiz do projeto.

### Passo a passo
Cria o arquivo `icms/regra1.toml` (pouco importa o nome) com os conteúdos abaixo.
```toml
origem="AL"
destino="AL"
aliquota=99
reducao=1
restricao1=["N", "X"]
codigo_restricao1=[-1, -1]
restricao2="H"
codigo_restricao2="85159000"
cst=20
observacao="Lei bostileira feita pra te roubar."
outorga=0 
```
Agora só falta executar o comando `python faturamento.py icms`. Depois de executá-lo, tu podes verificar se as regras de ICMS foram realmente criadas com o seguinte comando:
```bash
python dados.py query "
select * from tgficm
where tiprestricao in ('N', 'X')
and tiprestricao2='H'
and codrestricao2='85159000'
and uforig=(select coduf from tsiufs where uf='AL')
and ufdest=(select coduf from tsiufs where uf='AL')
" -z tgficm -b
```
ou
```bash
python dados.py query "
select * from tgficm i
join tgfobs o on o.codobspadrao=i.codobspadrao
where lower(observacao)=lower('Lei bostileira feita pra te roubar.')
" -z tgficm -b
```
Mas isso não deve ser necessário.
