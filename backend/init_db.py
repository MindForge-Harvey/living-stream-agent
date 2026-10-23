"""
数据库初始化脚本
用于创建数据库表和默认管理员账号
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine, Base, SessionLocal
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.models import Admin, User, ScriptTemplate, ScoringConfig, SuggestedQuestion


# 默认打分配置
DEFAULT_SCORING_CONFIG = {
    "name": "标准打分配置",
    "dimensions": [
        {
            "name": "吸引力",
            "key": "attention",
            "description": "开场即抓住注意力，有强烈好奇心驱动",
            "scores": {
                "9-10": "开场即抓住注意力，有强烈好奇心驱动，用户停留意愿极高",
                "7-8": "开场较吸引人，有一定好奇心，用户愿意继续观看",
                "5-6": "开场普通，缺乏亮点，用户可能继续观看但容易流失",
                "3-4": "开场平淡，缺乏吸引力，用户容易划走",
                "1-2": "开场无趣，完全无法吸引用户"
            }
        },
        {
            "name": "逻辑性",
            "key": "logic",
            "description": "产品介绍层次分明，卖点递进清晰",
            "scores": {
                "9-10": "产品介绍层次分明，卖点递进清晰，从痛点→方案→证据→行动完美衔接",
                "7-8": "逻辑较清晰，卖点有条理，过渡自然",
                "5-6": "逻辑基本通顺，但部分衔接生硬",
                "3-4": "逻辑混乱，卖点堆砌，缺乏条理",
                "1-2": "完全没有逻辑，东一句西一句"
            }
        },
        {
            "name": "感染力",
            "key": "emotion",
            "description": "情感充沛，能引发强烈共鸣",
            "scores": {
                "9-10": "情感充沛，能引发强烈共鸣，让用户产生\"我也想要\"的冲动",
                "7-8": "有一定情感表达，能打动部分用户",
                "5-6": "情感表达一般，缺乏感染力",
                "3-4": "语气平淡，像念稿，缺乏情感",
                "1-2": "完全无感情，机械式朗读"
            }
        },
        {
            "name": "专业性",
            "key": "professional",
            "description": "产品知识准确，数据详实，有权威背书",
            "scores": {
                "9-10": "产品知识准确，数据详实，有权威背书，用户信任度极高",
                "7-8": "产品介绍较专业，有一定数据支撑",
                "5-6": "产品介绍基本准确，但缺乏深度",
                "3-4": "产品介绍有明显错误或夸大",
                "1-2": "产品介绍错误百出，完全不专业"
            }
        }
    ],
    "prompt_template": """你是一位专业的直播话术评审专家。请对用户提供的直播话术进行严格评分。

## 评分维度（每项1-10分）

### 1. 吸引力（Attention）
- **9-10分**：开场即抓住注意力，有强烈好奇心驱动，用户停留意愿极高
- **7-8分**：开场较吸引人，有一定好奇心，用户愿意继续观看
- **5-6分**：开场普通，缺乏亮点，用户可能继续观看但容易流失
- **3-4分**：开场平淡，缺乏吸引力，用户容易划走
- **1-2分**：开场无趣，完全无法吸引用户

### 2. 逻辑性（Logic）
- **9-10分**：产品介绍层次分明，卖点递进清晰，从痛点→方案→证据→行动完美衔接
- **7-8分**：逻辑较清晰，卖点有条理，过渡自然
- **5-6分**：逻辑基本通顺，但部分衔接生硬
- **3-4分**：逻辑混乱，卖点堆砌，缺乏条理
- **1-2分**：完全没有逻辑，东一句西一句

### 3. 感染力（Emotion）
- **9-10分**：情感充沛，能引发强烈共鸣，让用户产生"我也想要"的冲动
- **7-8分**：有一定情感表达，能打动部分用户
- **5-6分**：情感表达一般，缺乏感染力
- **3-4分**：语气平淡，像念稿，缺乏情感
- **1-2分**：完全无感情，机械式朗读

### 4. 专业性（Professional）
- **9-10分**：产品知识准确，数据详实，有权威背书，用户信任度极高
- **7-8分**：产品介绍较专业，有一定数据支撑
- **5-6分**：产品介绍基本准确，但缺乏深度
- **3-4分**：产品介绍有明显错误或夸大
- **1-2分**：产品介绍错误百出，完全不专业

## 输出格式

请严格按照以下格式输出评分结果：

### 评分总览
| 维度 | 分数 | 评语 |
|------|------|------|
| 吸引力 | X/10 | 一句话评语 |
| 逻辑性 | X/10 | 一句话评语 |
| 感染力 | X/10 | 一句话评语 |
| 专业性 | X/10 | 一句话评语 |
| **综合** | **X/10** | - |

### 优点
- 列出2-3个具体优点

### 待改进
- 列出2-3个具体改进建议

### 优化方向
- 给出1-2个最关键的优化方向

直接给出评分结果，不要多余的解释。"""
}

# 预置模板
PRESET_TEMPLATES = [
    {
        "name": "移动宽带套餐直播脚本",
        "category": "preset",
        "product_type": "通信",
        "description": "适用于移动宽带套餐推广的直播脚本模板",
        "template_content": """## 开场白（30秒）
"家人们，宽带选得好，上网没烦恼！今天给大家带来移动宽带超值套餐，网速快、价格低、服务好！"

## 产品介绍（2分钟）
1. **套餐内容**
   - 带宽：[100M/200M/500M/1000M]
   - 流量：[是否含手机流量]
   - 通话：[是否含通话时长]

2. **核心卖点**
   - 网速稳定：光纤入户，玩游戏不卡顿
   - 价格实惠：月费低至[X]元，比营业厅更优惠
   - 安装便捷：预约后[X]天内上门安装

3. **适用场景**
   - 家庭上网：看视频、刷抖音不缓冲
   - 居家办公：视频会议流畅稳定
   - 游戏娱乐：低延迟，团战不掉线

## 互动环节（1分钟）
"家里宽带到期的扣1，想换宽带的扣2！"
"觉得网速重要还是价格重要的？网速扣A，价格扣B"

## 促单话术（1分钟）
"今天直播间下单，首年月费只要[X]元，还送[路由器/话费]！"
"名额有限，只有[X]个名额，抢完恢复原价！"
"现在下单，明天就能安排上门安装！"

## 结尾（30秒）
"宽带选移动，生活更轻松！赶紧下单，享受飞一般的网速体验！记得关注我们，更多优惠等着你！"
"""
    }
]

DEFAULT_SUGGESTED_QUESTIONS = [
    "帮我生成一段护肤品的直播脚本",
    "对以下直播话术进行打分",
    "优化这段直播话术",
]


def init_database():
    """初始化数据库"""
    print("正在创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成")

    # 创建默认管理员和超级管理员
    db = SessionLocal()
    try:
        # 检查是否已有超级管理员
        super_admin = db.query(Admin).filter(Admin.is_superadmin == True).first()
        if not super_admin:
            if not settings.SUPER_ADMIN_INITIAL_PASSWORD:
                print("未设置 SUPER_ADMIN_INITIAL_PASSWORD，跳过超级管理员初始化")
                print("请在 .env 中配置强口令后重新启动，或手动创建超级管理员")
            else:
                initial_password_hash = get_password_hash(settings.SUPER_ADMIN_INITIAL_PASSWORD)
                # 检查是否存在 username="admin" 的普通管理员
                existing_admin = db.query(Admin).filter(Admin.username == "admin").first()
                if existing_admin:
                    # 将现有管理员升级为超级管理员
                    print("正在将现有管理员升级为超级管理员...")
                    existing_admin.is_superadmin = True
                    existing_admin.hashed_password = initial_password_hash
                    db.commit()
                    print("超级管理员升级完成 (用户名: admin, 密码来自 SUPER_ADMIN_INITIAL_PASSWORD)")
                else:
                    # 创建新的超级管理员
                    print("正在创建超级管理员账号...")
                    super_admin = Admin(
                        username="admin",
                        hashed_password=initial_password_hash,
                        is_active=True,
                        is_superadmin=True
                    )
                    db.add(super_admin)
                    db.commit()
                    print("超级管理员创建完成 (用户名: admin, 密码来自 SUPER_ADMIN_INITIAL_PASSWORD)")
        else:
            print("超级管理员账号已存在，跳过创建")

        # 普通管理员通过超级管理员后台绑定 userId 创建，不再初始化默认密码账号
        admin = db.query(Admin).filter(Admin.username == "admin", Admin.is_superadmin == False).first()
        if not admin:
            admin_count = db.query(Admin).filter(Admin.is_superadmin == False).count()
            if admin_count == 0:
                print("未创建默认普通管理员，请在超级管理员后台绑定 userId 创建管理员")
        else:
            print("管理员账号已存在，跳过创建")

        # 初始化预置模板
        print("正在初始化预置模板...")
        created_count = 0
        for preset in PRESET_TEMPLATES:
            existing = db.query(ScriptTemplate).filter(
                ScriptTemplate.name == preset["name"],
                ScriptTemplate.category == "preset"
            ).first()
            
            if not existing:
                template = ScriptTemplate(
                    name=preset["name"],
                    category=preset["category"],
                    product_type=preset["product_type"],
                    template_content=preset["template_content"],
                    description=preset["description"]
                )
                db.add(template)
                created_count += 1
        
        db.commit()
        if created_count > 0:
            print(f"已初始化 {created_count} 个预置模板")
        else:
            print("预置模板已存在，跳过初始化")

        # 初始化默认打分配置
        print("正在初始化默认打分配置...")
        default_config = db.query(ScoringConfig).filter(ScoringConfig.is_default == True).first()
        if not default_config:
            config = ScoringConfig(
                name=DEFAULT_SCORING_CONFIG["name"],
                dimensions=DEFAULT_SCORING_CONFIG["dimensions"],
                prompt_template=DEFAULT_SCORING_CONFIG["prompt_template"],
                is_default=True
            )
            db.add(config)
            db.commit()
            print("默认打分配置初始化完成")
        else:
            print("默认打分配置已存在，跳过初始化")

        # 初始化推荐问题
        print("正在初始化推荐问题...")
        question_count = db.query(SuggestedQuestion).count()
        if question_count == 0:
            for index, content in enumerate(DEFAULT_SUGGESTED_QUESTIONS):
                db.add(SuggestedQuestion(
                    content=content,
                    sort_order=index,
                    is_active=True,
                ))
            db.commit()
            print("推荐问题初始化完成")
        else:
            print("推荐问题已存在，跳过初始化")

    finally:
        db.close()


if __name__ == "__main__":
    init_database()
    print("数据库初始化完成！")
