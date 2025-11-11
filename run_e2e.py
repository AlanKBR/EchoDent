#!/usr/bin/env python3
"""Script para iniciar Flask para testes E2E sem scheduler/jobs."""

import os
import sys
import traceback

# Desabilitar scheduler para testes E2E (previne bloqueios)
os.environ["DISABLE_SCHEDULER"] = "1"

from app import create_app

app = create_app()

if __name__ == "__main__":
    try:
        # Debug sem reloader
        app.run(debug=True, use_reloader=False, host="127.0.0.1", port=5000)
    except Exception as e:
        print("\n\n=== ERRO CRÍTICO NO SERVIDOR ===", file=sys.stderr)
        print(f"Tipo: {type(e).__name__}", file=sys.stderr)
        print(f"Mensagem: {e}", file=sys.stderr)
        print("\n=== TRACEBACK ===", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
