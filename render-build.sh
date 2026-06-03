#!/usr/bin/env bash
# Sair em caso de erro
set -o errexit

# Instalar o Tesseract e o idioma português
apt-get update
apt-get install -y tesseract-ocr tesseract-ocr-por