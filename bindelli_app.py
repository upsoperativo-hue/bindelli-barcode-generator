import streamlit as st
import fitz  # PyMuPDF
import re
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.graphics import renderPDF
from PyPDF2 import PdfMerger

st.title("Generatore Barcode per Bindelli UPS")

# Upload PDF
uploaded_file = st.file_uploader("Carica il PDF DCR", type="pdf")

if uploaded_file:
    pdf_in_bytes = uploaded_file.read()
    pdf_in = fitz.open(stream=pdf_in_bytes, filetype="pdf")

    trk_re = re.compile(r"1Z[0-9A-Z]{16}")

    BAR_HEIGHT = 28
    BAR_WIDTH = 0.85
    X_SHIFT = 0
    Y_GAP = 6
    HUMAN_READABLE = False
    DEBUG_BOX = False

    tot_placed = 0

    # Output PDF buffer
    output_buffer = BytesIO()

    # Copia del PDF originale
    pdf_out = fitz.open()

    for page in pdf_in:
        W, H = page.rect.width, page.rect.height

        # Trova "Car#:"
        car_hits = page.search_for("Car#:") or []
        car_hits.sort(key=lambda r: (round(r.y0, 2), round(r.x0, 2)))

        # Trova tracking UPS
        text = page.get_text("text") or ""
        trks = trk_re.findall(text)

        # Se mancano dati, copia la pagina e continua
        if not car_hits or not trks:
            pdf_out.insert_pdf(pdf_in, from_page=page.number, to_page=page.number)
            continue

        # Overlay PDF
        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=(W, H))

        N = min(len(trks), len(car_hits))

        for i in range(N):
            tracking = trks[i]
            car_rect = car_hits[i]

            bc = createBarcodeDrawing(
                "Code128",
                value=tracking,
                barHeight=BAR_HEIGHT,
                barWidth=BAR_WIDTH,
                humanReadable=HUMAN_READABLE
            )

            x = float(car_rect.x0) + X_SHIFT
            y_top_mupdf = float(car_rect.y1)
            y = H - y_top_mupdf - Y_GAP - float(bc.height)
            y = max(0, y)

            if DEBUG_BOX:
                c.saveState()
                c.setStrokeColorRGB(1, 0, 0)
                c.rect(x, y, float(bc.width), float(bc.height), stroke=1, fill=0)
                c.restoreState()

            renderPDF.draw(bc, c, x, y)
            tot_placed += 1

        c.save()
        packet.seek(0)
        overlay = fitz.open("pdf", packet.read())

        # Applica overlay
        new_page = pdf_out.new_page(width=W, height=H)
        new_page.show_pdf_page(new_page.rect, pdf_in, page.number)
        new_page.show_pdf_page(new_page.rect, overlay, 0)

    # Salva PDF finale
    pdf_out.save(output_buffer)
    pdf_out.close()

    st.success(f"Barcode inseriti: {tot_placed}")

    st.download_button(
        "Scarica PDF con Barcode",
        data=output_buffer.getvalue(),
        file_name="bindelli_con_barcode.pdf",
        mime="application/pdf"
    )
