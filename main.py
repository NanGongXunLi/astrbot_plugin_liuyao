"""
astrbot_plugin_liuyao - 六爻数理占卜
防护版：输入校验 + 内容过滤 + 伦理限制

使用协议：
1. 本工具基于《增删卜易》《易冒》等古籍理论，结果仅供参考
2. 不构成投资、婚姻、事业等重大决策建议
3. 禁止用于违法、伤害他人、迷信诈骗等用途
4. 事在人为，卦示吉凶仅为一种视角
"""

from datetime import datetime
from astrbot.api.star import Context, Star, register
from astrbot.api.event.filter import llm_tool
from astrbot.api import logger
from astrbot.core.message.message_event_result import MessageChain
from .divination import divinate
from .card import card as generate_card
from .data import wuxing_ke

BLOCKED_KEYWORDS = [
    "杀人", "自杀", "违法", "犯罪", "贩毒", "赌博", "诈骗",
    "害人", "诅咒", "下降头", "邪术", "偷窃", "抢劫",
]
MAX_NUM, MAX_NUMS = 99999, 10


class LiuYaoPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("六爻数理占卜插件已加载")

    @llm_tool("liuyao_divinate")
    async def liuyao_divinate(self, event, numbers: list, question: str = ""):
        """
        六爻占卜。输入数字起卦，返回评分卡片。
        基于《增删卜易》《易冒》理论，量化评分仅供参考。
        禁止用于违法或伤害他人的用途。

        Args:
            numbers(list[int]): 正整数数组，如[6,4,2]。
            question(str): 所问之事。

        Returns:
            str: 图片已发送。
        """
        if not numbers or len(numbers) < 1:
            return "至少需要1个数字。"
        if len(numbers) > MAX_NUMS:
            return f"最多{MAX_NUMS}个数字。"
        if not all(isinstance(n, int) and 0 < n <= MAX_NUM for n in numbers):
            return "请输入正整数。"

        if question:
            for kw in BLOCKED_KEYWORDS:
                if kw in question:
                    logger.warning(f"拦截: {question}")
                    return "超出占卜范围。"

        try:
            now = datetime.now()
            result = divinate(numbers, question, now)
            if "error" in result:
                return f"起卦失败：{result['error']}"

            result["_time"] = now.strftime("%Y-%m-%d %H:%M")
            lines = result["六爻排盘"]
            sd = result["评分明细"]

            parts = []
            for L in lines:
                if L['动爻']:
                    dn = L['六亲']
                    if sd['动变评分'] < 0:
                        parts.append(f"{dn}想发力但被牵制" if '回头克' in sd['动变详情'] else f"{dn}受到压制")
                    else:
                        parts.append(f"{dn}发力助推")
                    break
            shi = next((L for L in lines if L['世应'] == '世'), None)
            ying = next((L for L in lines if L['世应'] == '应'), None)
            if shi and ying:
                if wuxing_ke(ying['五行']) == shi['五行']:
                    parts.append("对面实力更强")
                elif wuxing_ke(shi['五行']) == ying['五行']:
                    parts.append("我方占主动")
            if sd['月建评分'] <= -3:
                parts.append("时机不对")
            if sd['日辰评分'] <= -1:
                parts.append("当天不利")
            result["_cause"] = "，".join(parts) if parts else "综合因素影响"

            card_path = generate_card(result)
            
            # 尝试事件发图
            img_sent = False
            try:
                from astrbot.core.message.message_event_result import MessageChain
                if event:
                    await event.send(MessageChain().file_image(card_path))
                    img_sent = True
            except Exception:
                pass
            
            if img_sent:
                return "【卦象卡片已发送】"
            else:
                return f"【卦象卡片】图片路径: {card_path}"

        except Exception as e:
            logger.error(f"占卜出错: {e}")
            return "数据异常，请重试。"


@register("liuyao_plugin", author="南宫墨铭", desc="六爻数理占卜。输入数字自动起卦，输出评分卡片。", version="v1.0.0")
def register_plugin():
    return LiuYaoPlugin
