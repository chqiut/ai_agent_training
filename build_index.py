#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
索引构建脚本：build_index.py
===========================

本脚本负责：
1. 读取 data/ 目录下的 CSV 数据
2. 将数据转换为文本向量
3. 使用 sentence-transformers 生成向量
4. 构建 FAISS 索引并保存到 faiss_index/ 目录

FAISS 是 Facebook AI开发的向量相似度搜索库，
非常适合用于 RAG（检索增强生成）场景。

使用方法：
    python build_index.py
"""

import os
import pickle
from pathlib import Path
from typing import Optional

# 设置 Hugging Face 镜像（国内加速）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
FAISS_DIR = PROJECT_ROOT / "faiss_index"

# 确保目录存在
FAISS_DIR.mkdir(exist_ok=True)


class Document:
    """
    文档对象，用于存储要索引的文本及其元数据

    在 RAG 系统中，我们通常将文档分割成小块（chunk），
    每个 chunk 作为一个独立的文档进行索引。
    """

    def __init__(self, content: str, metadata: Optional[dict] = None):
        self.content = content
        self.metadata = metadata or {}


class FAISSIndexBuilder:
    """
    FAISS 索引构建器

    负责：
    1. 将文档转换为向量
    2. 构建 FAISS 索引
    3. 保存索引和文档映射
    """

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        初始化索引构建器

        Args:
            model_name: sentence-transformers 模型名称
                       使用多语言模型以便更好地处理中文
        """
        self.use_tfidf = False
        self.model = None
        self.dimension = 384

        try:
            print(f"🔄 尝试加载向量化模型: {model_name}")
            self.model = SentenceTransformer(model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            print(f"✓ 向量维度: {self.dimension}")
        except Exception as e:
            print(f"⚠ 模型加载失败 ({e})，使用 TF-IDF 向量化作为备选")
            self.use_tfidf = True
            self.dimension = 500

    def load_csv_documents(self) -> list[Document]:
        """
        从 CSV 文件加载文档

        我们将每条记录转换为一段文本，以便进行向量检索。
        例如：客户记录 -> "客户 C1001 注册于华北地区，等级为金卡会员"
        """
        documents = []

        # 1. 加载客户维度数据
        customer_file = DATA_DIR / "CustomerDim.csv"
        if customer_file.exists():
            df = pd.read_csv(customer_file)
            for _, row in df.iterrows():
                content = (
                    f"客户信息：客户ID={row['customer_id']}，"
                    f"姓名={row['name']}，"
                    f"所在地区={row['region']}，"
                    f"注册日期={row['register_date']}，"
                    f"会员等级={row['tier']}"
                )
                documents.append(Document(content, {
                    "source": "CustomerDim",
                    "id": row["customer_id"]
                }))

        # 2. 加载产品维度数据
        product_file = DATA_DIR / "ProductDim.csv"
        if product_file.exists():
            df = pd.read_csv(product_file)
            for _, row in df.iterrows():
                content = (
                    f"产品信息：产品ID={row['product_id']}，"
                    f"产品名称={row['product_name']}，"
                    f"类别={row['category']}，"
                    f"品牌={row['brand']}，"
                    f"价格区间={row['price_range']}"
                )
                documents.append(Document(content, {
                    "source": "ProductDim",
                    "id": row["product_id"]
                }))

        # 3. 加载销售事实数据（采样，避免过多）
        sales_file = DATA_DIR / "SalesFact.csv"
        if sales_file.exists():
            df = pd.read_csv(sales_file)
            # 采样 200 条记录
            df_sample = df.sample(min(200, len(df)), random_state=42)
            for _, row in df_sample.iterrows():
                content = (
                    f"销售记录：订单ID={row['order_id']}，"
                    f"客户ID={row['customer_id']}，"
                    f"产品ID={row['product_id']}，"
                    f"购买数量={row['quantity']}，"
                    f"单价={row['unit_price']}，"
                    f"订单日期={row['order_date']}"
                )
                documents.append(Document(content, {
                    "source": "SalesFact",
                    "id": row["order_id"]
                }))

        # 4. 加载元数据
        metadata_file = DATA_DIR / "MetadataDim.csv"
        if metadata_file.exists():
            df = pd.read_csv(metadata_file)
            for _, row in df.iterrows():
                content = (
                    f"业务指标：{row['metric_name']}，"
                    f"描述={row['description']}，"
                    f"指标类型={row['metric_type']}"
                )
                documents.append(Document(content, {
                    "source": "MetadataDim",
                    "id": row["metric_id"]
                }))

        print(f"✓ 已加载 {len(documents)} 个文档")
        return documents

    def build_index(self, documents: list[Document]) -> faiss.Index:
        """
        构建 FAISS 索引

        使用 IndexFlatIP（内积索引）进行暴力检索。
        对于教学场景，暴力检索足够且易于理解。

        注意：我们使用归一化向量，所以内积等同于余弦相似度。
        """
        if not documents:
            raise ValueError("文档列表为空，请先加载文档")

        print(f"🔄 正在生成 {len(documents)} 个文档的向量...")

        # 提取所有文档内容
        texts = [doc.content for doc in documents]

        if self.use_tfidf:
            # 使用 TF-IDF 作为备选方案
            from sklearn.feature_extraction.text import TfidfVectorizer
            import numpy as np

            vectorizer = TfidfVectorizer(max_features=500)
            embeddings = vectorizer.fit_transform(texts).toarray()
            print(f"✓ 使用 TF-IDF 向量化")
        else:
            # 使用 sentence-transformers 向量化
            embeddings = self.model.encode(
                texts,
                show_progress_bar=True,
                convert_to_numpy=True
            )
            # 归一化向量（使内积等同于余弦相似度）
            faiss.normalize_L2(embeddings)

        print(f"✓ 向量矩阵形状: {embeddings.shape}")

        # 创建 FAISS 索引
        # IndexFlatIP: 暴力内积搜索，适用于小规模数据集
        index = faiss.IndexFlatIP(self.dimension)
        index.add(embeddings.astype('float32'))

        print(f"✓ 索引已构建，包含 {index.ntotal} 个向量")
        return index

    def save_index(self, index: faiss.Index, documents: list[Document]) -> None:
        """
        保存索引和文档到磁盘

        我们需要保存两样东西：
        1. FAISS 索引文件（index.faiss）
        2. 文档映射文件（index.pkl），用于在检索时知道返回哪个文档
        """
        # 保存 FAISS 索引
        index_path = FAISS_DIR / "index.faiss"
        faiss.write_index(index, str(index_path))
        print(f"✓ 索引已保存: {index_path}")

        # 保存文档映射
        docs_path = FAISS_DIR / "index.pkl"
        with open(docs_path, 'wb') as f:
            pickle.dump(documents, f)
        print(f"✓ 文档映射已保存: {docs_path}")

    def load_index(self) -> tuple[faiss.Index, list[Document]]:
        """
        从磁盘加载索引和文档
        """
        index_path = FAISS_DIR / "index.faiss"
        docs_path = FAISS_DIR / "index.pkl"

        if not index_path.exists() or not docs_path.exists():
            raise FileNotFoundError("索引文件不存在，请先运行 build_index.py")

        index = faiss.read_index(str(index_path))
        with open(docs_path, 'rb') as f:
            documents = pickle.load(f)

        print(f"✓ 索引已加载，包含 {index.ntotal} 个向量")
        return index, documents


def main() -> None:
    """主函数：构建 FAISS 索引"""
    print("=" * 50)
    print("AI Agent Training - FAISS 索引构建脚本")
    print("=" * 50)
    print()

    # 检查数据文件是否存在
    if not any(DATA_DIR.glob("*.csv")):
        print("✗ 错误：data/ 目录中没有 CSV 文件")
        print("  请先运行 generate_data.py 生成数据")
        return

    print("📚 第一步：加载文档...")
    print("-" * 40)

    builder = FAISSIndexBuilder()
    documents = builder.load_csv_documents()

    print()
    print("🔨 第二步：构建 FAISS 索引...")
    print("-" * 40)

    index = builder.build_index(documents)

    print()
    print("💾 第三步：保存索引...")
    print("-" * 40)

    builder.save_index(index, documents)

    print()
    print("=" * 50)
    print("✅ 索引构建完成！")
    print("=" * 50)
    print()
    print("生成的文件：")
    print(f"  - FAISS 索引: {FAISS_DIR}/index.faiss")
    print(f"  - 文档映射: {FAISS_DIR}/index.pkl")
    print()
    print("可以在 RAG 检索中使用此索引。")


if __name__ == "__main__":
    main()