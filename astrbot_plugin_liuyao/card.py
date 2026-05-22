"""
六爻占卜卡片 - 浅色版
"""

from PIL import Image, ImageDraw, ImageFont
import os

FONT_PATH = "C:\\Windows\\Fonts\\simhei.ttf"
CACHE_DIR = r"C:\Users\Lenovo\.astrbot_launcher\instances\ed1fd077-3587-4f3a-98dc-a6db4356f0ba\core\data\workspaces\default_FriendMessage_2891097219"

SCALE = 3
W, H = 600 * SCALE, 600 * SCALE
M = 35 * SCALE

# 浅色配色
BG = (245, 245, 240)          # 米白底
CARD_BG = (255, 255, 255)     # 纯白卡
ACCENT = (200, 150, 50)       # 暗金
ACCENT2 = (160, 120, 40)
TEXT_M = (40, 40, 40)         # 主文字 深黑
TEXT_S = (100, 100, 100)      # 灰
TEXT_D = (150, 150, 150)      # 浅灰
DIV = (220, 220, 215)         # 分割线


def ft(px):
    return ImageFont.truetype(FONT_PATH, px * SCALE)


def card(result):
    qi = result["起卦信息"]
    sd = result["评分明细"]
    ts = result.get("_time", "")
    total = sd['综合评分']
    ji = sd['吉凶']

    if total >= 3:
        jc, jb, badg = (40, 160, 80), (230, 250, 235), "吉"
    elif total >= -1:
        jc, jb, badg = (200, 150, 50), (255, 248, 230), "平"
    else:
        jc, jb, badg = (210, 70, 70), (255, 235, 235), "凶"

    ys = result["用神"]
    tip = {"父母": "多查资料、请教长辈，保持耐心", "官鬼": "主动争取、展现能力，防竞争者",
           "妻财": "把握时机、见好就收", "兄弟": "注意人际关系，防他人影响",
           "子孙": "放平心态，随缘而为"}.get(ys, "顺势而为")

    img = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle([15 * SCALE, 15 * SCALE, W - 15 * SCALE, H - 15 * SCALE],
                         radius=16 * SCALE, fill=CARD_BG)

    y = 38 * SCALE

    # 标题
    dr.text((M, y), "六爻占卜", fill=ACCENT2, font=ft(14))
    dr.text((M, y + 24 * SCALE), ts, fill=TEXT_D, font=ft(13))

    # 卦名
    y = 90 * SCALE
    dr.text((M, y), qi['卦名'], fill=TEXT_M, font=ft(32))
    dr.text((M + 42 * SCALE + 160 * SCALE, y + 8 * SCALE),
            f"→ {qi['变卦']}", fill=ACCENT, font=ft(20))
    dr.text((M, y + 44 * SCALE),
            f"{qi['所属宫']}宫 · {qi.get('动爻','')}", fill=TEXT_S, font=ft(13))

    y += 78 * SCALE
    dr.line([(M, y), (W - M, y)], fill=DIV, width=2)

    # 信息
    y += 22 * SCALE
    for i, (lb, vl) in enumerate([("月建", result['月建']), ("日辰", result['日辰']),
                                   ("用神", f"{ys}（{result['用神五行']}）")]):
        x = M + i * 160 * SCALE
        dr.text((x, y), lb, fill=TEXT_S, font=ft(13))
        dr.text((x, y + 20 * SCALE), vl, fill=TEXT_M, font=ft(17))

    # 评分条
    y += 60 * SCALE
    for i, (lb, sc) in enumerate([("月建", sd['月建评分']), ("日辰", sd['日辰评分']),
                                   ("动爻", sd['动变评分'])]):
        bx = M + i * 160 * SCALE
        dr.text((bx, y), lb, fill=TEXT_S, font=ft(13))
        dr.text((bx + 40 * SCALE, y), f"{sc:+d}", fill=TEXT_M, font=ft(15))
        by2 = y + 26 * SCALE
        bw = 110 * SCALE
        dr.rectangle([bx, by2, bx + bw, by2 + 7 * SCALE], fill=(235, 235, 230))
        lo = max(-6, min(6, sc))
        p = (lo + 6) / 12
        fc = (80, 180, 100) if sc >= 0 else (200, 90, 90)
        dr.rectangle([bx, by2, bx + int(bw * p), by2 + 7 * SCALE], fill=fc)

    # 吉凶
    y += 60 * SCALE
    cx, cy = W // 2, y + 55 * SCALE
    rr = 52 * SCALE
    dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=jb, outline=jc, width=3)
    dr.text((cx - 18 * SCALE, cy - 18 * SCALE), f"{total}", fill=jc, font=ft(28))
    dr.text((cx - 22 * SCALE, cy + 14 * SCALE), "分", fill=TEXT_S, font=ft(13))
    gx = cx + rr + 32 * SCALE
    dr.text((gx, cy - 20 * SCALE), badg, fill=jc, font=ft(42))
    dr.text((gx, cy + 22 * SCALE),
            f"{sd['月建评分']}+{sd['日辰评分']}+{sd['动变评分']}", fill=TEXT_S, font=ft(13))

    y = cy + rr + 26 * SCALE
    dr.line([(M, y), (W - M, y)], fill=DIV, width=2)

    # 建议
    y += 20 * SCALE
    dr.text((M, y), "建议", fill=ACCENT2, font=ft(15))
    dr.text((M, y + 28 * SCALE), tip, fill=TEXT_M, font=ft(20))

    # 成因（可选）
    cause = result.get("_cause", "")
    if cause:
        y += 60 * SCALE
        dr.text((M, y), "成因", fill=ACCENT2, font=ft(15))
        dr.text((M, y + 28 * SCALE), cause, fill=TEXT_S, font=ft(16))

    # 底部署名（右下）
    # 底部署名（右下）
    dr.text((W - M - 120 * SCALE, H - 52 * SCALE), "南宫墨铭 · 六爻占卜", fill=(180, 180, 180), font=ft(13))
    dr.text((M, H - 22 * SCALE), "仅供娱乐参考，不构成决策建议", fill=(200, 200, 200), font=ft(12))

    os.makedirs(CACHE_DIR, exist_ok=True)
    p = os.path.join(CACHE_DIR, "divination_card.png")
    img.save(p, quality=95)
    return p
