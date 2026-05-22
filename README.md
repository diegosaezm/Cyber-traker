# CyberDay Chile — Price Tracker 🖥️🔥

Monitorea precios de PCs y Notebooks en **Falabella, Ripley y Paris** antes y durante el CyberDay.
Detecta si un "descuento" es real o si la tienda infló el precio previamente.

---

## 📁 Archivos

| Archivo | Descripción |
|---|---|
| `tracker.py` | Script principal — monitorea y envía alertas |
| `config.py` | **Tu configuración** — emails y URLs de productos |
| `report.py` | Muestra el historial de precios en consola |
| `requirements.txt` | Dependencias Python |

---

## ⚙️ Instalación

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Instalar navegador para Playwright
playwright install chromium

# 3. Editar config.py con tus datos
```

---

## 🔧 Configuración (config.py)

### Email (Gmail)
1. Ve a https://myaccount.google.com/apppasswords
2. Crea una contraseña de aplicación para "Mail"
3. Pégala en `config.py` → `"password"`

### Agregar productos
Busca el producto en la tienda, copia la URL y pégala en `PRODUCTS`:

```python
PRODUCTS = {
    "falabella": [
        "https://www.falabella.com/falabella-cl/product/XXX/Notebook-ASUS",
    ],
    "ripley": [
        "https://simple.ripley.cl/notebook-lenovo-ideapad-XXX",
    ],
    "paris": [
        "https://www.paris.cl/notebook-hp-XXX.html",
    ],
}
```

---

## 🚀 Uso

```bash
# Iniciar el tracker (corre cada 30 minutos)
python tracker.py

# Ver reporte del historial de precios
python report.py
```

---

## 🧠 Cómo funciona

1. Cada 30 minutos scrapeamos el precio actual de cada producto.
2. Guardamos el precio en SQLite con timestamp.
3. Comparamos con el **precio máximo histórico** (no solo el "precio tachado" de la tienda).
4. Si la bajada es ≥ 5%, se envía un email de alerta.

> **Tip:** Ejecuta `tracker.py` desde hoy mismo para construir historial de precios antes del CyberDay (1 junio).

---

## 📊 Ejemplo de reporte

```
══════════════════════════════════════════════════════════
  📊  CYBERDAY PRICE TRACKER — REPORTE DE PRECIOS
══════════════════════════════════════════════════════════

🏪 FALABELLA  |  Notebook ASUS VivoBook 15 Core i5
   Precio actual : $   499.990
   Precio máximo : $   579.990  (precio más alto registrado)
   Precio mínimo : $   499.990
   Descuento real:       13.8%  🔥 REAL!
   Registros     : 24 mediciones
```

---

## ⚠️ Notas

- Los selectores CSS pueden cambiar si las tiendas actualizan su sitio. Si deja de funcionar, revisa `tracker.py` y actualiza los selectores.
- Playwright abre un navegador headless, así que el scraping es más robusto que con solo `requests`.
- Usa con moderación — no hagas requests cada 1 minuto para no sobrecargar los servidores.
