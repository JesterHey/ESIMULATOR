#!/usr/bin/env python3
"""
DAG结构可视化器
专门用于生成清晰可读的DAG图结构
"""

import json
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict
import numpy as np

class DAGVisualizer:
    """DAG可视化器"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_colors = {}
        self.node_shapes = {}
        self.edge_colors = {}
        
    def load_signal_data(self, json_file: str):
        """加载信号连接数据"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 构建NetworkX图
        for conn in data['connections']:
            self.graph.add_edge(conn['source'], conn['destination'])
        
        # 设置节点属性
        for signal_name, signal_info in data['signals'].items():
            self._set_node_attributes(signal_name, signal_info)
        
        return data
    
    def _set_node_attributes(self, node_name: str, signal_info: dict):
        """设置节点属性"""
        category = signal_info['category']
        
        # 根据信号类别设置颜色
        color_map = {
            'general_input': '#90EE90',      # 浅绿色
            'general_output': '#FFB6C1',     # 浅粉色
            'accumulator': '#87CEEB',        # 天蓝色
            'carry_flag': '#FFD700',         # 金色
            'clock_input': '#FFA500',        # 橙色
            'arithmetic_wire': '#DDA0DD',    # 梅花色
            'internal_wire': '#D3D3D3',      # 浅灰色
            'internal_register': '#F0E68C',  # 卡其色
            'temporary_register': '#98FB98', # 苍绿色
            'other': '#FFFFFF'               # 白色
        }
        
        self.node_colors[node_name] = color_map.get(category, '#FFFFFF')
    
    def create_hierarchical_layout(self) -> dict:
        """创建层次化布局"""
        # 使用拓扑排序确定层次
        try:
            layers = list(nx.topological_generations(self.graph))
        except nx.NetworkXError:
            # 如果有环，使用近似方法
            layers = self._approximate_layers()
        
        pos = {}
        y_spacing = 2.0
        
        for layer_idx, layer in enumerate(layers):
            y = -layer_idx * y_spacing
            x_spacing = 10.0 / max(1, len(layer))
            
            for node_idx, node in enumerate(sorted(layer)):
                x = (node_idx - len(layer)/2) * x_spacing
                pos[node] = (x, y)
        
        return pos
    
    def _approximate_layers(self) -> list:
        """近似层次化分组（处理有环图）"""
        # 使用入度作为层次指标
        in_degrees = dict(self.graph.in_degree())
        max_in_degree = max(in_degrees.values()) if in_degrees.values() else 0
        
        layers = [[] for _ in range(max_in_degree + 1)]
        for node, in_degree in in_degrees.items():
            layers[in_degree].append(node)
        
        return [layer for layer in layers if layer]  # 移除空层
    
    def draw_dag_structure(self, output_file: str = "results/dag_structure"):
        """绘制DAG结构图"""
        plt.figure(figsize=(20, 14))
        
        # 创建布局
        pos = self.create_hierarchical_layout()
        
        # 过滤显示的节点（只显示主要信号）
        main_nodes = [node for node in self.graph.nodes() 
                     if node.startswith('alu.') and not node.startswith('alu.n0') 
                     and not node.startswith('const_')]
        
        subgraph = self.graph.subgraph(main_nodes)
        main_pos = {node: pos[node] for node in main_nodes if node in pos}
        
        # 绘制节点
        node_colors = [self.node_colors.get(node, '#FFFFFF') for node in main_nodes]
        nx.draw_networkx_nodes(subgraph, main_pos, 
                              nodelist=main_nodes,
                              node_color=node_colors,
                              node_size=1000,
                              alpha=0.8,
                              edgecolors='black',
                              linewidths=1)
        
        # 绘制边
        nx.draw_networkx_edges(subgraph, main_pos,
                              edge_color='gray',
                              arrows=True,
                              arrowsize=20,
                              arrowstyle='->',
                              alpha=0.6,
                              width=1)
        
        # 添加标签
        labels = {node: node.replace('alu.', '') for node in main_nodes}
        nx.draw_networkx_labels(subgraph, main_pos, labels,
                               font_size=8,
                               font_weight='bold')
        
        # 添加图例
        legend_elements = [
            mpatches.Patch(color='#90EE90', label='Input Signals'),
            mpatches.Patch(color='#FFB6C1', label='Output Signals'),
            mpatches.Patch(color='#87CEEB', label='Accumulator'),
            mpatches.Patch(color='#FFD700', label='Carry Flag'),
            mpatches.Patch(color='#FFA500', label='Clock'),
            mpatches.Patch(color='#D3D3D3', label='Internal Wires'),
            mpatches.Patch(color='#F0E68C', label='Registers')
        ]
        
        plt.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.15, 1))
        plt.title('Intel 4004 ALU - DAG Structure (Main Signals)', 
                 fontsize=16, fontweight='bold', pad=20)
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(f"{output_file}.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 生成DOT文件
        self._generate_dot_file(subgraph, f"{output_file}.dot")
        
        return len(main_nodes), len(subgraph.edges())
    
    def _generate_dot_file(self, graph: nx.DiGraph, filename: str):
        """生成Graphviz DOT文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("digraph Intel_4004_ALU {\n")
            f.write("  rankdir=TB;\n")
            f.write("  node [style=filled, fontname=\"Arial\"];\n")
            f.write("  edge [fontname=\"Arial\"];\n\n")
            
            # 写入节点
            for node in graph.nodes():
                color = self.node_colors.get(node, '#FFFFFF')
                label = node.replace('alu.', '')
                f.write(f'  "{node}" [label="{label}", fillcolor="{color}"];\n')
            
            f.write("\n")
            
            # 写入边
            for source, target in graph.edges():
                f.write(f'  "{source}" -> "{target}";\n')
            
            f.write("}\n")
    
    def create_simplified_dag(self, max_nodes: int = 30):
        """创建简化的DAG图（只显示关键节点）"""
        # 计算节点重要性（入度+出度）
        importance = {}
        for node in self.graph.nodes():
            if node.startswith('alu.') and not node.startswith('alu.n0'):
                in_deg = self.graph.in_degree(node)
                out_deg = self.graph.out_degree(node)
                importance[node] = in_deg + out_deg
        
        # 选择最重要的节点
        top_nodes = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
        selected_nodes = [node for node, _ in top_nodes]
        
        # 创建子图
        subgraph = self.graph.subgraph(selected_nodes)
        
        plt.figure(figsize=(16, 12))
        
        # 使用spring布局
        pos = nx.spring_layout(subgraph, k=3, iterations=50)
        
        # 绘制节点
        node_colors_list = [self.node_colors.get(node, '#FFFFFF') for node in selected_nodes]
        node_sizes_list = [importance[node] * 100 + 500 for node in selected_nodes]
        
        nx.draw_networkx_nodes(subgraph, pos,
                              nodelist=selected_nodes,
                              node_color=node_colors_list,
                              node_size=node_sizes_list,
                              alpha=0.8,
                              edgecolors='black',
                              linewidths=2)
        
        # 绘制边
        nx.draw_networkx_edges(subgraph, pos,
                              edge_color='gray',
                              arrows=True,
                              arrowsize=20,
                              arrowstyle='->',
                              alpha=0.6,
                              width=2)
        
        # 添加标签
        labels = {node: node.replace('alu.', '') for node in selected_nodes}
        nx.draw_networkx_labels(subgraph, pos, labels,
                               font_size=10,
                               font_weight='bold')
        
        plt.title(f'Intel 4004 ALU - Simplified DAG (Top {max_nodes} Critical Signals)', 
                 fontsize=16, fontweight='bold', pad=20)
        plt.axis('off')
        plt.tight_layout()
        plt.savefig("results/simplified_dag.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        return len(selected_nodes), len(subgraph.edges())

def main():
    """主函数"""
    print("=== DAG结构可视化器 ===")
    
    # 设置matplotlib中文字体
    plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    visualizer = DAGVisualizer()
    
    print("1. 加载信号连接数据...")
    try:
        data = visualizer.load_signal_data("4004_signal_connections.json")
        print(f"   加载了 {len(data['signals'])} 个信号和 {len(data['connections'])} 个连接")
    except FileNotFoundError:
        print("   错误：未找到 4004_signal_connections.json")
        print("   请先运行 signal_connection_analyzer.py")
        return
    
    print("\n2. 生成完整DAG结构图...")
    nodes, edges = visualizer.draw_dag_structure()
    print(f"   生成了包含 {nodes} 个节点和 {edges} 条边的DAG图")
    print("   文件: results/dag_structure.png, results/dag_structure.dot")
    
    print("\n3. 生成简化DAG结构图...")
    s_nodes, s_edges = visualizer.create_simplified_dag(25)
    print(f"   生成了包含 {s_nodes} 个关键节点和 {s_edges} 条边的简化DAG图")
    print("   文件: results/simplified_dag.png")
    
    print(f"\n=== DAG结构特征 ===")
    print(f"图类型: {'DAG (无环)' if nx.is_directed_acyclic_graph(visualizer.graph) else '有向图 (含环)'}")
    print(f"强连通分量数: {nx.number_strongly_connected_components(visualizer.graph)}")
    print(f"最长路径长度: {nx.dag_longest_path_length(visualizer.graph) if nx.is_directed_acyclic_graph(visualizer.graph) else '无法计算(有环)'}")

if __name__ == "__main__":
    main()
