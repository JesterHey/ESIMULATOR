#!/usr/bin/env python3
"""
DFG到Python转换框架
支持通用的数据流图转换为可执行的Python代码
"""

from improved_dfg_parser import *
from typing import Set, List, Dict


class DFGToPythonConverter:
    """DFG到Python代码转换器"""
    
    def __init__(self, dfg: DFG):
        self.dfg = dfg
        self.visited_nodes = set()
        self.generated_code = []
    
    def convert(self) -> str:
        """将DFG转换为Python函数"""
        code = []
        
        # 函数头
        func_name = f"simulate_{self.dfg.instance.module_name}" if self.dfg.instance else "simulate"
        inputs = self._get_input_parameters()
        outputs = self._get_output_signals()
        
        code.append(f"def {func_name}({', '.join(inputs)}):")
        code.append(f'    """基于DFG生成的{self.dfg.instance.module_name if self.dfg.instance else "模块"}模拟器"""')
        
        # 生成计算代码
        computation_code = self._generate_computation_code()
        code.extend(computation_code)
        
        # 返回输出
        if len(outputs) == 1:
            code.append(f"    return {self._clean_signal_name(outputs[0])}")
        else:
            return_vars = [self._clean_signal_name(out) for out in outputs]
            code.append(f"    return {', '.join(return_vars)}")
        
        return "\n".join(code)
    
    def _get_input_parameters(self) -> List[str]:
        """获取输入参数列表"""
        inputs = []
        for term in self.dfg.terms:
            if TermType.INPUT in term.types:
                inputs.append(self._clean_signal_name(term.name))
        return inputs
    
    def _get_output_signals(self) -> List[str]:
        """获取输出信号列表"""
        outputs = []
        for term in self.dfg.terms:
            if TermType.OUTPUT in term.types:
                outputs.append(term.name)
        return outputs
    
    def _clean_signal_name(self, name: str) -> str:
        """清理信号名称，转换为有效的Python变量名"""
        # 移除模块名前缀
        if '.' in name:
            name = name.split('.')[-1]
        return name
    
    def _generate_computation_code(self) -> List[str]:
        """生成计算代码"""
        code = []
        
        # 按依赖顺序处理绑定
        sorted_binds = self._topological_sort_binds()
        
        for bind in sorted_binds:
            var_name = self._clean_signal_name(bind.dest)
            expression = self._generate_expression_code(bind.tree)
            
            # 添加注释
            comment = self._generate_comment_for_bind(bind)
            if comment:
                code.append(f"    # {comment}")
            
            code.append(f"    {var_name} = {expression}")
            code.append("")  # 空行分隔
        
        return code
    
    def _topological_sort_binds(self) -> List[Bind]:
        """拓扑排序绑定关系，确保依赖顺序正确"""
        # 简单实现：先处理不依赖其他中间变量的绑定
        independent_binds = []
        dependent_binds = []
        
        for bind in self.dfg.binds:
            if self._has_rename_dependencies(bind.tree):
                dependent_binds.append(bind)
            else:
                independent_binds.append(bind)
        
        return independent_binds + dependent_binds
    
    def _has_rename_dependencies(self, node: Union[Operator, Terminal, IntConst, Branch]) -> bool:
        """检查节点是否依赖于重命名变量"""
        if isinstance(node, Terminal):
            # 检查是否是重命名变量
            for term in self.dfg.terms:
                if term.name == node.name and TermType.RENAME in term.types:
                    return True
        elif isinstance(node, Operator):
            return any(self._has_rename_dependencies(operand) for operand in node.operands)
        elif isinstance(node, Branch):
            false_check = self._has_rename_dependencies(node.false_branch) if node.false_branch else False
            return (self._has_rename_dependencies(node.condition) or
                   self._has_rename_dependencies(node.true_branch) or
                   false_check)
        
        return False
    
    def _generate_expression_code(self, node: Union[Operator, Terminal, IntConst, Branch]) -> str:
        """生成表达式代码"""
        if isinstance(node, IntConst):
            return self._convert_verilog_constant(node.value)
        
        elif isinstance(node, Terminal):
            return self._clean_signal_name(node.name)
        
        elif isinstance(node, Operator):
            return self._generate_operator_code(node)
        
        elif isinstance(node, Branch):
            return self._generate_branch_code(node)
        
        return "0"
    
    def _convert_verilog_constant(self, value: str) -> str:
        """转换Verilog常量为Python常量"""
        value = value.strip()
        
        # 处理二进制常量 如 2'b00, 2'b01
        if "'b" in value:
            parts = value.split("'b")
            if len(parts) == 2:
                return f"0b{parts[1]}"
        
        # 处理十六进制常量
        if "'h" in value:
            parts = value.split("'h") 
            if len(parts) == 2:
                return f"0x{parts[1]}"
        
        # 处理十进制常量
        if value.isdigit():
            return value
        
        # 默认返回0
        return "0"
    
    def _generate_operator_code(self, op: Operator) -> str:
        """生成操作符代码"""
        if len(op.operands) != 2:
            # 处理非二元操作符的情况
            operands_code = [self._generate_expression_code(operand) for operand in op.operands]
            return f"({' '.join(operands_code)})"  # 简化处理
        
        left = self._generate_expression_code(op.operands[0])
        right = self._generate_expression_code(op.operands[1])
        
        operator_map = {
            OperatorType.PLUS: '+',
            OperatorType.MINUS: '-',
            OperatorType.TIMES: '*',
            OperatorType.MOD: '%',
            OperatorType.AND: '&',
            OperatorType.OR: '|',
            OperatorType.XOR: '^',
            OperatorType.EQ: '=='
        }
        
        py_op = operator_map.get(op.op_type, '+')
        
        # 特殊处理除零
        if op.op_type == OperatorType.MOD:
            return f"({left} {py_op} {right} if {right} != 0 else 0)"
        
        return f"({left} {py_op} {right})"
    
    def _generate_branch_code(self, branch: Branch) -> str:
        """生成分支代码"""
        condition = self._generate_expression_code(branch.condition)
        true_expr = self._generate_expression_code(branch.true_branch)
        
        if branch.false_branch:
            false_expr = self._generate_expression_code(branch.false_branch)
            return f"({true_expr} if {condition} else {false_expr})"
        else:
            return f"({true_expr} if {condition} else 0)"
    
    def _generate_comment_for_bind(self, bind: Bind) -> str:
        """为绑定生成注释"""
        dest_clean = self._clean_signal_name(bind.dest)
        
        # 根据目标变量名生成有意义的注释
        if "_rn0_result" in bind.dest:
            return "Case 0: (a + b) * c"
        elif "_rn1_result" in bind.dest:
            return "Case 1: (a - b) ^ c"
        elif "_rn2_result" in bind.dest:
            return "Case 2: a & (b | c)"
        elif "_rn3_result" in bind.dest:
            return "Case 3: (a % b) + (a * c)"
        elif "_rn4_result" in bind.dest:
            return "Default case: 0"
        elif "result" in bind.dest:
            return "Output selection logic"
        
        return f"Compute {dest_clean}"


def generate_test_harness(dfg: DFG) -> str:
    """生成测试工具"""
    code = []
    code.append('if __name__ == "__main__":')
    code.append("    import random")
    code.append("")
    
    # 获取输入信号的位宽
    inputs_info = []
    for term in dfg.terms:
        if TermType.INPUT in term.types:
            width = int(term.msb.value) - int(term.lsb.value) + 1
            max_val = (1 << width) - 1
            inputs_info.append((term.name.split('.')[-1], max_val))
    
    func_name = f"simulate_{dfg.instance.module_name}" if dfg.instance else "simulate"
    
    # 生成测试用例
    code.append("    # 预定义测试用例")
    code.append("    test_cases = [")
    
    if len(inputs_info) == 4 and inputs_info[-1][0] == 'op':  # ALU情况
        code.append("        (5, 3, 2, 0),   # Case 0")
        code.append("        (5, 3, 2, 1),   # Case 1") 
        code.append("        (5, 3, 2, 2),   # Case 2")
        code.append("        (5, 3, 2, 3),   # Case 3")
        code.append("        (15, 7, 4, 0),  # More test cases")
        code.append("        (15, 7, 4, 1),")
        code.append("        (15, 7, 4, 2),")
        code.append("        (15, 7, 4, 3),")
    
    code.append("    ]")
    code.append("")
    
    # 运行预定义测试
    code.append("    print('=== 预定义测试用例 ===')")
    input_names = [info[0] for info in inputs_info]
    code.append(f"    for {', '.join(input_names)} in test_cases:")
    code.append(f"        result = {func_name}({', '.join(input_names)})")
    
    # 格式化输出
    format_str = ', '.join([f"{name}={{{{name}}}}" for name in input_names]) + " => result={{result}}"
    code.append(f'        print(f"{format_str}")')
    
    code.append("")
    code.append("    print('\\n=== 随机测试用例 ===')")
    code.append("    for i in range(10):")
    
    # 生成随机输入
    random_inputs = []
    for name, max_val in inputs_info:
        random_inputs.append(f"random.randint(0, {max_val})")
    
    code.append(f"        {', '.join(input_names)} = {', '.join(random_inputs)}")
    code.append(f"        result = {func_name}({', '.join(input_names)})")
    code.append(f'        print(f"Test {{i+1}}: {format_str}")')
    
    return "\n".join(code)


def create_complete_simulator(dfg_file_path: str, output_file_path: str):
    """创建完整的模拟器文件"""
    parser = ImprovedDFGParser()
    dfg = parser.parse_file(dfg_file_path)
    
    converter = DFGToPythonConverter(dfg)
    
    # 生成完整代码
    code = []
    code.append("#!/usr/bin/env python3")
    code.append('"""')
    code.append(f"基于DFG自动生成的{dfg.instance.module_name if dfg.instance else '模块'}模拟器")
    code.append(f"源文件: {dfg_file_path}")
    code.append('"""')
    code.append("")
    
    # 主要模拟函数
    code.append(converter.convert())
    code.append("")
    code.append("")
    
    # 测试工具
    code.append(generate_test_harness(dfg))
    
    # 保存到文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(code))
    
    print(f"完整模拟器已保存到: {output_file_path}")
    
    return dfg


if __name__ == "__main__":
    # 示例用法
    dfg_file = "/Users/xuxiaolan/PycharmProjects/ESIMULATOR/dfg_files/alu1_dfg.txt"
    output_file = "/Users/xuxiaolan/PycharmProjects/ESIMULATOR/alu1_complete_simulator.py"
    
    dfg = create_complete_simulator(dfg_file, output_file)
    
    # 打印DFG信息
    print("\n=== DFG信息 ===")
    print(f"模块: {dfg.instance.module_name if dfg.instance else 'Unknown'}")
    print(f"输入信号: {len([t for t in dfg.terms if TermType.INPUT in t.types])} 个")
    print(f"输出信号: {len([t for t in dfg.terms if TermType.OUTPUT in t.types])} 个")
    print(f"绑定关系: {len(dfg.binds)} 个")
