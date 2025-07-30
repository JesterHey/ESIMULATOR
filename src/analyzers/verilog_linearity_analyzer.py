#!/usr/bin/env python3
"""
基于Verilog源码的线性/非线性运算分析器
直接分析原始Verilog代码，识别线性和非线性运算模式
"""

import re
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


@dataclass
class VerilogStatement:
    """Verilog语句结构"""
    line_num: int
    statement: str
    dest_signal: str
    expression: str
    statement_type: str  # 'assign', 'always', 'wire', etc.


@dataclass
class OperationInfo:
    """运算信息"""
    operation: str
    operands: List[str]
    is_linear: bool
    complexity_score: int


class VerilogLinearityAnalyzer:
    """Verilog线性度分析器"""
    
    def __init__(self, verilog_file: str):
        self.verilog_file = verilog_file
        self.statements = []
        self.linear_operations = []
        self.nonlinear_operations = []
        self.control_logic = []
        self.storage_updates = []
        
        # 定义线性和非线性运算符
        self.linear_ops = {'+', '-', '&', '|', '^', '~', '<<', '>>', '===', '==', '!=', '<', '>', '<=', '>='}
        self.nonlinear_ops = {'*', '/', '%', '**'}
        self.control_constructs = {'if', 'case', 'always', '?', ':'}
    
    def parse_verilog_file(self):
        """解析Verilog文件"""
        with open(self.verilog_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        self.statements = []
        in_always_block = False
        always_block_lines = []
        current_statement = ""
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # 跳过注释和空行
            if not line or line.startswith('//') or line.startswith('/*'):
                continue
            
            # 检测always块
            if 'always' in line:
                in_always_block = True
                always_block_lines = [i]
                current_statement = line
                continue
            
            # 处理always块内容
            if in_always_block:
                current_statement += " " + line
                always_block_lines.append(i)
                
                if 'end' in line and line.strip() == 'end':
                    self._parse_always_block(always_block_lines[0], current_statement)
                    in_always_block = False
                    current_statement = ""
                continue
            
            # 处理assign语句
            if line.startswith('assign'):
                self._parse_assign_statement(i, line)
            
            # 处理wire声明中的连续赋值
            elif '=' in line and ('wire' in line or self._is_expression_line(line)):
                self._parse_wire_assignment(i, line)
    
    def _is_expression_line(self, line: str) -> bool:
        """判断是否是表达式行"""
        # 简单启发式：包含运算符且不是声明
        has_operator = any(op in line for op in ['=', '&', '|', '^', '+', '-', '*', '/', '%'])
        is_declaration = any(kw in line for kw in ['input', 'output', 'wire', 'reg', 'module'])
        return has_operator and not is_declaration
    
    def _parse_assign_statement(self, line_num: int, line: str):
        """解析assign语句"""
        # 提取 assign dest = expression;
        match = re.match(r'assign\s+(\w+)\s*=\s*(.+);?', line)
        if match:
            dest = match.group(1)
            expr = match.group(2).rstrip(';')
            
            stmt = VerilogStatement(
                line_num=line_num,
                statement=line,
                dest_signal=dest,
                expression=expr,
                statement_type='assign'
            )
            self.statements.append(stmt)
    
    def _parse_wire_assignment(self, line_num: int, line: str):
        """解析wire赋值"""
        # 处理类似 wire dest = expression; 的语句
        if '=' in line:
            parts = line.split('=', 1)
            if len(parts) == 2:
                left = parts[0].strip()
                right = parts[1].strip().rstrip(';')
                
                # 提取信号名
                dest = re.search(r'(\w+)\s*$', left)
                if dest:
                    stmt = VerilogStatement(
                        line_num=line_num,
                        statement=line,
                        dest_signal=dest.group(1),
                        expression=right,
                        statement_type='wire'
                    )
                    self.statements.append(stmt)
    
    def _parse_always_block(self, start_line: int, block_content: str):
        """解析always块"""
        # 提取always块中的赋值语句
        assignments = re.findall(r'(\w+)\s*<=?\s*([^;]+);', block_content)
        
        for i, (dest, expr) in enumerate(assignments):
            stmt = VerilogStatement(
                line_num=start_line + i,
                statement=f"{dest} <= {expr};",
                dest_signal=dest,
                expression=expr,
                statement_type='always'
            )
            self.statements.append(stmt)
    
    def analyze_operations(self):
        """分析运算类型"""
        for stmt in self.statements:
            op_info = self._analyze_expression(stmt.expression)
            
            if stmt.statement_type == 'always':
                self.storage_updates.append((stmt, op_info))
            elif self._has_control_logic(stmt.expression):
                self.control_logic.append((stmt, op_info))
            elif op_info.is_linear:
                self.linear_operations.append((stmt, op_info))
            else:
                self.nonlinear_operations.append((stmt, op_info))
    
    def _analyze_expression(self, expr: str) -> OperationInfo:
        """分析表达式的运算类型"""
        # 查找所有运算符
        found_ops = []
        operands = []
        
        # 线性运算符检测
        linear_found = []
        for op in self.linear_ops:
            if op in expr:
                linear_found.append(op)
        
        # 非线性运算符检测
        nonlinear_found = []
        for op in self.nonlinear_ops:
            if op in expr:
                nonlinear_found.append(op)
        
        # 控制结构检测
        has_conditional = '?' in expr and ':' in expr
        has_case_like = any(keyword in expr.lower() for keyword in ['case', 'if'])
        
        # 提取操作数（简化版）
        operands = re.findall(r'\b\w+\b', expr)
        operands = [op for op in operands if not op.isdigit()]  # 过滤数字
        
        # 计算复杂度分数
        complexity = len(linear_found) + len(nonlinear_found) * 3
        if has_conditional:
            complexity += 2
        
        # 判断是否为线性
        is_linear = len(nonlinear_found) == 0 and not has_case_like
        
        all_ops = linear_found + nonlinear_found
        if has_conditional:
            all_ops.append('?:')
        
        return OperationInfo(
            operation=', '.join(all_ops) if all_ops else 'assignment',
            operands=operands,
            is_linear=is_linear,
            complexity_score=complexity
        )
    
    def _has_control_logic(self, expr: str) -> bool:
        """检测是否包含控制逻辑"""
        return ('?' in expr and ':' in expr) or any(kw in expr.lower() for kw in ['case', 'if'])
    
    def generate_analysis_report(self) -> str:
        """生成分析报告"""
        report = []
        report.append("=" * 80)
        report.append("Intel 4004 ALU Verilog 线性/非线性运算分析报告")
        report.append("=" * 80)
        
        # 统计信息
        report.append(f"\n📊 运算分布统计:")
        report.append(f"  线性运算: {len(self.linear_operations)} 个")
        report.append(f"  非线性运算: {len(self.nonlinear_operations)} 个")
        report.append(f"  控制逻辑: {len(self.control_logic)} 个")
        report.append(f"  存储更新: {len(self.storage_updates)} 个")
        report.append(f"  总语句数: {len(self.statements)} 个")
        
        # 线性运算详情
        if self.linear_operations:
            report.append(f"\n🔵 线性运算部分 ({len(self.linear_operations)} 个):")
            report.append("  ├─ 特点: 加法、减法、位运算、比较运算")
            report.append("  └─ 硬件实现: 简单组合逻辑，延迟低")
            
            for i, (stmt, op_info) in enumerate(self.linear_operations[:10], 1):
                report.append(f"\n  {i}. 行 {stmt.line_num}: {stmt.dest_signal}")
                report.append(f"     运算: {op_info.operation}")
                report.append(f"     表达式: {stmt.expression}")
                report.append(f"     复杂度: {op_info.complexity_score}")
            
            if len(self.linear_operations) > 10:
                report.append(f"     ... 还有 {len(self.linear_operations) - 10} 个线性运算")
        
        # 非线性运算详情
        if self.nonlinear_operations:
            report.append(f"\n🔴 非线性运算部分 ({len(self.nonlinear_operations)} 个):")
            report.append("  ├─ 特点: 乘法、除法、模运算")
            report.append("  └─ 硬件实现: 复杂逻辑，延迟高，面积大")
            
            for i, (stmt, op_info) in enumerate(self.nonlinear_operations, 1):
                report.append(f"\n  {i}. 行 {stmt.line_num}: {stmt.dest_signal}")
                report.append(f"     运算: {op_info.operation}")
                report.append(f"     表达式: {stmt.expression}")
                report.append(f"     复杂度: {op_info.complexity_score}")
        
        # 控制逻辑详情
        if self.control_logic:
            report.append(f"\n🟡 控制逻辑部分 ({len(self.control_logic)} 个):")
            report.append("  ├─ 特点: 条件选择、分支判断")
            report.append("  └─ 硬件实现: 多路选择器、条件逻辑")
            
            for i, (stmt, op_info) in enumerate(self.control_logic[:8], 1):
                report.append(f"\n  {i}. 行 {stmt.line_num}: {stmt.dest_signal}")
                report.append(f"     控制类型: {op_info.operation}")
                report.append(f"     表达式: {stmt.expression[:60]}{'...' if len(stmt.expression) > 60 else ''}")
        
        # 存储更新详情
        if self.storage_updates:
            report.append(f"\n🟢 存储更新部分 ({len(self.storage_updates)} 个):")
            report.append("  ├─ 特点: 寄存器赋值、状态更新")
            report.append("  └─ 硬件实现: 触发器、锁存器")
            
            # 按复杂度排序
            sorted_updates = sorted(self.storage_updates, key=lambda x: x[1].complexity_score, reverse=True)
            
            for i, (stmt, op_info) in enumerate(sorted_updates[:8], 1):
                report.append(f"\n  {i}. {stmt.dest_signal} (复杂度: {op_info.complexity_score})")
                report.append(f"     表达式: {stmt.expression[:60]}{'...' if len(stmt.expression) > 60 else ''}")
        
        # 设计建议
        report.append(f"\n💡 设计优化建议:")
        
        if self.nonlinear_operations:
            report.append(f"  🔴 非线性运算优化:")
            report.append(f"     - 考虑流水线设计减少关键路径延迟")
            report.append(f"     - 使用专用乘法器/除法器IP核")
            report.append(f"     - 评估是否可以用移位和加法替代")
        
        if len(self.control_logic) > 5:
            report.append(f"  🟡 控制逻辑优化:")
            report.append(f"     - 复杂控制逻辑较多，注意时序收敛")
            report.append(f"     - 考虑状态机重构减少组合逻辑层数")
        
        linear_ratio = len(self.linear_operations) / len(self.statements) * 100
        report.append(f"  📊 线性化程度: {linear_ratio:.1f}% (线性运算占比)")
        
        if linear_ratio > 70:
            report.append(f"     ✅ 设计线性度良好，硬件实现相对简单")
        elif linear_ratio > 40:
            report.append(f"     ⚠️  中等复杂度设计，需要平衡性能和面积")
        else:
            report.append(f"     🔴 高复杂度设计，需要重点优化关键路径")
        
        return "\n".join(report)
    
    def extract_code_sections(self) -> Dict[str, List[str]]:
        """提取不同类型的代码段"""
        sections = {
            'linear_code': [],
            'nonlinear_code': [],
            'control_code': [],
            'storage_code': []
        }
        
        for stmt, op_info in self.linear_operations:
            sections['linear_code'].append(f"// 线性运算: {op_info.operation}")
            sections['linear_code'].append(stmt.statement)
        
        for stmt, op_info in self.nonlinear_operations:
            sections['nonlinear_code'].append(f"// 非线性运算: {op_info.operation}")
            sections['nonlinear_code'].append(stmt.statement)
        
        for stmt, op_info in self.control_logic:
            sections['control_code'].append(f"// 控制逻辑: {op_info.operation}")
            sections['control_code'].append(stmt.statement)
        
        for stmt, op_info in self.storage_updates:
            sections['storage_code'].append(f"// 存储更新: {stmt.dest_signal}")
            sections['storage_code'].append(stmt.statement)
        
        return sections


def main():
    """主函数"""
    verilog_file = "/Users/xuxiaolan/PycharmProjects/ESIMULATOR/verilog_files/4004.v"
    
    try:
        analyzer = VerilogLinearityAnalyzer(verilog_file)
        analyzer.parse_verilog_file()
        analyzer.analyze_operations()
        
        # 生成分析报告
        report = analyzer.generate_analysis_report()
        print(report)
        
        # 保存详细报告
        with open("/Users/xuxiaolan/PycharmProjects/ESIMULATOR/4004_verilog_linearity_analysis.txt", 'w', encoding='utf-8') as f:
            f.write(report)
            
            # 添加代码段
            sections = analyzer.extract_code_sections()
            f.write("\n\n" + "=" * 80)
            f.write("\n提取的代码段")
            f.write("\n" + "=" * 80)
            
            for section_name, codes in sections.items():
                if codes:
                    f.write(f"\n\n## {section_name.replace('_', ' ').title()}:\n")
                    for code in codes:
                        f.write(f"{code}\n")
        
        print(f"\n详细分析报告已保存到: 4004_verilog_linearity_analysis.txt")
        
    except Exception as e:
        print(f"分析错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
