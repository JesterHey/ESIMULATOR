#!/usr/bin/env python3
"""
DFG线性/非线性运算分析器
从数据流图中识别和分离线性与非线性运算部分
"""

from improved_dfg_parser import *
from typing import Set, Dict, List, Tuple
from enum import Enum


class ComputationType(Enum):
    """运算类型分类"""
    LINEAR = "线性运算"           # 加法、减法、位运算、移位
    NONLINEAR = "非线性运算"     # 乘法、除法、模运算
    CONTROL = "控制逻辑"         # 分支、选择、比较
    STORAGE = "存储更新"         # 寄存器赋值
    COMBINATIONAL = "组合逻辑"   # 纯组合运算


class OperationAnalyzer:
    """运算分析器"""
    
    def __init__(self):
        # 线性运算符
        self.linear_ops = {
            OperatorType.PLUS, OperatorType.MINUS, 
            OperatorType.AND, OperatorType.OR, OperatorType.XOR
        }
        
        # 非线性运算符
        self.nonlinear_ops = {
            OperatorType.TIMES, OperatorType.MOD
        }
        
        # 控制运算符
        self.control_ops = {
            OperatorType.EQ
        }
    
    def classify_operation(self, node: Union[Operator, Terminal, IntConst, Branch]) -> ComputationType:
        """分类运算类型"""
        if isinstance(node, IntConst):
            return ComputationType.COMBINATIONAL
        
        elif isinstance(node, Terminal):
            return ComputationType.COMBINATIONAL
        
        elif isinstance(node, Operator):
            if node.op_type in self.linear_ops:
                return ComputationType.LINEAR
            elif node.op_type in self.nonlinear_ops:
                return ComputationType.NONLINEAR
            elif node.op_type in self.control_ops:
                return ComputationType.CONTROL
            else:
                return ComputationType.COMBINATIONAL
        
        elif isinstance(node, Branch):
            return ComputationType.CONTROL
        
        return ComputationType.COMBINATIONAL
    
    def analyze_expression_complexity(self, node: Union[Operator, Terminal, IntConst, Branch]) -> Dict[str, int]:
        """分析表达式复杂度"""
        complexity = {
            "linear_ops": 0,
            "nonlinear_ops": 0,
            "control_ops": 0,
            "depth": 0
        }
        
        def traverse(node, depth=0):
            complexity["depth"] = max(complexity["depth"], depth)
            
            if isinstance(node, Operator):
                if node.op_type in self.linear_ops:
                    complexity["linear_ops"] += 1
                elif node.op_type in self.nonlinear_ops:
                    complexity["nonlinear_ops"] += 1
                elif node.op_type in self.control_ops:
                    complexity["control_ops"] += 1
                
                for operand in node.operands:
                    traverse(operand, depth + 1)
            
            elif isinstance(node, Branch):
                complexity["control_ops"] += 1
                traverse(node.condition, depth + 1)
                traverse(node.true_branch, depth + 1)
                if node.false_branch:
                    traverse(node.false_branch, depth + 1)
        
        traverse(node)
        return complexity


class DFGLinearityAnalyzer:
    """DFG线性度分析器"""
    
    def __init__(self, dfg: DFG):
        self.dfg = dfg
        self.analyzer = OperationAnalyzer()
        self.linear_binds = []
        self.nonlinear_binds = []
        self.control_binds = []
        self.storage_binds = []
    
    def analyze(self):
        """执行完整分析"""
        self._classify_bindings()
        self._analyze_data_paths()
        self._identify_critical_paths()
    
    def _classify_bindings(self):
        """分类绑定关系"""
        for bind in self.dfg.binds:
            op_type = self.analyzer.classify_operation(bind.tree)
            complexity = self.analyzer.analyze_expression_complexity(bind.tree)
            
            bind_info = {
                'bind': bind,
                'type': op_type,
                'complexity': complexity
            }
            
            # 判断是否为存储操作（目标是寄存器）
            target_term = self.dfg.get_term_by_name(bind.dest)
            if target_term and TermType.REG in target_term.types:
                self.storage_binds.append(bind_info)
            elif op_type == ComputationType.LINEAR:
                self.linear_binds.append(bind_info)
            elif op_type == ComputationType.NONLINEAR:
                self.nonlinear_binds.append(bind_info)
            elif op_type == ComputationType.CONTROL:
                self.control_binds.append(bind_info)
    
    def _analyze_data_paths(self):
        """分析数据路径"""
        self.data_paths = {
            'linear_paths': [],
            'nonlinear_paths': [],
            'mixed_paths': []
        }
        
        # 追踪从输入到输出的路径
        inputs = [t for t in self.dfg.terms if TermType.INPUT in t.types]
        outputs = [t for t in self.dfg.terms if TermType.OUTPUT in t.types]
        
        for output in outputs:
            path = self._trace_path_to_output(output.name)
            if path:
                path_type = self._classify_path(path)
                self.data_paths[path_type].append({
                    'output': output.name,
                    'path': path
                })
    
    def _trace_path_to_output(self, signal_name: str) -> List[str]:
        """追踪到输出的路径"""
        path = []
        visited = set()
        
        def trace_recursive(sig_name):
            if sig_name in visited:
                return
            visited.add(sig_name)
            path.append(sig_name)
            
            # 查找生成此信号的绑定
            bind = self.dfg.get_bind_by_dest(sig_name)
            if bind:
                # 提取依赖的信号
                deps = self._extract_dependencies(bind.tree)
                for dep in deps:
                    trace_recursive(dep)
        
        trace_recursive(signal_name)
        return path
    
    def _extract_dependencies(self, node: Union[Operator, Terminal, IntConst, Branch]) -> List[str]:
        """提取节点的依赖信号"""
        deps = []
        
        def extract_recursive(node):
            if isinstance(node, Terminal):
                deps.append(node.name)
            elif isinstance(node, Operator):
                for operand in node.operands:
                    extract_recursive(operand)
            elif isinstance(node, Branch):
                extract_recursive(node.condition)
                extract_recursive(node.true_branch)
                if node.false_branch:
                    extract_recursive(node.false_branch)
        
        extract_recursive(node)
        return deps
    
    def _classify_path(self, path: List[str]) -> str:
        """对路径进行分类"""
        has_linear = False
        has_nonlinear = False
        
        for signal in path:
            bind = self.dfg.get_bind_by_dest(signal)
            if bind:
                op_type = self.analyzer.classify_operation(bind.tree)
                if op_type == ComputationType.LINEAR:
                    has_linear = True
                elif op_type == ComputationType.NONLINEAR:
                    has_nonlinear = True
        
        if has_nonlinear and has_linear:
            return 'mixed_paths'
        elif has_nonlinear:
            return 'nonlinear_paths'
        elif has_linear:
            return 'linear_paths'
        else:
            return 'linear_paths'  # 默认分类
    
    def _identify_critical_paths(self):
        """识别关键路径"""
        self.critical_paths = []
        
        # 基于复杂度识别关键路径
        for bind_info in self.nonlinear_binds + self.control_binds:
            complexity = bind_info['complexity']
            if (complexity['nonlinear_ops'] > 0 or 
                complexity['control_ops'] > 2 or 
                complexity['depth'] > 3):
                self.critical_paths.append(bind_info)
    
    def generate_report(self) -> str:
        """生成分析报告"""
        report = []
        report.append("=" * 60)
        report.append("DFG 线性/非线性运算分析报告")
        report.append("=" * 60)
        
        # 统计信息
        report.append(f"\n📊 运算类型统计:")
        report.append(f"  线性运算绑定: {len(self.linear_binds)} 个")
        report.append(f"  非线性运算绑定: {len(self.nonlinear_binds)} 个")
        report.append(f"  控制逻辑绑定: {len(self.control_binds)} 个")
        report.append(f"  存储更新绑定: {len(self.storage_binds)} 个")
        
        # 线性运算详情
        if self.linear_binds:
            report.append(f"\n🔵 线性运算部分:")
            for bind_info in self.linear_binds:
                bind = bind_info['bind']
                complexity = bind_info['complexity']
                report.append(f"  • {bind.dest}")
                report.append(f"    运算: {bind.tree}")
                report.append(f"    复杂度: 线性运算{complexity['linear_ops']}个, 深度{complexity['depth']}")
        
        # 非线性运算详情
        if self.nonlinear_binds:
            report.append(f"\n🔴 非线性运算部分:")
            for bind_info in self.nonlinear_binds:
                bind = bind_info['bind']
                complexity = bind_info['complexity']
                report.append(f"  • {bind.dest}")
                report.append(f"    运算: {bind.tree}")
                report.append(f"    复杂度: 非线性运算{complexity['nonlinear_ops']}个, 深度{complexity['depth']}")
        
        # 控制逻辑详情
        if self.control_binds:
            report.append(f"\n🟡 控制逻辑部分:")
            for bind_info in self.control_binds:
                bind = bind_info['bind']
                complexity = bind_info['complexity']
                report.append(f"  • {bind.dest}")
                report.append(f"    类型: 分支/条件选择")
                report.append(f"    复杂度: 控制运算{complexity['control_ops']}个, 深度{complexity['depth']}")
        
        # 存储更新详情
        if self.storage_binds:
            report.append(f"\n🟢 存储更新部分:")
            for bind_info in self.storage_binds:
                bind = bind_info['bind']
                report.append(f"  • {bind.dest} (寄存器)")
                report.append(f"    更新逻辑: {type(bind.tree).__name__}")
        
        # 关键路径
        if hasattr(self, 'critical_paths') and self.critical_paths:
            report.append(f"\n⚠️  关键路径识别:")
            for i, bind_info in enumerate(self.critical_paths, 1):
                bind = bind_info['bind']
                complexity = bind_info['complexity']
                report.append(f"  {i}. {bind.dest}")
                report.append(f"     原因: 高复杂度运算 (深度={complexity['depth']}, 非线性={complexity['nonlinear_ops']})")
        
        return "\n".join(report)
    
    def extract_verilog_sections(self) -> Dict[str, List[str]]:
        """提取对应的Verilog代码段"""
        sections = {
            'linear_section': [],
            'nonlinear_section': [],
            'control_section': [],
            'storage_section': []
        }
        
        # 基于绑定关系生成对应的Verilog片段
        for bind_info in self.linear_binds:
            verilog_code = self._generate_verilog_from_bind(bind_info['bind'])
            sections['linear_section'].append(verilog_code)
        
        for bind_info in self.nonlinear_binds:
            verilog_code = self._generate_verilog_from_bind(bind_info['bind'])
            sections['nonlinear_section'].append(verilog_code)
        
        for bind_info in self.control_binds:
            verilog_code = self._generate_verilog_from_bind(bind_info['bind'])
            sections['control_section'].append(verilog_code)
        
        for bind_info in self.storage_binds:
            verilog_code = self._generate_verilog_from_bind(bind_info['bind'])
            sections['storage_section'].append(verilog_code)
        
        return sections
    
    def _generate_verilog_from_bind(self, bind: Bind) -> str:
        """从绑定关系生成Verilog代码"""
        dest = bind.dest.split('.')[-1]  # 移除模块前缀
        expr = self._node_to_verilog(bind.tree)
        return f"assign {dest} = {expr};"
    
    def _node_to_verilog(self, node: Union[Operator, Terminal, IntConst, Branch]) -> str:
        """将节点转换为Verilog表达式"""
        if isinstance(node, IntConst):
            return node.value
        
        elif isinstance(node, Terminal):
            return node.name.split('.')[-1]  # 移除模块前缀
        
        elif isinstance(node, Operator):
            op_map = {
                OperatorType.PLUS: '+', OperatorType.MINUS: '-',
                OperatorType.TIMES: '*', OperatorType.MOD: '%',
                OperatorType.AND: '&', OperatorType.OR: '|',
                OperatorType.XOR: '^', OperatorType.EQ: '=='
            }
            
            if len(node.operands) == 2:
                left = self._node_to_verilog(node.operands[0])
                right = self._node_to_verilog(node.operands[1])
                op_str = op_map.get(node.op_type, '+')
                return f"({left} {op_str} {right})"
            else:
                # 处理其他情况
                operands_str = ', '.join(self._node_to_verilog(op) for op in node.operands)
                return f"{node.op_type.value}({operands_str})"
        
        elif isinstance(node, Branch):
            cond = self._node_to_verilog(node.condition)
            true_val = self._node_to_verilog(node.true_branch)
            false_val = self._node_to_verilog(node.false_branch) if node.false_branch else "1'b0"
            return f"({cond} ? {true_val} : {false_val})"
        
        return "/* unknown */"


def main():
    """主函数 - 分析4004 ALU的DFG"""
    parser = ImprovedDFGParser()
    
    try:
        # 解析4004 DFG文件
        dfg = parser.parse_file("/Users/xuxiaolan/PycharmProjects/ESIMULATOR/dfg_files/4004_dfg.txt")
        
        # 创建线性度分析器
        analyzer = DFGLinearityAnalyzer(dfg)
        analyzer.analyze()
        
        # 生成并打印报告
        report = analyzer.generate_report()
        print(report)
        
        # 提取Verilog代码段
        print("\n" + "=" * 60)
        print("提取的Verilog代码段")
        print("=" * 60)
        
        sections = analyzer.extract_verilog_sections()
        
        for section_name, codes in sections.items():
            if codes:
                print(f"\n### {section_name.replace('_', ' ').title()}:")
                for i, code in enumerate(codes[:5], 1):  # 只显示前5个
                    print(f"  {i}. {code}")
                if len(codes) > 5:
                    print(f"  ... 还有 {len(codes) - 5} 个")
        
        # 保存详细报告
        with open("/Users/xuxiaolan/PycharmProjects/ESIMULATOR/4004_linearity_analysis.txt", 'w', encoding='utf-8') as f:
            f.write(report)
            f.write("\n\n" + "=" * 60)
            f.write("\n详细Verilog代码段\n")
            f.write("=" * 60)
            for section_name, codes in sections.items():
                if codes:
                    f.write(f"\n\n### {section_name.replace('_', ' ').title()}:\n")
                    for i, code in enumerate(codes, 1):
                        f.write(f"{i}. {code}\n")
        
        print(f"\n详细分析报告已保存到: 4004_linearity_analysis.txt")
        
    except Exception as e:
        print(f"分析错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
