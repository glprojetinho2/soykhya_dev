#!/bin/sh
echo $1
python acao.py query "select count(*) a from tgfpro where ncm=$1" | jq -r '.[].A'
