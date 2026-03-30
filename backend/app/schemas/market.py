from pydantic import BaseModel


class IndexQuote(BaseModel):
    code: str
    name: str
    price: float = 0
    change: float = 0
    change_pct: float = 0


class MarketBreadth(BaseModel):
    up: int = 0
    down: int = 0
    flat: int = 0
    limit_up: int = 0
    limit_down: int = 0
    total: int = 0


class MarketOverviewResponse(BaseModel):
    indices: list[IndexQuote] = []
    breadth: MarketBreadth = MarketBreadth()
    timestamp: str = ""


class SectorItem(BaseModel):
    name: str
    change_pct: float = 0
    up_count: int = 0
    down_count: int = 0


class MoneyFlowItem(BaseModel):
    name: str
    change_pct: float = 0
    net_flow: float = 0
    net_flow_pct: float = 0


class LimitUpStock(BaseModel):
    code: str
    name: str
    board_count: int = 1
    change_pct: float = 0
    turnover: float = 0
    sector: str = ""


class LadderLevel(BaseModel):
    level: int
    count: int = 0
    stocks: list[LimitUpStock] = []


class LimitUpLeader(BaseModel):
    code: str
    name: str
    board_count: int
    sector: str = ""


class LimitUpResponse(BaseModel):
    date: str
    market_height: int = 0
    market_leader: LimitUpLeader | None = None
    ladder: list[LadderLevel] = []
    first_board_count: int = 0
    broken_boards: list[dict] = []
    sector_distribution: dict[str, int] = {}
