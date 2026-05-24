"""
CyberDay Chile - Price Tracker
Monitorea precios de PCs/Notebooks en Falabella, Ripley y Paris
y envía alertas por email cuando detecta bajadas reales de precio.
"""

import sys
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import sqlite3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import time
import logging
from config import EMAIL_CONFIG, PRODUCTS
from db import init_db, save_price, get_last_price, get_last_date, get_max_price
from datetime import date
import os 

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
import sys

# Fix para Windows: forzar UTF-8 en la terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("tracker.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)






# ─────────────────────────────────────────────
# Scrapers por tienda (con Playwright para JS)
# ─────────────────────────────────────────────
def scrape_with_playwright(url, price_selector, name_selector):
    """Scraper genérico con Playwright para sitios con JavaScript."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)  # espera carga JS

            # Precio
            price_el = page.query_selector(price_selector)
            raw_price = price_el.inner_text().strip() if price_el else None

            # Nombre
            name_el = page.query_selector(name_selector)
            name = name_el.inner_text().strip() if name_el else "Sin nombre"

            browser.close()

            if raw_price:
                price = int("".join(filter(str.isdigit, raw_price)))
                return {"name": name, "price": price, "url": url}
    except Exception as e:
        log.error(f"Error scraping {url}: {e}")
    return None


def scrape_falabella(url):
    """
    Falabella guarda los precios en atributos data-* estables en los <li>:
      data-cmr-price      → precio con tarjeta CMR
      data-internet-price → precio internet (el que queremos, prices-0)
      data-normal-price   → precio normal tachado
    Usamos esos atributos en vez de clases CSS que cambian con cada deploy.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            # Precio internet (prices-0) via atributo data estable
            price_el = page.query_selector("li[data-internet-price]")
            raw_price = price_el.get_attribute("data-internet-price") if price_el else None

            # Si no hay precio internet, intentar CMR
            if not raw_price:
                price_el = page.query_selector("li[data-cmr-price]")
                raw_price = price_el.get_attribute("data-cmr-price") if price_el else None

            # Nombre del producto
            name_el = (page.query_selector("h1[class*='product-title']") or
                       page.query_selector("h1[class*='pdp-title']") or
                       page.query_selector("h1"))
            name = name_el.inner_text().strip() if name_el else "Sin nombre"
            browser.close()

            if raw_price:
                # El valor viene como "649.990" o "649990"
                price = int("".join(filter(str.isdigit, raw_price)))
                if price > 0:
                    return {"name": name, "price": price, "url": url}
    except Exception as e:
        log.error(f"Error scraping Falabella {url}: {e}")
    return None


def scrape_ripley(url):
    return scrape_with_playwright(
        url,
        price_selector="div.best-price",
        name_selector="h1.product-title"
    )
def scrape_dbs(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                locale="es-CL",
            )
            page = context.new_page()
            page.goto(url, timeout=30000, wait_until="networkidle")  # espera red idle
            page.wait_for_selector("[data-price-amount]", timeout=10000)  # espera el precio
            page.wait_for_timeout(3000)

            price_el = page.query_selector("[data-price-amount]")
            raw_price = price_el.get_attribute("data-price-amount") if price_el else None

            name_el = page.query_selector("h1")
            name = name_el.inner_text().strip() if name_el else "Sin nombre"
            browser.close()

            if raw_price:
                price = int(float(raw_price))
                return {"name": name, "price": price, "url": url}
    except Exception as e:
        log.error(f"Error scraping DBS {url}: {e}")
    return None

def scrape_paris(url):
    return scrape_with_playwright(
        url,
        price_selector="span.price-sell",
        name_selector="h1.product-name"
    )


SCRAPERS = {
    "falabella": scrape_falabella,
    "ripley":    scrape_ripley,
    "paris":     scrape_paris,
    "dbs":       scrape_dbs
}


# ─────────────────────────────────────────────
# Detección de bajada real de precio
# ─────────────────────────────────────────────
def calculate_discount(old_price, new_price):
    if not old_price or old_price == 0:
        return 0
    return round((old_price - new_price) / old_price * 100, 1)


def is_real_discount(conn, url, new_price, min_discount_pct=5):
    from db import get_max_price
    max_price = get_max_price(conn, url)
    if not max_price:
        return False, 0
    discount = calculate_discount(max_price, new_price)
    return discount >= min_discount_pct, discount


# ─────────────────────────────────────────────
# Email
# ─────────────────────────────────────────────
def send_email_alert(alerts):
    """Envía un email con todos los productos en oferta real."""
    cfg = EMAIL_CONFIG
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔥 CyberDay Alert — {len(alerts)} oferta(s) real(es) detectada(s)"
    msg["From"]    = cfg["sender"]
    msg["To"]      = cfg["recipient"]

    # HTML body
    rows = ""
    for a in alerts:
        rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee">{a['store'].capitalize()}</td>
            <td style="padding:8px;border-bottom:1px solid #eee">{a['name']}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;color:#e53e3e">
                ${a['new_price']:,}
            </td>
            <td style="padding:8px;border-bottom:1px solid #eee;color:#38a169">
                -{a['discount']}%
            </td>
            <td style="padding:8px;border-bottom:1px solid #eee">
                <a href="{a['url']}">Ver producto</a>
            </td>
        </tr>
        """

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto">
        <h2 style="color:#2d3748">🖥️ CyberDay Price Tracker</h2>
        <p>Se detectaron <strong>{len(alerts)}</strong> oferta(s) con descuento real:</p>
        <table style="width:100%;border-collapse:collapse">
            <thead>
                <tr style="background:#2d3748;color:white">
                    <th style="padding:10px;text-align:left">Tienda</th>
                    <th style="padding:10px;text-align:left">Producto</th>
                    <th style="padding:10px;text-align:left">Precio actual</th>
                    <th style="padding:10px;text-align:left">Descuento real</th>
                    <th style="padding:10px;text-align:left">Link</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <p style="color:#718096;font-size:12px;margin-top:20px">
            El descuento real se calcula comparando con el precio más alto registrado en el historial.
        </p>
    </body></html>
    """

    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"]) as server:
            server.login(cfg["sender"], cfg["password"])
            server.sendmail(cfg["sender"], cfg["recipient"], msg.as_string())
        log.info(f"✅ Email enviado con {len(alerts)} alertas.")
    except Exception as e:
        log.error(f"Error enviando email: {e}")


# ─────────────────────────────────────────────
# Loop principal
# ─────────────────────────────────────────────
def run_tracker(interval_minutes=30):
    conn = init_db()
    log.info(f"🚀 Tracker iniciado. Revisando cada {interval_minutes} min.")
    log.info(f"   Productos en seguimiento: {sum(len(v) for v in PRODUCTS.values())}")

    while True:
        alerts = []

        for store, urls in PRODUCTS.items():
            scraper = SCRAPERS.get(store)
            if not scraper:
                log.warning(f"No hay scraper para '{store}'")
                continue

            for url in urls:
                log.info(f"Revisando [{store}] {url[:60]}...")
                result = scraper(url)

                if not result:
                    log.warning(f"  ⚠ No se pudo obtener precio.")
                    continue

                new_price = result["price"]
                name      = result["name"]
                log.info(f"  💰 {name[:50]} → ${new_price:,}")

                from datetime import date

                real, discount = is_real_discount(conn, url, new_price, min_discount_pct=5)

                last_price = get_last_price(conn, url)
                last_date  = get_last_date(conn, url)
                hoy        = date.today().isoformat()

                if last_price != new_price or last_date != hoy:
                    save_price(conn, store, url, name, new_price)
                    log.info("  Guardado.")
                else:
                    log.info("  Sin cambios hoy, omitiendo.")

                if real:
                    log.info(f"  🔥 OFERTA REAL detectada: -{discount}%")
                    alerts.append({
                        "store":     store,
                        "name":      name,
                        "new_price": new_price,
                        "discount":  discount,
                        "url":       url,
                    })

                time.sleep(2)  # pausa entre requests

        if alerts:
            send_email_alert(alerts)
        else:
            log.info("Sin ofertas reales en este ciclo.")

        if os.environ.get("RUN_ONCE") == "true":
            log.info("MODO GIT ACTIVADO - CICLO ÚNICO OKEI")
            break

        log.info(f"Esperando {interval_minutes} minutos para la próxima revisión...\n")
        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    run_tracker(interval_minutes=30)
