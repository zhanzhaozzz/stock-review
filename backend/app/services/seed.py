"""Seed initial data: default admin user and strategy library."""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.models.strategy import Strategy

logger = logging.getLogger(__name__)

INITIAL_STRATEGIES = [
    {
        "name": "擒龙战法",
        "applicable_cycles": ["发酵", "高潮"],
        "conditions": "主线发酵或高潮阶段，龙头地位明确",
        "entry_rules": (
            "1. 龙头首分后弱转强（竞价、打板）\n"
            "2. 盘龙低吸 分歧转修复（底背驰加典型的底分型）"
        ),
        "exit_rules": "龙头出现明确见顶信号或板块退潮",
        "position_rules": (
            "龙头战法仓位:\n"
            "1. 1/2 ~ 3/4（打板）\n"
            "2. 1/4 ~ 1/2（低吸）"
        ),
        "buy_point_rules": (
            "操作级别: 短线/倒差价 做30F/60F笔（5F/15F线段）\n"
            "进场: 激进型 5F级别线段背驰+1F级别线段背驰+5F典型底顶分型/停顿法"
        ),
        "sort_order": 1,
    },
    {
        "name": "补涨套利",
        "applicable_cycles": ["高位混沌"],
        "conditions": "主线发酵至高潮阶段、主线高位混沌阶段",
        "entry_rules": (
            "1. 盘龙分歧转修复主线内的前排首板（打板，要求距调整线+3%内三天内启动）\n"
            "2. 主线分歧转修复次日弱转强 前排 1进2（竞价、打板）"
        ),
        "exit_rules": "主线退潮或补涨标的冲高回落",
        "position_rules": (
            "补涨套利仓位:\n"
            "1. 1/4 ~ 1/2（打板）"
        ),
        "buy_point_rules": "稳健型: 5F/15F级别线段背驰+30F/60F级别典型底分型",
        "sort_order": 2,
    },
    {
        "name": "缠龙低吸",
        "applicable_cycles": ["高位混沌"],
        "conditions": "高位混沌阶段，主线分歧转修复日",
        "entry_rules": "主线分歧转修复日低吸至少是突破近期平台的首板 30F/60F回调笔",
        "exit_rules": "标的反弹无力或板块持续退潮",
        "position_rules": "条件: 要求主线题材大，市场发酵至高潮阶段，情绪修复点",
        "buy_point_rules": "简易性: 30F/60F底分型停顿法",
        "sort_order": 3,
    },
    {
        "name": "试错轻仓",
        "applicable_cycles": ["冰点", "启动"],
        "conditions": "冰点阶段，切换至潜在主线",
        "entry_rules": (
            "1. 首板 指数、情绪冰点共振反转（打板，要求距调整线+3%内三天内启动）\n"
            "2. 1进2、2进3 前排 弱转强、分歧转修复（竞价、打板）"
        ),
        "exit_rules": "反转失败则快速止损",
        "position_rules": (
            "潜龙低吸仓位:\n"
            "1. 5F一买进 1/5\n"
            "2. 5F二买进 1/4"
        ),
        "buy_point_rules": "进出场方式需建立在30F级别线段背驰/回调、反弹，需结合支撑压力和预判工具",
        "sort_order": 4,
    },
]


async def seed_admin_user(session: AsyncSession):
    settings = get_settings()
    result = await session.execute(select(User).where(User.username == settings.admin_username))
    if result.scalar_one_or_none() is None:
        from passlib.context import CryptContext
        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        admin = User(
            username=settings.admin_username,
            hashed_password=pwd_ctx.hash(settings.admin_password),
            display_name="管理员",
            is_admin=True,
        )
        session.add(admin)
        await session.commit()
        logger.info("Default admin user created: %s", settings.admin_username)


async def seed_strategies(session: AsyncSession):
    result = await session.execute(select(Strategy))
    if result.scalars().first() is not None:
        return
    for s in INITIAL_STRATEGIES:
        session.add(Strategy(**s))
    await session.commit()
    logger.info("Seeded %d initial strategies", len(INITIAL_STRATEGIES))


async def run_seed(session: AsyncSession):
    await seed_admin_user(session)
    await seed_strategies(session)
