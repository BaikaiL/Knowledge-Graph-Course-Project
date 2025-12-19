import logging
import json
from neo4j.exceptions import Neo4jError

# 配置日志
logger = logging.getLogger(__name__)


class KBQAService:
    """
    知识问答服务类：负责将自然语言转换为Cypher查询，并生成回答。
    """

    def __init__(self, connection_manager, llm_client, model_name="qwen-max"):
        """
        :param connection_manager: 你的 Neo4jConnectionManager 实例
        :param llm_client: 初始化好的 LLM 客户端 (如 OpenAI 实例)
        :param model_name: 模型名称
        """
        self.connection_manager = connection_manager
        self.client = llm_client
        self.model_name = model_name

        # 【重要】适配你实际图数据库的Schema（中文标签+关系）
        self.schema_definition = """
        图谱包含以下节点标签(Labels，需用反引号包裹)：
        1. `代茶饮`: 属性 [名称]（如：姜枣茶、枸杞子茶）
        2. `中药材`: 属性 [名称]（如：枸杞、生姜、菊花）
        3. `功效`: 属性 [名称]（如：补血益气、养肝明目）
        4. `适用人群`: 属性 [名称]（如：作家、电脑族、女性上班族）
        5. `禁忌人群`: 属性 [名称]（如：熬夜人群、脾胃虚寒者）

        图谱包含以下关系类型(Relationships，需用反引号包裹)：
        1. (:`代茶饮`)-[:`原料`]->(:`中药材`) : 代茶饮的原料是某中药材
        2. (:`代茶饮`)-[:`益处`]->(:`功效`) : 代茶饮的益处（功效）是某功效
        3. (:`代茶饮`)-[:`的适用人群`]->(:`适用人群`) : 代茶饮适合的人群
        4. (:`代茶饮`)-[:`不适合人群`]->(:`禁忌人群`) : 代茶饮不适合的人群
        """

    def _get_cypher_from_llm(self, user_question):
        """
        调用 LLM 将自然语言转换为 Cypher 语句
        """
        # 适配你库结构的系统提示词
        system_prompt = f"""
        你是一个 Neo4j Cypher 专家助手，必须严格适配以下图谱Schema，生成能直接执行的Cypher语句。

        {self.schema_definition}

        规则：
        1. 只返回Cypher语句，无markdown格式、无解释，直接输出可执行代码。
        2. 中文节点标签、关系必须用反引号（`）包裹（如:`代茶饮`、:`原料`），否则会语法错误。
        3. 模糊匹配用 CONTAINS（如匹配含“枸杞”的代茶饮：n.名称 CONTAINS '枸杞'）。
        4. 结果限制为 LIMIT 10，避免数据过多。
        5. 关系对应规则：
           - 问“原料/组成”→ 用:`原料`关系
           - 问“功效/益处”→ 用:`益处`关系
           - 问“适合什么人”→ 用:`的适用人群`关系
           - 问“不适合什么人”→ 用:`不适合人群`关系
        6. 推荐类问题需返回`代茶饮`.名称 + 对应关联节点的属性（如功效、人群）。

        示例（完全适配你的库结构）：
        用户：姜枣茶的原料是什么？
        Cypher: MATCH (t:`代茶饮` {{名称: '姜枣茶'}})-[:`原料`]->(i:`中药材`) RETURN t.名称, i.名称 LIMIT 10

        用户：枸杞子茶有什么益处？
        Cypher: MATCH (t:`代茶饮` {{名称: '枸杞子茶'}})-[:`益处`]->(e:`功效`) RETURN t.名称, e.名称 LIMIT 10

        用户：电脑族适合喝什么代茶饮？
        Cypher: MATCH (t:`代茶饮`)-[:`的适用人群`]->(s:`适用人群`) WHERE s.名称 CONTAINS '电脑族' RETURN t.名称, s.名称 LIMIT 10

        用户：玫瑰薄荷茶不适合什么人喝？
        Cypher: MATCH (t:`代茶饮` {{名称: '玫瑰薄荷茶'}})-[:`不适合人群`]->(tab:`禁忌人群`) RETURN t.名称, tab.名称 LIMIT 10
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question}
                ],
                temperature=0  # 保证输出稳定
            )
            cypher = response.choices[0].message.content.strip()
            # 清理冗余格式
            cypher = cypher.replace("```cypher", "").replace("```", "").strip()
            logger.info(f"生成的 Cypher: {cypher}")
            return cypher
        except Exception as e:
            logger.error(f"LLM 生成 Cypher 失败: {str(e)}")
            raise

    # 以下 _execute_cypher、_generate_natural_answer、answer 方法保持不变
    def _execute_cypher(self, cypher):
        """
        执行查询并格式化结果
        """
        try:
            with self.connection_manager.get_session() as session:
                result = session.run(cypher)
                # 将结果转换为简单的列表/字典格式
                data = [record.data() for record in result]
                return data
        except Neo4jError as e:
            logger.error(f"Cypher 执行错误: {str(e)}")
            return []

    def _generate_natural_answer(self, user_question, graph_data):
        """
        根据图谱查询结果生成自然语言回答
        """
        if not graph_data:
            return "抱歉，我在知识图谱中没有找到相关信息，或者该问题超出了我的知识范围。"

        system_prompt = "你是一个中药代茶饮领域的专家助手。请根据用户的问题和提供的数据库查询结果，生成通顺、专业且亲切的回答。"

        user_prompt = f"""
        用户问题：{user_question}
        数据库查询结果：{json.dumps(graph_data, ensure_ascii=False)}

        请生成回答：
        1. 若结果包含多个代茶饮，分点列出，每个代茶饮对应说明其关联信息（如原料、益处、适用人群）。
        2. 若某代茶饮的属性缺失（如无禁忌人群），无需提及该属性。
        3. 语言简洁，避免使用专业术语堆砌，让普通用户容易理解。
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"生成回答失败: {str(e)}")
            return "抱歉，生成回答时出现了系统错误。"

    def answer(self, question):
        """
        主入口：处理用户提问
        """
        print(f"用户提问: {question}")

        # 1. 文本转 Cypher
        try:
            cypher_query = self._get_cypher_from_llm(question)
        except Exception:
            return "系统繁忙，无法理解您的问题。"

        # 2. 查询图数据库
        data = self._execute_cypher(cypher_query)
        logger.info(f"查询结果条数: {len(data)}")

        # 3. 生成最终回复
        final_answer = self._generate_natural_answer(question, data)
        return final_answer