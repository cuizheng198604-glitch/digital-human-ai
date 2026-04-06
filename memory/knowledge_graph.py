# -*- coding: utf-8 -*-
"""
知识图谱 - 基于 NetworkX
用于存储用户实体、关系和知识结构
"""
import networkx as nx
from typing import Dict, List, Set, Tuple, Optional
import json
from datetime import datetime
import os


class KnowledgeGraph:
    """用户知识图谱"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
    
    def add_entity(
        self,
        user_id: str,
        entity: str,
        entity_type: str,
        properties: Dict = None
    ):
        """添加实体
        
        Args:
            user_id: 用户ID
            entity: 实体名称
            entity_type: 实体类型 (person, interest, topic, etc.)
            properties: 实体属性
        """
        node_id = f"{user_id}:{entity}"
        self.graph.add_node(
            node_id,
            entity=entity,
            type=entity_type,
            properties=properties or {},
            created_at=datetime.now().isoformat()
        )
    
    def add_relation(
        self,
        user_id: str,
        entity1: str,
        relation: str,
        entity2: str
    ):
        """添加关系
        
        Args:
            user_id: 用户ID
            entity1: 源实体
            relation: 关系类型 (喜欢、属于、关注等)
            entity2: 目标实体
        """
        node1 = f"{user_id}:{entity1}"
        node2 = f"{user_id}:{entity2}"
        
        if not self.graph.has_node(node1):
            self.add_entity(user_id, entity1, "unknown")
        if not self.graph.has_node(node2):
            self.add_entity(user_id, entity2, "unknown")
        
        self.graph.add_edge(node1, node2, relation=relation)
    
    def get_entity_neighbors(
        self,
        user_id: str,
        entity: str,
        max_depth: int = 1
    ) -> List[str]:
        """获取实体关联的节点
        
        Args:
            user_id: 用户ID
            entity: 实体名称
            max_depth: 搜索深度
        
        Returns:
            List[str]: 关联实体列表
        """
        node_id = f"{user_id}:{entity}"
        if node_id not in self.graph:
            return []
        
        neighbors = set()
        current_level = {node_id}
        
        for _ in range(max_depth):
            next_level = set()
            for node in current_level:
                neighbors.update(self.graph.successors(node))
                neighbors.update(self.graph.predecessors(node))
                next_level.update(neighbors)
            current_level = next_level - neighbors
        
        # 返回实体名称（去除user_id前缀）
        return [n.split(":", 1)[1] for n in neighbors]
    
    def get_user_entities(
        self,
        user_id: str,
        entity_type: str = None
    ) -> List[Dict]:
        """获取用户的所有实体
        
        Args:
            user_id: 用户ID
            entity_type: 过滤类型（可选）
        
        Returns:
            List[Dict]: 实体列表
        """
        entities = []
        prefix = f"{user_id}:"
        
        for node, data in self.graph.nodes(data=True):
            if node.startswith(prefix):
                if entity_type is None or data.get("type") == entity_type:
                    entities.append({
                        "name": data.get("entity", ""),
                        "type": data.get("type", ""),
                        "properties": data.get("properties", {})
                    })
        return entities
    
    def get_user_relations(self, user_id: str) -> List[Dict]:
        """获取用户的所有关系
        
        Args:
            user_id: 用户ID
        
        Returns:
            List[Dict]: 关系列表
        """
        relations = []
        prefix = f"{user_id}:"
        
        for u, v, data in self.graph.edges(data=True):
            if u.startswith(prefix) and v.startswith(prefix):
                relations.append({
                    "from": u.replace(prefix, ""),
                    "to": v.replace(prefix, ""),
                    "relation": data.get("relation", "")
                })
        return relations
    
    def find_path(
        self,
        user_id: str,
        entity1: str,
        entity2: str
    ) -> List[str]:
        """查找两个实体之间的路径
        
        Args:
            user_id: 用户ID
            entity1: 起点实体
            entity2: 终点实体
        
        Returns:
            List[str]: 路径上的实体列表
        """
        node1 = f"{user_id}:{entity1}"
        node2 = f"{user_id}:{entity2}"
        
        if node1 not in self.graph or node2 not in self.graph:
            return []
        
        try:
            path = nx.shortest_path(self.graph, node1, node2)
            return [n.split(":", 1)[1] for n in path]
        except nx.NetworkXNoPath:
            return []
    
    def get_related_entities(
        self,
        user_id: str,
        entity: str,
        relation_type: str = None
    ) -> List[Tuple[str, str]]:
        """获取与实体相关的实体及关系
        
        Args:
            user_id: 用户ID
            entity: 实体名称
            relation_type: 关系类型过滤（可选）
        
        Returns:
            List[Tuple[实体, 关系]]: 相关实体和关系
        """
        node_id = f"{user_id}:{entity}"
        if node_id not in self.graph:
            return []
        
        results = []
        
        # 出边
        for successor, data in self.graph[node_id].items():
            rel = data.get("relation", "")
            if relation_type is None or rel == relation_type:
                results.append((successor.split(":", 1)[1], rel))
        
        # 入边
        for predecessor, data in self.graph.pred[node_id].items():
            rel = data.get("relation", "")
            if relation_type is None or rel == relation_type:
                results.append((predecessor.split(":", 1)[1], rel))
        
        return results
    
    def save(self, filepath: str):
        """保存图谱到文件
        
        Args:
            filepath: 文件路径
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = nx.node_link_data(self.graph)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, filepath: str):
        """从文件加载图谱
        
        Args:
            filepath: 文件路径
        """
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.graph = nx.node_link_graph(data)
    
    def to_dict(self) -> Dict:
        """转换为字典格式
        
        Returns:
            Dict: 图谱数据
        """
        return {
            "entities": [
                {"id": n, **d} for n, d in self.graph.nodes(data=True)
            ],
            "relations": [
                {"from": u, "to": v, **d} for u, v, d in self.graph.edges(data=True)
            ]
        }
    
    def clear_user_data(self, user_id: str):
        """清除用户所有数据
        
        Args:
            user_id: 用户ID
        """
        prefix = f"{user_id}:"
        nodes_to_remove = [n for n in self.graph.nodes() if n.startswith(prefix)]
        self.graph.remove_nodes_from(nodes_to_remove)


# 测试
if __name__ == "__main__":
    kg = KnowledgeGraph()
    
    # 添加实体
    kg.add_entity("user1", "AI技术", "interest", {"level": "high", "duration": "2年"})
    kg.add_entity("user1", "科技", "field")
    kg.add_entity("user1", "张三种", "person")
    kg.add_entity("user1", "机器学习", "topic")
    
    # 添加关系
    kg.add_relation("user1", "AI技术", "属于", "科技")
    kg.add_relation("user1", "机器学习", "属于", "AI技术")
    kg.add_relation("user1", "张三种", "喜欢", "AI技术")
    kg.add_relation("user1", "张三种", "擅长", "机器学习")
    
    # 测试查询
    print("=== 用户实体 ===")
    for e in kg.get_user_entities("user1"):
        print(f"  [{e['type']}] {e['name']}: {e['properties']}")
    
    print("\n=== 用户关系 ===")
    for r in kg.get_user_relations("user1"):
        print(f"  {r['from']} --[{r['relation']}]--> {r['to']}")
    
    print("\n=== AI技术的关联实体 ===")
    neighbors = kg.get_entity_neighbors("user1", "AI技术")
    print(f"  {neighbors}")
    
    print("\n=== 张三种喜欢的实体 ===")
    related = kg.get_related_entities("user1", "张三种")
    for entity, rel in related:
        print(f"  {entity} ({rel})")
