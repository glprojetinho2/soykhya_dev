#!/bin/sh
find componentes/$1/* | entr python bi.py gravar $1
