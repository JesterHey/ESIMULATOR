#!/usr/bin/env python3
"""
DFG线性分析结果到图形式转换器
将dfg_linearity_corrector.py生成的分析结果转换成simulated_annealing.py可接受的图格式
"""

import re
import os
from typing import Dict, List, Set, Tuple, Optional
import networkx as nx
from collections import defaultdict


class LinearityAnalysisToGraphConverter:
    """将线性分析结果转换为图的转换器"""
    
    def __init__(self):
        self.signal_linearity: Dict[str, bool] = {}
        self.signal_reasons: Dict[str, str] = {}
        
    def parse_linearity_analysis_file(self, analysis_file_path: str) -> Dict[str, Dict]:
        """解析线性分析结果文件
        
        Args:
            analysis_file_path: 分析结果文件路径
            
        Returns:
            Dict包含信号名称到属性的映射
        """
        signal_data = {}
        
        if not os.path.exists(analysis_file_path):
            raise FileNotFoundError(f"分析文件不存在: {analysis_file_path}")
            
        with open(analysis_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找详细信号分析部分
        details_section_match = re.search(r'详细信号分析:\s*-+\s*(.*?)(?:\n\n|\Z)', content, re.DOTALL)
        if not details_section_match:
            raise ValueError("无法在分析文件中找到详细信号分析部分")
        
        details_content = details_section_match.group(1)
        
        # 解析每个信号的信息
        # 格式: signal_name : 线性/非线性 - reason
        pattern = r'(\S+)\s*:\s*(线性|非线性)\s*-\s*(.*)'
        
        for line in details_content.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
                
            match = re.match(pattern, line)
            if match:
                signal_name = match.group(1)
                linearity_text = match.group(2) 
                reason = match.group(3).strip()
                
                is_linear = linearity_text == '线性'
                
                signal_data[signal_name] = {
                    'is_linear': is_linear,
                    'reason': reason,
                    'linearity_text': linearity_text
                }
                
        return signal_data
    
    def parse_dfg_file(self, dfg_file_path: str) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
        """解析DFG文件获取信号定义和依赖关系
        
        Args:
            dfg_file_path: DFG文件路径
            
        Returns:
            Tuple of (signals dict, binds dict)
            - signals: {signal_name: [type_list]}
            - binds: {dest_signal: expression_tree}
        """
        if not os.path.exists(dfg_file_path):
            raise FileNotFoundError(f"DFG文件不存在: {dfg_file_path}")
            
        with open(dfg_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析Term部分获取信号定义
        signals = {}
        term_pattern = r'\(Term name:(\S+) type:\[(.*?)\]'
        for match in re.finditer(term_pattern, content):
            name = match.group(1)
            types_str = match.group(2)
            types = [t.strip().strip("'") for t in types_str.split(',') if t.strip()]
            signals[name] = types
        
        # 解析Bind部分获取依赖关系
        binds = {}
        bind_pattern = r'\(Bind dest:(\S+).*?tree:(.*?)\)(?=\n\(Bind|\n\n|\Z)'
        for match in re.finditer(bind_pattern, content, re.DOTALL):
            dest = match.group(1)
            tree = match.group(2).strip()
            binds[dest] = tree
            
        return signals, binds
    
    def extract_dependencies(self, expression_tree: str) -> Set[str]:
        """从表达式树中提取依赖的信号名称
        
        Args:
            expression_tree: 表达式树字符串
            
        Returns:
            依赖的信号名称集合
        """
        # 查找所有Terminal节点，但要过滤掉无效的信号名
        terminal_pattern = r'Terminal ([^)\s,]+)'
        dependencies = set()
        
        for match in re.finditer(terminal_pattern, expression_tree):
            signal_name = match.group(1)
            # 过滤掉包含不合法字符的信号名
            if self._is_valid_signal_name(signal_name):
                dependencies.add(signal_name)
            
        return dependencies
    
    def _is_valid_signal_name(self, name: str) -> bool:
        """检查是否是有效的信号名称"""
        # 有效的信号名应该：
        # 1. 不包含括号
        # 2. 不以数字开头（除非是alu.nXXXX格式）
        # 3. 包含字母数字和点、下划线
        if ')' in name or '(' in name or ',' in name:
            return False
        
        # 允许alu.开头的信号名和其他合理的信号名
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_.]*$', name):
            return True
            
        # 允许alu.nXXXX格式
        if re.match(r'^alu\.n\d+$', name):
            return True
            
        return False
    
    def create_graph_from_analysis(self, analysis_file_path: str, 
                                  dfg_file_path: Optional[str] = None) -> nx.DiGraph:
        """从分析结果和DFG文件创建图
        
        Args:
            analysis_file_path: 线性分析结果文件路径
            dfg_file_path: DFG文件路径，如果为None则尝试自动推断
            
        Returns:
            NetworkX有向图，包含节点属性和边
        """
        # 解析线性分析结果
        signal_data = self.parse_linearity_analysis_file(analysis_file_path)
        
        # 推断DFG文件路径
        if dfg_file_path is None:
            # 从分析文件名推断DFG文件名
            analysis_filename = os.path.basename(analysis_file_path)
            # 假设格式为: XXXX_dfg_linearity_analysis.txt
            if '_dfg_linearity_analysis.txt' in analysis_filename:
                dfg_base = analysis_filename.replace('_dfg_linearity_analysis.txt', '_dfg.txt')
                # 找到项目根目录
                current_dir = os.path.dirname(os.path.abspath(analysis_file_path))
                found = False
                
                # 尝试从多个位置查找dfg_files目录
                search_paths = [
                    current_dir,  # 当前目录
                    os.path.dirname(current_dir),  # 上级目录
                    os.path.dirname(os.path.dirname(current_dir)),  # 上上级目录
                    os.getcwd(),  # 工作目录
                    os.path.join(os.getcwd(), '..'),  # 工作目录的上级
                ]
                
                for search_dir in search_paths:
                    potential_dfg_path = os.path.join(search_dir, 'dfg_files', dfg_base)
                    if os.path.exists(potential_dfg_path):
                        dfg_file_path = potential_dfg_path
                        found = True
                        break
                
                if not found:
                    raise ValueError(f"无法找到DFG文件 {dfg_base}，搜索路径: {search_paths}")
            else:
                raise ValueError(f"无法从分析文件名推断DFG文件路径: {analysis_filename}")
        
        # 解析DFG文件
        signals, binds = self.parse_dfg_file(dfg_file_path)
        
        # 创建图
        graph = nx.DiGraph()
        
        # 添加节点和属性
        for signal_name, signal_attr in signal_data.items():
            # 获取信号类型信息
            signal_types = signals.get(signal_name, ['Wire'])  # 默认为Wire类型
            
            # 添加节点属性
            node_attrs = {
                'is_linear': signal_attr['is_linear'],
                'reason': signal_attr['reason'], 
                'linearity_text': signal_attr['linearity_text'],
                'types': signal_types
            }
            
            graph.add_node(signal_name, **node_attrs)
        
        # 为没有在分析中的信号也添加节点（设为未知状态）
        for signal_name, signal_types in signals.items():
            if signal_name not in graph.nodes:
                graph.add_node(signal_name, 
                             is_linear=None, 
                             reason='未分析',
                             linearity_text='未知',
                             types=signal_types)
        
        # 添加边（依赖关系）
        for dest_signal, expression_tree in binds.items():
            dependencies = self.extract_dependencies(expression_tree)
            
            for dep_signal in dependencies:
                # 确保依赖的信号也在图中
                if dep_signal not in graph.nodes:
                    # 添加依赖信号节点（可能不在signals中，比如常量）
                    graph.add_node(dep_signal, 
                                 is_linear=None,
                                 reason='外部信号',
                                 linearity_text='未知',
                                 types=['Unknown'])
                
                # 添加从依赖信号到目标信号的边
                graph.add_edge(dep_signal, dest_signal)
        
        return graph
    
    def validate_graph_for_simulated_annealing(self, graph: nx.DiGraph) -> Dict[str, any]:
        """验证图是否适用于模拟退火算法
        
        Args:
            graph: 要验证的图
            
        Returns:
            验证结果和统计信息
        """
        validation_result = {
            'is_valid': True,
            'issues': [],
            'statistics': {}
        }
        
        # 检查节点属性
        nodes_with_linearity = 0
        linear_nodes = 0
        nonlinear_nodes = 0
        unknown_nodes = 0
        
        for node_name, node_data in graph.nodes(data=True):
            if 'is_linear' not in node_data:
                validation_result['issues'].append(f"节点 {node_name} 缺少 is_linear 属性")
                validation_result['is_valid'] = False
            else:
                nodes_with_linearity += 1
                if node_data['is_linear'] is True:
                    linear_nodes += 1
                elif node_data['is_linear'] is False:
                    nonlinear_nodes += 1
                else:
                    unknown_nodes += 1
        
        # 统计信息
        validation_result['statistics'] = {
            'total_nodes': graph.number_of_nodes(),
            'total_edges': graph.number_of_edges(),
            'nodes_with_linearity': nodes_with_linearity,
            'linear_nodes': linear_nodes,
            'nonlinear_nodes': nonlinear_nodes,
            'unknown_nodes': unknown_nodes,
            'is_connected': nx.is_connected(graph.to_undirected()) if graph.number_of_nodes() > 0 else False,
            'has_cycles': len(list(nx.simple_cycles(graph))) > 0
        }
        
        return validation_result


def convert_analysis_to_graph(analysis_file_path: str, 
                            dfg_file_path: Optional[str] = None,
                            validate: bool = True) -> Tuple[nx.DiGraph, Optional[Dict]]:
    """便利函数：将分析结果转换为图
    
    Args:
        analysis_file_path: 线性分析结果文件路径
        dfg_file_path: DFG文件路径（可选，会自动推断）
        validate: 是否验证生成的图
        
    Returns:
        Tuple of (graph, validation_result)
    """
    converter = LinearityAnalysisToGraphConverter()
    
    # 创建图
    graph = converter.create_graph_from_analysis(analysis_file_path, dfg_file_path)
    
    # 可选验证
    validation_result = None
    if validate:
        validation_result = converter.validate_graph_for_simulated_annealing(graph)
    
    return graph, validation_result


def main():
    """测试函数"""
    import sys
    
    # 测试转换器
    analysis_file = "/home/runner/work/ESIMULATOR/ESIMULATOR/results/4004_dfg_linearity_analysis.txt"
    
    try:
        print("正在转换线性分析结果到图格式...")
        graph, validation = convert_analysis_to_graph(analysis_file)
        
        print(f"\n转换成功!")
        print(f"节点数: {graph.number_of_nodes()}")
        print(f"边数: {graph.number_of_edges()}")
        
        if validation:
            print(f"\n验证结果:")
            print(f"图有效性: {'有效' if validation['is_valid'] else '无效'}")
            stats = validation['statistics']
            print(f"线性节点: {stats['linear_nodes']}")
            print(f"非线性节点: {stats['nonlinear_nodes']}")
            print(f"未知节点: {stats['unknown_nodes']}")
            print(f"连通性: {'连通' if stats['is_connected'] else '非连通'}")
            print(f"包含环: {'是' if stats['has_cycles'] else '否'}")
            
            if validation['issues']:
                print(f"\n问题:")
                for issue in validation['issues']:
                    print(f"  - {issue}")
        
        # 显示一些示例节点
        print(f"\n示例节点属性:")
        node_count = 0
        for node_name, node_data in graph.nodes(data=True):
            if node_count >= 5:
                break
            print(f"  {node_name}: {node_data}")
            node_count += 1
            
    except Exception as e:
        print(f"转换失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()