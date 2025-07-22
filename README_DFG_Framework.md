# DFG到Python转换框架

## 概述

这个框架将数据流图(DFG)文本表示转换为等效的Python代码。它支持完整的Verilog硬件描述到功能模拟器的转换。

## 核心组件

### 1. 数据结构设计

#### 基本节点类型
- **IntConst**: 整数常量（支持二进制、十六进制等Verilog格式）
- **Terminal**: 终端节点（变量引用）
- **Operator**: 操作符节点（算术、逻辑、比较运算）
- **Branch**: 分支节点（条件选择，支持嵌套）

#### 高级结构
- **Term**: 信号定义（输入、输出、寄存器、中间变量）
- **Bind**: 绑定关系（信号赋值）
- **Instance**: 模块实例
- **DFG**: 完整的数据流图

### 2. 解析器架构

```python
class ImprovedDFGParser:
    def parse_file(filepath) -> DFG
    def _parse_instance_line(line) -> Instance
    def _parse_term_line(line) -> Term  
    def _parse_bind_line(line) -> Bind
    def _parse_expression(expr) -> Union[Operator, Terminal, IntConst, Branch]
    def _parse_branch_recursive(expr) -> Branch
```

#### 关键特性
- **递归下降解析**: 处理复杂嵌套表达式
- **括号平衡**: 正确分割嵌套结构
- **错误处理**: 容错性解析
- **类型安全**: 强类型数据结构

### 3. 代码生成器

```python
class DFGToPythonConverter:
    def convert() -> str
    def _topological_sort_binds() -> List[Bind]
    def _generate_expression_code(node) -> str
    def _generate_operator_code(op) -> str
    def _generate_branch_code(branch) -> str
```

#### 转换特性
- **拓扑排序**: 确保依赖关系正确
- **表达式优化**: 生成简洁的Python代码
- **错误处理**: 处理除零等边界条件
- **格式化**: 生成可读的代码和注释

## 使用方法

### 基本用法

```python
from dfg_to_python import create_complete_simulator

# 转换DFG文件为Python模拟器
dfg = create_complete_simulator(
    dfg_file_path="dfg_files/alu1_dfg.txt",
    output_file_path="simulators/alu1_simulator.py"
)
```

### 高级用法

```python
from improved_dfg_parser import ImprovedDFGParser
from dfg_to_python import DFGToPythonConverter

# 解析DFG
parser = ImprovedDFGParser()
dfg = parser.parse_file("your_dfg_file.txt")

# 分析结构
analyze_dfg_structure(dfg)

# 生成代码
converter = DFGToPythonConverter(dfg)
python_code = converter.convert()
```

## 支持的Verilog结构

### 1. 数据类型
- 多位向量 `[msb:lsb]`
- 常量表示 `2'b00`, `4'hF`, 十进制数

### 2. 操作符
- 算术: `+`, `-`, `*`, `%`
- 逻辑: `&`, `|`, `^`
- 比较: `==`

### 3. 控制结构
- 条件选择 (case/if-else)
- 嵌套分支
- 默认值处理

### 4. 信号类型
- Input: 输入端口
- Output: 输出端口  
- Reg: 寄存器
- Rename: 中间变量

## 转换示例

### DFG输入
```
Bind dest:alu1._rn0_result tree:(Operator Times Next:((Operator Plus Next:((Terminal alu1.a),(Terminal alu1.b))),(Terminal alu1.c)))
```

### Python输出
```python
# Case 0: (a + b) * c
_rn0_result = ((a + b) * c)
```

### 复杂分支转换
```
Branch Cond:(Operator Eq Next:((Terminal alu1.op),(IntConst 2'b00))) True:(Terminal alu1._rn0_result) False:(...)
```

转换为：
```python
result = (_rn0_result if (op == 0b00) else (...))
```

## 测试和验证

### 自动生成测试用例
- 预定义测试用例覆盖所有操作模式
- 随机测试用例验证边界条件
- 位宽正确性检查

### 示例输出
```
=== 预定义测试用例 ===
a=5, b=3, c=2, op=0 => result=16    # (5+3)*2
a=5, b=3, c=2, op=1 => result=0     # (5-3)^2  
a=5, b=3, c=2, op=2 => result=1     # 5&(3|2)
a=5, b=3, c=2, op=3 => result=12    # (5%3)+(5*2)
```

## 项目文件结构

```
ESIMULATOR/
├── dfg_files/
│   └── alu1_dfg.txt              # 输入DFG文件
├── verilog_files/
│   └── alu1.v                    # 原始Verilog文件
├── improved_dfg_parser.py        # 增强DFG解析器
├── dfg_to_python.py             # 转换框架
├── alu1_complete_simulator.py   # 生成的完整模拟器
└── README.md                    # 本文档
```

## 扩展性

### 添加新操作符
1. 在 `OperatorType` 枚举中添加新类型
2. 在 `_generate_operator_code` 中添加对应的Python操作符
3. 更新测试用例

### 支持新的数据结构
1. 定义新的节点类型（继承基本接口）
2. 在解析器中添加识别逻辑
3. 在代码生成器中添加转换逻辑

### 优化建议
- 使用更高效的表达式简化算法
- 添加常量折叠优化
- 支持更多Verilog语法结构
- 生成更人性化的变量名

## 总结

这个框架提供了一个完整的从DFG文本到Python模拟器的转换解决方案。它具有以下优点：

1. **完整性**: 支持复杂的嵌套结构和多种操作符
2. **正确性**: 通过拓扑排序和类型检查确保结果正确
3. **可读性**: 生成的代码包含注释和良好的格式
4. **可扩展性**: 模块化设计便于添加新特性
5. **可测试性**: 自动生成测试用例验证功能

该框架特别适用于硬件设计验证、教学演示和快速原型开发等场景。
