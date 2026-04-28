import io
import os
import math
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether, HRFlowable, PageBreak,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Fontes ────────────────────────────────────────────────────────────────────
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

_has_custom = _reg("Bricolage",      "BricolageGrotesque-Regular.ttf")
_reg("Bricolage-Bold", "BricolageGrotesque-Bold.ttf")
_reg("Outfit",         "Outfit-Regular.ttf")
_reg("Outfit-Bold",    "Outfit-Bold.ttf")
_reg("Instrument",     "InstrumentSans-Regular.ttf")
_reg("Instrument-Bold","InstrumentSans-Bold.ttf")

if _has_custom:
    TITLE_FONT  = "Bricolage-Bold"
    BODY_FONT   = "Outfit"
    BODY_BOLD   = "Outfit-Bold"
    LABEL_FONT  = "Instrument"
    LABEL_BOLD  = "Instrument-Bold"
else:
    TITLE_FONT  = "Helvetica-Bold"
    BODY_FONT   = "Helvetica"
    BODY_BOLD   = "Helvetica-Bold"
    LABEL_FONT  = "Helvetica"
    LABEL_BOLD  = "Helvetica-Bold"

# ── Paleta ────────────────────────────────────────────────────────────────────
ORANGE       = colors.HexColor("#FF6B1A")
ORANGE_DARK  = colors.HexColor("#C94E00")
ORANGE_MID   = colors.HexColor("#FF8C42")
ORANGE_PALE  = colors.HexColor("#FFF0E8")
ORANGE_FAINT = colors.HexColor("#FFF8F4")
CHARCOAL     = colors.HexColor("#1C1C1C")
WARM_GRAY    = colors.HexColor("#6B6560")
RULE_GRAY    = colors.HexColor("#E8E0D8")
WHITE        = colors.white

# Cores para o donut chart de macros
MACRO_COLORS = {
    "proteinas": colors.HexColor("#FF6B1A"),  # laranja
    "carbs":     colors.HexColor("#FFB347"),  # laranja claro
    "gorduras":  colors.HexColor("#1C1C1C"),  # carvão
}

PAGE_W, PAGE_H = A4
MARGIN    = 14 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


# ── Arte do cabeçalho (melhorada) ─────────────────────────────────────────────
def _draw_cover_art(c, x, y, w, h):
    c.saveState()
    clip = c.beginPath()
    clip.rect(x, y, w, h)
    c.clipPath(clip, stroke=0, fill=0)

    # Gradiente simulado com retângulos
    c.setFillColor(CHARCOAL)
    c.rect(x, y, w, h, fill=1, stroke=0)

    # Arco principal grosso
    c.setStrokeColor(ORANGE_DARK)
    c.setLineWidth(28)
    c.setLineCap(1)
    path = c.beginPath()
    path.moveTo(x, y)
    path.curveTo(x + w*0.15, y + h*0.9, x + w*0.55, y + h*1.1, x + w, y + h*0.55)
    c.drawPath(path, stroke=1, fill=0)

    # Arco secundário
    c.setStrokeColor(ORANGE)
    c.setLineWidth(12)
    path2 = c.beginPath()
    path2.moveTo(x, y + h*0.18)
    path2.curveTo(x + w*0.2, y + h*1.0, x + w*0.65, y + h*1.05, x + w, y + h*0.75)
    c.drawPath(path2, stroke=1, fill=0)

    # Arco terciário fino
    c.setStrokeColor(ORANGE_MID)
    c.setLineWidth(4)
    path3 = c.beginPath()
    path3.moveTo(x + w*0.05, y)
    path3.curveTo(x + w*0.3, y + h*0.7, x + w*0.7, y + h*0.95, x + w, y + h*0.88)
    c.drawPath(path3, stroke=1, fill=0)

    # Pontos decorativos
    dots = [(0.08,0.72),(0.18,0.55),(0.28,0.80),(0.42,0.62),(0.55,0.78),
            (0.65,0.50),(0.78,0.70),(0.88,0.58),(0.72,0.88),(0.35,0.42),
            (0.50,0.35),(0.15,0.35)]
    for dx, dy in dots:
        c.setFillColor(ORANGE_MID)
        c.circle(x + dx*w, y + dy*h, 1.8, fill=1, stroke=0)

    for dx, dy, r in [(0.22,0.68,4),(0.60,0.65,5.5),(0.82,0.76,3.5)]:
        c.setFillColor(ORANGE)
        c.circle(x + dx*w, y + dy*h, r, fill=1, stroke=0)

    # Linha de base
    c.setStrokeColor(ORANGE)
    c.setLineWidth(1.5)
    c.line(x, y + 2, x + w, y + 2)

    c.restoreState()


# ══════════════════════════════════════════════════════════════════════════════
#  FLOWABLES
# ══════════════════════════════════════════════════════════════════════════════

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

        # Logo NUUtri
        c.setFillColor(WHITE)
        c.setFont(TITLE_FONT, 32)
        c.drawString(14, h - 20*mm, "NUU")
        nuu_w = c.stringWidth("NUU", TITLE_FONT, 32)
        c.setFillColor(colors.HexColor("#FFCBAA"))
        c.setFont(BODY_FONT, 32)
        c.drawString(14 + nuu_w, h - 20*mm, "tri")

        # Tagline
        c.setFillColor(colors.HexColor("#FFCBAA"))
        c.setFont(LABEL_FONT, 7.5)
        c.drawString(14, h - 25*mm, "NUTRIÇÃO INTELIGENTE  ·  RESULTADOS REAIS")

        # Nome do usuário
        if self.user_name:
            c.setFillColor(WHITE)
            c.setFont(BODY_BOLD, 10)
            label = self.user_name.upper()
            x = w - c.stringWidth(label, BODY_BOLD, 10) - 14
            c.drawString(x, h - 18*mm, label)

        # Data
        c.setFillColor(colors.HexColor("#FFCBAA"))
        c.setFont(LABEL_FONT, 7.5)
        date_str = datetime.now().strftime("%d . %m . %Y")
        x = w - c.stringWidth(date_str, LABEL_FONT, 7.5) - 14
        c.drawString(x, h - 23.5*mm, date_str)

        # Objetivo
        if self.objetivo:
            obj = self.objetivo[:42] + ("..." if len(self.objetivo) > 42 else "")
            x = w - c.stringWidth(obj, LABEL_FONT, 7.5) - 14
            c.drawString(x, h - 28*mm, obj)


class MacroCard(Flowable):
    """Cards de macros com barra de progresso proporcional."""
    def __init__(self, width, cals, prot, carbs, fats):
        Flowable.__init__(self)
        self.bw = width
        self.values = [
            ("CALORIAS", cals, "kcal", None),
            ("PROTEÍNAS", prot, "g", MACRO_COLORS["proteinas"]),
            ("CARBS", carbs, "g", MACRO_COLORS["carbs"]),
            ("GORDURAS", fats, "g", MACRO_COLORS["gorduras"]),
        ]
        self.height = 26 * mm

    def draw(self):
        c = self.canv
        n = len(self.values)
        gap = 3 * mm
        card_w = (self.bw - gap * (n - 1)) / n
        h = self.height

        # Calcula total de calorias por macro para barras de progresso
        try:
            prot_cal = float(str(self.values[1][1]).replace(",", ".")) * 4
            carb_cal = float(str(self.values[2][1]).replace(",", ".")) * 4
            fat_cal  = float(str(self.values[3][1]).replace(",", ".")) * 9
            total_cal = prot_cal + carb_cal + fat_cal
            ratios = [0, prot_cal/total_cal if total_cal else 0,
                      carb_cal/total_cal if total_cal else 0,
                      fat_cal/total_cal if total_cal else 0]
        except (ValueError, ZeroDivisionError):
            ratios = [0, 0.33, 0.33, 0.33]

        for i, (label, val, unit, accent_color) in enumerate(self.values):
            cx = i * (card_w + gap)
            is_first = i == 0
            bg = CHARCOAL if is_first else ORANGE_PALE

            # Card background
            c.setFillColor(bg)
            c.roundRect(cx, 0, card_w, h, 3*mm, fill=1, stroke=0)

            # Acento superior
            accent_c = ORANGE_MID if is_first else (accent_color or ORANGE)
            c.setFillColor(accent_c)
            c.roundRect(cx, h - 2.5*mm, card_w, 2.5*mm, 2*mm, fill=1, stroke=0)
            c.rect(cx, h - 2.5*mm, card_w, 1.5*mm, fill=1, stroke=0)

            # Label
            text_color = colors.HexColor("#FFCBAA") if is_first else WARM_GRAY
            c.setFillColor(text_color)
            c.setFont(LABEL_FONT, 6.5)
            c.drawCentredString(cx + card_w/2, h - 8*mm, label)

            # Valor
            val_color = WHITE if is_first else CHARCOAL
            c.setFillColor(val_color)
            c.setFont(TITLE_FONT, 18)
            c.drawCentredString(cx + card_w/2, h - 16.5*mm, str(val))

            # Unidade
            c.setFillColor(text_color)
            c.setFont(LABEL_FONT, 7)
            c.drawCentredString(cx + card_w/2, h - 20.5*mm, unit)

            # Barra de progresso (só nos cards de macro, não no de calorias)
            if i > 0 and ratios[i] > 0:
                bar_y = 2.5 * mm
                bar_w = card_w - 8*mm
                bar_h = 2 * mm
                bar_x = cx + 4*mm

                # Fundo da barra
                bg_bar = colors.HexColor("#E8E0D8") if not is_first else colors.HexColor("#333333")
                c.setFillColor(bg_bar)
                c.roundRect(bar_x, bar_y, bar_w, bar_h, 1*mm, fill=1, stroke=0)

                # Preenchimento da barra
                fill_w = bar_w * ratios[i]
                if fill_w > 0:
                    c.setFillColor(accent_color or ORANGE)
                    c.roundRect(bar_x, bar_y, max(fill_w, 2*mm), bar_h, 1*mm, fill=1, stroke=0)

                # Percentual
                pct = f"{int(ratios[i]*100)}%"
                c.setFillColor(text_color)
                c.setFont(LABEL_FONT, 6.5)
                c.drawCentredString(cx + card_w/2, bar_y - 2.5*mm, pct)


class DonutChart(Flowable):
    """Gráfico de rosca mostrando distribuição calórica dos macros."""
    def __init__(self, width, prot, carbs, fats):
        Flowable.__init__(self)
        self.bw = width
        try:
            self.prot_cal = float(str(prot).replace(",", ".")) * 4
            self.carb_cal = float(str(carbs).replace(",", ".")) * 4
            self.fat_cal  = float(str(fats).replace(",", ".")) * 9
        except ValueError:
            self.prot_cal = self.carb_cal = self.fat_cal = 1
        self.height = 52 * mm

    def _draw_arc(self, c, cx, cy, r, start_deg, end_deg, color, width=12):
        """Desenha um arco colorido com segmentos finos para suavidade."""
        c.setStrokeColor(color)
        c.setLineWidth(width)
        c.setLineCap(1)

        steps = max(int(abs(end_deg - start_deg)), 1)
        for i in range(steps):
            a1 = math.radians(start_deg + (end_deg - start_deg) * i / steps)
            a2 = math.radians(start_deg + (end_deg - start_deg) * (i + 1) / steps)
            x1 = cx + r * math.cos(a1)
            y1 = cy + r * math.sin(a1)
            x2 = cx + r * math.cos(a2)
            y2 = cy + r * math.sin(a2)
            c.line(x1, y1, x2, y2)

    def draw(self):
        c = self.canv
        total = self.prot_cal + self.carb_cal + self.fat_cal
        if total == 0:
            return

        chart_size = 38 * mm
        cx_chart = chart_size / 2 + 4*mm
        cy_chart = self.height / 2
        radius = 15 * mm
        ring_w = 10

        segments = [
            (self.prot_cal / total, MACRO_COLORS["proteinas"], "Proteínas"),
            (self.carb_cal / total, MACRO_COLORS["carbs"], "Carboidratos"),
            (self.fat_cal  / total, MACRO_COLORS["gorduras"], "Gorduras"),
        ]

        # Desenha o donut
        start = 90
        for ratio, color, _ in segments:
            sweep = ratio * 360
            if sweep > 0:
                self._draw_arc(c, cx_chart, cy_chart, radius, start, start + sweep, color, ring_w)
                start += sweep

        # Centro do donut — total de calorias
        c.setFillColor(WHITE)
        c.circle(cx_chart, cy_chart, radius - 8, fill=1, stroke=0)
        c.setFillColor(CHARCOAL)
        c.setFont(TITLE_FONT, 13)
        total_kcal = str(int(total))
        c.drawCentredString(cx_chart, cy_chart + 1*mm, total_kcal)
        c.setFillColor(WARM_GRAY)
        c.setFont(LABEL_FONT, 6)
        c.drawCentredString(cx_chart, cy_chart - 4*mm, "kcal totais")

        # Legenda ao lado do donut
        legend_x = cx_chart + radius + 18*mm
        legend_y = cy_chart + 14*mm
        legend_data = [
            (MACRO_COLORS["proteinas"], "Proteínas", self.prot_cal, f"{int(self.prot_cal/total*100)}%"),
            (MACRO_COLORS["carbs"],     "Carboidratos", self.carb_cal, f"{int(self.carb_cal/total*100)}%"),
            (MACRO_COLORS["gorduras"],  "Gorduras", self.fat_cal, f"{int(self.fat_cal/total*100)}%"),
        ]

        for i, (color, name, cals, pct) in enumerate(legend_data):
            ly = legend_y - i * 12*mm

            # Bolinha colorida
            c.setFillColor(color)
            c.circle(legend_x, ly + 1.5, 3, fill=1, stroke=0)

            # Nome
            c.setFillColor(CHARCOAL)
            c.setFont(BODY_BOLD, 8.5)
            c.drawString(legend_x + 8, ly, name)

            # Valor e percentual
            c.setFillColor(WARM_GRAY)
            c.setFont(LABEL_FONT, 7)
            c.drawString(legend_x + 8, ly - 4.5*mm, f"{int(cals)} kcal  ·  {pct}")


class MealBlock(Flowable):
    """Bloco de refeicao com acento lateral e visual refinado."""
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

        # Background
        c.setFillColor(ORANGE_FAINT)
        c.roundRect(0, 0, w, h, 2.5*mm, fill=1, stroke=0)

        # Acento lateral laranja
        c.setFillColor(ORANGE)
        c.roundRect(0, 0, accent, h, 2.5*mm, fill=1, stroke=0)
        c.rect(accent - 2, 0, 2, h, fill=1, stroke=0)

        # Nome da refeicao
        c.setFillColor(CHARCOAL)
        c.setFont(BODY_BOLD, 9.5)
        c.drawString(accent + 6, h - 7.5*mm, self.meal_name)

        # Linha separadora
        c.setStrokeColor(RULE_GRAY)
        c.setLineWidth(0.5)
        c.line(accent + 6, h - 9.2*mm, w - 6, h - 9.2*mm)

        # Alimentos
        for i, food in enumerate(self.foods):
            fy = h - 9.2*mm - (i + 1) * 6.5*mm + 1.5*mm

            # Bullet decorativo
            c.setFillColor(ORANGE_MID)
            c.circle(accent + 10, fy + 2.2, 1.2, fill=1, stroke=0)

            # Texto do alimento — trunca usando largura real da fonte
            c.setFillColor(WARM_GRAY)
            c.setFont(BODY_FONT, 8.5)
            max_w = w - accent - 22
            text = food
            if c.stringWidth(text, BODY_FONT, 8.5) > max_w:
                while text and c.stringWidth(text + "...", BODY_FONT, 8.5) > max_w:
                    text = text[:-1]
                text = text.rstrip() + "..."
            c.drawString(accent + 16, fy, text)


class HydrationBlock(Flowable):
    """Bloco visual para recomendacao de hidratacao."""
    def __init__(self, width, liters="2.5"):
        Flowable.__init__(self)
        self.bw = width
        self.liters = liters
        self.height = 18 * mm

    def draw(self):
        c = self.canv
        w, h = self.bw, self.height

        # Background na paleta NUUtri
        c.setFillColor(ORANGE_FAINT)
        c.roundRect(0, 0, w, h, 3*mm, fill=1, stroke=0)

        # Acento lateral laranja
        c.setFillColor(ORANGE_MID)
        c.roundRect(0, 0, 3.5*mm, h, 2.5*mm, fill=1, stroke=0)
        c.rect(1.5*mm, 0, 2*mm, h, fill=1, stroke=0)

        # Icone de agua — circulo com "~" para agua
        drop_x = 14*mm
        drop_y = h / 2
        c.setFillColor(ORANGE)
        c.circle(drop_x, drop_y, 4*mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(BODY_BOLD, 8)
        c.drawCentredString(drop_x, drop_y - 1.2*mm, "H2O")

        # Texto principal
        c.setFillColor(CHARCOAL)
        c.setFont(BODY_BOLD, 10)
        c.drawString(24*mm, h - 6.5*mm, f"Hidratação: {self.liters}L por dia")

        c.setFillColor(WARM_GRAY)
        c.setFont(BODY_FONT, 8)
        c.drawString(24*mm, h - 11.5*mm, "Distribua ao longo do dia. Aumente em dias de treino.")

        # 8 gotinhas representando copos
        glass_x = w - 40*mm
        for i in range(8):
            gx = glass_x + i * 4.5*mm
            gy = h / 2 - 1.5*mm
            c.setFillColor(ORANGE_MID)
            c.circle(gx, gy, 1.5*mm, fill=1, stroke=0)


class SectionDivider(Flowable):
    """Divisor de secao com linha e icone."""
    def __init__(self, width):
        Flowable.__init__(self)
        self.bw = width
        self.height = 3 * mm

    def draw(self):
        c = self.canv
        w = self.bw
        y = self.height / 2

        # Linha com gradiente simulado
        c.setStrokeColor(RULE_GRAY)
        c.setLineWidth(0.5)
        c.line(0, y, w, y)

        # Losango central decorativo
        cx = w / 2
        c.setFillColor(ORANGE)
        size = 1.5*mm
        path = c.beginPath()
        path.moveTo(cx, y + size)
        path.lineTo(cx + size, y)
        path.lineTo(cx, y - size)
        path.lineTo(cx - size, y)
        path.close()
        c.drawPath(path, fill=1, stroke=0)


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
        c.drawString(0, 2.5, "NUUtri . Plano gerado por inteligencia artificial . Nao substitui acompanhamento nutricional profissional")
        c.setFillColor(ORANGE_DARK)
        c.setFont(LABEL_BOLD, 6.5)
        c.drawRightString(self.bw, 2.5, "nuutri.app")


class DayHeader(Flowable):
    """Faixa de cabecalho de cada dia da semana."""
    def __init__(self, width, day_name: str, day_number: int):
        Flowable.__init__(self)
        self.bw = width
        self.day_name = day_name
        self.day_number = day_number
        self.height = 12 * mm

    def draw(self):
        c = self.canv
        w, h = self.bw, self.height

        c.setFillColor(CHARCOAL)
        c.roundRect(0, 0, w, h, 2*mm, fill=1, stroke=0)

        c.setFillColor(ORANGE)
        c.setFont(TITLE_FONT, 22)
        num = str(self.day_number).zfill(2)
        c.drawString(10, h - 8.5*mm, num)
        num_w = c.stringWidth(num, TITLE_FONT, 22)

        c.setFillColor(WHITE)
        c.setFont(BODY_BOLD, 11)
        c.drawString(10 + num_w + 6, h - 7.5*mm, self.day_name.upper())

        c.setStrokeColor(ORANGE)
        c.setLineWidth(1)
        c.line(w - 30, h/2, w - 10, h/2)


# ══════════════════════════════════════════════════════════════════════════════
#  ESTILOS
# ══════════════════════════════════════════════════════════════════════════════

def _s():
    return {
        "plan_title": ParagraphStyle("pt", fontName=TITLE_FONT, fontSize=20,
                                     textColor=CHARCOAL, spaceAfter=1, leading=24),
        "plan_sub":   ParagraphStyle("ps", fontName=BODY_FONT, fontSize=10,
                                     textColor=WARM_GRAY, spaceAfter=6),
        "section":    ParagraphStyle("sec", fontName=LABEL_BOLD, fontSize=10,
                                     textColor=ORANGE_DARK, spaceBefore=10, spaceAfter=4,
                                     leading=13),
        "body":       ParagraphStyle("body", fontName=BODY_FONT, fontSize=9.5,
                                     textColor=CHARCOAL, leading=15, spaceAfter=3),
        "body_sm":    ParagraphStyle("bsm", fontName=BODY_FONT, fontSize=8.5,
                                     textColor=WARM_GRAY, leading=13, spaceAfter=2),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  TABELA SEMANAL
# ══════════════════════════════════════════════════════════════════════════════

def _weekly_overview_table(dias: list, page_width: float) -> Table:
    DAYS_SHORT = ["SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"]
    PROT_KEYWORDS = ["frango","atum","carne","salmao","tilapia","peixe","camarao",
                     "whey","proteina","patinho","alcatra","file","costela"]
    SKIP_KEYWORDS = ["cafe","lanche","manha"]

    header   = []
    proteins = []

    for i, dia in enumerate(dias):
        label = dia.get("dia", DAYS_SHORT[i] if i < 7 else f"DIA {i+1}")
        short = label[:3].upper()
        header.append(Paragraph(
            f'<font name="{LABEL_BOLD}" size="7" color="#FFCBAA">{short}</font>',
            ParagraphStyle("oh", alignment=1, leading=10)
        ))

        prot_label = "---"
        for ref in dia.get("refeicoes", []):
            nome_ref = ref.get("nome", "").lower()
            if any(sk in nome_ref for sk in SKIP_KEYWORDS):
                continue
            for food in ref.get("alimentos", []):
                fl = food.lower()
                for kw in PROT_KEYWORDS:
                    if kw in fl:
                        prot_label = food.split("(")[0].strip()
                        prot_label = prot_label.capitalize()[:20]
                        break
                if prot_label != "---":
                    break
            if prot_label != "---":
                break

        proteins.append(Paragraph(
            f'<font name="{BODY_FONT}" size="7.5" color="#1C1C1C">{prot_label}</font>',
            ParagraphStyle("op", alignment=1, leading=11)
        ))

    col_w = page_width / len(dias)
    t = Table([header, proteins], colWidths=[col_w] * len(dias))
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), CHARCOAL),
        ("BACKGROUND",    (0, 1), (-1, 1), ORANGE_FAINT),
        ("BOX",           (0, 0), (-1, -1), 0.5, RULE_GRAY),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, RULE_GRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE NUMBERING CALLBACK
# ══════════════════════════════════════════════════════════════════════════════

def _add_page_number(canvas, doc):
    """Adiciona numero de pagina no rodape de cada pagina."""
    page_num = canvas.getPageNumber()
    text = f"{page_num}"
    canvas.saveState()
    canvas.setFont(LABEL_FONT, 7)
    canvas.setFillColor(WARM_GRAY)
    canvas.drawCentredString(PAGE_W / 2, 8 * mm, text)
    canvas.restoreState()


# ══════════════════════════════════════════════════════════════════════════════
#  GERADORES DE PDF
# ══════════════════════════════════════════════════════════════════════════════

def generate_nutrition_pdf(plan_data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=10*mm, bottomMargin=16*mm,
    )

    s = _s()
    story = []

    # ── CAPA / BANNER ─────────────────────────────────────────────────────────
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

    # ── PERFIL ────────────────────────────────────────────────────────────────
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
            ("BACKGROUND",    (0,0),(-1,-1), ORANGE_PALE),
            ("BOX",           (0,0),(-1,-1), 0.5, RULE_GRAY),
            ("INNERGRID",     (0,0),(-1,-1), 0.3, RULE_GRAY),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 5*mm))

    # ── METAS DIARIAS ─────────────────────────────────────────────────────────
    story.append(Paragraph("METAS DIÁRIAS", s["section"]))
    story.append(MacroCard(
        CONTENT_W,
        plan_data.get("calorias","---"),
        plan_data.get("proteinas","---"),
        plan_data.get("carbs","---"),
        plan_data.get("gorduras","---"),
    ))
    story.append(Spacer(1, 4*mm))

    # ── GRAFICO DE DISTRIBUICAO ───────────────────────────────────────────────
    try:
        prot_val = plan_data.get("proteinas", "0")
        carb_val = plan_data.get("carbs", "0")
        fat_val  = plan_data.get("gorduras", "0")
        if all(v and str(v) not in ("---", "0") for v in [prot_val, carb_val, fat_val]):
            story.append(Paragraph("DISTRIBUIÇÃO CALÓRICA", s["section"]))
            story.append(DonutChart(CONTENT_W, prot_val, carb_val, fat_val))
            story.append(Spacer(1, 2*mm))
    except Exception:
        pass

    story.append(SectionDivider(CONTENT_W))
    story.append(Spacer(1, 3*mm))

    # ── HIDRATACAO ────────────────────────────────────────────────────────────
    # Estima hidratacao baseado no peso
    try:
        peso_str = str(plan_data.get("peso", "70")).replace("kg", "").replace(",", ".").strip()
        peso_num = float(peso_str)
        liters = round(peso_num * 0.035, 1)
    except (ValueError, TypeError):
        liters = 2.5
    story.append(HydrationBlock(CONTENT_W, str(liters)))
    story.append(Spacer(1, 4*mm))

    story.append(SectionDivider(CONTENT_W))
    story.append(Spacer(1, 3*mm))

    # ── REFEICOES ─────────────────────────────────────────────────────────────
    refeicoes = plan_data.get("refeicoes", [])
    if refeicoes:
        first_mb = MealBlock(CONTENT_W, refeicoes[0]["nome"], refeicoes[0]["alimentos"])
        story.append(KeepTogether([
            Paragraph("CARDÁPIO DO DIA", s["section"]),
            Spacer(1, 2*mm),
            first_mb,
            Spacer(1, 3*mm),
        ]))
        for ref in refeicoes[1:]:
            mb = MealBlock(CONTENT_W, ref["nome"], ref["alimentos"])
            story.append(KeepTogether([mb, Spacer(1, 3*mm)]))

    # ── SUPLEMENTACAO ─────────────────────────────────────────────────────────
    if plan_data.get("suplementos"):
        story.append(SectionDivider(CONTENT_W))
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph("SUPLEMENTAÇÃO", s["section"]))
        story.append(Paragraph(plan_data["suplementos"], s["body"]))
        story.append(Spacer(1, 3*mm))

    # ── OBSERVACOES ───────────────────────────────────────────────────────────
    if plan_data.get("observacoes"):
        story.append(Paragraph("OBSERVAÇÕES E DICAS", s["section"]))
        story.append(Paragraph(plan_data["observacoes"], s["body"]))
        story.append(Spacer(1, 3*mm))

    # ── RODAPE ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4*mm))
    story.append(FooterRule(CONTENT_W))

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    buffer.seek(0)
    return buffer.read()


def generate_weekly_nutrition_pdf(plan_data: dict) -> bytes:
    """Gera PDF semanal NUUtri — capa + 7 paginas, uma por dia."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=10*mm, bottomMargin=16*mm,
    )

    s = _s()
    story = []
    dias = plan_data.get("dias", [])

    # ── PAGINA 1: Capa ────────────────────────────────────────────────────────
    story.append(CoverBanner(
        CONTENT_W,
        user_name=plan_data.get("user_name", ""),
        objetivo=plan_data.get("objetivo", ""),
    ))
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("Plano Nutricional Semanal", s["plan_title"]))
    if plan_data.get("objetivo"):
        story.append(Paragraph(plan_data["objetivo"], s["plan_sub"]))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.75, color=RULE_GRAY, spaceAfter=4*mm))

    # Perfil
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
            row = [
                Paragraph(
                    f'<font name="{LABEL_BOLD}" size="7" color="#C94E00">{lbl.upper()}</font><br/>'
                    f'<font name="{BODY_FONT}" size="9">{val}</font>',
                    ParagraphStyle("pc", leading=14)
                )
                for lbl, val in chunk
            ]
            rows.append(row)
        cw = CONTENT_W / cols
        t = Table(rows, colWidths=[cw]*cols)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), ORANGE_PALE),
            ("BOX",           (0,0),(-1,-1), 0.5, RULE_GRAY),
            ("INNERGRID",     (0,0),(-1,-1), 0.3, RULE_GRAY),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 5*mm))

    # Macros diarios
    story.append(Paragraph("METAS DIÁRIAS", s["section"]))
    story.append(MacroCard(
        CONTENT_W,
        plan_data.get("calorias","---"),
        plan_data.get("proteinas","---"),
        plan_data.get("carbs","---"),
        plan_data.get("gorduras","---"),
    ))
    story.append(Spacer(1, 4*mm))

    # Grafico donut na capa semanal
    try:
        prot_val = plan_data.get("proteinas", "0")
        carb_val = plan_data.get("carbs", "0")
        fat_val  = plan_data.get("gorduras", "0")
        if all(v and str(v) not in ("---", "0") for v in [prot_val, carb_val, fat_val]):
            story.append(Paragraph("DISTRIBUIÇÃO CALÓRICA", s["section"]))
            story.append(DonutChart(CONTENT_W, prot_val, carb_val, fat_val))
            story.append(Spacer(1, 2*mm))
    except Exception:
        pass

    # Hidratacao
    try:
        peso_str = str(plan_data.get("peso", "70")).replace("kg", "").replace(",", ".").strip()
        peso_num = float(peso_str)
        liters = round(peso_num * 0.035, 1)
    except (ValueError, TypeError):
        liters = 2.5
    story.append(HydrationBlock(CONTENT_W, str(liters)))
    story.append(Spacer(1, 4*mm))

    # Suplementos e observacoes na capa
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

    # ── PAGINAS 2-8: Um dia por pagina ───────────────────────────────────────
    for i, dia in enumerate(dias):
        story.append(PageBreak())

        day_name = dia.get("dia", f"Dia {i+1}")
        story.append(DayHeader(CONTENT_W, day_name, i + 1))
        story.append(Spacer(1, 5*mm))

        refeicoes = dia.get("refeicoes", [])
        for ref in refeicoes:
            mb = MealBlock(CONTENT_W, ref["nome"], ref["alimentos"])
            story.append(KeepTogether([mb, Spacer(1, 3*mm)]))

        story.append(Spacer(1, 4*mm))
        story.append(FooterRule(CONTENT_W))

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    buffer.seek(0)
    return buffer.read()
