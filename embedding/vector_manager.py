import os
import dashscope
from dashscope import TextEmbedding
from neo4j import GraphDatabase


class VectorManager:
    def __init__(self, uri, user, password, api_key=None):
        """
        初始化向量管理器
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

        # 优先使用传入的 Key，否则读取环境变量
        self.api_key = api_key or os.getenv('DASHSCOPE_API_KEY')
        if not self.api_key:
            raise ValueError("错误：未找到 DashScope API Key，请在初始化时传入或设置环境变量。")

        # 指定模型版本，如果阿里云发布了 v4 请保持此名称，目前常用的是 v3
        # 注意：不同模型的维度不同，v3/v4 通常为 1024 维
        self.model_name = 'text-embedding-v3'
        self.dimension = 1024

    def close(self):
        if self.driver:
            self.driver.close()

    def get_embedding(self, text):
        """
        调用阿里云 API 将文本转换为向量
        """
        try:
            resp = TextEmbedding.call(
                model=self.model_name,
                input=text,
                api_key=self.api_key
            )
            if resp.status_code == 200:
                # 提取向量数据
                return resp.output['embeddings'][0]['embedding']
            else:
                print(f"[API Error] Code: {resp.code}, Message: {resp.message}")
                return None
        except Exception as e:
            print(f"[Exception] 获取向量失败: {e}")
            return None

    def create_index_if_not_exists(self):
        """
        在 Neo4j 中创建向量索引
        """
        with self.driver.session() as session:
            # 检查索引是否存在（简化逻辑：直接尝试创建，如果存在则跳过）
            print(f"正在检查/创建向量索引，维度: {self.dimension}...")

            # 使用 f-string 注入维度参数
            cypher = f"""
                CREATE VECTOR INDEX function_embedding_index IF NOT EXISTS
                FOR (n:功效) ON (n.embedding)
                OPTIONS {{indexConfig: {{
                 `vector.dimensions`: {self.dimension},
                 `vector.similarity_function`: 'cosine'
                }}}}
            """
            session.run(cypher)
            print("索引 'function_embedding_index' 准备就绪。")

    def refresh_embeddings(self, force_update=False):
        """
        遍历数据库中的【功效】节点，生成并写入向量
        :param force_update: 是否强制更新所有节点（默认只处理没有向量的节点）
        """
        with self.driver.session() as session:
            # 1. 确定查询范围
            if force_update:
                query = "MATCH (n:功效) RETURN n.名称 AS name"
            else:
                query = "MATCH (n:功效) WHERE n.embedding IS NULL RETURN n.名称 AS name"

            result = session.run(query)
            nodes = [record["name"] for record in result]

            if not nodes:
                print("没有发现需要生成向量的节点。")
                return

            print(f"发现 {len(nodes)} 个节点待处理...")

            # 2. 批量处理（实际生产中建议分批提交，这里为了演示逐个处理）
            count = 0
            for name in nodes:
                vector = self.get_embedding(name)
                if vector:
                    session.run("""
                        MATCH (n:功效 {名称: $name})
                        CALL db.create.setNodeVectorProperty(n, 'embedding', $vector)
                    """, name=name, vector=vector)
                    count += 1
                    if count % 10 == 0:
                        print(f"已处理 {count}/{len(nodes)}: {name}")
                else:
                    print(f"跳过节点: {name} (向量生成失败)")

            print(f"完成！共更新 {count} 个节点的向量数据。")

    def search(self, user_query, top_k=3, threshold=0.7):
        """
        执行向量相似度搜索
        """
        # 1. 把用户的问题转向量
        query_vector = self.get_embedding(user_query)
        if not query_vector:
            return []

        # 2. 在数据库中搜最像的
        with self.driver.session() as session:
            cypher = """
            CALL db.index.vector.queryNodes('function_embedding_index', $k, $query_vector)
            YIELD node, score
            WHERE score >= $threshold
            RETURN node.名称 AS name, score
            """
            result = session.run(cypher, k=top_k, query_vector=query_vector, threshold=threshold)

            matches = [{"name": r["name"], "score": r["score"]} for r in result]
            return matches