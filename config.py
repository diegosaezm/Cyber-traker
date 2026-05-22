# config.py — Lee configuración desde variables de entorno (para Railway)
# Localmente puedes setearlas en un archivo .env o directamente aquí.

import os
import json

# ─────────────────────────────────────────────
# Email — se leen desde variables de entorno en Railway
# ─────────────────────────────────────────────
EMAIL_CONFIG = {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 465,
    "sender":    os.environ.get("EMAIL_SENDER", "tu_email@gmail.com"),
    "password":  os.environ.get("EMAIL_PASSWORD", "xxxx xxxx xxxx xxxx"),
    "recipient": os.environ.get("EMAIL_RECIPIENT", "tu_email@gmail.com"),
}

# ─────────────────────────────────────────────
# Productos — se leen desde variable de entorno PRODUCTS_JSON
# Formato JSON: {"falabella": ["url1"], "ripley": ["url2"], "paris": []}
# Si no hay variable de entorno, usa los valores hardcodeados abajo.
# ─────────────────────────────────────────────
_products_json = os.environ.get("PRODUCTS_JSON", "")

if _products_json:
    PRODUCTS = json.loads(_products_json)
else:
    # Para desarrollo local — pon tus URLs aquí
    PRODUCTS = {
        "falabella": [
            "https://www.falabella.com/falabella-cl/product/17500185/Ideapad-Slim-3-Gen-10-Intel-Core-i5-13420H-24GB-RAM-512GB-SSD-15.3%22-WUXGA-(1920x1200)-Lenovo/17500185",
        ],
        "ripley": [
            # "https://simple.ripley.cl/...",
        ],
        "paris": [],
    }

# Descuento mínimo real para disparar alerta (%)
MIN_DISCOUNT_PCT = int(os.environ.get("MIN_DISCOUNT_PCT", "5"))

# Intervalo entre revisiones (minutos)
CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "30"))
