#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据生成脚本：generate_data.py
=============================

本脚本负责：
1. 生成示例 CSV 数据文件（CustomerDim, ProductDim, SalesFact, MetadataDim）
2. 将 CSV 数据加载到 DuckDB 数据库（duckdb/agent.db）

这使得我们能够用 SQL 查询结构化业务数据。

使用方法：
    python generate_data.py
"""

import csv
import os
from pathlib import Path
from datetime import datetime, timedelta
import random

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DUCKDB_DIR = PROJECT_ROOT / "duckdb"

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
DUCKDB_DIR.mkdir(exist_ok=True)


def generate_customer_dim() -> list[dict]:
    """
    生成客户维度数据（CustomerDim.csv）
   包含：客户ID、姓名、地区、注册时间、客户等级
    """
    regions = ["华北", "华东", "华南", "华中", "西南", "西北", "东北"]
    tiers = ["普通会员", "银卡会员", "金卡会员", "钻石会员"]
    customers = []

    for i in range(1, 101):
        customers.append({
            "customer_id": f"C{1000 + i}",
            "name": f"客户_{i:03d}",
            "region": random.choice(regions),
            "register_date": (datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1500))).strftime("%Y-%m-%d"),
            "tier": random.choice(tiers)
        })

    return customers


def generate_product_dim() -> list[dict]:
    """
    生成产品维度数据（ProductDim.csv）
    包含：产品ID、产品名称、类别、品牌、价格区间
    """
    categories = ["电子产品", "服装", "食品", "家居", "图书", "运动户外", "美妆"]
    brands = ["品牌A", "品牌B", "品牌C", "品牌D", "品牌E"]
    products = []

    for i in range(1, 51):
        products.append({
            "product_id": f"P{2000 + i}",
            "product_name": f"产品_{i:03d}",
            "category": random.choice(categories),
            "brand": random.choice(brands),
            "price_range": random.choice(["0-100", "100-500", "500-1000", "1000+"])
        })

    return products


def generate_sales_fact(customers: list[dict], products: list[dict]) -> list[dict]:
    """
    生成销售事实数据（SalesFact.csv）
    包含：订单ID、客户ID、产品ID、购买数量、单价、订单日期
    """
    orders = []
    order_id = 1

    for _ in range(500):
        customer = random.choice(customers)
        product = random.choice(products)
        quantity = random.randint(1, 10)
        unit_price = random.uniform(10, 1000)
        order_date = (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")

        orders.append({
            "order_id": f"O{3000 + order_id}",
            "customer_id": customer["customer_id"],
            "product_id": product["product_id"],
            "quantity": quantity,
            "unit_price": round(unit_price, 2),
            "order_date": order_date
        })
        order_id += 1

    return orders


def generate_metadata_dim() -> list[dict]:
    """
    生成元数据（MetadataDim.csv）
    包含：指标ID、指标名称、指标描述、指标类型
    """
    metadata = [
        {"metric_id": "M001", "metric_name": "总销售额", "description": "所有订单的销售总额", "metric_type": "数值"},
        {"metric_id": "M002", "metric_name": "订单数量", "description": "总订单数", "metric_type": "计数"},
        {"metric_id": "M003", "metric_name": "客户数", "description": "有购买行为的客户数", "metric_type": "计数"},
        {"metric_id": "M004", "metric_name": "平均订单金额", "description": "总销售额/订单数量", "metric_type": "比率"},
        {"metric_id": "M005", "metric_name": "热销产品", "description": "销量最高的产品", "metric_type": "枚举"},
    ]

    return metadata


def write_csv(filename: str, data: list[dict]) -> None:
    """写入 CSV 文件"""
    if not data:
        return

    filepath = DATA_DIR / filename
    fieldnames = list(data[0].keys())

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"✓ 已生成: {filepath}")


def create_duckdb_database() -> None:
    """
    将 CSV 数据加载到 DuckDB 数据库

    DuckDB 是一个嵌入式 OLAP 引擎，非常适合分析型查询。
    我们在这里将 CSV 文件加载为 DuckDB 表，方便后续用 SQL 查询。
    """
    try:
        import duckdb
    except ImportError:
        print("✗ 需要安装 duckdb: pip install duckdb")
        return

    db_path = DUCKDB_DIR / "agent.db"

    # 连接到 DuckDB 数据库（如果不存在则自动创建）
    conn = duckdb.connect(str(db_path))

    # 读取各个 CSV 文件并创建表
    tables = [
        ("customer_dim", "CustomerDim.csv"),
        ("product_dim", "ProductDim.csv"),
        ("sales_fact", "SalesFact.csv"),
        ("metadata_dim", "MetadataDim.csv"),
    ]

    for table_name, csv_file in tables:
        csv_path = DATA_DIR / csv_file
        if csv_path.exists():
            # 使用 COPY 命令导入 CSV 数据到表
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} AS
                SELECT * FROM read_csv_auto('{csv_path}')
            """)
            print(f"✓ 已创建表: {table_name}")

    # 创建一些有用的视图（预计算的聚合查询）
    conn.execute("""
        CREATE OR REPLACE VIEW sales_summary AS
        SELECT
            DATE_TRUNC('month', order_date) as month,
            COUNT(*) as order_count,
            SUM(quantity * unit_price) as total_sales,
            COUNT(DISTINCT customer_id) as customer_count
        FROM sales_fact
        GROUP BY DATE_TRUNC('month', order_date)
        ORDER BY month
    """)

    conn.execute("""
        CREATE OR REPLACE VIEW top_products AS
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            SUM(s.quantity) as total_quantity,
            SUM(s.quantity * s.unit_price) as total_revenue
        FROM sales_fact s
        JOIN product_dim p ON s.product_id = p.product_id
        GROUP BY p.product_id, p.product_name, p.category
        ORDER BY total_quantity DESC
        LIMIT 10
    """)

    conn.execute("""
        CREATE OR REPLACE VIEW customer_stats AS
        SELECT
            c.customer_id,
            c.name,
            c.region,
            c.tier,
            COUNT(s.order_id) as order_count,
            COALESCE(SUM(s.quantity * s.unit_price), 0) as total_spent
        FROM customer_dim c
        LEFT JOIN sales_fact s ON c.customer_id = s.customer_id
        GROUP BY c.customer_id, c.name, c.region, c.tier
    """)

    print(f"✓ 已创建视图: sales_summary, top_products, customer_stats")
    print(f"✓ 数据库路径: {db_path}")

    conn.close()


def main() -> None:
    """主函数：生成所有数据并创建数据库"""
    print("=" * 50)
    print("AI Agent Training - 数据生成脚本")
    print("=" * 50)
    print()

    print("📊 第一步：生成 CSV 数据文件...")
    print("-" * 40)

    # 生成数据
    customers = generate_customer_dim()
    products = generate_product_dim()
    sales = generate_sales_fact(customers, products)
    metadata = generate_metadata_dim()

    # 写入 CSV
    write_csv("CustomerDim.csv", customers)
    write_csv("ProductDim.csv", products)
    write_csv("SalesFact.csv", sales)
    write_csv("MetadataDim.csv", metadata)

    print()
    print("🗄️ 第二步：创建 DuckDB 数据库...")
    print("-" * 40)

    create_duckdb_database()

    print()
    print("=" * 50)
    print("✅ 数据生成完成！")
    print("=" * 50)
    print()
    print("生成的文件：")
    print(f"  - CSV 数据: {DATA_DIR}/*.csv")
    print(f"  - DuckDB 数据库: {DUCKDB_DIR}/agent.db")
    print()
    print("可以使用以下 SQL 查询示例：")
    print("  SELECT * FROM sales_summary;")
    print("  SELECT * FROM top_products;")
    print("  SELECT * FROM customer_stats;")


if __name__ == "__main__":
    main()