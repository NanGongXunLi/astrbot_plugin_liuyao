"""
六爻数理占卜 - 起卦逻辑
数字起卦法 + 世爻定用神 + 纳甲动变 + 六兽
"""

from datetime import datetime
from .data import (
    BAGUA, BAGUA_WUXING, DIZHI_WUXING, DIZHI_ORDER,
    NAJIA, SHI_GONG, GUA_MING,
    match_yongshen, calculate_score, get_wuxing_relation,
    get_shi_yao, get_liuqin_wuxing,
    get_liuyao_full, get_ying_pos, get_shichen_num,
    get_lunar_month_info, get_ganzhi_from_date,
    LIUSHEN_MEANING,
)

# 日辰地支简化（从基准日推算）
BASE_DIZHI_INDEX = 0  # 2024-01-01 = 甲子日
BASE_DATE = datetime(2024, 1, 1)

def get_day_info(dt=None):
    """获取日辰地支和五行"""
    if dt is None:
        dt = datetime.now()
    delta = (dt - BASE_DATE).days
    idx = (BASE_DIZHI_INDEX + delta) % 12
    dz = DIZHI_ORDER[idx]
    wx = DIZHI_WUXING.get(dz, "木")
    return dz, wx

def num_to_yao(numbers: list, dt=None) -> dict:
    """
    数字起卦法（用户自定义规则）：
    1. 数字个数为偶则平分，为奇则前少后多
    2. 前一半数字之和%8得 上卦数
    3. 后一半数字之和%8得 下卦数
    4. (上卦数 + 下卦数 + 时辰数) % 6得 动爻（余0为六爻）
    """
    if dt is None:
        dt = datetime.now()
    
    n = len(numbers)
    if n % 2 == 0:
        mid = n // 2
    else:
        mid = (n - 1) // 2  # 前少后多
    
    shang_sum = sum(numbers[:mid])
    xia_sum = sum(numbers[mid:])
    
    shang_num = shang_sum % 8 or 8  # 0→8（坤）
    xia_num = xia_sum % 8 or 8
    
    shang_gua = BAGUA[shang_num]
    xia_gua = BAGUA[xia_num]
    
    # 动爻：(上卦数(%8余数) + 下卦数(%8余数) + 时辰数) % 6
    sc = get_shichen_num(dt)
    dong_yao = (shang_num + xia_num + sc) % 6
    if dong_yao == 0:
        dong_yao = 6
    
    key = shang_gua + xia_gua
    gua_name = GUA_MING.get(key, f"{shang_gua}{xia_gua}")
    
    shi_pos, shi_dz, shi_wx, gong, gong_wx = get_shi_yao(shang_gua, xia_gua)
    ying_pos = SHI_GONG.get(key, {}).get("应", 3)
    
    # 世爻纳甲用本卦实际纳甲（上下卦各自的纳甲）
    pos_map = {1: "初", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六"}
    shi_key = pos_map[shi_pos]
    if shi_pos <= 3:
        if xia_gua in NAJIA and shi_key in NAJIA[xia_gua]:
            shi_dz, shi_wx = NAJIA[xia_gua][shi_key]
    else:
        if shang_gua in NAJIA and shi_key in NAJIA[shang_gua]:
            shi_dz, shi_wx = NAJIA[shang_gua][shi_key]
    
    # === 计算变卦（放在return前）===
    _BIAN_GUA = {
        ("乾",1): "巽", ("乾",2): "离", ("乾",3): "兑",
        ("兑",1): "坎", ("兑",2): "震", ("兑",3): "乾",
        ("离",1): "艮", ("离",2): "乾", ("离",3): "震",
        ("震",1): "坤", ("震",2): "兑", ("震",3): "离",
        ("巽",1): "乾", ("巽",2): "艮", ("巽",3): "坎",
        ("坎",1): "兑", ("坎",2): "坤", ("坎",3): "巽",
        ("艮",1): "离", ("艮",2): "巽", ("艮",3): "坤",
        ("坤",1): "震", ("坤",2): "坎", ("坤",3): "艮",
    }
    if dong_yao <= 3:
        bian_xia = _BIAN_GUA.get((xia_gua, dong_yao), xia_gua)
        bian_shang = shang_gua
    else:
        bian_shang = _BIAN_GUA.get((shang_gua, dong_yao - 3), shang_gua)
        bian_xia = xia_gua
    bian_key = bian_shang + bian_xia
    bian_name = GUA_MING.get(bian_key, f"{bian_shang}{bian_xia}")
    
    # 变爻纳甲（用变卦上下卦各自的纳甲）
    pos_map = {1: "初", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六"}
    bian_najia = None
    if dong_yao <= 3:
        # 动爻在下卦 → 变卦下卦的对应爻
        if bian_xia in NAJIA and pos_map[dong_yao] in NAJIA[bian_xia]:
            bian_najia = NAJIA[bian_xia][pos_map[dong_yao]]
    else:
        if bian_shang in NAJIA and pos_map[dong_yao] in NAJIA[bian_shang]:
            bian_najia = NAJIA[bian_shang][pos_map[dong_yao]]
    
    return {
        "上卦": shang_gua,
        "下卦": xia_gua,
        "卦名": gua_name,
        "动爻": dong_yao,
        "所属宫": gong,
        "宫五行": gong_wx,
        "世爻位置": shi_pos,
        "应爻位置": ying_pos,
        "世爻纳甲": (shi_dz, shi_wx),
        "起卦详情": f"前{mid}位和={shang_sum}÷8余{shang_num}→{shang_gua}，后{n-mid}位和={xia_sum}÷8余{xia_num}→{xia_gua}，时辰{sc}，动爻({shang_num}+{xia_num}+{sc})%6={dong_yao}",
        "变卦": bian_name,
        "变卦组合": bian_key,
        "变爻纳甲": bian_najia,
    }

def get_yao_najia(shang_gua: str, xia_gua: str, dong_yao: int) -> tuple:
    """获取动爻的纳甲地支五行（用上下卦各自的纳甲）"""
    pos_map = {1: "初", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六"}
    pos_key = pos_map[dong_yao]
    gua = xia_gua if dong_yao <= 3 else shang_gua
    if gua in NAJIA and pos_key in NAJIA[gua]:
        return NAJIA[gua][pos_key]
    return ("子", "水")

def get_action_info(yao_info: dict, yongshen_wx: str) -> list:
    """动爻生克 + 回头生/回头克"""
    actions = []
    dong_yao = yao_info["动爻"]
    shang, xia = yao_info["上卦"], yao_info["下卦"]
    dz, wx = get_yao_najia(shang, xia, dong_yao)

    gua_name = xia if dong_yao <= 3 else shang
    action_from = f"{gua_name}卦第{dong_yao}爻纳{dz}{wx}"

    # 动爻 vs 用神
    rel = get_wuxing_relation(yongshen_wx, wx)
    if rel == "我生":
        actions.append({"desc": f"{action_from}生用神", "score": 1})
    elif rel == "我克":
        actions.append({"desc": f"{action_from}克用神", "score": -1})
    elif rel == "同":
        actions.append({"desc": f"{action_from}合用神", "score": 1})
    elif rel == "生我":
        actions.append({"desc": f"用神生{action_from}（泄气）", "score": -1})
    elif rel == "克我":
        actions.append({"desc": f"用神克{action_from}（耗力）", "score": -1})

    # 回头生/回头克（变爻 vs 动爻）
    bian_najia = yao_info.get("变爻纳甲")
    if bian_najia and "评分明细" in yao_info:
        bian_dz, bian_wx = bian_najia
        rel2 = get_wuxing_relation(wx, bian_wx)
        
        # 回头生需要用神有根（得日月生扶，不被日月克冲）
        # 从评分明细获取月建和日辰的评分来判断
        sd = yao_info["评分明细"]
        month_ok = sd['月建评分'] >= 0  # 月建不生克（0或正分）或生用神
        day_ok = sd['日辰评分'] >= 0    # 日辰同上
        
        if rel2 == "我生":  # 变爻生动爻
            if month_ok and day_ok:
                actions.append({"desc": f"变爻{bian_dz}{bian_wx}回头生动爻（用神有根）", "score": 2})
            else:
                actions.append({"desc": f"变爻{bian_dz}{bian_wx}回头生动爻（用神无根，效力打折）", "score": 0})
        elif rel2 == "我克":  # 变爻克动爻
            actions.append({"desc": f"变爻{bian_dz}{bian_wx}回头克动爻", "score": -2})

    return actions

def divinate(numbers: list, question: str = "", dt=None) -> dict:
    """完整占卜流程。dt 可指定日期时间，默认当前时间。"""
    if len(numbers) < 3:
        return {"error": "需要三个数字"}

    if dt is None:
        dt = datetime.now()

    # 1. 起卦（新规则：拆分数字求和+时辰定动爻）
    yao_info = num_to_yao(numbers, dt)
    shang, xia = yao_info["上卦"], yao_info["下卦"]

    # 2. 取用神 + 六亲定五行（以宫首卦五行为"我"）
    yongshen = match_yongshen(question)
    gong_wx = yao_info["宫五行"]
    ys_wx = get_liuqin_wuxing(gong_wx, yongshen)

    # 3. 取月建（农历）和日辰
    month_dz, month_wx = get_lunar_month_info(dt)
    day_dz, day_wx = get_day_info(dt)
    day_gan, day_zhi = get_ganzhi_from_date(dt)

    # 5. 综合评分（先算，用于回头生判定）
    score_result = calculate_score(ys_wx, month_wx, day_wx,
                                    month_dz, day_dz, [])
    # 把评分传给yao_info供回头生判定
    yao_info["评分明细"] = score_result

    # 4. 动变生克（现在可以读取评分明细了）
    actions = get_action_info(yao_info, ys_wx)

    # 重新计算含动变的评分
    score_result = calculate_score(ys_wx, month_wx, day_wx,
                                    month_dz, day_dz, actions)

    # 6. 完整六爻排盘
    lines = get_liuyao_full(
        shang, xia,
        yao_info["所属宫"], gong_wx,
        yao_info["世爻位置"], yao_info["应爻位置"],
        yao_info["动爻"], day_gan
    )

    return {
        "起卦信息": {
            "输入数字": f"{numbers[0]}, {numbers[1]}, {numbers[2]}",
            "卦名": yao_info["卦名"],
            "本卦": f"{shang}{xia}（上{shang}下{xia}）",
            "动爻": f"第{yao_info['动爻']}爻动",
            "所属宫": yao_info["所属宫"],
            "宫五行": gong_wx,
            "日干支": f"{day_gan}{day_zhi}",
            "变卦": yao_info["变卦"],
            "变卦组合": yao_info["变卦组合"],
            "变爻纳甲": yao_info["变爻纳甲"],
            "世爻位置": yao_info["世爻位置"],
            "应爻位置": yao_info["应爻位置"],
            "起卦详情": yao_info.get("起卦详情", ""),
        },
        "用神": yongshen,
        "用神五行": ys_wx,
        "月建": f"{month_dz}（{month_wx}）",
        "日辰": f"{day_dz}（{day_wx}）",
        "六爻排盘": lines,
        "评分明细": score_result,
    }
