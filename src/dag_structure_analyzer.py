#!/usr/bin/env python3
"""
简化的DAG结构展示器
专门展示DAG的文本结构和层次关系
"""

import json
from collections import defaultdict, deque

class SimpleDAGAnalyzer:
    """简化的DAG分析器"""
    
    def __init__(self):
        self.signals = {}
        self.connections = []
        self.graph = defaultdict(list)
        self.reverse_graph = defaultdict(list)
        
    def load_data(self, json_file: str = "4004_signal_connections.json"):
        """加载数据"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.signals = data['signals']
        self.connections = data['connections']
        
        # 构建图结构
        for conn in self.connections:
            source = conn['source'] 
            dest = conn['destination']
            self.graph[source].append(dest)
            self.reverse_graph[dest].append(source)
    
    def topological_sort(self) -> list:
        """拓扑排序"""
        in_degree = defaultdict(int)
        
        # 计算入度
        for signal in self.signals:
            in_degree[signal] = 0
        
        for conn in self.connections:
            in_degree[conn['destination']] += 1
        
        # Kahn算法
        queue = deque([signal for signal, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for neighbor in self.graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    def analyze_layers(self) -> dict:
        """分析信号层次"""
        topo_order = self.topological_sort()
        
        # 计算每个信号的层次
        levels = {}
        for i, signal in enumerate(topo_order):
            levels[signal] = i
        
        # 按层次分组
        layers = defaultdict(list)
        for signal, level in levels.items():
            if signal.startswith('alu.') and not signal.startswith('alu.n0'):
                layers[level].append(signal)
        
        return dict(layers)
    
    def display_dag_structure(self):
        """显示DAG结构"""
        print("=== Intel 4004 ALU DAG结构分析 ===\n")
        
        # 基本统计
        main_signals = [s for s in self.signals.keys() 
                       if s.startswith('alu.') and not s.startswith('alu.n0')]
        
        print(f"信号总数: {len(self.signals)}")
        print(f"主要信号数: {len(main_signals)}")
        print(f"连接数: {len(self.connections)}")
        
        # 拓扑排序结果
        topo_order = self.topological_sort()
        main_topo = [s for s in topo_order if s in main_signals]
        
        print(f"\n=== 拓扑排序结果（主要信号，前20个）===")
        for i, signal in enumerate(main_topo[:20]):
            signal_info = self.signals[signal]
            category = signal_info['category']
            fan_in = signal_info['fan_in']
            fan_out = signal_info['fan_out']
            print(f"{i+1:2d}. {signal:<25} [{category:<15}] 扇入:{fan_in:2d} 扇出:{fan_out:2d}")
        
        if len(main_topo) > 20:
            print(f"    ... 还有 {len(main_topo) - 20} 个信号")
        
        # 层次分析
        layers = self.analyze_layers()
        print(f"\n=== 信号层次分布 ===")
        
        layer_keys = sorted([k for k in layers.keys() if layers[k]])[:10]  # 只显示前10层
        for layer_num in layer_keys:
            signals_in_layer = layers[layer_num]
            print(f"层次 {layer_num:2d}: {len(signals_in_layer)} 个信号")
            for signal in signals_in_layer[:5]:  # 每层最多显示5个
                category = self.signals[signal]['category']
                print(f"         {signal:<25} [{category}]")
            if len(signals_in_layer) > 5:
                print(f"         ... 还有 {len(signals_in_layer) - 5} 个信号")
            print()
        
        # 关键节点分析
        print("=== 关键节点分析 ===")
        
        # 计算复杂度
        complexity = [(signal, info['fan_in'] + info['fan_out']) 
                     for signal, info in self.signals.items() 
                     if signal.startswith('alu.') and not signal.startswith('alu.n0')]
        complexity.sort(key=lambda x: x[1], reverse=True)
        
        print("最复杂的10个信号（按扇入+扇出排序）:")
        for i, (signal, comp) in enumerate(complexity[:10]):
            signal_info = self.signals[signal]
            category = signal_info['category']
            fan_in = signal_info['fan_in']
            fan_out = signal_info['fan_out']
            print(f"{i+1:2d}. {signal:<25} [{category:<15}] 复杂度:{comp:2d} (扇入:{fan_in}, 扇出:{fan_out})")
        
        # 输入输出信号
        print(f"\n=== 接口信号 ===")
        
        inputs = [(s, info) for s, info in self.signals.items() 
                 if 'input' in info['category'].lower() and s.startswith('alu.')]
        outputs = [(s, info) for s, info in self.signals.items() 
                  if 'output' in info['category'].lower() and s.startswith('alu.')]
        
        print(f"输入信号 ({len(inputs)} 个):")
        for signal, info in sorted(inputs)[:10]:
            category = info['category']
            fan_out = info['fan_out']
            print(f"  {signal:<25} [{category:<15}] 扇出:{fan_out}")
        
        print(f"\n输出信号 ({len(outputs)} 个):")
        for signal, info in sorted(outputs):
            category = info['category']
            fan_in = info['fan_in']
            print(f"  {signal:<25} [{category:<15}] 扇入:{fan_in}")
    
    def generate_dag_text_report(self, filename: str = "results/dag_structure_report.txt"):
        """生成DAG结构文本报告"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("Intel 4004 ALU DAG结构详细报告\n")
            f.write("=" * 50 + "\n\n")
            
            # 完整拓扑排序
            topo_order = self.topological_sort()
            main_topo = [s for s in topo_order 
                        if s.startswith('alu.') and not s.startswith('alu.n0')]
            
            f.write("完整拓扑排序结果:\n")
            f.write("-" * 25 + "\n")
            for i, signal in enumerate(main_topo):
                signal_info = self.signals[signal]
                category = signal_info['category']
                fan_in = signal_info['fan_in']
                fan_out = signal_info['fan_out']
                f.write(f"{i+1:3d}. {signal:<30} [{category:<15}] 扇入:{fan_in:2d} 扇出:{fan_out:2d}\n")
            
            # 连接关系详情
            f.write(f"\n连接关系详情:\n")
            f.write("-" * 15 + "\n")
            
            main_connections = [conn for conn in self.connections 
                              if conn['source'].startswith('alu.') and 
                                 conn['destination'].startswith('alu.') and
                                 not conn['source'].startswith('alu.n0') and
                                 not conn['destination'].startswith('alu.n0')]
            
            for conn in main_connections:
                source = conn['source']
                dest = conn['destination']
                conn_type = conn['type']
                f.write(f"{source:<30} -> {dest:<30} [{conn_type}]\n")
            
            # DAG属性
            f.write(f"\nDAG属性分析:\n")
            f.write("-" * 15 + "\n")
            f.write(f"总节点数: {len(self.signals)}\n")
            f.write(f"主要节点数: {len(main_topo)}\n")
            f.write(f"总边数: {len(self.connections)}\n")
            f.write(f"主要边数: {len(main_connections)}\n")
            
            # 检查是否为DAG
            if len(topo_order) == len(self.signals):
                f.write("图类型: DAG (有向无环图)\n")
            else:
                f.write("图类型: 有向图 (包含环路)\n")
                f.write(f"成功排序节点数: {len(topo_order)}\n")

def main():
    """主函数"""
    analyzer = SimpleDAGAnalyzer()
    
    try:
        analyzer.load_data()
        analyzer.display_dag_structure()
        analyzer.generate_dag_text_report()
        print(f"\n详细报告已保存到: results/dag_structure_report.txt")
        
    except FileNotFoundError:
        print("错误：未找到 4004_signal_connections.json")
        print("请先运行 signal_connection_analyzer.py 生成数据文件")

if __name__ == "__main__":
    main()
