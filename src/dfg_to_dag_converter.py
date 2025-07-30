#!/usr/bin/env python3
"""
DFG to DAG Converter with Topological Sorting
将DFG文本转换为有向无环图并进行拓扑排序以分析信号连接关系
"""

import re
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional
import graphviz

@dataclass
class Signal:
    """信号节点"""
    name: str
    signal_type: List[str]  # ['Input', 'Wire'], ['Reg'], etc.
    msb: Optional[int] = None
    lsb: Optional[int] = None
    
    def __str__(self):
        width = f"[{self.msb}:{self.lsb}]" if self.msb is not None else ""
        return f"{self.name}{width} ({','.join(self.signal_type)})"

@dataclass
class Connection:
    """连接关系"""
    source: str
    destination: str
    connection_type: str  # 'direct', 'operator', 'branch', etc.
    operation: Optional[str] = None
    
    def __str__(self):
        op_str = f" ({self.operation})" if self.operation else ""
        return f"{self.source} -> {self.destination} [{self.connection_type}]{op_str}"

class DFGParser:
    """DFG解析器"""
    
    def __init__(self):
        self.signals: Dict[str, Signal] = {}
        self.connections: List[Connection] = []
        
    def parse_dfg_file(self, file_path: str):
        """解析DFG文件"""
        with open(file_path, 'r') as f:
            content = f.read()
        
        # 解析Term部分
        self._parse_terms(content)
        
        # 解析Bind部分
        self._parse_binds(content)
        
        return self.signals, self.connections
    
    def _parse_terms(self, content: str):
        """解析Term定义"""
        term_pattern = r'\(Term name:([^\s]+) type:\[(.*?)\](?:\s+msb:\(IntConst (\d+)\))?\s*(?:lsb:\(IntConst (\d+)\))?\)'
        
        for match in re.finditer(term_pattern, content):
            name = match.group(1)
            signal_types = [t.strip().strip("'") for t in match.group(2).split(',')]
            msb = int(match.group(3)) if match.group(3) else None
            lsb = int(match.group(4)) if match.group(4) else None
            
            self.signals[name] = Signal(name, signal_types, msb, lsb)
    
    def _parse_binds(self, content: str):
        """解析Bind绑定关系"""
        bind_pattern = r'\(Bind dest:([^\s]+)(?:\s+msb:\(IntConst \d+\))?\s*(?:lsb:\(IntConst \d+\))?\s+tree:(.*?)\)(?=\n\(Bind|\nBranch:|\Z)'
        
        for match in re.finditer(bind_pattern, content, re.DOTALL):
            dest = match.group(1)
            tree_expr = match.group(2)
            
            # 从表达式中提取依赖的信号
            dependencies = self._extract_dependencies(tree_expr)
            
            for dep in dependencies:
                if dep['signal'] in self.signals or dep['signal'].startswith('IntConst'):
                    self.connections.append(Connection(
                        source=dep['signal'],
                        destination=dest,
                        connection_type=dep['type'],
                        operation=dep.get('operation')
                    ))
    
    def _extract_dependencies(self, expr: str) -> List[Dict]:
        """从表达式中提取依赖关系"""
        dependencies = []
        
        # 提取Terminal引用
        terminal_pattern = r'\(Terminal ([^)]+)\)'
        for match in re.finditer(terminal_pattern, expr):
            dependencies.append({
                'signal': match.group(1),
                'type': 'direct',
                'operation': None
            })
        
        # 提取操作符
        operator_pattern = r'\(Operator (\w+) Next:'
        for match in re.finditer(operator_pattern, expr):
            op_type = match.group(1)
            # 这里需要进一步解析操作符的操作数
            dependencies.append({
                'signal': f'op_{op_type}',
                'type': 'operator',
                'operation': op_type
            })
        
        # 提取常量
        const_pattern = r'\(IntConst ([^)]+)\)'
        for match in re.finditer(const_pattern, expr):
            dependencies.append({
                'signal': f'const_{match.group(1)}',
                'type': 'constant',
                'operation': None
            })
        
        # 提取分支条件
        branch_pattern = r'\(Branch Cond:\(Terminal ([^)]+)\)'
        for match in re.finditer(branch_pattern, expr):
            dependencies.append({
                'signal': match.group(1),
                'type': 'branch_condition',
                'operation': 'branch'
            })
        
        return dependencies

class DAGBuilder:
    """DAG构建器"""
    
    def __init__(self, signals: Dict[str, Signal], connections: List[Connection]):
        self.signals = signals
        self.connections = connections
        self.graph = defaultdict(list)  # adjacency list
        self.in_degree = defaultdict(int)
        self.signal_connections = defaultdict(list)
        
    def build_dag(self):
        """构建DAG"""
        # 构建邻接表和入度统计
        for conn in self.connections:
            if conn.source != conn.destination:  # 避免自环
                self.graph[conn.source].append(conn.destination)
                self.in_degree[conn.destination] += 1
                self.signal_connections[conn.destination].append(conn)
                
                # 确保源节点也在入度统计中
                if conn.source not in self.in_degree:
                    self.in_degree[conn.source] = 0
        
        return self.graph, self.in_degree
    
    def topological_sort(self) -> List[str]:
        """拓扑排序"""
        # Kahn算法
        queue = deque()
        result = []
        temp_in_degree = self.in_degree.copy()
        
        # 找到所有入度为0的节点
        for node in temp_in_degree:
            if temp_in_degree[node] == 0:
                queue.append(node)
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            # 更新邻居节点的入度
            for neighbor in self.graph[current]:
                temp_in_degree[neighbor] -= 1
                if temp_in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 检查是否存在环
        if len(result) != len(temp_in_degree):
            print("Warning: 检测到环路，可能不是完全的DAG")
        
        return result
    
    def analyze_signal_dependencies(self) -> Dict[str, Dict]:
        """分析信号依赖关系"""
        analysis = {}
        
        for signal_name, signal in self.signals.items():
            # 直接依赖
            direct_deps = [conn.source for conn in self.signal_connections[signal_name]]
            
            # 间接依赖 (通过DFS)
            indirect_deps = self._find_indirect_dependencies(signal_name)
            
            # 被依赖的信号
            dependents = [dest for dest in self.graph[signal_name]]
            
            analysis[signal_name] = {
                'signal_info': signal,
                'direct_dependencies': direct_deps,
                'indirect_dependencies': indirect_deps,
                'dependents': dependents,
                'connections': self.signal_connections[signal_name]
            }
        
        return analysis
    
    def _find_indirect_dependencies(self, signal: str, visited: Optional[Set[str]] = None) -> Set[str]:
        """递归查找间接依赖"""
        if visited is None:
            visited = set()
        
        if signal in visited:
            return set()
        
        visited.add(signal)
        indirect = set()
        
        # 获取直接依赖
        for conn in self.signal_connections[signal]:
            dep = conn.source
            if dep not in visited:
                indirect.add(dep)
                # 递归查找更深层的依赖
                indirect.update(self._find_indirect_dependencies(dep, visited.copy()))
        
        return indirect

class DAGVisualizer:
    """DAG可视化器"""
    
    def __init__(self, dag_builder: DAGBuilder):
        self.dag_builder = dag_builder
    
    def generate_dot_graph(self, output_file: str = "dfg_dag"):
        """生成Graphviz DOT图"""
        dot = graphviz.Digraph(comment="DFG DAG")
        dot.attr(rankdir='TB')
        
        # 添加节点
        for signal_name, signal in self.dag_builder.signals.items():
            # 根据信号类型设置颜色
            color = self._get_node_color(signal.signal_type)
            label = f"{signal_name}\\n({','.join(signal.signal_type)})"
            if signal.msb is not None:
                label += f"\\n[{signal.msb}:{signal.lsb}]"
            
            dot.node(signal_name, label=label, style='filled', fillcolor=color)
        
        # 添加边
        for conn in self.dag_builder.connections:
            edge_color = self._get_edge_color(conn.connection_type)
            label = conn.operation if conn.operation else ""
            dot.edge(conn.source, conn.destination, label=label, color=edge_color)
        
        # 保存图形
        dot.render(output_file, format='png', cleanup=True)
        dot.save(f"{output_file}.dot")
        
        return dot
    
    def _get_node_color(self, signal_types: List[str]) -> str:
        """根据信号类型获取节点颜色"""
        if 'Input' in signal_types:
            return 'lightblue'
        elif 'Output' in signal_types:
            return 'lightgreen'
        elif 'Reg' in signal_types:
            return 'lightyellow'
        elif 'Wire' in signal_types:
            return 'lightgray'
        else:
            return 'white'
    
    def _get_edge_color(self, connection_type: str) -> str:
        """根据连接类型获取边颜色"""
        color_map = {
            'direct': 'black',
            'operator': 'blue',
            'branch_condition': 'red',
            'constant': 'gray'
        }
        return color_map.get(connection_type, 'black')

def main():
    """主函数"""
    dfg_file = "/Users/xuxiaolan/PycharmProjects/ESIMULATOR/dfg_files/4004_dfg.txt"
    
    print("=== DFG到DAG转换器 ===")
    
    # 1. 解析DFG
    print("1. 解析DFG文件...")
    parser = DFGParser()
    signals, connections = parser.parse_dfg_file(dfg_file)
    
    print(f"   发现 {len(signals)} 个信号")
    print(f"   发现 {len(connections)} 个连接")
    
    # 2. 构建DAG
    print("\n2. 构建DAG...")
    dag_builder = DAGBuilder(signals, connections)
    graph, in_degree = dag_builder.build_dag()
    
    print(f"   DAG节点数: {len(in_degree)}")
    print(f"   DAG边数: {sum(len(neighbors) for neighbors in graph.values())}")
    
    # 3. 拓扑排序
    print("\n3. 执行拓扑排序...")
    topo_order = dag_builder.topological_sort()
    
    print(f"   拓扑排序完成，共 {len(topo_order)} 个节点")
    print("   前10个节点:", topo_order[:10])
    
    # 4. 分析信号依赖关系
    print("\n4. 分析信号依赖关系...")
    dependencies = dag_builder.analyze_signal_dependencies()
    
    # 5. 输出分析报告
    print("\n5. 生成分析报告...")
    
    # 生成详细报告
    with open("4004_dag_analysis_report.txt", "w", encoding="utf-8") as f:
        f.write("Intel 4004 ALU DFG到DAG分析报告\n")
        f.write("=" * 50 + "\n\n")
        
        f.write("拓扑排序结果:\n")
        f.write("-" * 20 + "\n")
        for i, node in enumerate(topo_order):
            f.write(f"{i+1:3d}. {node}\n")
        
        f.write(f"\n信号依赖关系分析:\n")
        f.write("-" * 20 + "\n")
        
        for signal_name in sorted(dependencies.keys()):
            if signal_name in signals:  # 只分析真实的信号
                dep_info = dependencies[signal_name]
                signal_info = dep_info['signal_info']
                
                f.write(f"\n信号: {signal_info}\n")
                f.write(f"  直接依赖 ({len(dep_info['direct_dependencies'])}): {dep_info['direct_dependencies']}\n")
                f.write(f"  间接依赖 ({len(dep_info['indirect_dependencies'])}): {list(dep_info['indirect_dependencies'])}\n")
                f.write(f"  被依赖者 ({len(dep_info['dependents'])}): {dep_info['dependents']}\n")
                
                if dep_info['connections']:
                    f.write("  连接详情:\n")
                    for conn in dep_info['connections']:
                        f.write(f"    {conn}\n")
    
    # 6. 生成可视化图形
    print("\n6. 生成可视化图形...")
    try:
        visualizer = DAGVisualizer(dag_builder)
        dot_graph = visualizer.generate_dot_graph("4004_dfg_dag")
        print("   已生成 4004_dfg_dag.png 和 4004_dfg_dag.dot")
    except Exception as e:
        print(f"   可视化生成失败: {e}")
        print("   请安装graphviz: pip install graphviz")
    
    # 7. 统计信息
    print("\n7. 统计信息:")
    print("-" * 20)
    
    # 按信号类型统计
    type_stats = defaultdict(int)
    for signal in signals.values():
        for signal_type in signal.signal_type:
            type_stats[signal_type] += 1
    
    print("信号类型统计:")
    for sig_type, count in sorted(type_stats.items()):
        print(f"  {sig_type}: {count}")
    
    # 按连接类型统计
    conn_type_stats = defaultdict(int)
    for conn in connections:
        conn_type_stats[conn.connection_type] += 1
    
    print("\n连接类型统计:")
    for conn_type, count in sorted(conn_type_stats.items()):
        print(f"  {conn_type}: {count}")
    
    # 关键路径分析
    print("\n关键路径分析:")
    max_deps = max(len(dep['indirect_dependencies']) for dep in dependencies.values() if dep['signal_info'].name in signals)
    critical_signals = [name for name, dep in dependencies.items() 
                       if dep['signal_info'].name in signals and len(dep['indirect_dependencies']) == max_deps]
    
    print(f"  最大依赖深度: {max_deps}")
    print(f"  关键信号: {critical_signals[:5]}")  # 显示前5个
    
    print(f"\n报告已保存到: 4004_dag_analysis_report.txt")

if __name__ == "__main__":
    main()
