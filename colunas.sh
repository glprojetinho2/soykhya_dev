#/bin/sh
python dados.py estrutura $1 | jq '.entity.field.[] | {a: .name, b: .description}' | cut -d':' -f2 | grep -E '\w' | sed "s/,/:/g" | sed 's/"$/",/g' | tr '\n' ' ' | sed 's/, $/}/' | sed 's/^/{/' | jq
