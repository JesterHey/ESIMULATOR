"""从线性分析导出的 graph json 构建 networkx 有向图的工具"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any

try:
    import networkx as nx
except ImportError:  # 提示用户安装
    nx = None  # type: ignore


def load_graph_from_json(json_path: str):
    """读取 analyzer 导出的 *_linearity_graph.json 并返回 DiGraph
    节点属性:
        - is_linear (bool)
        - reason (str)
        - operators (List[str])
        - expression_type (str)
    边: src -> dst (表示 dst 依赖 src)
    """
    if nx is None:
        raise RuntimeError("需要安装 networkx 才能加载图: pip install networkx")
    data = json.loads(Path(json_path).read_text(encoding='utf-8'))
    G = nx.DiGraph()
    for name, attrs in data['nodes'].items():
        G.add_node(name, **attrs)
    for src, dst in data['edges']:
        if src not in G:
            G.add_node(src, is_linear=False, reason='external', operators=[], expression_type='external')
        if dst not in G:
            G.add_node(dst, is_linear=False, reason='external', operators=[], expression_type='external')
        G.add_edge(src, dst)
    return G

__all__ = ["load_graph_from_json"]
