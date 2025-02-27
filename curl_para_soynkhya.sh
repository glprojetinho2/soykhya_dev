#!/bin/sh
corpo="$(wl-paste | grep -oE 'data-raw .+' | cut -d' ' -f2- | cut -d "'" -f2 | jq '.requestBody')"
servico="$(wl-paste | grep -oP 'serviceName=([^&])+' | cut -d'=' -f2)"
echo -e "r = self.soyrequest(\"$servico\",$corpo).json()"
