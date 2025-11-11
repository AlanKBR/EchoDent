"""Script para capturar logs do Flask."""

import logging

from app import create_app

app = create_app()

# Verificar se há logs registrados
with app.app_context():
    # Obter o logger do Flask
    logger = app.logger

    print("=== Handlers do Logger ===")
    for handler in logger.handlers:
        print(f"- {handler.__class__.__name__}: {handler}")

    print("\n=== Nível de logging ===")
    print(f"Logger level: {logging.getLevelName(logger.level)}")

    print("\n=== Testando log manual ===")
    logger.error("TESTE: Este é um erro de teste")
    logger.warning("TESTE: Este é um warning de teste")
