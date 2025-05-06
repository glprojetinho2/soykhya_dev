#!/bin/sh
  
find componentes/$1/* | entr -s "date -u +%H:%M:%S && python bi.py gravar $1"
