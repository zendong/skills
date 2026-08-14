#!/usr/bin/env python3
"""Prepare public Action packages 25-48 from the approved second-batch plan."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
WORKSPACE = SKILL_DIR.parents[2]
IMAGE_DIR = WORKSPACE / "private-skills/skills/pracmo-image/output/2026-08-11-public-action-batch-02"
OUTPUT_DIR = SKILL_DIR / "output"


def level(title: str, description: str, sessions: int, minutes: int, criterion: str, text: str) -> dict:
    return {
        "title": title,
        "description": description,
        "targetSessions": sessions,
        "estMinutes": minutes,
        "promotionCriterion": criterion,
        "contentBlocks": [{"blockType": "text", "textContent": text}],
    }


def generated(kind: str, instruction: str, question_type: str | None = None) -> dict:
    result = {"schemaVersion": 1, "type": kind, "instruction": instruction}
    if question_type:
        result["quickQa"] = {"questionType": question_type}
    return result


ITEMS = [
    {
        "id": 25, "slug": "life-easter-egg", "title": "今日一张生活彩蛋", "category": "creative",
        "tags": ["生活观察", "随手拍", "视觉日记", "3分钟", "创作素材"], "image": "25-life-easter-egg-source.png",
        "alt": "阳光经过玻璃在墙上投下彩虹，一片红叶落在光影中",
        "description": "每天发现并拍下一处容易错过的光影、颜色、排列或微小细节，再用一句话记录自己为什么停下来；一张照片和一句观察即算完成。",
        "icon": "camera", "color": "gold", "schedule": "daily", "config": {}, "deadline": "21:00", "completion": "rich_media", "mode": "self_directed",
    },
    {
        "id": 26, "slug": "three-minute-office-stretch", "title": "办公室三分钟舒展", "category": "fitness",
        "tags": ["久坐活动", "办公室运动", "舒展", "3分钟", "低强度"], "image": "26-office-stretch-source.png",
        "alt": "办公者在明亮工位旁进行温和的肩胸舒展",
        "description": "工作间隙用三分钟温和活动颈肩、胸背、手腕或髋踝，不追求幅度；完成一轮舒适动作即可，出现疼痛、眩晕或异常不适时立即停止。",
        "icon": "fitness", "color": "cyan", "schedule": "weekdays", "config": {}, "deadline": "15:30", "completion": "one_tap", "mode": "self_directed",
    },
    {
        "id": 27, "slug": "send-delayed-message", "title": "发出那条拖延的消息", "category": "work",
        "tags": ["沟通闭环", "拖延清理", "职场沟通", "5分钟", "行动力"], "image": "27-send-delayed-message-source.png",
        "alt": "手将纸飞机送向桌面另一侧，象征发出拖延已久的消息",
        "description": "选一条该确认、请求、拒绝或跟进的消息，先核对对象、事实和语气，再在五分钟内发送；不鼓励情绪激动时冲动沟通。",
        "icon": "chat", "color": "blue", "schedule": "weekdays", "config": {}, "deadline": "17:30", "completion": "one_tap", "mode": "self_directed",
    },
    {
        "id": 28, "slug": "say-one-sentence", "title": "今天用外语说一句", "category": "language",
        "tags": ["开口练习", "真实场景", "外语表达", "2分钟", "低门槛"], "image": "28-speak-foreign-language-source.png",
        "alt": "两个人在街边咖啡馆自然交谈",
        "description": "根据眼前场景，用目标语言主动说一句描述、请求、感受或计划；不是照稿朗读，允许简单和停顿，真正开口说出一句即算完成。",
        "icon": "microphone", "color": "coral", "schedule": "daily", "config": {}, "deadline": "20:30", "completion": "one_tap", "mode": "self_directed",
    },
    {
        "id": 29, "slug": "cool-shopping-cart", "title": "购物车冷静二十四小时", "category": "habit",
        "tags": ["理性消费", "延迟满足", "购物习惯", "愿望清单", "冲动管理"], "image": "29-cool-shopping-cart-source.png",
        "alt": "购物车停在沙漏旁，等待时间过去再做决定",
        "description": "把一件非必需品移入愿望清单，记住购买理由，至少隔二十四小时再决定；完成一次延迟决定即算完成，不评价合理的刚需消费。",
        "icon": "timer", "color": "orange", "schedule": "weekly_quota", "config": {"quota": 1}, "deadline": "21:00", "completion": "one_tap", "mode": "self_directed",
    },
    {
        "id": 30, "slug": "write-opinion-card", "title": "今天写一张观点卡", "category": "writing",
        "tags": ["观点写作", "卡片笔记", "结构表达", "8分钟", "思考记录"], "image": "30-opinion-card-source.png",
        "alt": "三张由红线连接的观点卡片摆在深绿色书桌上",
        "description": "围绕一个小问题写下自己的判断、主要理由和一个支持或反驳例子，形成一张可修订的观点卡；三部分完整即可，不要求首次就正确。",
        "icon": "writing", "color": "forest", "schedule": "weekly_quota", "config": {"quota": 3}, "deadline": "21:00", "completion": "text", "mode": "self_directed",
    },
    {
        "id": 31, "slug": "daily-cognitive-bias", "title": "每日一个认知偏差拆解", "category": "mind",
        "tags": ["认知偏差", "思维训练", "决策", "心理常识", "深度阅读"], "image": "31-cognitive-bias-source.png",
        "alt": "同一器物经过两块镜片呈现不同形态",
        "description": "每天用一个生活案例拆解一种认知偏差，理解直觉如何影响判断，并用一个自检问题把知识迁移到自己的决策中。",
        "icon": "meditate", "color": "purple", "schedule": "daily", "config": {}, "deadline": "20:30", "completion": "one_tap", "mode": "puki_generated",
        "generated": generated("reading", "生成一期中文认知偏差深度轻阅读。优先结合甲程目标和当前状态，从决策、社交、学习、消费或信息判断中选择一个偏差，避开近期偏差、情境和案例。正文700—1000字，结构为：具体生活情境、直觉答案、偏差如何形成、一个反例或适用边界、一个可当天使用的自检问题。区分稳定概念、合理推断和个体差异；不编造研究、数据、来源或引语，不把偏差标签用于诊断用户或他人。内容不能只下定义，必须展示判断链条和纠偏取舍。输出前检查主题单一、案例自包含、边界清楚且与近期摘要不重复。"),
    },
    {
        "id": 32, "slug": "world-system-cross-section", "title": "世界系统小剖面", "category": "study",
        "tags": ["系统思维", "跨学科", "原理拆解", "生活知识", "深度学习"], "image": "32-world-system-source.png",
        "alt": "城市的供水、能源与交通节点组成清晰的系统网络",
        "description": "每天拆开一个与生活有关的小系统，看清输入、节点、反馈、瓶颈与异常，逐步建立跨学科的系统思维。",
        "icon": "school", "color": "blue", "schedule": "weekdays", "config": {}, "deadline": "20:00", "completion": "one_tap", "mode": "puki_generated",
        "generated": generated("reading", "生成一期中文“世界系统小剖面”。结合甲程目标，从供水、物流、交通信号、垃圾处理、电网、通信、支付、天气预报等稳定日常系统中选一个，避开近期系统与案例。正文800—1200字，按输入、关键节点、反馈机制、常见瓶颈、某节点异常时会怎样、可迁移到其他系统的问题展开，并给出一条可画成简图的链路。明确这是帮助理解的简化模型，不冒充具体城市或机构真实流程；不编造实时数据、内部规则、来源或最新结论。输出前检查因果关系、反馈回路和边界是否清楚，术语是否给普通用户解释。"),
    },
    {
        "id": 33, "slug": "everyday-object-design-history", "title": "一件日用品的设计史", "category": "creative",
        "tags": ["设计史", "日用品", "产品观察", "创意灵感", "轻阅读"], "image": "33-everyday-design-history-source.png",
        "alt": "四把不同时代的椅子呈现日用品设计演变",
        "description": "从一件普通日用品的演变中观察问题、材料、功能和形态如何互相影响，把熟悉物品重新看成一连串设计取舍。",
        "icon": "design", "color": "clay", "schedule": "daily", "config": {}, "deadline": "20:30", "completion": "one_tap", "mode": "puki_generated",
        "generated": generated("reading", "生成一期中文日用品设计史轻阅读。结合甲程目标，从拉链、雨伞、椅子、铅笔、保温杯、剪刀、订书机等普通物品中选一个，避开近期物品与设计问题。正文600—900字，依次说明：最初要解决的问题、一次关键演变、材料与形态的取舍、一个失败或受限方向、今天可观察的细节。只采用稳定且可合理确认的历史信息；不确定的年代、人物或动机应省略或明确为推测，不编造首创者和品牌故事。不要只罗列年份，重点解释设计为何改变。输出前检查没学过设计的用户也能理解并完成观察任务。"),
    },
    {
        "id": 34, "slug": "name-one-emotion", "title": "今天认识一种情绪", "category": "mind",
        "tags": ["情绪词汇", "自我觉察", "心理常识", "每日一读", "温和练习"], "image": "34-name-emotion-source.png",
        "alt": "不同颜色和形态的透明玻璃投下细腻光影",
        "description": "每天认识一种常见情绪或混合感受，理解它可能出现的体验和需要，用更准确且不评判的词描述自己。",
        "icon": "heart", "color": "coral", "schedule": "daily", "config": {}, "deadline": "21:00", "completion": "one_tap", "mode": "puki_generated",
        "generated": generated("reading", "生成一期中文情绪词汇轻阅读。结合甲程目标，从常见且非诊断性的情绪或混合感受中选一个，避开近期词语。正文450—700字，结构为：这种感受可能是什么样、常见但非必然的触发、它可能在提醒或保护什么、两个容易混淆的相近情绪、一个不评判的自我观察句。使用“可能、有人会”等审慎措辞，不替用户断定原因，不进行心理诊断，不承诺治疗效果。不得编造研究、数据或专家引语。若主题可能引发明显不适，提醒用户可暂停并寻求合格专业支持。输出前检查语言温和、边界清楚且没有把情绪分成好坏。"),
    },
    {
        "id": 35, "slug": "daily-negotiation-strategy", "title": "每日一个谈判微策略", "category": "work",
        "tags": ["谈判", "沟通策略", "职场成长", "边界表达", "案例拆解"], "image": "35-negotiation-micro-strategy-source.png",
        "alt": "两方在桌面共同调整木块并搭出一座桥",
        "description": "每天从一个工作情境学习谈判策略，理解双方利益、条件交换和适用边界，再练习一句能立即迁移的表达。",
        "icon": "briefcase", "color": "orange", "schedule": "weekdays", "config": {}, "deadline": "18:30", "completion": "one_tap", "mode": "puki_generated",
        "generated": generated("reading", "生成一期中文谈判微策略深度轻阅读。结合甲程目标，从澄清利益、条件交换、替代方案、锚定、沉默、总结共识、边界表达中选一个，避开近期策略与场景。正文700—1000字，包含：策略目标、一个双方案例、双方真实关切、可用表达、适用边界、容易失效或伤害关系的情况、今日一句话练习。至少比较两种选择，不把强硬或获胜等同于好结果。禁止欺骗、威胁、操控、歧视或利用权力压迫，不编造企业内幕和实时政策。输出前检查是否兼顾效率、关系和信息透明，案例是否自包含。"),
    },
    {
        "id": 36, "slug": "daily-chart-literacy", "title": "每天读懂一张图表", "category": "reading",
        "tags": ["图表阅读", "数据素养", "信息辨别", "阅读训练", "每日一图"], "image": "36-read-a-chart-v2-source.png",
        "alt": "放大镜揭示柱状图与折线图的坐标和比例关系",
        "description": "每天阅读一份原创小数据和图表描述，练习查看坐标、口径、比例与限制，判断图表真正能说明什么。",
        "icon": "reading", "color": "mint", "schedule": "weekdays", "config": {}, "deadline": "20:00", "completion": "one_tap", "mode": "puki_generated",
        "generated": generated("reading", "生成一期中文图表素养轻阅读。结合甲程目标，创建一个不依赖现实新闻的原创小数据集，用Markdown表格清楚给出数据，并说明可想象成柱状图、折线图、散点图或比例图中的一种，避开近期图形与主题。正文500—800字，依次引导：先看标题之外的对象、单位和范围；读坐标或口径；识别主要关系；指出至少一个不能推出的结论；给出更诚实的重画建议。数据必须内部一致、计算简单可核对，不伪装成真实机构统计。输出前复算关键数字，检查是否区分相关与因果、绝对数与比例。"),
    },
    {
        "id": 37, "slug": "spot-false-logic", "title": "识破一句伪逻辑", "category": "study",
        "tags": ["逻辑训练", "论证分析", "每日一题", "批判思考", "单选题"], "image": "37-spot-false-logic-source.png",
        "alt": "一条推理链中断裂的红色环节被光线照亮",
        "description": "每天拆解一个原创短论证，识别错误因果、以偏概全或概念偷换，并通过文本证据说清漏洞在哪里。",
        "icon": "exam", "color": "blue", "schedule": "weekdays", "config": {}, "deadline": "20:00", "completion": "one_tap", "mode": "puki_generated",
        "generated": generated("quick_qa", "结合甲程目标生成逻辑辨析单选题。每题提供一个原创、具体、自包含的短论证，轮换错误因果、以偏概全、诉诸情绪、错误二分、概念偷换和样本偏差，避开近期结构与情境。设置4个长度和语法相近的选项，只有一个最准确地指出论证缺口；干扰项应是常见误判，不能靠措辞明显排除。解释须引用论证中的关键前提或跳步，并给一个能检验该漏洞的反例或补充问题。不要把“我不同意结论”当作逻辑错误，不涉及实时政治新闻或群体刻板印象。输出前检查答案唯一、术语准确且难度适配用户状态。", "single_choice"),
    },
    {
        "id": 38, "slug": "english-tone-thermometer", "title": "英语语气温度计", "category": "language",
        "tags": ["英语语气", "情境口语", "礼貌表达", "每日一题", "语言感觉"], "image": "38-english-tone-source.png",
        "alt": "两个人在冷暖光线交界处自然交谈",
        "description": "每天在具体关系和场景中比较几种英语表达，练习判断直接、自然、礼貌和过度正式之间的语气差别。",
        "icon": "chat", "color": "coral", "schedule": "daily", "config": {}, "deadline": "20:30", "completion": "one_tap", "mode": "puki_generated",
        "generated": generated("quick_qa", "生成A2—B2难度的英语语气单选题，并根据甲程目标与当前状态调节词汇和情境。每题给出双方关系、沟通目的和一个具体生活或工作场景，再提供4种语法基本正确但语气不同的英语说法，让用户选最合适的一项。轮换请求、拒绝、提醒、不同意见、道歉和确认等任务，避开近期句型。解释指出礼貌标记、直接程度、正式度和关系线索，并给一种可接受变体；承认地区和关系差异，不把单一表达说成绝对正确。避免罕见俚语、文化刻板印象和需要实时知识的场景。输出前检查答案有充分情境依据且四项长度接近。", "single_choice"),
    },
    {
        "id": 39, "slug": "one-minute-estimation", "title": "一分钟估算挑战", "category": "skill",
        "tags": ["费米估算", "数量感", "问题拆解", "一分钟挑战", "简答题"], "image": "39-one-minute-estimation-source.png",
        "alt": "计时器、量尺、积木与豆子组成桌面估算实验",
        "description": "每天用一个生活问题练习拆分变量、提出假设和判断数量级；答案不必精确，重点是形成可检查的推理链。",
        "icon": "terminal", "color": "gold", "schedule": "weekdays", "config": {}, "deadline": "20:00", "completion": "one_tap", "mode": "puki_generated",
        "generated": generated("quick_qa", "结合甲程目标生成费米估算简答题。每题选择一个普通用户可理解、无需实时数据的生活问题，提供必要边界，要求用户写出关键假设、分解步骤和合理数量级。轮换空间、时间、人数、容量、速度和资源消耗等变量，避开近期题目。参考答案展示一种透明的拆解方法，逐步计算并指出最敏感的假设；评分接受不同但自洽的路径，重点看单位、数量级和推理链，不要求唯一数字。不得把虚构结果包装成真实统计，不出医疗剂量、投资收益或高风险工程估算。输出前复算算术，确认信息足够且能在约一分钟形成初步方案。", "short_answer"),
    },
    {
        "id": 40, "slug": "find-hidden-stance", "title": "这段话藏了什么立场", "category": "reading",
        "tags": ["媒介素养", "立场识别", "深度阅读", "信息辨别", "单选题"], "image": "40-hidden-stance-source.png",
        "alt": "红色观察窗口揭示同一场景被不同纸张框选后的差异",
        "description": "每天阅读一段原创短文，从选择性信息、情绪词和预设前提中判断文本立场，同时区分证据与无法确定的动机。",
        "icon": "book", "color": "clay", "schedule": "weekdays", "config": {}, "deadline": "20:30", "completion": "one_tap", "mode": "puki_generated",
        "generated": generated("quick_qa", "结合甲程目标生成中文立场识别单选题。每题写一段180—280字原创短文，围绕低风险日常或公共议题，通过选择性信息、情绪词、模糊主体、预设前提或框架顺序体现一种可由文本支持的立场，避开近期主题。提供4个相近选项，唯一最佳答案必须由具体措辞或信息安排支持；干扰项体现过度推断、把事实当评价、猜测人格或忽略限定词。解释引用文本线索，并明确哪些作者动机仍无法确定。不要使用实时新闻、政治动员、群体刻板印象或受版权保护原文。输出前检查文本自包含、答案唯一且不是靠常识站队。", "single_choice"),
    },
    {
        "id": 41, "slug": "headline-makeover-arena", "title": "标题改造擂台", "category": "writing",
        "tags": ["标题写作", "文案练习", "表达优化", "改写挑战", "简答题"], "image": "41-headline-arena-source.png",
        "alt": "三张空白标题卡在擂台构图中接受铅笔改造",
        "description": "每天把一个空泛或夸张标题改得更具体、更诚实、更吸引人，并用信息匹配和不过度承诺来检查结果。",
        "icon": "writing", "color": "coral", "schedule": "weekly_quota", "config": {"quota": 3}, "deadline": "21:00", "completion": "one_tap", "mode": "puki_generated",
        "generated": generated("quick_qa", "结合甲程目标生成中文标题改写简答题。每题提供一段80—160字原创内容摘要、发布场景和一个存在空泛、信息遗漏、语气错位或标题党问题的原标题，要求用户改写。轮换文章、报告、邮件、分享和作品说明等场景，避开近期主题。评分维度为具体性、与内容匹配、吸引力、语气适合和不过度承诺；参考答案提供3种不同方向及各自取舍，接受其他满足标准的表达，不要求逐字一致。不得使用真实人物、品牌或实时事件，不鼓励恐吓和夸大成效。输出前检查摘要足以支持改写、原标题问题清晰且答案不是单纯变短。", "short_answer"),
    },
    {
        "id": 42, "slug": "meeting-rescue-response", "title": "会议救场怎么接", "category": "work",
        "tags": ["会议沟通", "临场反应", "职场场景", "沟通判断", "单选题"], "image": "42-meeting-rescue-source.png",
        "alt": "团队在会议卡点中通过三张便签重新聚焦下一步",
        "description": "每天处理一个会议跑题、冷场、分歧或信息不足场景，选择一句兼顾目标、关系和信息完整性的临场回应。",
        "icon": "presentation", "color": "blue", "schedule": "weekdays", "config": {}, "deadline": "17:30", "completion": "one_tap", "mode": "puki_generated",
        "generated": generated("quick_qa", "生成中文会议临场回应单选题，并结合甲程目标与当前状态调整复杂度。每题给出会议目标、用户角色、关系边界和当前卡点，轮换跑题、冷场、分歧升级、信息不足、时间将尽和责任模糊等情境。提供4句自然回应，唯一最佳项应在澄清事实、回扣目标、保护关系和推动下一步之间取得更好平衡；错误项体现暴力打断、含糊拖延、越权承诺或回避问题。解释比较关键取舍，并给一个可替换表达。不得假设用户有管理权，不生成羞辱、操控或歧视话术。输出前检查角色权限明确、答案唯一且选项都像真实会议语言。", "single_choice"),
    },
]


FOLLOW_ITEMS = [
    {
        "id": 43, "slug": "three-quick-dishes", "title": "从零做出三道快手菜", "category": "skill",
        "tags": ["快手菜", "做饭入门", "生活技能", "跟练计划", "零基础"], "image": "43-three-quick-dishes-source.png",
        "alt": "三道适合新手完成的家常快手菜摆在明亮餐桌上", "icon": "spark", "color": "orange",
        "description": "用五个可重复练阶掌握厨房安全、免火组合、一锅完成和基础翻炒，最终形成三道能按设备与饮食限制调整的快手菜。",
        "schedule": "weekly_quota", "config": {"quota": 3}, "deadline": "19:30",
        "levels": [
            level("安全备菜", "先建立干净、稳定、不过度追求速度的备菜流程。", 3, 12, "能独立完成洗手、台面清理、稳定砧板、食材清洗与生熟分开，并在结束后关闭设备。", "开始前洗手并清理台面，用湿布或防滑垫固定砧板；只选择熟悉、常见的食材和完整工具。练习把食材、调味、垃圾容器按使用顺序摆好，生熟食材和工具分开。刀具始终在视线内，切配动作放慢，结束后确认火源、电源和水龙头。未成年人需由监护人陪同；不处理野生食材、来源不明食材或高风险生食。"),
            level("免火组合", "不用开火完成一道有主食、蛋白质和蔬果的简单组合。", 3, 10, "能按一份主食、一份可直接食用蛋白质和一份蔬果完成组合，并说清保质与过敏原注意事项。", "选择包装标明可直接食用且在保质期内的食材，例如全麦面包、酸奶、熟制豆制品、罐装豆类或洗净蔬果。用酸、咸、香和少量油脂调出一种简单味型，先少量添加再尝味。检查个人过敏原和储存要求，冷藏食材不要长时间留在室温。完成一份颜色和口感有变化的冷拌或组合餐。"),
            level("一锅完成", "用一只锅完成一份有明确先后顺序的热食。", 4, 20, "能在不过度拥挤锅具的情况下完成一次煮制，食材熟度合适、设备已关闭且台面恢复安全。", "选择粥、面、汤饭或蔬菜豆腐锅等低门槛方案。先阅读食材包装的加热和保存说明，再按耐煮到易熟的顺序下锅；锅柄朝内，水量不超过安全容量。试味时使用独立小勺，避免直接接触蒸汽。肉、蛋和海鲜必须充分加热；不确定熟度时使用食品温度计或选择更保守的熟制方案。"),
            level("基础翻炒", "学习控制锅温、少量分批和安全翻动。", 5, 20, "能完成一道不粘连、不过度焦糊的蔬菜或熟制蛋白质翻炒，并能在失控前主动调低或关闭火力。", "先把所有食材切配完成再开火，锅具保持干燥，油量适中。使用中小火练习判断锅温，先下较难熟食材，分批加入并用锅铲翻动，不做抛锅动作。油烟明显或食材快速焦黑时立即调低或关闭火力。使用来源可靠、适合彻底加热的食材；避免把冷冻含水食材直接投入热油。"),
            level("三菜自由组合", "把前三阶方法组合成自己的三道快手菜清单。", 6, 30, "能在三十分钟左右安全完成三道结构不同的菜，并写下设备、食材与时间的可替代方案。", "从免火组合、一锅完成和基础翻炒中各选一道，先列出共同食材和操作顺序，减少重复清洗与等待。根据现有设备、饮食限制、过敏原和可用时间替换食材，不追求复杂摆盘。完成后记录每道菜最容易失控的一步和下次调整。出现火情时先切断热源，油锅起火不要用水，无法安全处理时立即撤离并求助。"),
        ],
        "checkpoints": [(1, "完成第一道菜", False), (3, "掌握基础热加工", True), (4, "形成三道菜清单", True)],
    },
    {
        "id": 44, "slug": "balance-challenge", "title": "平衡力闯关计划", "category": "fitness",
        "tags": ["平衡训练", "身体控制", "低冲击", "闯关", "居家运动"], "image": "44-balance-challenge-source.png",
        "alt": "练习者在稳固墙面和椅子旁安全进行平衡训练", "icon": "fitness", "color": "mint",
        "description": "在稳固支撑物旁用五个练阶，从重心转移进阶到低幅动态平衡；动作稳定、无疼痛并能随时扶稳后再升级。",
        "schedule": "weekly_quota", "config": {"quota": 3}, "deadline": "20:00",
        "levels": [
            level("双脚重心转移", "在双脚着地时感受左右和前后的重心变化。", 4, 6, "能在不抓紧支撑物的情况下完成两轮缓慢转移，脚掌持续贴地且没有明显晃动。", "穿防滑鞋或赤脚站在平整地面，身旁放稳固墙面或不会滑动的重家具。双脚与髋同宽，目视前方，缓慢把重心移向左、右、前、后，每个方向停留两次呼吸。膝盖保持放松，不闭眼、不站在软垫上。出现眩晕、疼痛或明显不稳时立即坐下休息。"),
            level("扶稳单脚站", "在充分扶持下建立单脚承重感觉。", 5, 7, "左右脚都能轻松完成3组，每组10—20秒，扶持手没有用力拉扯且呼吸自然。", "单手扶住稳固支撑，另一脚只离地少许，支撑腿膝盖微屈，骨盆保持大致水平。每侧做3次，每次10—20秒；脚踝剧烈晃动时缩短时间或增加扶持。不要追求抬腿高度，不在楼梯、湿滑或拥挤环境练习。"),
            level("轻触支撑", "逐步减少手部用力，让身体承担更多控制。", 5, 8, "能用一到两根手指轻触支撑完成每侧20秒，并能在失稳前主动扶住。", "重复单脚站，但把抓握改为手掌轻放，再逐步改为指尖轻触。始终让支撑物在伸手可及范围内，练习重点是主动恢复，而不是硬撑到失衡。每次只减少一种帮助；若当天疲劳、饮酒、服用影响平衡的药物或身体不适，停留在更安全练阶或跳过。"),
            level("脚跟接脚尖走", "在一条短直线上练习窄支撑步行。", 6, 8, "能沿墙完成往返两次，步幅稳定、视线平视且无需持续抓墙。", "沿干净墙面留出两到三米路线，一只脚脚跟靠近另一只脚脚尖缓慢前行，手臂自然张开，目视前方固定点。先用手掌轻触墙，再逐步减少接触。不要在交通区域、台阶边或有宠物穿行处练习。转身时用普通小步，不做快速旋转。"),
            level("低幅动态平衡", "在安全范围内加入小步、触点和方向变化。", 8, 10, "能按前、侧、后三个方向各完成5次轻触，支撑腿稳定并能随时回到双脚站立。", "站在支撑物旁，把一只脚向前、侧、后方轻点地面再收回，每个方向5次，幅度以支撑腿稳定为限。随后尝试慢速跨过一条贴地软带，不使用高障碍。保持呼吸，动作不追求速度。既往跌倒、神经系统或前庭问题、孕期或特殊健康情况应先咨询合格专业人士。"),
        ],
        "checkpoints": [(1, "单脚承重入门", False), (3, "窄支撑步行稳定", True), (4, "完成动态平衡闯关", True)],
    },
    {
        "id": 45, "slug": "phone-boundary-lab", "title": "手机边界实验室", "category": "habit",
        "tags": ["手机习惯", "注意力", "环境设计", "行为实验", "跟练计划"], "image": "45-phone-boundary-lab-source.png",
        "alt": "手机停在发光边界之外，圈内摆着书和计时器", "icon": "habit", "color": "cyan",
        "description": "把无意识刷手机当成可观察的行为实验，从识别触发到设计空间与替代动作，逐步留下真正适合自己的边界。",
        "schedule": "daily", "config": {}, "deadline": "21:30",
        "levels": [
            level("找到一个高频触发", "只观察一个最常发生的拿手机时刻。", 3, 4, "能连续三次在拿起手机后说出当时的地点、前一个动作和本来想做什么。", "选择一个最常出现的场景，例如起床后、等电梯、工作卡住或睡前。每次拿起手机后只做简短记录：时间、地点、前一个动作、打开了什么、本来想做什么。不要评价自控力，也不要求立刻减少使用；本阶目标只是把模糊习惯变成可观察线索。"),
            level("减少一个入口", "用环境调整降低一次无意识打开的概率。", 4, 5, "一种入口调整连续保留四次，并能说出它减少了哪一步自动操作。", "只选一个入口做实验：关闭一个非必要通知、把高频应用移出首屏、退出自动登录或取消桌面红点。不要关闭紧急联系人、医疗、工作值班等必要通知。每次实验后观察自己是否转向了另一个入口；如果造成重要信息遗漏，立即恢复并选择更温和的设置。"),
            level("建立无手机小空间", "让一个短场景拥有清晰的物理边界。", 5, 10, "能在选定场景连续完成五次，把手机放在伸手之外且没有影响必要联络。", "选择一个十分钟左右的场景，例如用餐、洗澡、读两页书或整理桌面。提前告知必要联系人，设置可接受的紧急联络方式，然后把手机放在固定位置。边界只覆盖这个场景，不扩张到全天。完成后记录注意力去了哪里，而不是只记录是否忍住。"),
            level("准备替代动作", "为触发时刻提供一个更容易开始的替代选项。", 5, 8, "至少找到一个能在同一触发场景中自然完成、且不会变成新负担的替代动作。", "为选定触发准备一个同样低成本的动作，例如喝水、看窗外、伸展、写一句待办、与身边人说一句话或读一小段纸质内容。触发出现时先做替代动作，再决定是否使用手机；不是强制禁止。比较不同替代的难度和即时反馈，只保留真正顺手的一个。"),
            level("形成个人边界", "把有效实验组合成可长期调整的个人规则。", 7, 10, "能写出一条包含场景、边界、例外和恢复方式的规则，并在中断后重新执行。", "回看前四阶，只选择一个有效入口调整、一个小空间和一个替代动作，写成“在什么场景、手机放哪里、什么情况例外、打破后如何恢复”。规则应服务睡眠、关系或专注等具体需要，不把使用时长等同于个人价值。每周允许修改一次；若规则持续造成焦虑或影响必要生活，缩小或停止实验。"),
        ],
        "checkpoints": [(1, "完成入口实验", False), (3, "找到有效替代", True), (4, "形成个人边界", True)],
    },
    {
        "id": 46, "slug": "creative-constraint-camp", "title": "创意限制挑战营", "category": "creative",
        "tags": ["创意挑战", "限制创作", "灵感训练", "作品练习", "跟练计划"], "image": "46-creative-constraints-source.png",
        "alt": "纸张、几何形与旧物在限制条件下组成多件小作品", "icon": "design", "color": "gold",
        "description": "用形状、颜色、随机词、旧物和同题多版等六个练阶，把限制变成创作发动机，连续留下可比较的小作品。",
        "schedule": "weekly_quota", "config": {"quota": 3}, "deadline": "21:00",
        "levels": [
            level("只用一种形状", "用单一形状探索大小、重复、旋转和留白。", 3, 12, "能完成3个构图，并指出哪一次变化最影响画面节奏。", "选择圆、三角或矩形中的一种，用纸片、笔画或数字工具做3个小构图。只能改变大小、数量、旋转和位置，不增加第二种形状。每版限制在十分钟内，完成后写一句观察：哪个变化制造了重点或节奏。作品不要求精致，重点是比较。"),
            level("只用两种颜色", "在有限色彩中练习主次、对比与面积关系。", 4, 15, "能用同一双色方案完成3版，并说清主色、强调色和面积取舍。", "任选两种有足够明度或色相差异的颜色，可额外使用纸张本色。围绕同一简单主题做3版：大面积平衡、强烈对比、局部强调。避免只用滤镜换色；必须调整颜色所占面积或位置。记录哪一版在小尺寸下仍清楚。"),
            level("三个随机词", "把互不相关的词连接成一个可理解的点子。", 4, 20, "能为同一组三词提出至少5个连接方向，并完成其中1个小作品。", "随机选择一个物件、一个动作和一种情绪，例如“钥匙、漂浮、安心”。先写5个不同连接，不在第一个点子上停下；再选一个做成150字以内短文、草图、照片摆拍或小手作。不要直接模仿现成角色、品牌或在世创作者独特风格。"),
            level("旧物换用途", "从材料属性出发，为普通旧物提出新用法。", 5, 25, "能根据硬度、形状、连接方式等属性提出3种用途，并安全完成1个原型。", "选择清洁、无尖锐破损、无化学污染的普通旧物，先列出材质、形状、强度和可连接方式，再提出3种新用途并做一个低风险原型。不拆解电池、电器、压力容器或不明材料，不把装饰原型用于承重、食品接触或儿童安全场景。"),
            level("同题做三版", "用同一主题刻意探索不同表达方向。", 5, 30, "能完成写实、夸张、极简或其他三种明确不同的版本，并比较各自适用场景。", "选择一个足够小的主题，先定义三种差异方向，例如写实、夸张、极简，或温暖、冷静、幽默。三版使用同样时长和画布，避免只换颜色。完成后从信息清楚、情绪、记忆点和制作成本四项比较，不急于选唯一最好。"),
            level("设计个人限制", "根据自己的惯性弱点组合一套可复用挑战。", 6, 30, "能写出包含目标、允许项、禁止项、时间和验收标准的限制，并完成两次不同主题作品。", "回看前五阶，找出自己最容易陷入的惯性，例如元素过多、迟迟不完成或总用同一种构图。设计一套限制：本次要练什么、允许什么、禁止什么、用时多久、怎样算完成。连续用于两个不同主题，再判断限制是在激发选择还是只增加负担；无效限制可以修改。"),
        ],
        "checkpoints": [(2, "完成随机词作品", False), (4, "完成同题三版", True), (5, "形成个人挑战规则", True)],
    },
    {
        "id": 47, "slug": "emotional-granularity", "title": "情绪颗粒度训练", "category": "mind",
        "tags": ["情绪颗粒度", "自我觉察", "情绪词典", "心智训练", "跟练计划"], "image": "47-emotional-granularity-source.png",
        "alt": "人物面孔经过不同颜色玻璃呈现细微情绪层次", "icon": "meditate", "color": "purple",
        "description": "用六个练阶从愉快度与能量开始，逐步分辨相近情绪、身体线索、情境与需要，建立个人情绪词典。",
        "schedule": "daily", "config": {}, "deadline": "21:30",
        "levels": [
            level("愉快度与能量", "先用两个简单维度描述当下状态。", 4, 4, "能连续四次用愉快或不愉快、能量高或低描述当下，并允许回答不确定。", "停下来观察一分钟，分别判断此刻更接近愉快还是不愉快、能量更高还是更低，可使用中间或不确定。写下一个可观察依据，例如呼吸、动作速度或注意力方向。不要解释人格，也不要求改变状态。本练习只帮助描述，不替代专业心理评估。"),
            level("从大类到具体词", "把模糊的好或不好展开成较具体的词。", 5, 6, "能为至少三次状态各列出2—3个候选词，并选出暂时最贴近的一个。", "从开心、难过、生气、害怕、惊讶、厌恶等大类开始，再列出2—3个更具体的候选，例如安心、满足、失落、委屈、烦躁或担忧。使用“我暂时更接近”而不是“我就是”。如果没有合适词，可以描述感受而不强行命名。"),
            level("分辨相近情绪", "通过对象、期待和行动倾向区分相近词。", 5, 8, "能比较一组相近词，并说出对象、未满足期待或行动倾向中的至少一个差异。", "每次选择一组相近词，例如紧张与兴奋、愧疚与羞耻、嫉妒与羡慕、孤独与独处。分别问：感受指向谁或什么、我原本期待什么、身体想靠近还是远离、我想修复什么。答案可以重叠，不把词典定义当成唯一标准。"),
            level("加入身体线索", "观察身体变化，但不把单一感觉直接等同于某种情绪。", 5, 8, "能记录至少三个身体线索，并同时列出两种可能解释而不急于下结论。", "从呼吸、心跳、肩颈、胃部、手部温度和动作冲动中选择可安全观察的线索。写下感觉的位置、强度和变化，再列出两种可能解释，例如疲劳、环境温度或某种情绪。身体症状明显、持续或令人担忧时，应停止练习并寻求合格医疗帮助，不自行诊断。"),
            level("连接情境与需要", "把感受放回具体情境，探索可能的需要和选择。", 6, 10, "能用“发生了什么—我感到什么—我可能在意什么—下一步可选什么”完成四句记录。", "只描述一个具体事件，区分可观察事实与自己的解释。写下最贴近的情绪候选，再探索自己可能在意的安全、尊重、连接、掌控、休息或成长等需要，最后列出一个低风险选择。需要不是对他人的命令；不要用情绪词证明自己一定正确。"),
            level("建立个人情绪词典", "整理自己的常用词、线索、情境和有效回应。", 8, 12, "能形成至少12个词条，每个包含个人含义、常见线索、易混淆词和一种温和回应。", "回看前五阶，从真实记录中选择至少12个常见词。每个词写下：它对我通常意味着什么、常见但非必然的身体或情境线索、容易混淆的词、一个可选择的温和回应。词典允许随经历修改，不用于给他人贴标签。若练习引发强烈或持续不适，可以暂停并联系可信任的人或合格专业人士。"),
        ],
        "checkpoints": [(2, "能分辨相近情绪", False), (4, "连接情境与需要", True), (5, "形成个人情绪词典", True)],
    },
    {
        "id": 48, "slug": "travel-english-route", "title": "旅行英语生存路线", "category": "language",
        "tags": ["旅行英语", "情境口语", "角色演练", "生存表达", "跟练计划"], "image": "48-travel-english-route-source.png",
        "alt": "旅行者在车站服务台自然询问路线", "icon": "walk", "color": "blue",
        "description": "沿问路、交通、入住、点餐、购物和求助六个练阶，练习表达意图、听不懂时修复对话，并完成现实角色演练。",
        "schedule": "weekly_quota", "config": {"quota": 3}, "deadline": "20:30",
        "levels": [
            level("问路", "说清目的地，并确认方向和地标。", 4, 8, "能不看稿完成一次问路、听懂或确认前两个步骤，并在没听懂时请求重复。", "核心意图：礼貌引起注意、说明目的地、确认第一个方向。练习“Excuse me, how can I get to ...?”和“Is it near ...?”，再加入修复句“Could you say that again more slowly?”。角色演练时一人给两步路线，另一人复述第一步。专有地名可替换，不依赖特定国家规则。"),
            level("交通与时间", "询问线路、出发时间、站台和换乘。", 5, 10, "能完成一次包含线路、时间和一次确认的对话，并正确复述关键数字。", "练习询问“Which line should I take?”“What time does it leave?”和“Do I need to change?”。听到数字后用“So, platform ... at ...?”复述确认。角色演练中加入一次线路变化或延误，但不编造真实时刻表；真实出行必须以官方现场信息为准。"),
            level("入住", "完成预订确认、房间需求和基本问题反馈。", 5, 12, "能说明姓名或预订信息、提出一个合理需求，并在信息不符时礼貌澄清。", "练习“ I have a reservation under ...”“Could I have ...?”和“I think there may be a mistake with ...”。角色演练轮换提前入住、安静房间、早餐时间和设施问题。只提供完成对话所需的虚构信息，不在练习中填写真实证件号、住址或支付信息。"),
            level("点餐", "询问菜品、饮食限制、数量和结账。", 5, 12, "能完成一次点餐，说明一种真实饮食限制或偏好，并确认关键内容。", "练习询问主要食材、辣度、份量和结账方式，例如“What is this made with?”“I cannot eat ...”和“Could we have the bill, please?”。角色演练中区分偏好与过敏；真实严重过敏不能只依赖语言练习或机器翻译，应使用当地可靠过敏卡并向商家明确确认。"),
            level("购物与退换", "询问尺寸、价格、试用条件和退换规则。", 5, 12, "能在不默认规则的情况下问清两项条件，并礼貌表达购买、再考虑或退换请求。", "练习“Do you have this in ...?”“Could I try it on?”“What is your return policy?”和“I'd like to think about it.”。角色演练加入缺货、尺寸不合或商品问题。不要假设所有地区都允许无理由退换，真实决定以商家书面规则为准。"),
            level("突发求助", "在压力下用短句说明位置、问题和需要。", 7, 10, "能用三句以内说清自己在哪里、发生了什么、需要哪种帮助，并能理解一个澄清问题。", "优先练习简短清楚的表达：“I need help.”“I'm at ...”“My ... is missing.”“Please call ...”。角色演练覆盖走失、物品遗失、错过交通和身体不适，但不模拟危险行为。真实紧急情况应优先联系当地官方紧急服务、现场工作人员或可信任的人；不要依赖本练习替代求助。"),
        ],
        "checkpoints": [(1, "完成交通对话", False), (3, "完成旅行日常任务", True), (5, "具备基础求助表达", True)],
    },
]


def build_payload(item: dict) -> dict:
    template = {
        "title": item["title"],
        "description": item["description"],
        "iconCode": item["icon"],
        "colorCode": item["color"],
        "scheduleType": item["schedule"],
        "scheduleConfigJson": json.dumps(item["config"], ensure_ascii=False, separators=(",", ":")),
        "timezone": "Asia/Shanghai",
        "deadlineLocalTime": item["deadline"],
        "gracePolicy": "none",
        "completionMode": item.get("completion", "one_tap"),
        "contentMode": item.get("mode", "follow_along"),
    }
    if "generated" in item:
        template["generatedContentConfig"] = item["generated"]
    if "levels" in item:
        template["followPlan"] = {
            "afterCompletionPolicy": "continue_last_level",
            "levels": item["levels"],
            "checkpoints": [
                {"levelIndex": index, "title": title, "description": title, "isKey": is_key}
                for index, title, is_key in item["checkpoints"]
            ],
        }
    return {
        "schemaVersion": "pracmo-public-action@v2",
        "clientRequestId": f"public-action-{item['id']:02d}-{item['slug']}-20260812-v1",
        "catalog": {
            "category": item["category"],
            "tags": item["tags"],
            "coverImage": {"localPath": "source-assets/cover.png", "alt": item["alt"]},
        },
        "template": template,
        "assets": [{"assetId": "cover", "role": "cover", "localPath": "source-assets/cover.png", "alt": item["alt"]}],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    items = ITEMS + FOLLOW_ITEMS
    if [item["id"] for item in items] != list(range(25, 49)):
        raise SystemExit("second batch IDs must be exactly 25-48")
    for item in items:
        action_dir = args.output_dir / f"{item['id']:02d}-{item['slug']}"
        source_dir = action_dir / "source-assets"
        source_dir.mkdir(parents=True, exist_ok=True)
        source = IMAGE_DIR / item["image"]
        if not source.is_file():
            raise SystemExit(f"missing cover source: {source}")
        shutil.copy2(source, source_dir / "cover.png")
        payload = build_payload(item)
        (action_dir / "public-action.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps({"prepared": len(items), "range": "25-48", "outputDir": str(args.output_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
