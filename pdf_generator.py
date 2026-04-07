import io
import os
import math
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_HERE = os.path.dirname(os.path.abspath(__file__))

def _reg(name, fname):
    path = os.path.join(_HERE, fname)
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont(name, path))
            return True
        except Exception:
            pass
    return False

_reg("Bricolage",      "BricolageGrotesque-Regular.ttf")
_reg("Bricolage-Bold", "BricolageGrotesque-Bold.ttf")
_reg("Outfit",         "Outfit-Regular.ttf")
_reg("Outfit-Bold",    "Outfit-Bold.ttf")
_reg("Instrument",     "InstrumentSans-Regular.ttf")
_reg("Instrument-Bold","InstrumentSans-Bold.ttf")

TITLE_FONT  = "Bricolage-Bold"
BODY_FONT   = "Outfit"
BODY_BOLD   = "Outfit-Bold"
LABEL_FONT  = "Instrument"
LABEL_BOLD  = "Instrument-Bold"

ORANGE       = colors.HexColor("#FF6B1A")
ORANGE_DARK  = colors.HexColor("#C94E00")
ORANGE_MID   = colors.HexColor("#FF8C42")
ORANGE_PALE  = colors.HexColor("#FFF0E8")
ORANGE_FAINT = colors.HexColor("#FFF8F4")
CHARCOAL     = colors.HexColor("#1C1C1C")
WARM_GRAY    = colors.HexColor("#6B6560")
RULE_GRAY    = colors.HexColor("#E8E0D8")
WHITE        = colors.white

PAGE_W, PAGE_H = A4
MARGIN    = 14 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


def _draw_cover_art(c, x, y, w, h):
    c.saveState()
    clip = c.beginPath()
    clip.rect(x, y, w, h)
    c.clipPath(clip, stroke=0, fill=0)

    c.setFillColor(CHARCOAL)
    c.rect(x, y, w, h, fill=1, stroke=0)

    c.setStrokeColor(ORANGE_DARK)
    c.setLineWidth(28)
    c.setLineCap(1)
    path = c.beginPath()
    path.moveTo(x, y)
    path.curveTo(x + w*0.15, y + h*0.9, x + w*0.55, y + h*1.1, x + w, y + h*0.55)
    c.drawPath(path, stroke=1, fill=0)

    c.setStrokeColor(ORANGE)
    c.setLineWidth(12)
    path2 = c.beginPath()
    path2.moveTo(x, y + h*0.18)
    path2.curveTo(x + w*0.2, y + h*1.0, x + w*0.65, y + h*1.05, x + w, y + h*0.75)
    c.drawPath(path2, stroke=1, fill=0)

    c.setStrokeColor(ORANGE_MID)
    c.setLineWidth(4)
    path3 = c.beginPath()
    path3.moveTo(x + w*0.05, y)
    path3.curveTo(x + w*0.3, y + h*0.7, x + w*0.7, y + h*0.95, x + w, y + h*0.88)
    c.drawPath(path3, stroke=1, fill=0)

    dots = [(0.08,0.72),(0.18,0.55),(0.28,0.80),(0.42,0.62),(0.55,0.78),
            (0.65,0.50),(0.78,0.70),(0.88,0.58),(0.72,0.88),(0.35,0.42),
            (0.50,0.35),(0.15,0.35)]
    for dx, dy in dots:
        c.setFillColor(ORANGE_MID)
        c.circle(x + dx*w, y + dy*h, 1.8, fill=1, stroke=0)

    for dx, dy, r in [(0.22,0.68,4),(0.60,0.65,5.5),(0.82,0.76,3.5)]:
        c.setFillColor(ORANGE)
        c.circle(x + dx*w, y + dy*h, r, fill=1, stroke=0)

    c.setStrokeColor(ORANGE)
    c.setLineWidth(1.5)
    c.line(x, y + 2, x + w, y + 2)

    c.restoreState()


class CoverBanner(Flowable):
    def __init__(self, width, user_name="", objetivo=""):
        Flowable.__init__(self)
        self.bw = width
        self.user_name = user_name
        self.objetivo = objetivo
        self.height = 46 * mm

    def draw(self):
        c = self.canv
        w, h = self.bw, self.height
        _draw_cover_art(c, 0, 0, w, h)

        c.setFillColor(WHITE)
        c.setFont(TITLE_FONT, 32)
        c.drawString(14, h - 20*mm, "NUU")
        nuu_w = c.stringWidth("NUU", TITLE_FONT, 32)
        c.setFillColor(ORANGE)
        c.setFont(BODY_FONT, 32)
        c.drawString(14 + nuu_w, h - 20*mm, "tri")

        c.setFillColor(colors.HexColor("#FFCBAA"))
        c.setFont(LABEL_FONT, 7.5)
        c.drawString(14, h - 25*mm, "NUTRIÇÃO INTELIGENTE  ·  RESULTADOS REAIS")

        if self.user_name:
            c.setFillColor(WHITE)
            c.setFont(BODY_BOLD, 10)
            label = self.user_name.upper()
            x = w - c.stringWidth(label, BODY_BOLD, 10) - 14
            c.drawString(x, h - 18*mm, label)

        c.setFillColor(colors.HexColor("#FFCBAA"))
        c.setFont(LABEL_FONT, 7.5)
        date_str = datetime.now().strftime("%d · %m · %Y")
        x = w - c.stringWidth(date_str, LABEL_FONT, 7.5) - 14
        c.drawString(x, h - 23.5*mm, date_str)

        if self.objetivo:
            obj = self.objetivo[:42] + ("…" if len(self.objetivo) > 42 else "")
            x = w - c.stringWidth(obj, LABEL_FONT, 7.5) - 14
            c.drawString(x, h - 28*mm, obj)


class MacroCard(Flowable):
    def __init__(self, width, cals, prot, carbs, fats):
        Flowable.__init__(self)
        self.bw = width
        self.values = [
            ("CALORIAS", cals, "kcal"),
            ("PROTEÍNAS", prot, "g"),
            ("CARBS", carbs, "g"),
            ("GORDURAS", fats, "g"),
        ]
        self.height = 24 * mm

    def draw(self):
        c = self.canv
        n = len(self.values)
        gap = 3 * mm
        card_w = (self.bw - gap * (n - 1)) / n
        h = self.height

        for i, (label, val, unit) in enumerate(self.values):
            cx = i * (card_w + gap)
            is_first = i == 0
            bg = CHARCOAL if is_first else ORANGE_PALE

            c.setFillColor(bg)
            c.roundRect(cx, 0, card_w, h, 3*mm, fill=1, stroke=0)

            accent_c = ORANGE_MID if is_first else ORANGE
            c.setFillColor(accent_c)
            c.roundRect(cx, h - 2.5*mm, card_w, 2.5*mm, 2*mm, fill=1, stroke=0)
            c.rect(cx, h - 2.5*mm, card_w, 1.5*mm, fill=1, stroke=0)

            text_color = colors.HexColor("#FFCBAA") if is_first else WARM_GRAY
            c.setFillColor(text_color)
            c.setFont(LABEL_FONT, 6.5)
            c.drawCentredString(cx + card_w/2, h - 8*mm, label)

            val_color = WHITE if is_first else CHARCOAL
            c.setFillColor(val_color)
            c.setFont(TITLE_FONT, 18)
            c.drawCentredString(cx + card_w/2, h - 16.5*mm, str(val))

            c.setFillColor(text_color)
            c.setFont(LABEL_FONT, 7)
            c.drawCentredString(cx + card_w/2, h - 20.5*mm, unit)


class MealBlock(Flowable):
    def __init__(self, width, meal_name, foods):
        Flowable.__init__(self)
        self.bw = width
        self.meal_name = meal_name
        self.foods = foods
        self.height = 10*mm + len(foods) * 6.5*mm + 4*mm

    def draw(self):
        c = self.canv
        w, h = self.bw, self.height
        accent = 3.5 * mm

        c.setFillColor(ORANGE_FAINT)
        c.roundRect(0, 0, w, h, 2.5*mm, fill=1, stroke=0)

        c.setFillColor(ORANGE)
        c.roundRect(0, 0, accent, h, 2.5*mm, fill=1, stroke=0)
        c.rect(accent - 2, 0, 2, h, fill=1, stroke=0)

        c.setFillColor(CHARCOAL)
        c.setFont(BODY_BOLD, 9.5)
        c.drawString(accent + 6, h - 7.5*mm, self.meal_name)

        c.setStrokeColor(RULE_GRAY)
        c.setLineWidth(0.5)
        c.line(accent + 6, h - 9.2*mm, w - 6, h - 9.2*mm)

        for i, food in enumerate(self.foods):
            fy = h - 9.2*mm - (i + 1) * 6.5*mm + 1.5*mm
            c.setFillColor(ORANGE_MID)
            c.circle(accent + 10, fy + 2.2, 1.2, fill=1, stroke=0)
            c.setFillColor(WARM_GRAY)
            c.setFont(BODY_FONT, 8.5)
            max_chars = int((w - accent - 22) / 4.2)
            text = food if len(food) <= max_chars else food[:max_chars] + "…"
            c.drawString(accent + 16, fy, text)


class FooterRule(Flowable):
    def __init__(self, width):
        Flowable.__init__(self)
        self.bw = width
        self.height = 9 * mm

    def draw(self):
        c = self.canv
        c.setStrokeColor(ORANGE)
        c.setLineWidth(1)
        c.line(0, self.height - 0.5, self.bw, self.height - 0.5)
        c.setFillColor(WARM_GRAY)
        c.setFont(LABEL_FONT, 6.5)
        c.drawString(0, 2.5, "NUUtri · Plano gerado por inteligência artificial · Não substitui acompanhamento nutricional profissional")
        c.setFillColor(ORANGE_DARK)
        c.setFont(LABEL_BOLD, 6.5)
        c.drawRightString(self.bw, 2.5, "nuutri.app")


def _s():
    return {
        "plan_title": ParagraphStyle("pt", fontName=TITLE_FONT, fontSize=20,
                                     textColor=CHARCOAL, spaceAfter=1, leading=24),
        "plan_sub":   ParagraphStyle("ps", fontName=BODY_FONT, fontSize=10,
                                     textColor=WARM_GRAY, spaceAfter=6),
        "section":    ParagraphStyle("sec", fontName=LABEL_BOLD, fontSize=8,
                                     textColor=ORANGE_DARK, spaceBefore=10, spaceAfter=4,
                                     leading=10),
        "body":       ParagraphStyle("body", fontName=BODY_FONT, fontSize=9.5,
                                     textColor=CHARCOAL, leading=15, spaceAfter=3),
        "body_sm":    ParagraphStyle("bsm", fontName=BODY_FONT, fontSize=8.5,
                                     textColor=WARM_GRAY, leading=13, spaceAfter=2),
    }


def generate_nutrition_pdf(plan_data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=10*mm, bottomMargin=16*mm,
    )

    s = _s()
    story = []

    story.append(CoverBanner(
        CONTENT_W,
        user_name=plan_data.get("user_name", ""),
        objetivo=plan_data.get("objetivo", ""),
    ))
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("Plano Nutricional Personalizado", s["plan_title"]))
    if plan_data.get("objetivo"):
        story.append(Paragraph(plan_data["objetivo"], s["plan_sub"]))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.75, color=RULE_GRAY, spaceAfter=4*mm))

    perfil = []
    for k, lbl in [("peso","Peso"),("altura","Altura"),("idade","Idade"),
                   ("sexo","Sexo"),("nivel_atividade","Atividade")]:
        if plan_data.get(k):
            perfil.append((lbl, plan_data[k]))

    if perfil:
        story.append(Paragraph("PERFIL", s["section"]))
        cols = 3
        rows = []
        for i in range(0, len(perfil), cols):
            chunk = perfil[i:i+cols]
            while len(chunk) < cols:
                chunk.append(("", ""))
            row = []
            for lbl, val in chunk:
                cell = Paragraph(
                    f'<font name="{LABEL_BOLD}" size="7" color="#C94E00">{lbl.upper()}</font><br/>'
                    f'<font name="{BODY_FONT}" size="9">{val}</font>',
                    ParagraphStyle("pc", leading=14)
                )
                row.append(cell)
            rows.append(row)
        cw = CONTENT_W / cols
        t = Table(rows, colWidths=[cw]*cols)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), ORANGE_FAINT),
            ("BOX",           (0,0),(-1,-1), 0.5, RULE_GRAY),
            ("INNERGRID",     (0,0),(-1,-1), 0.3, RULE_GRAY),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 5*mm))

    story.append(Paragraph("METAS DIÁRIAS", s["section"]))
    story.append(MacroCard(
        CONTENT_W,
        plan_data.get("calorias","—"),
        plan_data.get("proteinas","—"),
        plan_data.get("carbs","—"),
        plan_data.get("gorduras","—"),
    ))
    story.append(Spacer(1, 6*mm))

    refeicoes = plan_data.get("refeicoes", [])
    if refeicoes:
        story.append(Paragraph("CARDÁPIO DO DIA", s["section"]))
        story.append(Spacer(1, 2*mm))
        for ref in refeicoes:
            mb = MealBlock(CONTENT_W, ref["nome"], ref["alimentos"])
            story.append(KeepTogether([mb, Spacer(1, 3*mm)]))

    if plan_data.get("suplementos"):
        story.append(Paragraph("SUPLEMENTAÇÃO", s["section"]))
        story.append(Paragraph(plan_data["suplementos"], s["body"]))
        story.append(Spacer(1, 3*mm))

    if plan_data.get("observacoes"):
        story.append(Paragraph("OBSERVAÇÕES E DICAS", s["section"]))
        story.append(Paragraph(plan_data["observacoes"], s["body"]))
        story.append(Spacer(1, 3*mm))

    story.append(Spacer(1, 4*mm))
    story.append(FooterRule(CONTENT_W))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
