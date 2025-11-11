"""Service para gerenciar configurações de tema/estética (global).

Regras:
- Armazena cores primárias/secundárias em GlobalSetting (public schema)
- Atomicidade mandatória (try/commit/rollback)
- Validação básica de formato de cores (#RRGGBB)
"""

from __future__ import annotations

import re

from app.services import settings_service

# Chaves de tema armazenadas em GlobalSetting
THEME_KEYS = {
    "THEME_PRIMARY_COLOR",
    "THEME_SECONDARY_COLOR",
    "THEME_USE_SYSTEM_COLOR",  # "true" ou "false"
}


def is_valid_hex_color(color: str) -> bool:
    """Valida se a string é uma cor hexadecimal válida (#RRGGBB)."""
    if not color:
        return False
    return bool(re.match(r"^#[0-9A-Fa-f]{6}$", color.strip()))


def get_theme_settings() -> dict:
    """Retorna as configurações de tema atuais.

    Returns:
        Dict com chaves: primary_color, secondary_color, use_system_color
    """
    all_settings = dict(settings_service.get_all_settings())

    return {
        "primary_color": all_settings.get("THEME_PRIMARY_COLOR", "#0d6efd"),
        "secondary_color": all_settings.get(
            "THEME_SECONDARY_COLOR", "#6c757d"
        ),
        "use_system_color": all_settings.get(
            "THEME_USE_SYSTEM_COLOR", "false"
        ).lower()
        in ["true", "1", "yes"],
    }


def update_theme_settings(data: dict) -> tuple[bool, str]:
    """Atualiza configurações de tema.

    Args:
        data: Dict com chaves opcionais:
              - primary_color: str (hex)
              - secondary_color: str (hex)
              - use_system_color: bool

    Returns:
        Tupla (success: bool, message: str)
    """
    updates = {}

    # Validação de cores
    if "primary_color" in data:
        color = data["primary_color"].strip()
        if not is_valid_hex_color(color):
            return False, "Cor primária inválida (use formato #RRGGBB)"
        updates["THEME_PRIMARY_COLOR"] = color

    if "secondary_color" in data:
        color = data["secondary_color"].strip()
        if not is_valid_hex_color(color):
            return False, "Cor secundária inválida (use formato #RRGGBB)"
        updates["THEME_SECONDARY_COLOR"] = color

    # Toggle de sistema
    if "use_system_color" in data:
        value = data["use_system_color"]
        if isinstance(value, str):
            use_system = value.lower() in ["true", "1", "yes", "on"]
        else:
            use_system = bool(value)
        updates["THEME_USE_SYSTEM_COLOR"] = "true" if use_system else "false"

    # Atualiza em lote
    if updates:
        success = settings_service.update_settings_bulk(updates)
        if success:
            return True, "Tema atualizado com sucesso"
        else:
            return False, "Erro ao salvar configurações de tema"

    return True, "Nenhuma alteração feita"
