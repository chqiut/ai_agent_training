# -*- coding: utf-8 -*-
"""
设置 Hugging Face 镜像（国内加速）
"""
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

"""
RAG（检索增强生成）：rag.py
==========================

本模块实现基于 FAISS 的检索增强生成（RAG）功能。

RAG 工作流程：
1. 检索（Retrieval）：根据用户 query 在向量数据库中搜索相关文档
2. 增强（Augmentation）：将检索到的文档作为上下文加入 prompt
3. 生成（Generation）：LLM 基于增强后的 prompt 生成回答

为什么需要 RAG：
- 扩展 LLM 的知识范围
- 提供最新、最相关的信息
- 减少 LLM 的"幻觉"（hallucination）

MMR（最大边际相关）检索：
- 同时考虑相关性和多样性
- 避免返回过于相似的结果
- 提供更全面的信息覆盖

实验5内容：
    实现基于 FAISS 的 RAG 检索，支持 MMR。
"""

from typing import Optional
from dataclasses import dataclass
import numpy as np

from .llm_client import LLMClient, Message


# =============================================================================
# 数据结构
# =============================================================================

@dataclass
class RetrievedDocument:
    """
    检索到的文档

    Attributes:
        content: 文档内容
        metadata: 元数据（如来源、ID 等）
        score: 相似度分数
        rank: 排名
    """
    content: str
    metadata: dict
    score: float
    rank: int


# =============================================================================
# MMR 检索实现
# =============================================================================

def mmr_retrieve(
    query_embedding: np.ndarray,
    documents: list,
    index,
    lambda_param: float = 0.5,
    top_k: int = 5,
    fetch_k: int = 20
) -> list[int]:
    """
    MMR（最大边际相关）检索算法

    MMR 的核心思想：
    - 既要相关（与 query 相似）
    - 又要多样（相互之间不重复）

    公式：argmax[λ * sim(q, d) - (1-λ) * max(sim(d_i, d))]

    其中：
    - sim(q, d) 是 query 与文档的相似度
    - max(sim(d_i, d)) 是文档与已选文档的最大相似度
    - λ 是多样性权重（0.5 表示平衡）

    Args:
        query_embedding: 查询向量
        documents: 文档列表
        index: FAISS 索引
        lambda_param: 多样性参数（0-1），0.5 表示平衡
        top_k: 最终返回的结果数
        fetch_k: 初步检索获取的候选数

    Returns:
        选中的文档索引列表
    """
    # 初步检索，获取更多候选
    distances, indices = index.search(
        query_embedding.astype('float32'),
        fetch_k
    )

    selected = []
    remaining = list(indices[0])

    while len(selected) < top_k and remaining:
        best_score = -float('inf')
        best_idx = None

        for idx in remaining:
            if idx >= len(documents):
                continue

            # 计算相关性分数
            relevance = 1 - distances[0][list(indices[0]).index(idx)]

            # 计算多样性分数（与已选文档的最大相似度）
            diversity = 1.0
            if selected:
                selected_vectors = index.reconstruct_n(selected)
                doc_vector = index.reconstruct(idx)
                similarities = np.dot(selected_vectors, doc_vector) / (
                    np.linalg.norm(selected_vectors, axis=1) *
                    np.linalg.norm(doc_vector)
                )
                diversity = 1 - np.max(similarities)

            # MMR分数
            mmr_score = lambda_param * relevance + (1 - lambda_param) * diversity

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx is not None:
            selected.append(best_idx)
            remaining.remove(best_idx)
        else:
            break

    return selected


# =============================================================================
# RAG 检索器
# =============================================================================

class RAGRetriever:
    """
    RAG 检索器

   封装向量检索和结果处理。

    使用方式：
        retriever = RAGRetriever()
        docs = retriever.retrieve("客户购买行为分析", top_k=3)
        for doc in docs:
            print(doc.content)
    """

    def __init__(
        self,
        index_path: str = "faiss_index/index.faiss",
        docs_path: str = "faiss_index/index.pkl",
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"
    ):
        """
        初始化 RAG 检索器

        Args:
            index_path: FAISS 索引文件路径
            docs_path: 文档映射文件路径
            model_name: 向量化模型名称
        """
        self.index_path = index_path
        self.docs_path = docs_path
        self.model_name = model_name
        self.index = None
        self.documents = []
        self.model = None
        self._initialized = False

    def initialize(self) -> bool:
        """
        初始化检索器

        加载 FAISS 索引和文档。

        Returns:
            是否初始化成功
        """
        from pathlib import Path
        import faiss
        import pickle

        if self._initialized:
            return True

        index_file = Path(self.index_path)
        docs_file = Path(self.docs_path)

        if not index_file.exists() or not docs_file.exists():
            return False

        try:
            self.index = faiss.read_index(str(index_file))

            with open(docs_file, 'rb') as f:
                self.documents = pickle.load(f)

            # 延迟加载模型
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)

            self._initialized = True
            return True

        except Exception as e:
            return False

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        use_mmr: bool = True,
        lambda_param: float = 0.5
    ) -> list[RetrievedDocument]:
        """
        检索相关文档

        Args:
            query: 检索查询
            top_k: 返回结果数量
            use_mmr: 是否使用 MMR 检索
            lambda_param: MMR 多样性参数

        Returns:
            检索到的文档列表
        """
        if not self._initialized:
            if not self.initialize():
                return []

        if not self.documents or self.index.ntotal == 0:
            return []

        try:
            #编码查询
            query_embedding = self.model.encode([query])
            query_embedding = query_embedding / np.linalg.norm(
                query_embedding, axis=1, keepdims=True
            )

            if use_mmr:
                # 使用 MMR 检索
                selected_indices = mmr_retrieve(
                    query_embedding,
                    self.documents,
                    self.index,
                    lambda_param=lambda_param,
                    top_k=top_k,
                    fetch_k=min(top_k * 2, 20)
                )
            else:
                # 使用普通相似度检索
                distances, indices = self.index.search(
                    query_embedding.astype('float32'),
                    top_k
                )
                selected_indices = list(indices[0])

            # 构建结果
            results = []
            for rank, idx in enumerate(selected_indices):
                if idx < len(self.documents):
                    doc = self.documents[idx]
                    distance = distances[0][list(indices[0]).index(idx)]
                    results.append(RetrievedDocument(
                        content=doc.content,
                        metadata=doc.metadata,
                        score=float(1 - distance),
                        rank=rank + 1
                    ))

            return results

        except Exception:
            return []

    def build_context(self, documents: list[RetrievedDocument]) -> str:
        """
        构建检索上下文

        将检索到的文档格式化为可读的上下文字符串。

        Args:
            documents: 检索到的文档列表

        Returns:
            格式化的上下文字符串
        """
        if not documents:
            return ""

        context_parts = ["【检索到的相关信息】\n"]

        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get("source", "未知")
            doc_id = doc.metadata.get("id", "")
            context_parts.append(
                f"{i}. [{source} {doc_id}] (相似度: {doc.score:.2f})\n"
                f"   {doc.content}\n"
            )

        return "\n".join(context_parts)


# =============================================================================
# RAG 增强生成器
# =============================================================================

class RAGAugmentedGenerator:
    """
    RAG 增强生成器

    将检索与生成结合，实现完整的 RAG 流程。

    使用方式：
        generator = RAGAugmentedGenerator(llm_client)
        response = generator.generate(
            query="分析客户购买行为",
            system_prompt="你是一个数据分析师..."
        )
    """

    def __init__(
        self,
        llm_client: LLMClient,
        retriever: Optional[RAGRetriever] = None
    ):
        """
        初始化 RAG 增强生成器

        Args:
            llm_client: LLM 客户端
            retriever: RAG 检索器（如果为 None，使用默认配置）
        """
        self.llm_client = llm_client
        self.retriever = retriever or RAGRetriever()

    def generate(
        self,
        query: str,
        system_prompt: str,
        top_k: int = 3,
        use_mmr: bool = True
    ) -> str:
        """
        RAG 增强生成

        流程：
        1. 检索相关文档
        2. 构建增强上下文
        3. 调用 LLM 生成回答

        Args:
            query: 用户查询
            system_prompt: 系统提示词
            top_k: 检索结果数量
            use_mmr: 是否使用 MMR

        Returns:
            LLM 生成的回答
        """
        # 步骤1：检索
        docs = self.retriever.retrieve(query, top_k=top_k, use_mmr=use_mmr)

        # 步骤 2：构建上下文
        rag_context = self.retriever.build_context(docs)

        # 步骤 3：构建增强后的 prompt
        if rag_context:
            user_prompt = f"""{query}

{rag_context}

请基于以上检索到的信息回答用户的问题。
如果检索到的信息不能完全回答问题，请基于已有信息尽可能回答，
并说明哪些信息是检索自知识库的。"""
        else:
            user_prompt = query

        # 步骤 4：调用 LLM
        messages = [
            Message("system", system_prompt),
            Message("user", user_prompt)
        ]

        response = self.llm_client.chat(messages)
        return response.content