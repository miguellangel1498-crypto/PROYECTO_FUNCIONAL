"""Genera SEGURIDAD.pdf a partir de SEGURIDAD.md con formato limpio
(sin mostrar los simbolos de markdown # * - como texto literal).

Uso:
    python scripts/generar_pdf_seguridad.py
"""
import os
import re

from fpdf import FPDF

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGEN = os.path.join(RAIZ, "SEGURIDAD.md")
DESTINO = os.path.join(RAIZ, "SEGURIDAD.pdf")

ANCHO_UTIL = 190


def limpiar_inline(texto):
    texto = texto.replace("—", "-").replace("¡", "").replace("¿", "")
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)
    texto = re.sub(r"\*(.*?)\*", r"\1", texto)
    texto = re.sub(r"`(.*?)`", r"\1", texto)
    return texto


def parsear_bloques(texto_md):
    """Convierte el markdown en bloques logicos, uniendo lineas que en el
    archivo fuente estan envueltas manualmente en varias lineas pero forman
    un solo parrafo o un solo item de lista."""
    lineas = texto_md.splitlines()
    bloques = []
    buffer = []
    tipo_buffer = None
    en_codigo = False
    codigo_lineas = []
    tabla_lineas = []

    def flush_buffer():
        nonlocal buffer, tipo_buffer
        if buffer:
            bloques.append((tipo_buffer, " ".join(buffer).strip()))
        buffer = []
        tipo_buffer = None

    def flush_tabla():
        nonlocal tabla_lineas
        if tabla_lineas:
            bloques.append(("tabla", list(tabla_lineas)))
        tabla_lineas = []

    for linea in lineas:
        cruda = linea.rstrip()
        despojada = cruda.strip()

        if despojada.startswith("```"):
            if en_codigo:
                bloques.append(("codigo", list(codigo_lineas)))
                codigo_lineas = []
            else:
                flush_buffer()
            en_codigo = not en_codigo
            continue

        if en_codigo:
            codigo_lineas.append(cruda)
            continue

        if despojada.startswith("|"):
            flush_buffer()
            tabla_lineas.append(despojada)
            continue
        else:
            flush_tabla()

        if not despojada:
            flush_buffer()
            continue

        if despojada == "---":
            flush_buffer()
            bloques.append(("hr", None))
            continue

        m_h1 = re.match(r"^#\s+(.*)", despojada)
        m_h2 = re.match(r"^##\s+(.*)", despojada)
        m_bullet = re.match(r"^-\s+(.*)", despojada)

        if m_h1:
            flush_buffer()
            bloques.append(("h1", m_h1.group(1)))
        elif m_h2:
            flush_buffer()
            bloques.append(("h2", m_h2.group(1)))
        elif m_bullet:
            flush_buffer()
            buffer = [m_bullet.group(1)]
            tipo_buffer = "bullet"
        else:
            if tipo_buffer not in ("para", "bullet"):
                flush_buffer()
                tipo_buffer = "para"
            buffer.append(despojada)

    flush_buffer()
    flush_tabla()
    return bloques


class PDFSeguridad(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")


def renderizar_tabla(pdf, filas_crudas):
    filas = [f for f in filas_crudas if not re.match(r"^\|?[\s:|-]+\|?$", f)]
    datos = [[limpiar_inline(c.strip()) for c in f.strip("|").split("|")] for f in filas]
    if not datos:
        return
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    with pdf.table(col_widths=(1, 2.6), text_align=("LEFT", "LEFT")) as tabla:
        for fila_datos in datos:
            fila_tabla = tabla.row()
            for celda in fila_datos:
                fila_tabla.cell(celda)
    pdf.ln(2)


def render():
    with open(ORIGEN, encoding="utf-8") as f:
        bloques = parsear_bloques(f.read())

    pdf = PDFSeguridad(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(20, 18, 20)
    pdf.add_page()

    for tipo, contenido in bloques:
        if tipo == "h1":
            pdf.set_font("Helvetica", "B", 20)
            pdf.set_text_color(20, 20, 20)
            pdf.multi_cell(ANCHO_UTIL, 10, limpiar_inline(contenido))
            pdf.ln(4)
        elif tipo == "h2":
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(15, 90, 75)
            pdf.multi_cell(ANCHO_UTIL, 8, limpiar_inline(contenido))
            pdf.set_text_color(30, 30, 30)
            pdf.ln(2)
        elif tipo == "para":
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(ANCHO_UTIL, 6.5, limpiar_inline(contenido))
            pdf.ln(2)
        elif tipo == "bullet":
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(30, 30, 30)
            pdf.set_x(pdf.l_margin + 4)
            pdf.multi_cell(ANCHO_UTIL - 4, 6.5, f"·  {limpiar_inline(contenido)}")
        elif tipo == "hr":
            pdf.ln(1)
            pdf.set_draw_color(200, 200, 200)
            y = pdf.get_y()
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(4)
        elif tipo == "codigo":
            pdf.set_font("Courier", "", 10)
            pdf.set_fill_color(240, 240, 240)
            pdf.set_text_color(30, 30, 30)
            texto_codigo = "\n".join(limpiar_inline(l) for l in contenido) or " "
            pdf.multi_cell(ANCHO_UTIL, 6, texto_codigo, fill=True)
            pdf.ln(2)
        elif tipo == "tabla":
            renderizar_tabla(pdf, contenido)

    pdf.output(DESTINO)
    print(f"PDF generado en: {DESTINO}")


if __name__ == "__main__":
    render()
