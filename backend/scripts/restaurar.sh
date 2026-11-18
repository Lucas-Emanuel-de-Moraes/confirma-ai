#!/usr/bin/env bash
# Restaura um backup gerado por backup.sh. Uso: ./scripts/restaurar.sh backups/confirma_ai_AAAAMMDD_HHMMSS.sql.gz
set -euo pipefail
arquivo="${1:?Informe o arquivo de backup (.sql.gz)}"
read -r -p "Isto vai SOBRESCREVER o banco confirma_ai. Continuar? [s/N] " resp
[[ "$resp" =~ ^[sS]$ ]] || { echo "Cancelado."; exit 1; }
gunzip -c "$arquivo" | docker exec -i confirma-ai-db psql -q -U confirma -d confirma_ai
echo "Restauração concluída a partir de $arquivo"
