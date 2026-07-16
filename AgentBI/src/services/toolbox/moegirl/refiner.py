from __future__ import annotations

import re


AI_REFINEMENT_SYSTEM_PROMPT = """你是角色扮演资料编辑器。请把输入的萌娘百科 Markdown 清洗成适合大模型理解和扮演角色的资料。这是删除与重排任务，不是摘要任务。

保留并整理：
- 角色核心信息，例如身份、别名、年龄、生日、所属、外貌与重要设定
- 性格、动机、价值观、习惯、说话方式和人际关系
- 世界观相关背景、角色故事、剧情经历与成长变化
- 能体现人物形象的代表性台词、对话和重要事件

删除：
- 技能效果、技能数值、天赋、装备、玩法攻略和战斗机制
- 升级材料、突破材料、养成成本、获取方式和版本活动信息
- 配音演员、声优、CV、制作人员、外部评价等角色之外的元数据
- 页面导航、编辑提示、分类索引、重复内容和无关链接

对于应保留的部分，原则上逐段保留原文信息与时间顺序，尤其不能把长篇背景故事、剧情经历、关系变化或台词压缩成几句概述；输出很长也没有关系。只删除明确属于上述删除范围的内容，若同一段同时包含角色信息和玩法数据，只删玩法数据。

不要杜撰、补充或改写事实，也不要根据常识重写原文。可以修复 Markdown 层级、合并完全重复的段落，但不得为了简短而丢失角色扮演细节。只输出 Markdown 正文，不要解释处理过程，也不要使用代码围栏。"""


def build_ai_refinement_prompt(title: str, source_url: str, markdown: str) -> str:
    return (
        f"条目标题：{title}\n"
        f"来源：{source_url}\n\n"
        "请精炼以下已抓取的 Markdown：\n\n"
        f"{markdown}"
    )


def normalize_ai_markdown(text: str) -> str:
    normalized = text.strip()
    fenced = re.fullmatch(
        r"```(?:markdown|md)?\s*\n?(.*?)\n?```",
        normalized,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return (fenced.group(1) if fenced else normalized).strip()
