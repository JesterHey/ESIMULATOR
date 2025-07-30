#!/usr/bin/env python3
"""
改进的DFG到DAG转换器 - 支持环路检测和强连通分量分析
"""

import re
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional
import sys

@dataclass
class Signal:
    """信号节点"""
    name: str
    signal_type: List[str]
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
    connection_type: str
    operation: Optional[str] = None
    
    def __str__(self):
        op_str = f" ({self.operation})" if self.operation else ""
        return f"{self.source} -> {self.destination} [{self.connection_type}]{op_str}"

class ImprovedDFGParser:
    """改进的DFG解析器"""
    
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
        # 更精确的bind模式匹配
        bind_sections = content.split('Bind:')[1] if 'Bind:' in content else content
        
        # 使用递归下降解析器处理嵌套结构
        bind_entries = self._extract_bind_entries(bind_sections)
        
        for dest, tree_expr in bind_entries:
            dependencies = self._parse_expression_tree(tree_expr)
            
            for dep_signal in dependencies:
                if dep_signal != dest and (dep_signal in self.signals or dep_signal.startswith(('const_', 'op_'))):
                    self.connections.append(Connection(
                        source=dep_signal,
                        destination=dest,
                        connection_type='direct'
                    ))
    
    def _extract_bind_entries(self, content: str) -> List[Tuple[str, str]]:
        """提取Bind条目"""
        entries = []
        lines = content.strip().split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('(Bind dest:'):
                # 提取目标信号
                dest_match = re.search(r'dest:([^\s]+)', line)
                if dest_match:
                    dest = dest_match.group(1)
                    
                    # 查找tree部分
                    tree_start = line.find('tree:')
                    if tree_start != -1:
                        tree_expr = line[tree_start + 5:]
                        
                        # 处理多行表达式
                        paren_count = tree_expr.count('(') - tree_expr.count(')')
                        while paren_count > 0 and i + 1 < len(lines):
                            i += 1
                            next_line = lines[i].strip()
                            tree_expr += ' ' + next_line
                            paren_count += next_line.count('(') - next_line.count(')')
                        
                        # 移除最后的结束括号
                        if tree_expr.endswith(')'):
                            tree_expr = tree_expr[:-1]
                        
                        entries.append((dest, tree_expr))
            i += 1
        
        return entries
    
    def _parse_expression_tree(self, expr: str) -> Set[str]:
        """解析表达式树，提取所有引用的信号"""
        dependencies = set()
        
        # 移除外层括号
        expr = expr.strip()
        if expr.startswith('(') and expr.endswith(')'):
            expr = expr[1:-1]
        
        # 使用正则表达式提取所有Terminal引用
        terminal_pattern = r'Terminal\s+([^)]+)'
        for match in re.finditer(terminal_pattern, expr):
            signal_name = match.group(1).strip()
            dependencies.add(signal_name)
        
        # 提取IntConst（常量）
        const_pattern = r'IntConst\s+([^)]+)'
        const_counter = 0
        for match in re.finditer(const_pattern, expr):
            const_value = match.group(1).strip()
            dependencies.add(f'const_{const_counter}_{const_value}')
            const_counter += 1
        
        return dependencies

class GraphAnalyzer:
    """图分析器 - 处理有环图"""
    
    def __init__(self, signals: Dict[str, Signal], connections: List[Connection]):
        self.signals = signals
        self.connections = connections
        self.graph = defaultdict(list)
        self.reverse_graph = defaultdict(list)
        self.in_degree = defaultdict(int)
        
    def build_graph(self):
        """构建图结构"""
        for conn in self.connections:
            if conn.source != conn.destination:
                self.graph[conn.source].append(conn.destination)
                self.reverse_graph[conn.destination].append(conn.source)
                self.in_degree[conn.destination] += 1
                
                if conn.source not in self.in_degree:
                    self.in_degree[conn.source] = 0
        
        return self.graph, self.in_degree
    
    def find_strongly_connected_components(self) -> List[List[str]]:
        """使用Kosaraju算法找到强连通分量"""
        # 第一次DFS - 获得完成时间顺序
        visited = set()
        finish_order = []
        
        def dfs1(node):
            visited.add(node)
            for neighbor in self.graph[node]:
                if neighbor not in visited:
                    dfs1(neighbor)
            finish_order.append(node)
        
        for node in list(self.graph.keys()):
            if node not in visited:
                dfs1(node)
        
        # 第二次DFS - 在转置图上
        visited = set()
        sccs = []
        
        def dfs2(node, current_scc):
            visited.add(node)
            current_scc.append(node)
            for neighbor in self.reverse_graph[node]:
                if neighbor not in visited:
                    dfs2(neighbor, current_scc)
        
        for node in reversed(finish_order):
            if node not in visited:
                current_scc = []
                dfs2(node, current_scc)
                if len(current_scc) > 1:  # 只保留真正的强连通分量
                    sccs.append(current_scc)
        
        return sccs
    
    def modified_topological_sort(self) -> Tuple[List[str], List[List[str]]]:
        """改进的拓扑排序 - 识别并报告环路"""
        # 首先找出强连通分量
        sccs = self.find_strongly_connected_components()
        
        # 创建缩点图（将强连通分量看作单个节点）
        scc_map = {}  # 节点到SCC的映射
        for i, scc in enumerate(sccs):
            for node in scc:
                scc_map[node] = i
        
        # 执行修改的拓扑排序
        queue = deque()
        result = []
        temp_in_degree = self.in_degree.copy()
        
        # 找到入度为0的节点
        for node in temp_in_degree:
            if temp_in_degree[node] == 0:
                queue.append(node)
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for neighbor in self.graph[current]:
                temp_in_degree[neighbor] -= 1
                if temp_in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result, sccs
    
    def analyze_signal_hierarchy(self) -> Tuple[Dict[str, Dict], List[List[str]]]:
        """分析信号层次结构"""
        topo_order, sccs = self.modified_topological_sort()
        
        # 计算每个信号的层次级别
        levels = {}
        for i, signal in enumerate(topo_order):
            if signal in self.signals:
                levels[signal] = i
        
        # 分析依赖关系
        analysis = {}
        for signal_name, signal in self.signals.items():
            # 直接依赖
            direct_deps = [conn.source for conn in self.connections if conn.destination == signal_name]
            
            # 直接被依赖
            dependents = [conn.destination for conn in self.connections if conn.source == signal_name]
            
            # 计算扇入扇出
            fan_in = len(direct_deps)
            fan_out = len(dependents)
            
            analysis[signal_name] = {
                'signal_info': signal,
                'level': levels.get(signal_name, -1),
                'direct_dependencies': direct_deps,
                'dependents': dependents,
                'fan_in': fan_in,
                'fan_out': fan_out
            }
        
        return analysis, sccs

def main():
    """主函数"""
    dfg_file = "/Users/xuxiaolan/PycharmProjects/ESIMULATOR/dfg_files/4004_dfg.txt"
    
    print("=== 改进的DFG到DAG转换器 ===")
    
    # 1. 解析DFG
    print("1. 解析DFG文件...")
    parser = ImprovedDFGParser()
    signals, connections = parser.parse_dfg_file(dfg_file)
    
    print(f"   发现 {len(signals)} 个信号")
    print(f"   发现 {len(connections)} 个连接")
    
    # 2. 构建图并分析
    print("\n2. 构建图结构...")
    analyzer = GraphAnalyzer(signals, connections)
    graph, in_degree = analyzer.build_graph()
    
    print(f"   图节点数: {len(in_degree)}")
    print(f"   图边数: {len(connections)}")
    
    # 3. 查找强连通分量
    print("\n3. 分析强连通分量...")
    sccs = analyzer.find_strongly_connected_components()
    
    if sccs:
        print(f"   发现 {len(sccs)} 个强连通分量（环路）:")
        for i, scc in enumerate(sccs):
            print(f"     SCC {i+1}: {scc}")
    else:
        print("   未发现环路，图为DAG")
    
    # 4. 执行改进的拓扑排序
    print("\n4. 执行拓扑排序...")
    topo_order, _ = analyzer.modified_topological_sort()
    
    print(f"   排序完成，共 {len(topo_order)} 个节点")
    print("   前10个节点:", topo_order[:10])
    
    # 5. 分析信号层次结构
    print("\n5. 分析信号层次结构...")
    hierarchy_analysis, sccs_from_hierarchy = analyzer.analyze_signal_hierarchy()
    
    # 6. 生成详细报告
    print("\n6. 生成分析报告...")
    
    with open("4004_improved_dag_analysis.txt", "w", encoding="utf-8") as f:
        f.write("Intel 4004 ALU 改进DAG分析报告\n")
        f.write("=" * 50 + "\n\n")
        
        # 基本统计
        f.write("基本统计信息:\n")
        f.write("-" * 20 + "\n")
        f.write(f"总信号数: {len(signals)}\n")
        f.write(f"总连接数: {len(connections)}\n")
        f.write(f"图节点数: {len(in_degree)}\n")
        f.write(f"强连通分量数: {len(sccs)}\n\n")
        
        # 强连通分量分析
        if sccs:
            f.write("强连通分量（环路）分析:\n")
            f.write("-" * 25 + "\n")
            for i, scc in enumerate(sccs):
                f.write(f"SCC {i+1} (大小: {len(scc)}):\n")
                for node in scc:
                    if node in signals:
                        f.write(f"  - {node} ({','.join(signals[node].signal_type)})\n")
                    else:
                        f.write(f"  - {node}\n")
                f.write("\n")
        
        # 拓扑排序结果
        f.write("拓扑排序结果（前50个）:\n")
        f.write("-" * 30 + "\n")
        for i, node in enumerate(topo_order[:50]):
            level_info = f" (Level {hierarchy_analysis.get(node, {}).get('level', 'N/A')})" if node in hierarchy_analysis else ""
            f.write(f"{i+1:3d}. {node}{level_info}\n")
        
        # 信号层次分析
        f.write(f"\n信号层次分析:\n")
        f.write("-" * 15 + "\n")
        
        # 按类型分组
        by_type = defaultdict(list)
        for signal_name, info in hierarchy_analysis.items():
            signal_types = info['signal_info'].signal_type
            primary_type = signal_types[0] if signal_types else 'Unknown'
            by_type[primary_type].append((signal_name, info))
        
        for signal_type in sorted(by_type.keys()):
            f.write(f"\n{signal_type} 信号:\n")
            signals_of_type = sorted(by_type[signal_type], key=lambda x: x[1]['level'])
            
            for signal_name, info in signals_of_type[:10]:  # 只显示前10个
                f.write(f"  {signal_name:<30} Level:{info['level']:3d} FanIn:{info['fan_in']:2d} FanOut:{info['fan_out']:2d}\n")
            
            if len(signals_of_type) > 10:
                f.write(f"  ... 还有 {len(signals_of_type) - 10} 个 {signal_type} 信号\n")
        
        # 关键路径分析
        f.write(f"\n关键路径分析:\n")
        f.write("-" * 15 + "\n")
        
        # 找出扇入/扇出最大的信号
        max_fan_in = max(info['fan_in'] for info in hierarchy_analysis.values())
        max_fan_out = max(info['fan_out'] for info in hierarchy_analysis.values())
        
        high_fan_in = [name for name, info in hierarchy_analysis.items() if info['fan_in'] == max_fan_in]
        high_fan_out = [name for name, info in hierarchy_analysis.items() if info['fan_out'] == max_fan_out]
        
        f.write(f"最大扇入: {max_fan_in}\n")
        f.write(f"高扇入信号: {high_fan_in}\n")
        f.write(f"最大扇出: {max_fan_out}\n")
        f.write(f"高扇出信号: {high_fan_out}\n")
    
    # 7. 输出统计信息
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
    
    # 扇入扇出统计
    fan_in_stats = [info['fan_in'] for info in hierarchy_analysis.values()]
    fan_out_stats = [info['fan_out'] for info in hierarchy_analysis.values()]
    
    print(f"\n扇入统计: 平均={sum(fan_in_stats)/len(fan_in_stats):.1f}, 最大={max(fan_in_stats)}")
    print(f"扇出统计: 平均={sum(fan_out_stats)/len(fan_out_stats):.1f}, 最大={max(fan_out_stats)}")
    
    print(f"\n详细报告已保存到: 4004_improved_dag_analysis.txt")

if __name__ == "__main__":
    main()
