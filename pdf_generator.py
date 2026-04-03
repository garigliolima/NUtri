import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import Flowable


# ── Paleta NUUtri ──────────────────────────────────────────────────────────────
ORANGE      = colors.HexColor("#FF6B1A")
ORANGE_DARK = colors.HexColor("#CC4A00")
ORANGE_SOFT = colors.HexColor("#FFF0E8")
GRAY_DARK   = colors.HexColor("#1A1A1A")
GRAY_MID    = colors.HexColor("#555555")
GRAY_LIGHT  = colors.HexColor("#F5F5F5")
WHITE       = colors.white


class HeaderBanner(Flowable):
    """Cabeçalho laranja com logo NUUtri."""
    def __init__(self, width, user_name=""):
        Flowable.__init__(self)
        self.banner_width = width
        self.user_name = user_name
        self.height = 28 * mm

    def draw(self):
        c = self.canv
        w, h = self.banner_width, self.height

        # Fundo laranja
        c.setFillColor(ORANGE)
        c.rect(0, 0, w, h, fill=1, stroke=0)

        # Acento lateral esquerdo mais escuro
        c.setFillColor(ORANGE_DARK)
        c.rect(0, 0, 6, h, fill=1, stroke=0)

        # Logo / marca
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 26)
        c.drawString(14, h - 18 * mm, "NUU")
        c.setFont("Helvetica", 26)
        c.drawString(14 + c.stringWidth("NUU", "Helvetica-Bold", 26), h - 18 * mm, "tri")

        # Tagline
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#FFD4B8"))
        c.drawString(14, h - 23 * mm, "Nutrição inteligente • Resultados reais")

        # Nome do usuário à direita
        if self.user_name:
            c.setFont("Helvetica", 9)
            c.setFillColor(WHITE)
            label = f"Plano para: {self.user_name}"
            x = w - c.stringWidth(label, "Helvetica", 9) - 14
            c.drawString(x, h - 18 * mm, label)

        # Data
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#FFD4B8"))
        date_str = datetime.now().strftime("%d/%m/%Y")
        x = w - c.stringWidth(date_str, "Helvetica", 8) - 14
        c.drawString(x, h - 23 * mm, date_str)


class FooterLine(Flowable):
    """Rodapé discreto com aviso legal."""
    def __init__(self, width):
        Flowable.__init__(self)
        self.banner_width = width
        self.height = 10 * mm

    def draw(self):
        c = self.canv
        w = self.banner_width
        c.setStrokeColor(ORANGE)
        c.setLineWidth(1.5)
        c.line(0, self.height - 1, w, self.height - 1)
        c.setFillColor(GRAY_MID)
        c.setFont("Helvetica", 7)
        msg = "NUUtri • Plano gerado por IA — não substitui acompanhamento nutricional profissional."
        c.drawString(0, 2, msg)
        c.drawRightString(w, 2, "nuutri.app")


def _styles():
    return {
        "title": ParagraphStyle(
            "title", fontName="Helvetica-Bold", fontSize=18,
            textColor=ORANGE_DARK, spaceAfter=2, leading=22
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName="Helvetica", fontSize=11,
            textColor=GRAY_MID, spaceAfter=8
        ),
        "section": ParagraphStyle(
            "section", fontName="Helvetica-Bold", fontSize=12,
            textColor=ORANGE_DARK, spaceBefore=12, spaceAfter=4,
            borderPad=4
        ),
        "body": ParagraphStyle(
            "body", fontName="Helvetica", fontSize=10,
            textColor=GRAY_DARK, leading=15, spaceAfter=4
        ),
        "body_small": ParagraphStyle(
            "body_small", fontName="Helvetica", fontSize=9,
            textColor=GRAY_MID, leading=13, spaceAfter=3
        ),
        "bold": ParagraphStyle(
            "bold", fontName="Helvetica-Bold", fontSize=10,
            textColor=GRAY_DARK, leading=15
        ),
        "meal_title": ParagraphStyle(
            "meal_title", fontName="Helvetica-Bold", fontSize=10,
            textColor=WHITE
        ),
        "tag": ParagraphStyle(
            "tag", fontName="Helvetica-Bold", fontSize=9,
            textColor=ORANGE_DARK
        ),
    }


def _macro_table(calorias, proteinas, carbs, gorduras, page_width):
    """Tabela de macros com cards coloridos."""
    data = [
        [
            Paragraph("<b>🔥 Calorias</b>", ParagraphStyle("mc", fontName="Helvetica-Bold", fontSize=9, textColor=ORANGE_DARK, alignment=TA_CENTER)),
            Paragraph("<b>💪 Proteínas</b>", ParagraphStyle("mc", fontName="Helvetica-Bold", fontSize=9, textColor=ORANGE_DARK, alignment=TA_CENTER)),
            Paragraph("<b>🍞 Carboidratos</b>", ParagraphStyle("mc", fontName="Helvetica-Bold", fontSize=9, textColor=ORANGE_DARK, alignment=TA_CENTER)),
            Paragraph("<b>🥑 Gorduras</b>", ParagraphStyle("mc", fontName="Helvetica-Bold", fontSize=9, textColor=ORANGE_DARK, alignment=TA_CENTER)),
        ],
        [
            Paragraph(f"<b>{calorias}</b> kcal", ParagraphStyle("mv", fontName="Helvetica-Bold", fontSize=16, textColor=GRAY_DARK, alignment=TA_CENTER)),
            Paragraph(f"<b>{proteinas}</b> g", ParagraphStyle("mv", fontName="Helvetica-Bold", fontSize=16, textColor=GRAY_DARK, alignment=TA_CENTER)),
            Paragraph(f"<b>{carbs}</b> g", ParagraphStyle("mv", fontName="Helvetica-Bold", fontSize=16, textColor=GRAY_DARK, alignment=TA_CENTER)),
            Paragraph(f"<b>{gorduras}</b> g", ParagraphStyle("mv", fontName="Helvetica-Bold", fontSize=16, textColor=GRAY_DARK, alignment=TA_CENTER)),
        ],
    ]
    col_w = page_width / 4
    t = Table(data, colWidths=[col_w] * 4, rowHeights=[14 * mm, 16 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ORANGE_SOFT),
        ("BACKGROUND", (0, 1), (-1, 1), WHITE),
        ("BOX",        (0, 0), (-1, -1), 1, ORANGE),
        ("INNERGRID",  (0, 0), (-1, -1), 0.5, colors.HexColor("#FFCCAA")),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _meal_block(meal_name, foods, page_width, styles):
    """Bloco visual de uma refeição."""
    elements = []
    header_data = [[Paragraph(f"  {meal_name}", styles["meal_title"])]]
    header_table = Table(header_data, colWidths=[page_width], rowHeights=[10 * mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ORANGE),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",(0, 0), (-1, -1), 8),
        ("RIGHTPADDING",(0,0), (-1,-1), 8),
    ]))
    elements.append(header_table)

    rows = []
    for food in foods:
        rows.append([
            Paragraph(f"• {food}", ParagraphStyle("fi", fontName="Helvetica", fontSize=9, textColor=GRAY_DARK, leading=13))
        ])

    if rows:
        food_table = Table(rows, colWidths=[page_width])
        food_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GRAY_LIGHT),
            ("BOX",        (0, 0), (-1, -1), 0.5, colors.HexColor("#FFCCAA")),
            ("LEFTPADDING",(0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ]))
        elements.append(food_table)

    elements.append(Spacer(1, 4 * mm))
    return KeepTogether(elements)


def generate_nutrition_pdf(plan_data: dict) -> bytes:
    """
    Gera o PDF do plano nutricional NUUtri.

    plan_data esperado:
    {
        "user_name": "João Silva",
        "objetivo": "Hipertrofia",
        "calorias": "2400",
        "proteinas": "180",
        "carbs": "270",
        "gorduras": "70",
        "refeicoes": [
            {"nome": "☀️ Café da Manhã (07h)", "alimentos": ["Ovos mexidos (3 unidades)", "Pão integral (2 fatias)"]},
            ...
        ],
        "observacoes": "Beber 2-3L de água por dia...",
        "suplementos": "Whey protein pós-treino..."
    }
    """
    buffer = io.BytesIO()
    margin = 15 * mm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=10 * mm, bottomMargin=18 * mm,
    )

    page_width = A4[0] - 2 * margin
    s = _styles()
    story = []

    # ── Cabeçalho ──
    story.append(HeaderBanner(page_width, plan_data.get("user_name", "")))
    story.append(Spacer(1, 6 * mm))

    # ── Título do plano ──
    story.append(Paragraph("Plano Nutricional Personalizado", s["title"]))
    objetivo = plan_data.get("objetivo", "")
    if objetivo:
        story.append(Paragraph(f"Objetivo: {objetivo}", s["subtitle"]))
    story.append(HRFlowable(width=page_width, thickness=1.5, color=ORANGE, spaceAfter=4 * mm))

    # ── Perfil do usuário ──
    perfil_items = []
    for key, label in [("peso", "Peso"), ("altura", "Altura"), ("idade", "Idade"), ("sexo", "Sexo"), ("nivel_atividade", "Nível de atividade")]:
        if plan_data.get(key):
            perfil_items.append(f"<b>{label}:</b> {plan_data[key]}")

    if perfil_items:
        story.append(Paragraph("Perfil", s["section"]))
        cols = 2
        rows_data = []
        for i in range(0, len(perfil_items), cols):
            row = perfil_items[i:i+cols]
            while len(row) < cols:
                row.append("")
            rows_data.append([Paragraph(cell, s["body_small"]) for cell in row])
        t = Table(rows_data, colWidths=[page_width / cols] * cols)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), ORANGE_SOFT),
            ("BOX",        (0, 0), (-1, -1), 0.5, colors.HexColor("#FFCCAA")),
            ("INNERGRID",  (0, 0), (-1, -1), 0.3, colors.HexColor("#FFCCAA")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ("LEFTPADDING",(0,0),(-1,-1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 4 * mm))

    # ── Macros do dia ──
    story.append(Paragraph("Metas Diárias", s["section"]))
    story.append(_macro_table(
        plan_data.get("calorias", "—"),
        plan_data.get("proteinas", "—"),
        plan_data.get("carbs", "—"),
        plan_data.get("gorduras", "—"),
        page_width
    ))
    story.append(Spacer(1, 6 * mm))

    # ── Refeições ──
    refeicoes = plan_data.get("refeicoes", [])
    if refeicoes:
        story.append(Paragraph("Cardápio do Dia", s["section"]))
        story.append(Spacer(1, 2 * mm))
        for refeicao in refeicoes:
            story.append(_meal_block(refeicao["nome"], refeicao["alimentos"], page_width, s))

    # ── Suplementos ──
    if plan_data.get("suplementos"):
        story.append(Paragraph("Suplementação", s["section"]))
        story.append(Paragraph(plan_data["suplementos"], s["body"]))
        story.append(Spacer(1, 3 * mm))

    # ── Observações ──
    if plan_data.get("observacoes"):
        story.append(Paragraph("Observações e Dicas", s["section"]))
        story.append(Paragraph(plan_data["observacoes"], s["body"]))
        story.append(Spacer(1, 3 * mm))

    # ── Rodapé ──
    story.append(Spacer(1, 4 * mm))
    story.append(FooterLine(page_width))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
