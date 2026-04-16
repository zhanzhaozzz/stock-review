"""Phase 0 旧词迁移脚本 — 将数据库中的旧阶段词统一为 V1 规范词。

用法:
    python scripts/migrate_phase_v1_terms.py --dry-run   # 预览影响范围
    python scripts/migrate_phase_v1_terms.py              # 执行迁移
    python scripts/migrate_phase_v1_terms.py --db /path/to/db  # 指定数据库路径
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

VALID_PHASES = {"冰点", "启动", "发酵", "高潮", "高位混沌", "退潮"}

PHASE_ALIAS: dict[str, str] = {
    "低位混沌": "冰点",
    "低位混沌期": "冰点",
    "启动期": "启动",
    "上升期": "发酵",
    "发酵期": "发酵",
    "高潮期": "高潮",
    "高位混沌期": "高位混沌",
    "分歧": "高位混沌",
    "高位震荡": "高位混沌",
    "退潮期": "退潮",
}

PHASE_EXPAND: dict[str, list[str]] = {
    "上升期": ["启动", "发酵", "高潮"],
}

OLD_VALUES = tuple(PHASE_ALIAS.keys())


def normalize_phase(raw: str) -> str:
    if not raw:
        return raw
    s = raw.strip()
    if s in VALID_PHASES:
        return s
    return PHASE_ALIAS.get(s, s)


def normalize_phase_list(raw_list: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in raw_list:
        s = item.strip() if isinstance(item, str) else str(item)
        if s in PHASE_EXPAND:
            expanded = PHASE_EXPAND[s]
        else:
            expanded = [normalize_phase(s)]
        for phase in expanded:
            if phase in VALID_PHASES and phase not in seen:
                seen.add(phase)
                result.append(phase)
    return result


def migrate_single_field(conn: sqlite3.Connection, table: str, field: str, dry_run: bool) -> int:
    """迁移单值字段（market_sentiment / sentiment_cycle_main / cycle_phase）。"""
    placeholders = ",".join("?" for _ in OLD_VALUES)
    sql_count = f"SELECT COUNT(*) FROM {table} WHERE {field} IN ({placeholders})"
    count = conn.execute(sql_count, OLD_VALUES).fetchone()[0]

    label = f"{table}.{field}"
    if dry_run:
        print(f"  [dry-run] {label}: 影响 {count} 条")
        return count

    if count == 0:
        print(f"  {label}: 无需迁移 (0 条)")
        return 0

    for old_val, new_val in PHASE_ALIAS.items():
        conn.execute(
            f"UPDATE {table} SET {field} = ? WHERE {field} = ?",
            (new_val, old_val),
        )

    conn.commit()
    print(f"  {label}: 已迁移 {count} 条")
    return count


def migrate_json_list_field(conn: sqlite3.Connection, table: str, field: str, dry_run: bool) -> int:
    """迁移 JSON 列表字段（strategies.applicable_cycles）。"""
    rows = conn.execute(f"SELECT id, {field} FROM {table} WHERE {field} IS NOT NULL").fetchall()

    affected = 0
    for row_id, raw_json in rows:
        if not raw_json:
            continue
        try:
            original = json.loads(raw_json)
        except (json.JSONDecodeError, TypeError):
            continue

        if not isinstance(original, list):
            continue

        normalized = normalize_phase_list(original)
        if normalized != original:
            affected += 1
            if not dry_run:
                conn.execute(
                    f"UPDATE {table} SET {field} = ? WHERE id = ?",
                    (json.dumps(normalized, ensure_ascii=False), row_id),
                )

    if not dry_run and affected > 0:
        conn.commit()

    label = f"{table}.{field}"
    prefix = "[dry-run] " if dry_run else ""
    action = "影响" if dry_run else "已迁移"
    print(f"  {prefix}{label}: {action} {affected} 条")
    return affected


def main():
    parser = argparse.ArgumentParser(description="Phase 0: 旧阶段词 → V1 规范词迁移")
    parser.add_argument("--dry-run", action="store_true", help="只统计影响范围，不写入")
    parser.add_argument(
        "--db",
        type=str,
        default=str(Path(__file__).resolve().parent.parent / "data" / "stock_review.db"),
        help="数据库路径 (默认: backend/data/stock_review.db)",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"错误: 数据库文件不存在 - {db_path}")
        sys.exit(1)

    mode = "DRY-RUN 预览" if args.dry_run else "正式迁移"
    print(f"\n=== Phase 0 旧词迁移 ({mode}) ===")
    print(f"数据库: {db_path}\n")

    conn = sqlite3.connect(str(db_path))
    total = 0

    try:
        print("1. 单值字段迁移:")
        total += migrate_single_field(conn, "daily_reviews", "market_sentiment", args.dry_run)
        total += migrate_single_field(conn, "daily_reviews", "sentiment_cycle_main", args.dry_run)
        total += migrate_single_field(conn, "sentiment_cycle_log", "cycle_phase", args.dry_run)

        print("\n2. JSON 列表字段迁移:")
        total += migrate_json_list_field(conn, "strategies", "applicable_cycles", args.dry_run)

        print(f"\n合计: {'预计影响' if args.dry_run else '已迁移'} {total} 条记录")

        if args.dry_run:
            print("\n提示: 去掉 --dry-run 参数执行真实迁移")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
