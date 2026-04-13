"""
taco_db.py — Base de dados nutricional brasileira (TACO + TBCA)

Contém ~350 alimentos organizados por categoria com dados de:
- Energia (kcal), Proteínas (g), Carboidratos (g), Gorduras (g), Fibra (g)

Fontes:
- TACO (Tabela Brasileira de Composição de Alimentos) — Unicamp/NEPA
- TBCA (Tabela Brasileira de Composição de Alimentos) — USP/FCF

Valores por 100g de parte comestível.
Os dados são armazenados em SQLite para consulta rápida pelo bot.
"""

import sqlite3
import os
import json
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

TACO_DB_PATH = os.environ.get("TACO_DB_PATH", os.path.join(os.path.dirname(__file__), "taco.db"))


@contextmanager
def _conn():
    con = sqlite3.connect(TACO_DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ══════════════════════════════════════════════════════════════════════════════
#  DADOS TACO — por 100g de parte comestível
#  Formato: (nome, categoria, kcal, proteina_g, carb_g, gordura_g, fibra_g)
# ══════════════════════════════════════════════════════════════════════════════

_ALIMENTOS = [
    # ── CEREAIS E DERIVADOS ──────────────────────────────────────────────────
    ("Arroz integral cozido", "Cereais", 124, 2.6, 25.8, 1.0, 2.7),
    ("Arroz branco cozido", "Cereais", 128, 2.5, 28.1, 0.2, 1.6),
    ("Arroz parboilizado cozido", "Cereais", 123, 2.5, 26.1, 0.3, 1.1),
    ("Aveia em flocos", "Cereais", 394, 13.9, 66.6, 8.5, 9.1),
    ("Aveia em flocos finos", "Cereais", 388, 14.2, 63.5, 8.1, 9.8),
    ("Cevada em grão", "Cereais", 354, 12.5, 73.5, 2.3, 17.3),
    ("Farinha de mandioca torrada", "Cereais", 365, 1.2, 89.2, 0.3, 6.4),
    ("Farinha de milho", "Cereais", 351, 7.2, 79.1, 1.5, 5.5),
    ("Farinha de trigo integral", "Cereais", 340, 11.4, 72.8, 1.4, 11.8),
    ("Farinha de trigo refinada", "Cereais", 360, 9.8, 75.1, 1.4, 2.3),
    ("Granola", "Cereais", 421, 10.4, 64.5, 14.8, 7.2),
    ("Macarrão integral cozido", "Cereais", 124, 5.0, 23.5, 0.9, 2.9),
    ("Macarrão cozido", "Cereais", 102, 3.4, 19.9, 0.5, 1.4),
    ("Milho verde cozido", "Cereais", 138, 5.1, 28.6, 1.2, 3.9),
    ("Pão francês", "Cereais", 300, 8.0, 58.6, 3.1, 2.3),
    ("Pão integral", "Cereais", 253, 9.4, 49.9, 3.4, 6.9),
    ("Pão de forma integral", "Cereais", 244, 10.3, 41.0, 4.5, 6.0),
    ("Pão de forma branco", "Cereais", 271, 8.4, 50.7, 3.7, 2.5),
    ("Quinoa cozida", "Cereais", 120, 4.4, 21.3, 1.9, 2.8),
    ("Tapioca (goma hidratada)", "Cereais", 343, 0.5, 84.7, 0.1, 0.5),
    ("Cuscuz de milho cozido", "Cereais", 113, 2.6, 23.2, 0.5, 1.5),
    ("Pipoca sem óleo", "Cereais", 375, 11.8, 74.5, 4.2, 14.5),

    # ── LEGUMINOSAS ──────────────────────────────────────────────────────────
    ("Feijão carioca cozido", "Leguminosas", 76, 4.8, 13.6, 0.5, 8.5),
    ("Feijão preto cozido", "Leguminosas", 77, 4.5, 14.0, 0.5, 8.4),
    ("Feijão branco cozido", "Leguminosas", 99, 6.6, 17.6, 0.5, 6.3),
    ("Grão-de-bico cozido", "Leguminosas", 164, 8.9, 27.4, 2.6, 7.6),
    ("Lentilha cozida", "Leguminosas", 93, 6.3, 16.3, 0.5, 7.9),
    ("Ervilha cozida", "Leguminosas", 63, 4.9, 9.6, 0.3, 4.3),
    ("Soja cozida", "Leguminosas", 151, 14.0, 8.5, 7.0, 5.6),
    ("Amendoim torrado", "Leguminosas", 589, 27.2, 20.3, 46.0, 8.0),

    # ── VERDURAS, LEGUMES E HORTALIÇAS ───────────────────────────────────────
    ("Abóbora cozida", "Verduras e Legumes", 28, 0.9, 6.7, 0.1, 2.2),
    ("Abobrinha cozida", "Verduras e Legumes", 15, 0.7, 3.4, 0.1, 1.6),
    ("Alface americana", "Verduras e Legumes", 8, 0.6, 1.7, 0.1, 1.0),
    ("Alface crespa", "Verduras e Legumes", 11, 1.3, 1.7, 0.2, 2.0),
    ("Batata doce cozida", "Verduras e Legumes", 77, 0.6, 18.4, 0.1, 2.2),
    ("Batata inglesa cozida", "Verduras e Legumes", 52, 1.2, 11.9, 0.0, 1.3),
    ("Beterraba cozida", "Verduras e Legumes", 32, 1.2, 7.2, 0.1, 1.9),
    ("Brócolis cozido", "Verduras e Legumes", 25, 2.1, 4.4, 0.3, 3.4),
    ("Cenoura cozida", "Verduras e Legumes", 30, 0.8, 7.0, 0.2, 2.6),
    ("Couve-flor cozida", "Verduras e Legumes", 19, 1.2, 3.9, 0.2, 2.1),
    ("Couve manteiga refogada", "Verduras e Legumes", 90, 2.9, 8.0, 5.4, 5.7),
    ("Espinafre cozido", "Verduras e Legumes", 16, 1.8, 2.5, 0.2, 2.1),
    ("Inhame cozido", "Verduras e Legumes", 97, 2.0, 22.4, 0.1, 1.7),
    ("Mandioca cozida", "Verduras e Legumes", 125, 0.6, 30.1, 0.3, 1.6),
    ("Pepino", "Verduras e Legumes", 10, 0.7, 2.0, 0.1, 1.1),
    ("Pimentão verde", "Verduras e Legumes", 21, 0.8, 4.9, 0.1, 2.6),
    ("Pimentão vermelho", "Verduras e Legumes", 27, 1.0, 5.5, 0.3, 1.4),
    ("Quiabo cozido", "Verduras e Legumes", 22, 1.4, 4.4, 0.2, 3.0),
    ("Repolho cru", "Verduras e Legumes", 17, 0.9, 3.9, 0.1, 2.0),
    ("Rúcula", "Verduras e Legumes", 13, 1.5, 2.2, 0.2, 1.6),
    ("Tomate", "Verduras e Legumes", 15, 1.1, 3.1, 0.2, 1.2),
    ("Vagem cozida", "Verduras e Legumes", 25, 1.5, 5.3, 0.1, 3.2),
    ("Chuchu cozido", "Verduras e Legumes", 17, 0.4, 3.8, 0.1, 1.5),
    ("Berinjela cozida", "Verduras e Legumes", 19, 0.7, 4.5, 0.1, 2.5),
    ("Palmito em conserva", "Verduras e Legumes", 23, 2.0, 3.4, 0.5, 2.4),
    ("Cebola refogada", "Verduras e Legumes", 58, 0.9, 8.0, 2.6, 1.3),
    ("Alho cru", "Verduras e Legumes", 113, 7.0, 23.9, 0.2, 4.3),
    ("Cogumelo champignon", "Verduras e Legumes", 16, 1.8, 2.1, 0.2, 1.4),

    # ── FRUTAS ───────────────────────────────────────────────────────────────
    ("Abacate", "Frutas", 96, 1.2, 6.0, 8.4, 6.3),
    ("Abacaxi", "Frutas", 48, 0.9, 12.3, 0.1, 1.0),
    ("Açaí polpa congelada", "Frutas", 58, 0.8, 6.2, 3.9, 2.6),
    ("Banana prata", "Frutas", 98, 1.3, 26.0, 0.1, 2.0),
    ("Banana nanica", "Frutas", 92, 1.4, 23.8, 0.1, 1.9),
    ("Goiaba vermelha", "Frutas", 54, 1.1, 13.0, 0.4, 6.2),
    ("Kiwi", "Frutas", 51, 0.9, 11.5, 0.6, 2.7),
    ("Laranja", "Frutas", 37, 1.0, 8.9, 0.1, 1.8),
    ("Limão tahiti", "Frutas", 32, 0.9, 11.1, 0.1, 1.2),
    ("Mamão papaya", "Frutas", 40, 0.5, 10.4, 0.1, 1.8),
    ("Manga tommy", "Frutas", 51, 0.4, 12.8, 0.2, 1.6),
    ("Maçã fuji", "Frutas", 56, 0.3, 15.2, 0.1, 1.3),
    ("Melancia", "Frutas", 33, 0.9, 8.1, 0.0, 0.1),
    ("Melão", "Frutas", 29, 0.7, 7.5, 0.0, 0.3),
    ("Morango", "Frutas", 30, 0.9, 6.8, 0.3, 1.7),
    ("Pêra", "Frutas", 53, 0.6, 14.0, 0.1, 3.0),
    ("Uva itália", "Frutas", 53, 0.7, 13.6, 0.2, 0.9),
    ("Uva rubi", "Frutas", 49, 0.6, 12.7, 0.2, 0.7),
    ("Maracujá (suco natural)", "Frutas", 23, 0.4, 5.5, 0.1, 0.1),
    ("Coco ralado fresco", "Frutas", 321, 3.7, 10.4, 32.0, 5.4),
    ("Água de coco", "Frutas", 22, 0.0, 5.3, 0.0, 0.0),
    ("Ameixa vermelha", "Frutas", 36, 0.8, 8.8, 0.1, 2.4),
    ("Tangerina", "Frutas", 38, 0.8, 9.6, 0.1, 1.7),

    # ── CARNES E PEIXES ──────────────────────────────────────────────────────
    ("Frango peito sem pele grelhado", "Carnes", 159, 32.0, 0.0, 3.2, 0.0),
    ("Frango coxa sem pele cozida", "Carnes", 183, 27.2, 0.0, 7.9, 0.0),
    ("Frango sobrecoxa sem pele cozida", "Carnes", 196, 25.0, 0.0, 10.5, 0.0),
    ("Carne bovina patinho grelhado", "Carnes", 219, 32.4, 0.0, 9.5, 0.0),
    ("Carne bovina alcatra grelhada", "Carnes", 212, 32.0, 0.0, 8.8, 0.0),
    ("Carne bovina filé mignon grelhado", "Carnes", 222, 32.8, 0.0, 9.7, 0.0),
    ("Carne bovina acém cozido", "Carnes", 215, 26.7, 0.0, 11.7, 0.0),
    ("Carne bovina coxão mole cozido", "Carnes", 212, 32.5, 0.0, 8.5, 0.0),
    ("Carne bovina coxão duro cozido", "Carnes", 208, 33.0, 0.0, 8.0, 0.0),
    ("Carne bovina lagarto cozido", "Carnes", 206, 33.2, 0.0, 7.6, 0.0),
    ("Carne bovina músculo cozido", "Carnes", 194, 32.4, 0.0, 6.7, 0.0),
    ("Carne bovina maminha grelhada", "Carnes", 153, 26.4, 0.0, 5.1, 0.0),
    ("Carne moída refogada", "Carnes", 212, 26.5, 0.0, 11.5, 0.0),
    ("Carne suína lombo assado", "Carnes", 210, 33.3, 0.0, 8.1, 0.0),
    ("Carne suína pernil assado", "Carnes", 262, 27.6, 0.0, 16.6, 0.0),
    ("Carne suína bisteca grelhada", "Carnes", 220, 28.0, 0.0, 11.5, 0.0),
    ("Costela bovina cozida", "Carnes", 373, 23.8, 0.0, 30.5, 0.0),
    ("Fígado bovino grelhado", "Carnes", 225, 29.1, 5.6, 9.0, 0.0),
    ("Tilápia grelhada", "Carnes", 120, 25.0, 0.0, 2.0, 0.0),
    ("Salmão grelhado", "Carnes", 243, 26.1, 0.0, 15.0, 0.0),
    ("Atum em conserva (light)", "Carnes", 116, 25.8, 0.0, 0.8, 0.0),
    ("Sardinha em conserva", "Carnes", 165, 21.0, 0.0, 8.8, 0.0),
    ("Camarão cozido", "Carnes", 90, 18.4, 0.0, 1.3, 0.0),
    ("Peixe pescada branca grelhada", "Carnes", 116, 23.5, 0.0, 2.2, 0.0),
    ("Bacalhau cozido", "Carnes", 136, 29.0, 0.0, 1.8, 0.0),
    ("Carne seca (charque) cozida", "Carnes", 228, 32.0, 0.0, 10.8, 0.0),
    ("Peru peito assado", "Carnes", 156, 29.8, 0.0, 3.5, 0.0),

    # ── OVOS E LATICÍNIOS ────────────────────────────────────────────────────
    ("Ovo de galinha inteiro cozido", "Ovos e Laticínios", 146, 13.3, 0.6, 9.5, 0.0),
    ("Ovo de galinha clara cozida", "Ovos e Laticínios", 44, 9.7, 1.2, 0.0, 0.0),
    ("Ovo de galinha gema cozida", "Ovos e Laticínios", 352, 15.9, 2.7, 30.9, 0.0),
    ("Leite integral", "Ovos e Laticínios", 58, 3.0, 4.5, 3.0, 0.0),
    ("Leite desnatado", "Ovos e Laticínios", 35, 3.4, 5.0, 0.1, 0.0),
    ("Iogurte natural integral", "Ovos e Laticínios", 51, 4.1, 3.8, 2.1, 0.0),
    ("Iogurte natural desnatado", "Ovos e Laticínios", 42, 4.2, 5.6, 0.2, 0.0),
    ("Iogurte grego natural", "Ovos e Laticínios", 90, 5.0, 6.0, 5.0, 0.0),
    ("Iogurte grego light", "Ovos e Laticínios", 58, 6.5, 5.0, 0.8, 0.0),
    ("Queijo minas frescal", "Ovos e Laticínios", 264, 17.4, 3.2, 20.2, 0.0),
    ("Queijo mussarela", "Ovos e Laticínios", 330, 22.6, 3.0, 25.2, 0.0),
    ("Queijo cottage", "Ovos e Laticínios", 98, 11.5, 3.4, 4.3, 0.0),
    ("Queijo prato", "Ovos e Laticínios", 356, 22.7, 1.9, 29.1, 0.0),
    ("Queijo parmesão", "Ovos e Laticínios", 453, 35.6, 1.7, 33.5, 0.0),
    ("Ricota", "Ovos e Laticínios", 140, 12.6, 3.0, 8.1, 0.0),
    ("Requeijão cremoso", "Ovos e Laticínios", 257, 7.5, 2.8, 24.5, 0.0),
    ("Requeijão light", "Ovos e Laticínios", 167, 9.5, 5.5, 12.0, 0.0),
    ("Cream cheese", "Ovos e Laticínios", 342, 5.6, 3.2, 34.0, 0.0),
    ("Manteiga com sal", "Ovos e Laticínios", 726, 0.4, 0.0, 82.0, 0.0),
    ("Whey protein concentrado (pó)", "Ovos e Laticínios", 370, 75.0, 8.0, 4.0, 0.0),

    # ── ÓLEOS, GORDURAS E SEMENTES ───────────────────────────────────────────
    ("Azeite de oliva extra virgem", "Óleos e Gorduras", 884, 0.0, 0.0, 100.0, 0.0),
    ("Óleo de coco", "Óleos e Gorduras", 862, 0.0, 0.0, 100.0, 0.0),
    ("Óleo de soja", "Óleos e Gorduras", 884, 0.0, 0.0, 100.0, 0.0),
    ("Pasta de amendoim", "Óleos e Gorduras", 593, 28.0, 15.8, 47.5, 5.4),
    ("Castanha-do-pará", "Óleos e Gorduras", 643, 14.5, 15.1, 63.5, 7.9),
    ("Castanha de caju torrada", "Óleos e Gorduras", 570, 18.5, 29.1, 46.3, 3.7),
    ("Amêndoa torrada", "Óleos e Gorduras", 581, 21.1, 29.5, 47.3, 11.6),
    ("Nozes", "Óleos e Gorduras", 620, 14.0, 18.4, 59.4, 7.2),
    ("Semente de chia", "Óleos e Gorduras", 486, 16.5, 42.1, 30.7, 34.4),
    ("Semente de linhaça", "Óleos e Gorduras", 495, 14.1, 43.3, 32.3, 33.5),
    ("Semente de girassol", "Óleos e Gorduras", 570, 20.8, 20.0, 49.8, 8.6),
    ("Abacate (óleo)", "Óleos e Gorduras", 884, 0.0, 0.0, 100.0, 0.0),

    # ── AÇÚCARES E DOCES ─────────────────────────────────────────────────────
    ("Açúcar refinado", "Açúcares", 387, 0.0, 99.5, 0.0, 0.0),
    ("Açúcar mascavo", "Açúcares", 369, 0.7, 94.5, 0.0, 0.0),
    ("Mel", "Açúcares", 309, 0.3, 84.0, 0.0, 0.0),
    ("Chocolate amargo 70%", "Açúcares", 530, 7.8, 46.3, 34.1, 10.9),
    ("Chocolate ao leite", "Açúcares", 545, 6.4, 57.5, 30.5, 3.4),
    ("Geleia de frutas", "Açúcares", 262, 0.3, 65.5, 0.1, 0.5),
    ("Rapadura", "Açúcares", 368, 1.0, 90.8, 0.4, 0.0),
    ("Dextrose (pó)", "Açúcares", 370, 0.0, 92.0, 0.0, 0.0),

    # ── BEBIDAS ──────────────────────────────────────────────────────────────
    ("Café (infusão)", "Bebidas", 3, 0.3, 0.5, 0.0, 0.0),
    ("Chá verde (infusão)", "Bebidas", 0, 0.0, 0.0, 0.0, 0.0),
    ("Suco de laranja natural", "Bebidas", 45, 0.6, 10.4, 0.1, 0.4),
    ("Suco de uva integral", "Bebidas", 57, 0.1, 14.2, 0.0, 0.2),
    ("Leite de amêndoas", "Bebidas", 15, 0.5, 1.4, 1.1, 0.5),
    ("Leite de aveia", "Bebidas", 42, 0.5, 7.0, 1.5, 0.8),
    ("Refrigerante cola", "Bebidas", 37, 0.0, 9.4, 0.0, 0.0),

    # ── TUBÉRCULOS E RAÍZES ──────────────────────────────────────────────────
    ("Batata baroa cozida", "Tubérculos", 64, 0.9, 14.7, 0.2, 2.1),
    ("Cará cozido", "Tubérculos", 77, 1.4, 18.2, 0.1, 2.0),

    # ── INDUSTRIALIZADOS COMUNS ──────────────────────────────────────────────
    ("Peito de peru defumado", "Industrializados", 103, 16.2, 2.5, 3.1, 0.0),
    ("Presunto magro", "Industrializados", 93, 14.5, 2.0, 3.0, 0.0),
    ("Atum enlatado em água", "Industrializados", 102, 23.6, 0.0, 0.8, 0.0),
    ("Tofu firme", "Industrializados", 144, 15.7, 2.3, 8.7, 1.2),
    ("Proteína de soja texturizada (PTS)", "Industrializados", 290, 46.0, 31.0, 0.7, 14.0),
    ("Leite em pó integral", "Industrializados", 497, 26.3, 38.2, 26.7, 0.0),
    ("Leite em pó desnatado", "Industrializados", 362, 36.2, 51.6, 0.8, 0.0),
    ("Albumina em pó", "Industrializados", 345, 82.4, 2.0, 0.3, 0.0),
    ("Caseína em pó", "Industrializados", 360, 80.0, 4.0, 2.0, 0.0),
    ("Creatina monohidratada", "Industrializados", 0, 0.0, 0.0, 0.0, 0.0),
    ("Maltodextrina (pó)", "Industrializados", 380, 0.0, 95.0, 0.0, 0.0),

    # ── TEMPEROS E CONDIMENTOS ───────────────────────────────────────────────
    ("Molho de tomate", "Temperos", 28, 1.0, 5.1, 0.5, 1.3),
    ("Molho shoyu (soja)", "Temperos", 43, 4.0, 5.0, 0.0, 0.0),
    ("Vinagre", "Temperos", 4, 0.0, 0.6, 0.0, 0.0),
    ("Mostarda", "Temperos", 60, 3.7, 5.8, 3.3, 4.0),
    ("Catchup", "Temperos", 100, 1.3, 24.2, 0.2, 0.3),
]


# ══════════════════════════════════════════════════════════════════════════════
#  DADOS TBCA (USP) — complementares à TACO
#  Alimentos que NÃO estão na lista TACO acima.
#  Formato: (nome, categoria, kcal, proteina_g, carb_g, gordura_g, fibra_g)
# ══════════════════════════════════════════════════════════════════════════════

_ALIMENTOS_TBCA = [
    # ── CEREAIS E DERIVADOS (complementares) ─────────────────────────────────
    ("Arroz negro cozido", "Cereais", 117, 3.0, 23.5, 1.1, 2.3),
    ("Arroz arbóreo cozido", "Cereais", 130, 2.4, 28.7, 0.3, 0.4),
    ("Pão de queijo", "Cereais", 363, 5.2, 34.2, 22.4, 0.5),
    ("Pão sírio integral", "Cereais", 255, 9.8, 49.0, 2.4, 5.7),
    ("Pão australiano", "Cereais", 268, 8.5, 48.0, 4.5, 3.2),
    ("Wrap/tortilha de trigo", "Cereais", 312, 8.4, 52.0, 7.8, 2.1),
    ("Farinha de aveia", "Cereais", 388, 13.0, 66.0, 7.5, 10.3),
    ("Farinha de arroz", "Cereais", 366, 6.0, 80.1, 1.4, 2.4),
    ("Farinha de amêndoa", "Cereais", 590, 21.0, 20.0, 50.0, 10.0),
    ("Farinha de coco", "Cereais", 320, 19.3, 26.0, 8.4, 39.0),
    ("Polenta cozida", "Cereais", 58, 1.5, 12.4, 0.3, 1.0),
    ("Cuscuz marroquino cozido", "Cereais", 112, 3.8, 23.2, 0.2, 1.4),
    ("Trigo para kibe cozido", "Cereais", 83, 3.1, 18.6, 0.2, 4.5),
    ("Biscoito cream cracker", "Cereais", 432, 9.6, 68.7, 14.0, 2.5),
    ("Biscoito de arroz", "Cereais", 387, 7.2, 85.0, 2.4, 3.5),
    ("Panqueca (massa pronta)", "Cereais", 227, 6.4, 28.5, 10.0, 0.8),
    ("Macarrão de arroz cozido", "Cereais", 109, 0.9, 25.0, 0.2, 0.9),

    # ── LEGUMINOSAS (complementares) ─────────────────────────────────────────
    ("Feijão fradinho cozido", "Leguminosas", 70, 4.7, 12.0, 0.5, 4.8),
    ("Feijão verde cozido", "Leguminosas", 68, 4.3, 12.5, 0.3, 5.0),
    ("Feijão azuki cozido", "Leguminosas", 128, 7.5, 24.8, 0.1, 7.3),
    ("Edamame cozido", "Leguminosas", 122, 11.9, 8.9, 5.2, 5.2),
    ("Tremoço cozido", "Leguminosas", 119, 15.6, 9.9, 2.9, 2.8),
    ("Fava cozida", "Leguminosas", 71, 5.6, 11.5, 0.3, 5.4),

    # ── VERDURAS, LEGUMES E HORTALIÇAS (complementares) ──────────────────────
    ("Aspargo cozido", "Verduras e Legumes", 22, 2.4, 4.1, 0.2, 2.0),
    ("Acelga cozida", "Verduras e Legumes", 18, 1.6, 3.3, 0.1, 1.6),
    ("Agrião", "Verduras e Legumes", 17, 2.7, 1.3, 0.2, 1.5),
    ("Alcachofra cozida", "Verduras e Legumes", 47, 3.3, 10.5, 0.2, 5.4),
    ("Aipim frito", "Verduras e Legumes", 282, 1.9, 38.8, 14.0, 2.0),
    ("Batata doce roxa cozida", "Verduras e Legumes", 80, 0.7, 19.2, 0.1, 2.5),
    ("Batata inglesa assada", "Verduras e Legumes", 93, 2.5, 21.2, 0.1, 2.2),
    ("Berinjela grelhada", "Verduras e Legumes", 35, 0.8, 5.0, 1.5, 2.8),
    ("Brócolis americano cru", "Verduras e Legumes", 34, 2.8, 6.6, 0.4, 2.6),
    ("Cenoura crua", "Verduras e Legumes", 34, 1.3, 7.7, 0.2, 3.2),
    ("Couve-de-bruxelas cozida", "Verduras e Legumes", 36, 3.4, 7.1, 0.4, 3.7),
    ("Ervilha torta (vagem)", "Verduras e Legumes", 42, 2.8, 7.6, 0.2, 2.6),
    ("Espinafre cru", "Verduras e Legumes", 23, 2.9, 3.6, 0.4, 2.2),
    ("Jiló cozido", "Verduras e Legumes", 26, 0.9, 5.8, 0.2, 3.5),
    ("Maxixe cozido", "Verduras e Legumes", 14, 1.0, 2.5, 0.1, 1.8),
    ("Nabo cozido", "Verduras e Legumes", 16, 0.7, 3.5, 0.1, 1.5),
    ("Pimentão amarelo", "Verduras e Legumes", 27, 1.0, 6.3, 0.2, 0.9),
    ("Rabanete cru", "Verduras e Legumes", 12, 0.6, 2.0, 0.1, 1.6),
    ("Taioba cozida", "Verduras e Legumes", 34, 3.0, 5.2, 0.5, 3.2),
    ("Tomate cereja", "Verduras e Legumes", 18, 0.9, 3.9, 0.2, 1.2),
    ("Tomate seco", "Verduras e Legumes", 258, 14.1, 43.5, 3.0, 12.3),

    # ── FRUTAS (complementares) ──────────────────────────────────────────────
    ("Acerola", "Frutas", 33, 0.9, 8.0, 0.2, 1.5),
    ("Amora", "Frutas", 43, 1.4, 9.6, 0.5, 5.3),
    ("Banana da terra cozida", "Frutas", 128, 1.0, 33.7, 0.2, 1.5),
    ("Caju", "Frutas", 43, 1.0, 10.3, 0.3, 1.7),
    ("Carambola", "Frutas", 31, 1.0, 6.7, 0.3, 2.8),
    ("Cupuaçu polpa", "Frutas", 49, 1.0, 10.4, 0.5, 2.6),
    ("Figo fresco", "Frutas", 41, 0.5, 10.2, 0.2, 2.2),
    ("Framboesa", "Frutas", 52, 1.2, 11.9, 0.7, 6.5),
    ("Graviola polpa", "Frutas", 62, 0.8, 16.8, 0.2, 1.9),
    ("Jabuticaba", "Frutas", 58, 0.6, 15.3, 0.1, 2.3),
    ("Jaca", "Frutas", 88, 1.4, 22.5, 0.3, 1.0),
    ("Lichia", "Frutas", 65, 0.8, 16.5, 0.4, 1.3),
    ("Mangaba", "Frutas", 43, 0.7, 10.0, 0.3, 2.4),
    ("Mirtilo (blueberry)", "Frutas", 57, 0.7, 14.5, 0.3, 2.4),
    ("Nectarina", "Frutas", 44, 1.1, 10.6, 0.3, 1.7),
    ("Pêssego", "Frutas", 36, 0.8, 8.9, 0.1, 2.0),
    ("Pitaya", "Frutas", 50, 1.1, 11.0, 0.4, 3.0),
    ("Romã", "Frutas", 83, 1.7, 18.7, 1.2, 4.0),
    ("Tamarindo polpa", "Frutas", 239, 2.8, 62.5, 0.6, 5.1),
    ("Umbu", "Frutas", 37, 0.8, 9.4, 0.2, 2.0),
    ("Uva passa", "Frutas", 299, 3.1, 79.2, 0.5, 3.7),
    ("Banana verde (biomassa)", "Frutas", 110, 1.2, 26.3, 0.1, 2.8),
    ("Coco verde (água + polpa)", "Frutas", 47, 0.5, 5.0, 2.5, 1.2),
    ("Limão siciliano", "Frutas", 29, 1.1, 9.3, 0.3, 2.8),
    ("Manga espada", "Frutas", 64, 0.4, 16.7, 0.3, 1.8),
    ("Maracujá polpa", "Frutas", 68, 2.0, 12.3, 2.1, 1.1),

    # ── CARNES E PEIXES (complementares) ──────────────────────────────────────
    ("Frango asa sem pele cozida", "Carnes", 210, 28.0, 0.0, 10.5, 0.0),
    ("Frango moído refogado", "Carnes", 172, 25.0, 0.0, 7.8, 0.0),
    ("Carne bovina contrafilé grelhado", "Carnes", 237, 31.5, 0.0, 12.0, 0.0),
    ("Carne bovina picanha grelhada", "Carnes", 289, 27.0, 0.0, 20.0, 0.0),
    ("Carne bovina cupim assado", "Carnes", 312, 24.0, 0.0, 24.0, 0.0),
    ("Carne bovina fraldinha grelhada", "Carnes", 192, 28.5, 0.0, 8.5, 0.0),
    ("Carne suína costela assada", "Carnes", 340, 22.0, 0.0, 28.0, 0.0),
    ("Linguiça calabresa", "Carnes", 315, 15.0, 2.0, 27.0, 0.0),
    ("Linguiça de frango", "Carnes", 196, 15.5, 3.5, 13.5, 0.0),
    ("Salsicha", "Carnes", 243, 12.0, 3.0, 20.5, 0.0),
    ("Hambúrguer bovino grelhado", "Carnes", 260, 22.0, 5.0, 17.0, 0.5),
    ("Cordeiro pernil assado", "Carnes", 206, 28.0, 0.0, 10.0, 0.0),
    ("Pato assado", "Carnes", 201, 23.5, 0.0, 11.5, 0.0),
    ("Coelho cozido", "Carnes", 173, 25.5, 0.0, 7.5, 0.0),
    ("Tilápia empanada frita", "Carnes", 235, 18.0, 12.0, 13.0, 0.5),
    ("Salmão defumado", "Carnes", 117, 18.3, 0.0, 4.3, 0.0),
    ("Atum fresco grelhado", "Carnes", 184, 29.9, 0.0, 6.3, 0.0),
    ("Bacalhau dessalgado cozido", "Carnes", 100, 22.5, 0.0, 0.8, 0.0),
    ("Merluza cozida", "Carnes", 93, 18.6, 0.0, 1.9, 0.0),
    ("Panga (pangasius) cozido", "Carnes", 92, 15.2, 0.0, 3.5, 0.0),
    ("Robalo grelhado", "Carnes", 124, 23.6, 0.0, 2.6, 0.0),
    ("Dourado grelhado", "Carnes", 130, 24.0, 0.0, 3.5, 0.0),
    ("Pintado grelhado", "Carnes", 118, 22.0, 0.0, 3.0, 0.0),
    ("Truta grelhada", "Carnes", 150, 23.0, 0.0, 6.2, 0.0),
    ("Lula cozida", "Carnes", 81, 15.6, 1.8, 1.2, 0.0),
    ("Polvo cozido", "Carnes", 82, 14.9, 2.2, 1.0, 0.0),
    ("Mexilhão cozido", "Carnes", 86, 11.9, 3.7, 2.2, 0.0),
    ("Ostra crua", "Carnes", 51, 5.7, 2.7, 1.3, 0.0),
    ("Surimi (kani)", "Carnes", 99, 12.0, 9.8, 1.0, 0.0),

    # ── OVOS E LATICÍNIOS (complementares) ────────────────────────────────────
    ("Ovo de codorna cozido", "Ovos e Laticínios", 158, 13.1, 0.4, 11.1, 0.0),
    ("Ovo frito", "Ovos e Laticínios", 196, 13.6, 0.8, 15.3, 0.0),
    ("Omelete simples", "Ovos e Laticínios", 154, 10.6, 0.6, 12.0, 0.0),
    ("Leite semidesnatado", "Ovos e Laticínios", 46, 3.2, 4.8, 1.5, 0.0),
    ("Leite de cabra", "Ovos e Laticínios", 69, 3.6, 4.5, 4.1, 0.0),
    ("Coalhada", "Ovos e Laticínios", 56, 3.2, 4.5, 2.7, 0.0),
    ("Kefir de leite", "Ovos e Laticínios", 52, 3.5, 4.0, 2.0, 0.0),
    ("Queijo coalho", "Ovos e Laticínios", 328, 21.5, 2.0, 26.5, 0.0),
    ("Queijo provolone", "Ovos e Laticínios", 351, 25.6, 2.1, 26.6, 0.0),
    ("Queijo brie", "Ovos e Laticínios", 334, 20.8, 0.5, 27.7, 0.0),
    ("Queijo gorgonzola", "Ovos e Laticínios", 353, 21.4, 2.3, 28.7, 0.0),
    ("Queijo cheddar", "Ovos e Laticínios", 403, 25.0, 1.3, 33.1, 0.0),
    ("Nata (creme de leite)", "Ovos e Laticínios", 202, 2.0, 3.1, 20.2, 0.0),
    ("Leite condensado", "Ovos e Laticínios", 321, 7.5, 55.5, 8.0, 0.0),
    ("Creme de ricota", "Ovos e Laticínios", 120, 10.0, 4.0, 7.5, 0.0),

    # ── ÓLEOS, GORDURAS E SEMENTES (complementares) ───────────────────────────
    ("Óleo de canola", "Óleos e Gorduras", 884, 0.0, 0.0, 100.0, 0.0),
    ("Óleo de gergelim", "Óleos e Gorduras", 884, 0.0, 0.0, 100.0, 0.0),
    ("Tahine (pasta de gergelim)", "Óleos e Gorduras", 595, 17.0, 21.2, 53.8, 9.3),
    ("Semente de abóbora torrada", "Óleos e Gorduras", 446, 18.6, 53.8, 19.4, 18.4),
    ("Pistache torrado", "Óleos e Gorduras", 562, 20.2, 27.2, 45.3, 10.6),
    ("Macadâmia torrada", "Óleos e Gorduras", 718, 7.9, 13.8, 75.8, 8.6),
    ("Avelã torrada", "Óleos e Gorduras", 646, 15.0, 16.7, 62.4, 9.7),
    ("Manteiga de cacau", "Óleos e Gorduras", 884, 0.0, 0.0, 100.0, 0.0),
    ("Banha de porco", "Óleos e Gorduras", 898, 0.0, 0.0, 99.8, 0.0),
    ("Margarina", "Óleos e Gorduras", 719, 0.1, 0.7, 80.5, 0.0),

    # ── PRATOS PRONTOS BRASILEIROS ───────────────────────────────────────────
    ("Açaí na tigela com granola", "Pratos Prontos", 168, 2.0, 30.5, 5.2, 3.5),
    ("Acarajé", "Pratos Prontos", 289, 10.5, 22.3, 18.0, 3.8),
    ("Baião de dois", "Pratos Prontos", 145, 6.8, 20.5, 3.8, 3.2),
    ("Bobó de camarão", "Pratos Prontos", 105, 7.5, 8.2, 5.0, 1.0),
    ("Brigadeiro", "Pratos Prontos", 374, 6.0, 53.0, 16.0, 1.5),
    ("Caldo de feijão", "Pratos Prontos", 35, 2.2, 6.0, 0.3, 2.5),
    ("Carne de sol com mandioca", "Pratos Prontos", 158, 14.0, 12.5, 5.5, 1.0),
    ("Coxinha de frango frita", "Pratos Prontos", 279, 12.5, 23.5, 15.5, 0.8),
    ("Empada de frango", "Pratos Prontos", 324, 8.0, 29.0, 19.5, 1.0),
    ("Escondidinho de carne seca", "Pratos Prontos", 148, 9.5, 13.8, 5.8, 0.8),
    ("Estrogonofe de frango", "Pratos Prontos", 147, 13.5, 5.0, 8.2, 0.3),
    ("Farofa de ovo", "Pratos Prontos", 258, 5.0, 35.0, 11.0, 3.0),
    ("Feijoada", "Pratos Prontos", 138, 10.0, 9.0, 7.5, 4.5),
    ("Frango xadrez", "Pratos Prontos", 145, 16.5, 6.0, 6.0, 1.5),
    ("Lasanha bolonhesa", "Pratos Prontos", 152, 9.0, 15.0, 6.5, 1.0),
    ("Moqueca de peixe", "Pratos Prontos", 105, 10.5, 4.0, 5.5, 0.8),
    ("Moqueca baiana", "Pratos Prontos", 128, 9.5, 5.5, 7.8, 1.0),
    ("Pão de queijo assado", "Pratos Prontos", 363, 5.5, 34.0, 22.5, 0.5),
    ("Pastel de carne frito", "Pratos Prontos", 328, 7.5, 27.0, 21.0, 1.0),
    ("Quibe assado", "Pratos Prontos", 198, 15.0, 12.0, 10.0, 2.5),
    ("Risoto de cogumelos", "Pratos Prontos", 130, 3.5, 20.5, 3.8, 0.8),
    ("Salpicão de frango", "Pratos Prontos", 192, 10.5, 12.0, 11.5, 1.5),
    ("Sopa de legumes", "Pratos Prontos", 28, 1.0, 5.5, 0.3, 1.5),
    ("Sopa de lentilha", "Pratos Prontos", 55, 3.5, 9.0, 0.5, 3.0),
    ("Strogonoff de carne", "Pratos Prontos", 168, 14.5, 5.5, 10.0, 0.3),
    ("Tapioca com queijo", "Pratos Prontos", 195, 5.0, 28.0, 7.0, 0.3),
    ("Torta de frango", "Pratos Prontos", 232, 9.5, 22.0, 12.0, 0.8),
    ("Tutu de feijão", "Pratos Prontos", 110, 5.5, 16.5, 2.5, 4.5),
    ("Vatapá", "Pratos Prontos", 172, 6.5, 12.0, 11.0, 1.5),
    ("Virado à paulista", "Pratos Prontos", 165, 8.5, 15.0, 8.0, 4.0),
    ("Yakisoba de frango", "Pratos Prontos", 138, 8.0, 18.5, 3.5, 1.2),
    ("Arroz carreteiro", "Pratos Prontos", 155, 8.5, 18.0, 5.5, 1.0),
    ("Galinhada", "Pratos Prontos", 148, 10.0, 17.0, 4.5, 0.8),
    ("Parmegiana de frango", "Pratos Prontos", 195, 16.0, 10.5, 10.0, 0.5),

    # ── BEBIDAS (complementares) ─────────────────────────────────────────────
    ("Café com leite", "Bebidas", 32, 1.5, 3.2, 1.2, 0.0),
    ("Cappuccino (pó)", "Bebidas", 418, 9.5, 68.0, 13.0, 1.0),
    ("Chá de camomila (infusão)", "Bebidas", 1, 0.0, 0.2, 0.0, 0.0),
    ("Chá mate (infusão)", "Bebidas", 2, 0.1, 0.3, 0.0, 0.0),
    ("Isotônico", "Bebidas", 24, 0.0, 6.0, 0.0, 0.0),
    ("Leite de soja", "Bebidas", 41, 3.4, 2.2, 2.0, 0.5),
    ("Suco de açaí", "Bebidas", 82, 1.0, 12.5, 3.5, 2.0),
    ("Suco verde (couve+limão+gengibre)", "Bebidas", 22, 0.8, 4.5, 0.2, 0.8),
    ("Smoothie de frutas", "Bebidas", 68, 1.5, 15.0, 0.5, 1.5),
    ("Cerveja", "Bebidas", 43, 0.5, 3.6, 0.0, 0.0),
    ("Vinho tinto seco", "Bebidas", 85, 0.1, 2.6, 0.0, 0.0),

    # ── AÇÚCARES E DOCES (complementares) ────────────────────────────────────
    ("Açúcar demerara", "Açúcares", 377, 0.2, 97.3, 0.0, 0.0),
    ("Xarope de agave", "Açúcares", 310, 0.1, 76.4, 0.5, 0.2),
    ("Xilitol", "Açúcares", 240, 0.0, 100.0, 0.0, 0.0),
    ("Eritritol", "Açúcares", 0, 0.0, 100.0, 0.0, 0.0),
    ("Stevia (pó)", "Açúcares", 0, 0.0, 0.0, 0.0, 0.0),
    ("Doce de leite", "Açúcares", 315, 5.5, 55.0, 8.0, 0.0),
    ("Paçoca", "Açúcares", 459, 13.0, 50.5, 23.0, 3.5),
    ("Cocada", "Açúcares", 398, 2.8, 54.0, 19.5, 3.5),
    ("Goiabada", "Açúcares", 302, 0.4, 77.5, 0.1, 4.5),
    ("Barra de cereal (média)", "Açúcares", 395, 6.0, 69.5, 10.5, 5.0),
    ("Chocolate branco", "Açúcares", 539, 5.9, 59.2, 32.1, 0.9),
    ("Chocolate 85% cacau", "Açúcares", 500, 10.0, 30.0, 38.0, 14.0),

    # ── TEMPEROS E CONDIMENTOS (complementares) ──────────────────────────────
    ("Pesto de manjericão", "Temperos", 387, 4.5, 4.0, 39.0, 2.5),
    ("Molho inglês (worcestershire)", "Temperos", 78, 0.9, 19.4, 0.0, 0.0),
    ("Azeite de dendê", "Temperos", 884, 0.0, 0.0, 100.0, 0.0),
    ("Chimichurri", "Temperos", 158, 1.5, 5.0, 15.0, 2.0),
    ("Guacamole", "Temperos", 160, 2.0, 8.5, 14.7, 6.7),
    ("Homus (hummus)", "Temperos", 166, 7.9, 14.3, 9.6, 6.0),
    ("Leite de coco", "Temperos", 197, 2.0, 3.3, 21.3, 0.0),
    ("Molho barbecue", "Temperos", 150, 0.8, 35.0, 0.5, 0.5),
    ("Molho branco (béchamel)", "Temperos", 123, 3.5, 8.2, 8.5, 0.2),
    ("Molho pesto", "Temperos", 387, 4.5, 4.0, 39.0, 2.5),
    ("Molho rosé", "Temperos", 152, 2.0, 7.5, 12.5, 0.5),
    ("Gengibre fresco", "Temperos", 46, 1.0, 10.1, 0.5, 1.8),
    ("Cúrcuma (açafrão) em pó", "Temperos", 312, 9.7, 67.1, 3.2, 22.7),
    ("Canela em pó", "Temperos", 247, 4.0, 80.6, 1.2, 53.1),

    # ── INDUSTRIALIZADOS (complementares) ────────────────────────────────────
    ("Tofu macio (silken)", "Industrializados", 55, 4.8, 2.0, 3.0, 0.0),
    ("Tempeh", "Industrializados", 192, 20.3, 7.6, 10.8, 0.0),
    ("Seitan", "Industrializados", 370, 75.0, 14.0, 1.9, 0.6),
    ("Leite de arroz", "Industrializados", 47, 0.3, 9.2, 1.0, 0.3),
    ("Queijo vegano (média)", "Industrializados", 250, 2.0, 18.0, 19.0, 0.0),
    ("Hambúrguer vegetal", "Industrializados", 195, 15.0, 12.0, 10.0, 3.5),
    ("Salsicha vegetal", "Industrializados", 168, 18.0, 8.0, 7.0, 2.0),
    ("Proteína de ervilha (pó)", "Industrializados", 357, 80.0, 4.0, 2.5, 5.0),
    ("Colágeno hidrolisado (pó)", "Industrializados", 340, 90.0, 0.0, 0.0, 0.0),
    ("Palatinose (isomaltulose)", "Industrializados", 400, 0.0, 100.0, 0.0, 0.0),
    ("Waxy maize (pó)", "Industrializados", 380, 0.0, 95.0, 0.0, 0.0),
    ("BCAA em pó", "Industrializados", 285, 71.0, 0.0, 0.0, 0.0),
    ("Glutamina em pó", "Industrializados", 358, 89.5, 0.0, 0.0, 0.0),

    # ── TUBÉRCULOS (complementares) ──────────────────────────────────────────
    ("Gengibre (raiz)", "Tubérculos", 46, 1.0, 10.1, 0.5, 1.8),
    ("Açafrão (raiz fresca)", "Tubérculos", 62, 1.4, 12.7, 1.0, 2.3),
    ("Beterraba crua", "Tubérculos", 43, 1.6, 9.6, 0.1, 2.8),
    ("Rabanete", "Tubérculos", 12, 0.6, 2.0, 0.1, 1.6),
]


def init_taco_db():
    """Cria o banco nutricional se não existir e popula com dados TACO + TBCA."""
    # Se o arquivo existe mas está vazio (0 bytes), remove para recriar do zero
    if os.path.exists(TACO_DB_PATH) and os.path.getsize(TACO_DB_PATH) == 0:
        os.remove(TACO_DB_PATH)
        logger.info("TACO: banco vazio detectado e removido para recriação.")

    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS alimentos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nome        TEXT NOT NULL,
                categoria   TEXT NOT NULL,
                kcal        REAL NOT NULL,
                proteina_g  REAL NOT NULL,
                carb_g      REAL NOT NULL,
                gordura_g   REAL NOT NULL,
                fibra_g     REAL NOT NULL,
                fonte       TEXT NOT NULL DEFAULT 'TACO'
            );
            CREATE INDEX IF NOT EXISTS idx_alimentos_nome
                ON alimentos(nome);
            CREATE INDEX IF NOT EXISTS idx_alimentos_categoria
                ON alimentos(categoria);
        """)

        # Adiciona coluna fonte se não existir (migração de banco antigo)
        try:
            con.execute("SELECT fonte FROM alimentos LIMIT 1")
        except Exception:
            con.execute("ALTER TABLE alimentos ADD COLUMN fonte TEXT NOT NULL DEFAULT 'TACO'")
            logger.info("TACO: coluna 'fonte' adicionada ao banco existente.")

        count = con.execute("SELECT COUNT(*) as n FROM alimentos").fetchone()["n"]

        if count == 0:
            # Banco novo: insere TACO + TBCA de uma vez
            taco_rows = [(n, c, k, p, cb, g, f, "TACO") for n, c, k, p, cb, g, f in _ALIMENTOS]
            tbca_rows = [(n, c, k, p, cb, g, f, "TBCA") for n, c, k, p, cb, g, f in _ALIMENTOS_TBCA]
            con.executemany(
                "INSERT INTO alimentos (nome, categoria, kcal, proteina_g, carb_g, gordura_g, fibra_g, fonte) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                taco_rows + tbca_rows,
            )
            total = len(taco_rows) + len(tbca_rows)
            logger.info(f"Base nutricional: {len(taco_rows)} TACO + {len(tbca_rows)} TBCA = {total} alimentos.")
        else:
            # Banco existente: verifica se dados TBCA já foram inseridos
            tbca_count = con.execute("SELECT COUNT(*) as n FROM alimentos WHERE fonte = 'TBCA'").fetchone()["n"]
            if tbca_count == 0 and len(_ALIMENTOS_TBCA) > 0:
                # Deduplicação: insere somente alimentos TBCA cujo nome não existe
                existentes = {
                    row["nome"].lower()
                    for row in con.execute("SELECT nome FROM alimentos").fetchall()
                }
                novos = [
                    (n, c, k, p, cb, g, f, "TBCA")
                    for n, c, k, p, cb, g, f in _ALIMENTOS_TBCA
                    if n.lower() not in existentes
                ]
                if novos:
                    con.executemany(
                        "INSERT INTO alimentos (nome, categoria, kcal, proteina_g, carb_g, gordura_g, fibra_g, fonte) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        novos,
                    )
                    logger.info(f"TBCA: {len(novos)} alimentos novos adicionados (de {len(_ALIMENTOS_TBCA)} candidatos).")
                else:
                    logger.info("TBCA: todos os alimentos já existiam no banco.")
            else:
                logger.info(f"Base nutricional: banco já populado com {count} alimentos ({tbca_count} da TBCA).")


def buscar_alimento(termo: str, limite: int = 5) -> list[dict]:
    """
    Busca alimentos pelo nome (busca parcial, case-insensitive).
    Retorna lista de dicts com dados nutricionais por 100g.
    """
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM alimentos WHERE LOWER(nome) LIKE ? ORDER BY nome LIMIT ?",
            (f"%{termo.lower()}%", limite),
        ).fetchall()
    return [dict(r) for r in rows]


def buscar_por_categoria(categoria: str) -> list[dict]:
    """Retorna todos os alimentos de uma categoria."""
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM alimentos WHERE LOWER(categoria) LIKE ? ORDER BY nome",
            (f"%{categoria.lower()}%",),
        ).fetchall()
    return [dict(r) for r in rows]


def listar_categorias() -> list[str]:
    """Retorna todas as categorias disponíveis."""
    with _conn() as con:
        rows = con.execute(
            "SELECT DISTINCT categoria FROM alimentos ORDER BY categoria"
        ).fetchall()
    return [r["categoria"] for r in rows]


def calcular_porcao(termo: str, gramas: float) -> dict | None:
    """
    Busca um alimento e calcula os macros para a porção informada (em gramas).
    Retorna dict com os valores ajustados ou None se não encontrar.
    """
    resultados = buscar_alimento(termo, limite=1)
    if not resultados:
        return None
    al = resultados[0]
    fator = gramas / 100.0
    return {
        "nome": al["nome"],
        "porcao_g": gramas,
        "kcal": round(al["kcal"] * fator, 1),
        "proteina_g": round(al["proteina_g"] * fator, 1),
        "carb_g": round(al["carb_g"] * fator, 1),
        "gordura_g": round(al["gordura_g"] * fator, 1),
        "fibra_g": round(al["fibra_g"] * fator, 1),
    }


def gerar_contexto_nutricional(termos: list[str]) -> str:
    """
    Recebe uma lista de termos de alimentos e gera uma string formatada
    com os dados nutricionais para injetar no contexto do Claude.

    Exemplo de uso no bot:
        termos = ["frango", "arroz", "brócolis"]
        contexto = gerar_contexto_nutricional(termos)
        # Injeta no system prompt ou na mensagem do usuário
    """
    linhas = ["DADOS NUTRICIONAIS (por 100g, fontes: TACO/Unicamp + TBCA/USP):"]
    for termo in termos:
        resultados = buscar_alimento(termo, limite=3)
        for al in resultados:
            fonte = al.get("fonte", "TACO")
            linhas.append(
                f"- {al['nome']} [{fonte}]: {al['kcal']}kcal | "
                f"P:{al['proteina_g']}g | C:{al['carb_g']}g | "
                f"G:{al['gordura_g']}g | Fibra:{al['fibra_g']}g"
            )
    return "\n".join(linhas) if len(linhas) > 1 else ""


def resumo_banco() -> dict:
    """Retorna um resumo do banco de dados TACO."""
    with _conn() as con:
        total = con.execute("SELECT COUNT(*) as n FROM alimentos").fetchone()["n"]
        cats = con.execute(
            "SELECT categoria, COUNT(*) as n FROM alimentos GROUP BY categoria ORDER BY n DESC"
        ).fetchall()
    return {
        "total_alimentos": total,
        "categorias": [{"categoria": r["categoria"], "count": r["n"]} for r in cats],
    }
