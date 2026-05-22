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
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.message.message_event_result import MessageChain
from .divination import divinate
from .card import card as generate_card
from .data import wuxing_ke

BLOCKED_KEYWORDS = [
    "杀人", "自杀", "违法", "犯罪", "贩毒", "赌博", "诈骗",
    "害人", "诅咒", "下降头", "邪术", "偷窃", "抢劫",
]
MAX_NUM, MAX_NUMS = 99999, 10


def _patch_core_send():
    """启动时修补AstrBot核心框架的 event.send() 类型转换bug。"""
    import re
    target = "astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event"
    try:
        import importlib
        mod = importlib.import_module(target)
        src = open(mod.__file__, "r", encoding="utf-8").read()
        # 检查是否已经修补过
        if "session_id_str = str(session_id)" in src:
            logger.info("[liuyao] event.send() 补丁已生效，跳过。")
            return
        # 修补 _dispatch_send 中的类型转换
        old = r'(# session_id 必须是纯数字字符串)\s+session_id_int = \(\s+int\(session_id\) if session_id and session_id\.isdigit\(\) else None\s+\)'
        new = r'''\1
        session_id_str = str(session_id) if session_id is not None else ""
        session_id_int = int(session_id_str) if session_id_str.isdigit() else None'''
        if re.search(old, src):
            src = re.sub(old, new, src)
            with open(mod.__file__, "w", encoding="utf-8") as f:
                f.write(src)
            logger.info("[liuyao] event.send() 补丁已应用：_dispatch_send 类型转换修复。")
        else:
            logger.warning("[liuyao] event.send() 补丁：未匹配到目标代码段。")
    except Exception as e:
        logger.error(f"[liuyao] event.send() 补丁失败: {e}")


class LiuYaoPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config or {}
        self.card_enabled = getattr(self.config, 'card_enabled', True)
        self.detail_level = getattr(self.config, 'detail_level', '标准')
        _patch_core_send()
        logger.info(f"六爻数理占卜插件已加载 (卡片={'开' if self.card_enabled else '关'} 详细={self.detail_level})")

    @llm_tool("liuyao_divinate")
    async def liuyao_divinate(self, event, numbers: list, question: str = ""):
        """
        六爻占卜。输入数字起卦，返回评分卡片。
        基于《增删卜易》《易冒》理论，量化评分仅供参考。
        禁止用于违法或伤害他人的用途。
        只有用户明确提供了数字和问题时才调用此工具，不可自行编造数字。

        Args:
            numbers(list[int]): 正整数数组，如[6,4,2]。必须来自用户输入的明确数字，不可自己编造或猜测。
            question(str): 所问之事。必须由用户明确说出，不可自己编造。

        Returns:
            str: 图片已发送或错误提示。
        """
        # === 防幻觉：拒绝凭空编造的数字 ===
        if not numbers or len(numbers) < 1:
            return "请提供至少1个正整数起卦，例如：224，测今日运势。"
        if not question or not question.strip():
            return "请同时说明所问之事，例如：224，测今日运势。"
        if len(numbers) > MAX_NUMS:
            return f"最多{MAX_NUMS}个数字。"
        if not all(isinstance(n, int) and 0 < n <= MAX_NUM for n in numbers):
            return "请输入正整数。"

        # 检测常见幻觉模式：纯猜测的默认数字
        if len(numbers) == 1 and numbers[0] <= 8:
            return f"数字{numbers[0]}过小，起卦需要有效数字组合。请提供3个或更多数字。"
        _hallucination_patterns = {
            tuple([1, 2, 3]): 1, tuple([3, 2, 1]): 1,
            tuple([2, 3, 4]): 1, tuple([4, 3, 2]): 1,
            tuple([3, 4, 5]): 1, tuple([5, 4, 3]): 1,
            tuple([4, 5, 6]): 1, tuple([6, 5, 4]): 1,
            tuple([5, 6, 7]): 1, tuple([7, 6, 5]): 1,
            tuple([6, 7, 8]): 1, tuple([8, 7, 6]): 1,
            tuple([7, 8, 9]): 1, tuple([9, 8, 7]): 1,
            tuple([1, 1, 1]): 1, tuple([2, 2, 2]): 1,
            tuple([3, 3, 3]): 1, tuple([4, 4, 4]): 1,
            tuple([5, 5, 5]): 1, tuple([6, 6, 6]): 1,
            tuple([7, 7, 7]): 1, tuple([8, 8, 8]): 1,
            tuple([9, 9, 9]): 1,
            tuple([2, 4, 6]): 1, tuple([6, 4, 2]): 1,
            tuple([3, 6, 9]): 1, tuple([9, 6, 3]): 1,
            tuple([1, 4, 7]): 1, tuple([7, 4, 1]): 1,
            tuple([2, 5, 8]): 1, tuple([8, 5, 2]): 1,
            tuple([4, 8, 6]): 1,
        }
        if len(numbers) >= 3 and tuple(numbers[:3]) in _hallucination_patterns:
            return "数字过于规律，请使用区别于顺序或重复数字的有效组合起卦。如果确实要用，可以混合其他数字一起。"
        # 检查是否包含过多相同数字
        from collections import Counter
        counts = Counter(numbers)
        most_common_count = counts.most_common(1)[0][1]
        if len(numbers) >= 3 and most_common_count >= len(numbers) - 1 and len(counts) <= 2:
            return "数字过于集中，请使用多样化的数字起卦。"
        # 从原始用户消息验证数字来源（防LLM瞎编）
        try:
            raw_msg = event.get_message_str() if event else ""
            if raw_msg:
                input_digits = "".join(str(n) for n in numbers)
                cleaned_msg = raw_msg.replace(" ", "").replace(",", "").replace("[", "").replace("]", "")
                if input_digits not in cleaned_msg:
                    logger.warning(f"[liuyao] 数字未在用户消息中找到: numbers={numbers}")
                    return "检测到数字并非来自用户输入，请重新提供明确的起卦数字，例如：224，测今日运势。"
        except Exception as e:
            logger.debug(f"[liuyao] 原始消息校验跳过: {e}")

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


@register("liuyao_plugin", author="南宫墨铭", desc="六爻数理占卜。输入数字自动起卦，输出评分卡片。", version="v1.2.0")
def register_plugin():
    return LiuYaoPlugin
