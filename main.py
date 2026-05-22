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
        new = r'\1
        session_id_str = str(session_id) if session_id is not None else ""
        session_id_int = int(session_id_str) if session_id_str.isdigit() else None'
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
    def __init__(self, context: Context):
        super().__init__(context)
        _patch_core_send()
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


@register("liuyao_plugin", author="南宫墨铭", desc="六爻数理占卜。输入数字自动起卦，输出评分卡片。", version="v1.1.0")
def register_plugin():
    return LiuYaoPlugin
