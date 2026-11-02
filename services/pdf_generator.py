"""Geração da ficha de venda em PDF com ReportLab.
IMPORTANTE: A ficha NUNCA mostra custo, margem, lucro ou taxas internas.
"""

import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from config import IMAGES_DIR

BLUE = colors.HexColor("#2563eb")
DARK = colors.HexColor("#0f172a")
GREY = colors.HexColor("#64748b")
LIGHT = colors.HexColor("#f1f5f9")


def _brl(v):
    try:
        s = f"{float(v):,.2f}"
        return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "R$ 0,00"


def _draw_logo(c, x, y, w=45 * mm, h=14 * mm):
    c.setFillColor(BLUE)
    c.roundRect(x, y, w, h, 3 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(x + w / 2, y + h / 2 - 5, "WH INFO")


def generate_sale_pdf(sale: dict, settings: dict) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    margin = 18 * mm

    # --- cabeçalho ---
    _draw_logo(c, margin, H - margin - 14 * mm, 55 * mm, 14 * mm)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(W - margin, H - margin - 4 * mm, "COMPROVANTE DE VENDA")
    c.setFont("Helvetica", 9)
    c.setFillColor(GREY)
    c.drawRightString(W - margin, H - margin - 9 * mm, f"Nº {sale['sale_number']}")
    c.drawRightString(W - margin, H - margin - 13 * mm, sale.get("created_at", ""))

    # linha
    c.setStrokeColor(LIGHT)
    c.line(margin, H - margin - 20 * mm, W - margin, H - margin - 20 * mm)

    # --- dados da loja e cliente ---
    y = H - margin - 28 * mm
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, settings.get("store_name", "WH INFO"))
    c.setFont("Helvetica", 9)
    c.setFillColor(GREY)
    y -= 5 * mm
    if settings.get("store_phone"):
        c.drawString(margin, y, f"Tel: {settings['store_phone']}")
        y -= 4 * mm
    if settings.get("store_address"):
        c.drawString(margin, y, settings["store_address"])
        y -= 4 * mm

    if sale.get("client_name"):
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(W - margin, H - margin - 28 * mm, "Cliente")
        c.setFont("Helvetica", 9)
        c.setFillColor(GREY)
        c.drawRightString(W - margin, H - margin - 33 * mm, sale["client_name"])

    # --- itens ---
    y = H - margin - 55 * mm
    c.setFillColor(BLUE)
    c.rect(margin, y, W - 2 * margin, 8 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin + 3 * mm, y + 2.5 * mm, "PRODUTO")
    c.drawCentredString(W / 2 + 10 * mm, y + 2.5 * mm, "QTD")
    c.drawRightString(W - margin - 3 * mm, y + 2.5 * mm, "VALOR")
    y -= 2 * mm

    for it in sale.get("items", []):
        y -= 6 * mm
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin + 3 * mm, y, it.get("product_name", ""))
        c.setFont("Helvetica", 8.5)
        c.setFillColor(GREY)
        info = " ".join(filter(None, [it.get("storage", ""), it.get("color", "")]))
        if info:
            c.drawString(margin + 3 * mm, y - 4 * mm, info)
        c.setFillColor(DARK)
        c.setFont("Helvetica", 10)
        c.drawCentredString(W / 2 + 10 * mm, y, str(it.get("quantity", 1)))
        c.drawRightString(
            W - margin - 3 * mm,
            y,
            _brl(it.get("unit_price", 0) * it.get("quantity", 1)),
        )
        y -= 4 * mm

    # --- imagem do primeiro item (opcional) ---
    if sale.get("items"):
        fn = sale["items"][0].get("image_filename")
        if fn:
            path = os.path.join(IMAGES_DIR, fn)
            if os.path.exists(path):
                try:
                    from PIL import Image as PILImage

                    img = PILImage.open(path)
                    img.thumbnail((60 * mm, 60 * mm))
                    tmp = path + ".tmp.png"
                    img.convert("RGB").save(tmp, "PNG")
                    c.drawImage(
                        tmp,
                        W - margin - 55 * mm,
                        y - 55 * mm,
                        width=50 * mm,
                        height=50 * mm,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
                except Exception:
                    pass

    # --- pagamento ---
    y -= 8 * mm
    c.setStrokeColor(LIGHT)
    c.line(margin, y, W - margin, y)
    y -= 8 * mm
    pm = {"cash": "À vista", "debit": "Débito", "credit": "Crédito"}.get(
        sale.get("payment_method"), sale.get("payment_method", "")
    )
    c.setFillColor(DARK)
    c.setFont("Helvetica", 10)
    c.drawString(margin, y, f"Forma de pagamento: {pm}")
    inst = int(sale.get("installments", 1))
    if inst > 1:
        c.drawString(
            margin, y - 5 * mm, f"Parcelamento: {inst}x de {_brl(sale['total'] / inst)}"
        )
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(BLUE)
    c.drawRightString(W - margin, y, f"TOTAL: {_brl(sale['total'])}")

    # --- rodapé ---
    c.setFont("Helvetica", 8)
    c.setFillColor(GREY)
    c.drawCentredString(
        W / 2,
        25 * mm,
        "Obrigado pela preferência! Guarde este comprovante para eventuais garantias.",
    )
    c.drawCentredString(W / 2, 20 * mm, settings.get("store_name", "WH INFO"))

    c.showPage()
    c.save()
    return buf.getvalue()
