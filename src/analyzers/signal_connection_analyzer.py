#!/usr/bin/env python3
"""
专用信号连接关系分析器
专注于分析Intel 4004 ALU中真实硬件信号之间的连接关系
"""

import re
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional
import json

@dataclass
class HardwareSignal:
    """硬件信号"""
    name: str
    signal_type: List[str]
    width: int
    msb: Optional[int] = None
    lsb: Optional[int] = None
    
    def __str__(self):
        width_str = f"[{self.msb}:{self.lsb}]" if self.msb is not None else "[0:0]"
        return f"{self.name}{width_str} ({','.join(self.signal_type)})"
    
    @property
    def is_primary_signal(self) -> bool:
        """判断是否是主要硬件信号（非中间节点）"""
        return not (self.name.startswith(('const_', 'op_', 'alu.n0')) and 'Rename' not in self.signal_type)

@dataclass
class SignalConnection:
    """信号连接"""
    source: str
    destination: str
    connection_type: str
    is_combinational: bool = True
    is_critical_path: bool = False
    
    def __str__(self):
        path_indicator = " [CRITICAL]" if self.is_critical_path else ""
        logic_type = "COMB" if self.is_combinational else "SEQ"
        return f"{self.source} -> {self.destination} [{logic_type}]{path_indicator}"

class HardwareSignalAnalyzer:
    """硬件信号分析器"""
    
    def __init__(self):
        self.signals: Dict[str, HardwareSignal] = {}
        self.connections: List[SignalConnection] = []
        self.signal_graph = defaultdict(list)
        self.reverse_graph = defaultdict(list)
        
    def parse_dfg(self, file_path: str):
        """解析DFG文件，提取硬件信号信息"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self._extract_hardware_signals(content)
        self._extract_signal_connections(content)
        self._build_signal_graph()
        
    def _extract_hardware_signals(self, content: str):
        """提取硬件信号定义"""
        term_pattern = r'\(Term name:(alu\.[^\s]+) type:\[(.*?)\](?:\s+msb:\(IntConst (\d+)\))?\s*(?:lsb:\(IntConst (\d+)\))?\)'
        
        for match in re.finditer(term_pattern, content):
            name = match.group(1)
            signal_types = [t.strip().strip("'") for t in match.group(2).split(',')]
            msb = int(match.group(3)) if match.group(3) else 0
            lsb = int(match.group(4)) if match.group(4) else 0
            width = msb - lsb + 1 if msb is not None else 1
            
            signal = HardwareSignal(name, signal_types, width, msb, lsb)
            self.signals[name] = signal
    
    def _extract_signal_connections(self, content: str):
        """提取信号连接关系"""
        # 提取Bind部分
        bind_pattern = r'\(Bind dest:(alu\.[^\s]+)(?:[^)]*?tree:\s*(.*?))\)(?=\n\(Bind|\nBranch:|\n\n|\Z)'
        
        for match in re.finditer(bind_pattern, content, re.DOTALL):
            dest_signal = match.group(1)
            tree_expr = match.group(2) if match.group(2) else ""
            
            # 从表达式中提取源信号
            source_signals = self._parse_expression_for_signals(tree_expr)
            
            for source_signal in source_signals:
                if source_signal in self.signals and source_signal != dest_signal:
                    # 判断连接类型
                    is_combinational = self._is_combinational_logic(dest_signal, tree_expr)
                    
                    connection = SignalConnection(
                        source=source_signal,
                        destination=dest_signal,
                        connection_type='combinational' if is_combinational else 'sequential',
                        is_combinational=is_combinational
                    )
                    self.connections.append(connection)
    
    def _parse_expression_for_signals(self, expr: str) -> Set[str]:
        """从表达式中提取信号引用"""
        signals = set()
        
        # 提取Terminal引用的信号
        terminal_pattern = r'Terminal\s+(alu\.[^\s)]+)'
        for match in re.finditer(terminal_pattern, expr):
            signal_name = match.group(1)
            if signal_name in self.signals:
                signals.add(signal_name)
        
        return signals
    
    def _is_combinational_logic(self, dest_signal: str, expr: str) -> bool:
        """判断是否为组合逻辑"""
        if dest_signal not in self.signals:
            return True
        
        dest_types = self.signals[dest_signal].signal_type
        
        # 寄存器信号通常涉及时序逻辑
        if 'Reg' in dest_types:
            return False
        
        # Wire信号通常是组合逻辑
        if 'Wire' in dest_types:
            return True
        
        # 检查表达式中是否有时钟相关信号
        clock_patterns = ['clk', 'sysclk', 'clock']
        for pattern in clock_patterns:
            if pattern in expr.lower():
                return False
        
        return True
    
    def _build_signal_graph(self):
        """构建信号图"""
        for conn in self.connections:
            self.signal_graph[conn.source].append(conn.destination)
            self.reverse_graph[conn.destination].append(conn.source)
    
    def analyze_signal_hierarchy(self) -> Dict[str, Dict]:
        """分析信号层次结构"""
        # 执行拓扑排序获得信号层次
        topo_order = self._topological_sort()
        
        # 创建信号分析结果
        analysis = {}
        
        for signal_name, signal in self.signals.items():
            if not signal.is_primary_signal:
                continue
                
            # 计算信号层次级别
            level = topo_order.index(signal_name) if signal_name in topo_order else -1
            
            # 直接输入信号
            direct_inputs = [conn.source for conn in self.connections 
                           if conn.destination == signal_name]
            
            # 直接输出信号
            direct_outputs = [conn.destination for conn in self.connections 
                            if conn.source == signal_name]
            
            # 计算扇入扇出
            fan_in = len(direct_inputs)
            fan_out = len(direct_outputs)
            
            # 判断信号类型
            signal_category = self._categorize_signal(signal)
            
            analysis[signal_name] = {
                'signal': signal,
                'category': signal_category,
                'level': level,
                'direct_inputs': direct_inputs,
                'direct_outputs': direct_outputs,
                'fan_in': fan_in,
                'fan_out': fan_out,
                'is_critical': fan_in > 5 or fan_out > 5
            }
        
        return analysis
    
    def _topological_sort(self) -> List[str]:
        """拓扑排序"""
        in_degree = defaultdict(int)
        
        # 计算入度
        for signal in self.signals:
            in_degree[signal] = 0
        
        for conn in self.connections:
            in_degree[conn.destination] += 1
        
        # Kahn算法
        queue = deque([signal for signal, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for neighbor in self.signal_graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    def _categorize_signal(self, signal: HardwareSignal) -> str:
        """对信号进行分类"""
        signal_types = signal.signal_type
        name = signal.name.lower()
        
        if 'Input' in signal_types:
            if 'clk' in name or 'clock' in name:
                return 'clock_input'
            elif 'data' in name:
                return 'data_input'
            elif any(x in name for x in ['ctrl', 'control', 'cmd']):
                return 'control_input'
            else:
                return 'general_input'
        
        elif 'Output' in signal_types:
            if 'data' in name:
                return 'data_output'
            elif any(x in name for x in ['flag', 'status']):
                return 'status_output'
            else:
                return 'general_output'
        
        elif 'Reg' in signal_types:
            if 'acc' in name:
                return 'accumulator'
            elif 'tmp' in name:
                return 'temporary_register'
            elif 'cy' in name:
                return 'carry_flag'
            else:
                return 'internal_register'
        
        elif 'Wire' in signal_types:
            if any(x in name for x in ['add', 'sub', 'mul', 'div']):
                return 'arithmetic_wire'
            elif any(x in name for x in ['and', 'or', 'xor', 'not']):
                return 'logic_wire'
            else:
                return 'internal_wire'
        
        else:
            return 'other'
    
    def find_critical_paths(self) -> List[List[str]]:
        """找到关键路径"""
        # 简化的关键路径查找 - 找到从输入到输出的最长路径
        input_signals = [name for name, signal in self.signals.items() 
                        if 'Input' in signal.signal_type]
        output_signals = [name for name, signal in self.signals.items() 
                         if 'Output' in signal.signal_type]
        
        critical_paths = []
        
        for input_sig in input_signals:
            for output_sig in output_signals:
                path = self._find_path(input_sig, output_sig)
                if path and len(path) > 3:  # 只保留较长的路径
                    critical_paths.append(path)
        
        # 按路径长度排序，返回最长的几条
        critical_paths.sort(key=len, reverse=True)
        return critical_paths[:5]
    
    def _find_path(self, start: str, end: str) -> Optional[List[str]]:
        """使用BFS查找两个信号之间的路径"""
        if start == end:
            return [start]
        
        queue = deque([(start, [start])])
        visited = {start}
        
        while queue:
            current, path = queue.popleft()
            
            for neighbor in self.signal_graph[current]:
                if neighbor == end:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def generate_connection_summary(self) -> Tuple[Dict, Dict[str, Dict]]:
        """生成连接关系总结"""
        analysis = self.analyze_signal_hierarchy()
        critical_paths = self.find_critical_paths()
        
        # 按类别统计信号
        category_stats = defaultdict(int)
        for info in analysis.values():
            category_stats[info['category']] += 1
        
        # 统计连接类型
        connection_stats = defaultdict(int)
        for conn in self.connections:
            connection_stats[conn.connection_type] += 1
        
        # 识别关键信号
        critical_signals = [name for name, info in analysis.items() 
                          if info['is_critical']]
        
        summary = {
            'total_signals': len(self.signals),
            'primary_signals': len(analysis),
            'total_connections': len(self.connections),
            'category_distribution': dict(category_stats),
            'connection_type_distribution': dict(connection_stats),
            'critical_signals': critical_signals[:10],
            'critical_paths': critical_paths,
            'max_fan_in': max(info['fan_in'] for info in analysis.values()) if analysis else 0,
            'max_fan_out': max(info['fan_out'] for info in analysis.values()) if analysis else 0
        }
        
        return summary, analysis

def main():
    """主函数"""
    dfg_file = "/Users/xuxiaolan/PycharmProjects/ESIMULATOR/dfg_files/4004_dfg.txt"
    
    print("=== Intel 4004 ALU 信号连接关系分析器 ===")
    
    # 1. 创建分析器并解析DFG
    print("1. 解析DFG文件...")
    analyzer = HardwareSignalAnalyzer()
    analyzer.parse_dfg(dfg_file)
    
    print(f"   发现 {len(analyzer.signals)} 个硬件信号")
    print(f"   发现 {len(analyzer.connections)} 个连接")
    
    # 2. 生成连接分析
    print("\n2. 分析信号连接关系...")
    summary, detailed_analysis = analyzer.generate_connection_summary()
    
    # 3. 输出分析结果
    print("\n3. 生成分析报告...")
    
    # 生成详细报告
    with open("4004_signal_connection_analysis.txt", "w", encoding="utf-8") as f:
        f.write("Intel 4004 ALU 信号连接关系分析报告\n")
        f.write("=" * 50 + "\n\n")
        
        # 概述
        f.write("分析概述:\n")
        f.write("-" * 15 + "\n")
        f.write(f"总信号数: {summary['total_signals']}\n")
        f.write(f"主要信号数: {summary['primary_signals']}\n")
        f.write(f"连接数: {summary['total_connections']}\n")
        f.write(f"最大扇入: {summary['max_fan_in']}\n")
        f.write(f"最大扇出: {summary['max_fan_out']}\n\n")
        
        # 信号分类统计
        f.write("信号分类分布:\n")
        f.write("-" * 15 + "\n")
        for category, count in sorted(summary['category_distribution'].items()):
            f.write(f"{category}: {count}\n")
        f.write("\n")
        
        # 连接类型统计
        f.write("连接类型分布:\n")
        f.write("-" * 15 + "\n")
        for conn_type, count in summary['connection_type_distribution'].items():
            f.write(f"{conn_type}: {count}\n")
        f.write("\n")
        
        # 关键信号
        f.write("关键信号 (高扇入/扇出):\n")
        f.write("-" * 25 + "\n")
        for signal_name in summary['critical_signals']:
            if signal_name in detailed_analysis:
                info = detailed_analysis[signal_name]
                f.write(f"{signal_name:<30} 类别:{info['category']:<15} 扇入:{info['fan_in']:2d} 扇出:{info['fan_out']:2d}\n")
        f.write("\n")
        
        # 关键路径
        f.write("关键路径分析:\n")
        f.write("-" * 15 + "\n")
        for i, path in enumerate(summary['critical_paths'], 1):
            f.write(f"路径 {i} (长度: {len(path)}):\n")
            for j, signal in enumerate(path):
                prefix = "  " + ("└─ " if j == len(path)-1 else "├─ ")
                category = detailed_analysis.get(signal, {}).get('category', 'unknown')
                f.write(f"{prefix}{signal} ({category})\n")
            f.write("\n")
        
        # 详细信号分析（按类别分组）
        f.write("详细信号分析:\n")
        f.write("-" * 15 + "\n")
        
        # 按类别分组
        by_category = defaultdict(list)
        for signal_name, info in detailed_analysis.items():
            by_category[info['category']].append((signal_name, info))
        
        for category in sorted(by_category.keys()):
            f.write(f"\n{category.upper()} 信号:\n")
            signals_in_category = sorted(by_category[category], 
                                       key=lambda x: x[1]['fan_in'] + x[1]['fan_out'], 
                                       reverse=True)
            
            for signal_name, info in signals_in_category:
                f.write(f"  {signal_name:<35}")
                f.write(f" 扇入:{info['fan_in']:2d} 扇出:{info['fan_out']:2d}")
                if info['direct_inputs']:
                    f.write(f" ← {info['direct_inputs'][:3]}")
                    if len(info['direct_inputs']) > 3:
                        f.write(f" (+{len(info['direct_inputs'])-3} more)")
                f.write("\n")
    
    # 4. 生成JSON格式的结构化数据
    with open("4004_signal_connections.json", "w", encoding="utf-8") as f:
        # 准备JSON数据
        json_data = {
            'summary': summary,
            'signals': {
                name: {
                    'type': info['signal'].signal_type,
                    'width': info['signal'].width,
                    'category': info['category'],
                    'fan_in': info['fan_in'],
                    'fan_out': info['fan_out'],
                    'direct_inputs': info['direct_inputs'],
                    'direct_outputs': info['direct_outputs']
                } for name, info in detailed_analysis.items()
            },
            'connections': [
                {
                    'source': conn.source,
                    'destination': conn.destination,
                    'type': conn.connection_type,
                    'is_combinational': conn.is_combinational
                } for conn in analyzer.connections
            ]
        }
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    # 5. 输出关键发现
    print("\n4. 关键发现:")
    print("-" * 15)
    print(f"主要信号分布:")
    for category, count in sorted(summary['category_distribution'].items()):
        print(f"  {category}: {count}")
    
    print(f"\n最复杂信号 (按扇入+扇出排序):")
    complexity_ranking = [(name, info['fan_in'] + info['fan_out']) 
                         for name, info in detailed_analysis.items()]
    complexity_ranking.sort(key=lambda x: x[1], reverse=True)
    
    for signal_name, complexity in complexity_ranking[:5]:
        info = detailed_analysis[signal_name]
        print(f"  {signal_name:<30} 复杂度:{complexity:3d} ({info['category']})")
    
    print(f"\n关键路径数量: {len(summary['critical_paths'])}")
    if summary['critical_paths']:
        longest_path = summary['critical_paths'][0]
        print(f"最长路径长度: {len(longest_path)} ({longest_path[0]} -> {longest_path[-1]})")
    
    print(f"\n报告文件:")
    print(f"  详细分析: 4004_signal_connection_analysis.txt")
    print(f"  结构化数据: 4004_signal_connections.json")

if __name__ == "__main__":
    main()
