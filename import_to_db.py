#!/usr/bin/env python3
"""
gov-crawler 数据入库脚本
从 results/result.json 读取爬取数据，写入 SQLite 数据库
字段: title, url, date, summary, content
URL 去重: INSERT OR REPLACE
"""

import json
import sqlite3
import os
import sys

# 路径配置
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(PROJECT_DIR, "results", "result.json")
DB_PATH = os.path.join(PROJECT_DIR, "results", "data.db")

# 字段映射: JSON 字段 → DB 字段
FIELD_MAP = {
    "title":   "title",
    "url":     "url",
    "docDate": "date",
    "summary": "summary",   # JSON 中可能不存在，用 .get() 兜底 → None
    "content": "content",
}


def create_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data (
            title   TEXT,
            url     TEXT UNIQUE,
            date    TEXT,
            summary TEXT,
            content TEXT
        )
    """)
    conn.commit()


def load_json(path):
    if not os.path.exists(path):
        print(f"[ERROR] JSON 文件不存在: {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        # 如果 JSON 是 {"results": [...]} 格式，自动解包
        for v in data.values():
            if isinstance(v, list):
                data = v
                break

    if not isinstance(data, list):
        print("[ERROR] JSON 结构异常，预期为列表")
        sys.exit(1)

    return data


def insert_data(conn, records):
    inserted = 0
    updated = 0

    for item in records:
        row = {}
        for json_key, db_key in FIELD_MAP.items():
            row[db_key] = item.get(json_key, None)

        # 把空字符串也转成 None，保持数据干净
        for k in row:
            if row[k] == "":
                row[k] = None

        # 先查是否已存在
        cur = conn.execute("SELECT 1 FROM data WHERE url = ?", (row["url"],))
        exists = cur.fetchone() is not None

        conn.execute(
            """
            INSERT OR REPLACE INTO data (title, url, date, summary, content)
            VALUES (:title, :url, :date, :summary, :content)
            """,
            row,
        )

        if exists:
            updated += 1
        else:
            inserted += 1

    conn.commit()
    return inserted, updated


def main():
    print("=" * 50)
    print("gov-crawler → SQLite 数据入库")
    print("=" * 50)

    # 确保 results 目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # 加载 JSON
    print(f"\n[1] 读取 JSON: {JSON_PATH}")
    records = load_json(JSON_PATH)
    print(f"    共 {len(records)} 条记录")

    # 连接数据库
    print(f"\n[2] 连接数据库: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    try:
        create_table(conn)

        print(f"\n[3] 写入数据 ...")
        inserted, updated = insert_data(conn, records)

        # 统计
        total = conn.execute("SELECT COUNT(*) FROM data").fetchone()[0]

    finally:
        conn.close()

    print(f"\n[4] 完成!")
    print(f"    + 新增: {inserted} 条")
    print(f"    * 更新: {updated} 条")
    print(f"    = 总计: {total} 条")
    print(f"    数据库: {DB_PATH}")
    print()

    # 预览前3条
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT title, url, date, summary FROM data LIMIT 3").fetchall()
    conn.close()

    print("[预览] 前3条:")
    for i, r in enumerate(rows, 1):
        print(f"  {i}. {r['title'][:50]}...")
        print(f"     URL: {r['url'][:60]}...")
        print(f"     Date: {r['date']}, Summary: {r['summary']}")
    print()


if __name__ == "__main__":
    main()
