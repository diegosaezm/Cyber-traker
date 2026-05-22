"""
report.py — Ve el historial de precios guardado en la base de datos.
Uso: python report.py
"""

import sqlite3
from datetime import datetime

def show_report():
    try:
        conn = sqlite3.connect("prices.db")
    except Exception:
        print("❌ No se encontró prices.db. Ejecuta tracker.py primero.")
        return

    cur = conn.execute("""
        SELECT store, product_name, price, timestamp, product_url
        FROM price_history
        ORDER BY store, product_url, timestamp
    """)
    rows = cur.fetchall()

    if not rows:
        print("📭 Sin datos aún. Ejecuta tracker.py para empezar a registrar precios.")
        return

    # Agrupar por producto
    products = {}
    for store, name, price, ts, url in rows:
        key = url
        if key not in products:
            products[key] = {"store": store, "name": name, "url": url, "history": []}
        products[key]["history"].append((price, ts))

    print("\n" + "═"*70)
    print("  📊  CYBERDAY PRICE TRACKER — REPORTE DE PRECIOS")
    print("═"*70)

    for url, data in products.items():
        history = data["history"]
        prices  = [h[0] for h in history]
        current = prices[-1]
        max_p   = max(prices)
        min_p   = min(prices)
        discount = round((max_p - current) / max_p * 100, 1) if max_p else 0

        print(f"\n🏪 {data['store'].upper()}  |  {data['name'][:55]}")
        print(f"   Precio actual : ${current:>10,}")
        print(f"   Precio máximo : ${max_p:>10,}  (precio más alto registrado)")
        print(f"   Precio mínimo : ${min_p:>10,}")
        print(f"   Descuento real: {discount:>9}%  {'🔥 REAL!' if discount >= 5 else '⚠ Dudoso'}")
        print(f"   Registros     : {len(history)} mediciones")
        print(f"   URL           : {url[:65]}")

        print("   Historial:")
        for price, ts in history[-5:]:  # últimas 5
            dt = datetime.fromisoformat(ts).strftime("%d/%m %H:%M")
            bar = "█" * int(price / max_p * 20) if max_p else ""
            print(f"     {dt}  ${price:>10,}  {bar}")

    print("\n" + "═"*70 + "\n")
    conn.close()

if __name__ == "__main__":
    show_report()
