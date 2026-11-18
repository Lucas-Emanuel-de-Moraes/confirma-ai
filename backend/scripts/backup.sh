#!/usr/bin/env bash
# Backup do banco com pg_dump (RNF17 / PB35). Uso: ./scripts/backup.sh
# Funciona com o PostgreSQL do docker compose (contêiner confirma-ai-db).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
arquivo="backups/confirma_ai_$(date +%Y%m%d_%H%M%S).sql.gz"
docker exec confirma-ai-db pg_dump -U confirma -d confirma_ai --clean --if-exists | gzip > "$arquivo"
echo "Backup salvo em $arquivo ($(du -h "$arquivo" | cut -f1))"
