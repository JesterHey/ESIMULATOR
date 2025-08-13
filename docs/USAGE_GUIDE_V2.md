# ESIMULATOR 2.0 - 重组版使用文档

## 🎯 项目概述

ESIMULATOR 2.0是一个专门用于Data Flow Graph (DFG)线性分析的工具包，经过重新组织和优化，提供了更清晰的模块结构和更强大的功能。

## 📁 项目结构

```
ESIMULATOR/
├── 🚀 入口脚本
│   ├── esimulator_cli.py           # 主命令行工具
│   ├── analyze_linearity_v2.py     # 兼容性分析入口
│   └── demo_comparison_v2.py       # 兼容性对比演示
├── 📦 核心包 (esimulator/)
│   ├── __init__.py                 # 包初始化
│   ├── 🧠 core/                    # 核心模块
│   │   ├── linearity_analyzer.py      # 线性分析引擎
│   │   ├── dfg_parser.py              # DFG解析器
│   │   └── report_generator.py        # 报告生成器
│   ├── 💻 cli/                     # 命令行接口
│   │   ├── analyze_command.py         # 分析命令
│   │   ├── compare_command.py         # 对比命令
│   │   ├── batch_command.py           # 批量命令
│   │   └── visualize_command.py       # 可视化命令
│   ├── 🔧 utils/                   # 工具模块
│   │   └── file_utils.py              # 文件工具
│   └── 📚 examples/                # 示例代码
│       └── basic_usage.py             # 基本使用示例
├── 📊 数据文件
│   ├── dfg_files/                  # DFG输入文件
│   ├── verilog_files/              # Verilog源文件
│   └── results/                    # 分析结果
├── 📖 文档
│   ├── docs/                       # 技术文档
│   └── README.md                   # 项目说明
├── 🧪 测试和备份
│   ├── tests/                      # 测试文件
│   ├── src/                        # 原始源代码（保留）
│   └── backup_before_reorganize/   # 重构前备份
└── ⚙️ 配置文件
    ├── pyproject.toml              # Python项目配置
    └── LICENSE                     # 许可证
```

## 🚀 快速开始

### 1. 基本使用（命令行）

**安装依赖**（可选）：
```bash
pip install matplotlib  # 用于可视化功能
```

**基本线性分析**：
```bash
# 使用新的CLI工具
python esimulator_cli.py analyze dfg_files/4004_dfg.txt

# 或使用兼容性入口
python analyze_linearity_v2.py
```

**对比分析**：
```bash
# 使用兼容性入口
python demo_comparison_v2.py
```

**批量分析**：
```bash
# 分析整个目录中的所有DFG文件
python esimulator_cli.py batch dfg_files/ --output results/batch_analysis
```

**可视化生成**：
```bash
# 生成可视化图表
python esimulator_cli.py visualize dfg_files/4004_dfg.txt --output results/visualizations
```

### 2. 程序化使用（API）

**基本分析**：
```python
from esimulator import LinearityAnalyzer, ReportGenerator

# 创建分析器
analyzer = LinearityAnalyzer()

# 执行分析
result = analyzer.analyze_dfg_file("dfg_files/4004_dfg.txt")

# 生成报告
report_gen = ReportGenerator("output")
report_file = report_gen.generate_text_report(result)

print(f"报告已保存到: {report_file}")
```

**详细使用示例**：
```python
# 运行内置示例
python esimulator/examples/basic_usage.py
```

## 📋 命令行工具详解

### esimulator_cli.py 命令

```bash
python esimulator_cli.py <command> [options]
```

#### 可用命令

**1. analyze - 执行DFG线性分析**
```bash
python esimulator_cli.py analyze <dfg_file> [options]

选项:
  --output, -o DIR     输出目录 (默认: results)
  --format FORMAT      输出格式: txt, json, both (默认: txt)

示例:
  python esimulator_cli.py analyze dfg_files/4004_dfg.txt
  python esimulator_cli.py analyze dfg_files/4004_dfg.txt --format both -o my_results
```

**2. compare - 对比分析方法**
```bash
python esimulator_cli.py compare <dfg_file>

示例:
  python esimulator_cli.py compare dfg_files/4004_dfg.txt
```

**3. batch - 批量分析**
```bash
python esimulator_cli.py batch <input_dir> [options]

选项:
  --output, -o DIR     输出目录 (默认: results)

示例:
  python esimulator_cli.py batch dfg_files/ --output batch_results
```

**4. visualize - 生成可视化**
```bash
python esimulator_cli.py visualize <dfg_file> [options]

选项:
  --output, -o DIR     输出目录 (默认: results/visualizations)

示例:
  python esimulator_cli.py visualize dfg_files/4004_dfg.txt
```

## 🔧 API 参考

### LinearityAnalyzer 类

```python
from esimulator.core.linearity_analyzer import LinearityAnalyzer

analyzer = LinearityAnalyzer()
```

**主要方法**：
- `analyze_dfg_file(file_path: str) -> Dict` - 分析DFG文件
- `_analyze_signal_expression(signal_name: str, tree_expr: str) -> Dict` - 分析单个信号表达式

**属性**：
- `linear_operators: Set[str]` - 线性运算符集合
- `nonlinear_operators: Set[str]` - 非线性运算符集合

### DFGParser 类

```python
from esimulator.core.dfg_parser import DFGParser

parser = DFGParser()
result = parser.parse_file("dfg_files/4004_dfg.txt")
```

**主要方法**：
- `parse_file(file_path: str) -> Dict` - 解析DFG文件
- `get_signal_expression(signal_name: str) -> str` - 获取信号表达式
- `list_signals() -> List[str]` - 列出所有信号
- `extract_operators(expression: str) -> List[str]` - 提取运算符

### ReportGenerator 类

```python
from esimulator.core.report_generator import ReportGenerator

report_gen = ReportGenerator("output_dir")
```

**主要方法**：
- `generate_text_report(analysis_result: Dict, filename: str = None) -> str` - 生成文本报告
- `generate_json_report(analysis_result: Dict, filename: str = None) -> str` - 生成JSON报告
- `generate_summary_report(analysis_result: Dict) -> str` - 生成摘要报告

## 📊 输出文件说明

### 分析报告格式

**文本报告 (linearity_analysis.txt)**：
```text
ESIMULATOR DFG线性分析报告
==================================================

生成时间: 2025-08-07 22:52:00

分析摘要:
---------------
总表达式数: 80
线性表达式: 13 (16.2%)
非线性表达式: 67 (83.8%)

表达式类型分布:
--------------------
operator        :  64 ( 80.0%)
terminal        :  13 ( 16.2%)
branch          :   2 (  2.5%)
concat          :   1 (  1.2%)

详细信号分析:
--------------------
alu._rn0_dout       : 线性     - 常量赋值
alu._rn1_dout       : 线性     - 直接终端赋值
alu.acb_ib          : 非线性    - 包含非线性运算符: Unot
...
```

**JSON报告 (linearity_analysis.json)**：
```json
{
  "metadata": {
    "generated_at": "2025-08-07T22:52:00",
    "tool_version": "2.0.0",
    "analysis_type": "dfg_linearity"
  },
  "analysis_result": {
    "summary": {
      "total_expressions": 80,
      "linear_expressions": 13,
      "nonlinear_expressions": 67,
      "linearity_ratio": 0.1625
    },
    "detailed_analyses": {...}
  }
}
```


**使用方式**：
```bash
# 兼容性入口（功能完全相同）
python analyze_linearity_v2.py
python demo_comparison_v2.py

# 新CLI工具（功能更强大）
python esimulator_cli.py analyze dfg_files/4004_dfg.txt
python esimulator_cli.py compare dfg_files/4004_dfg.txt
```

## 🧪 示例和测试

### 运行内置示例

```bash
# 基本使用示例
python esimulator/examples/basic_usage.py

# 创建输出目录并查看结果
ls examples/output/
```

### 功能验证

```bash
# 验证CLI工具
python esimulator_cli.py analyze dfg_files/4004_dfg.txt --format both

# 验证兼容性
python analyze_linearity_v2.py
python demo_comparison_v2.py

# 检查输出文件
ls results/
```

## 🔧 定制化和扩展

### 自定义运算符分类

```python
from esimulator import LinearityAnalyzer

analyzer = LinearityAnalyzer()

# 修改线性运算符定义
analyzer.linear_operators.add('CustomOp')
analyzer.nonlinear_operators.discard('Sll')  # 将位移重新分类为线性

# 执行分析
result = analyzer.analyze_dfg_file("your_dfg_file.txt")
```

### 自定义报告格式

```python
from esimulator.core.report_generator import ReportGenerator

class CustomReportGenerator(ReportGenerator):
    def generate_custom_report(self, analysis_result):
        # 实现自定义报告逻辑
        pass
```

### 批量处理自定义

```python
from esimulator.utils.file_utils import find_dfg_files
from esimulator import LinearityAnalyzer

analyzer = LinearityAnalyzer()
dfg_files = find_dfg_files("your_dfg_directory")

for dfg_file in dfg_files:
    result = analyzer.analyze_dfg_file(dfg_file)
    # 处理结果...
```

## ⚠️ 注意事项

   
1. **文件路径**：使用相对路径或绝对路径访问DFG文件
2. **依赖项**：可视化功能需要安装matplotlib
3. **输出目录**：确保有写入权限到指定的输出目录

## 🆘 故障排除

**常见问题**：

1. **找不到DFG文件**：
   ```bash
   # 检查文件是否存在
   ls dfg_files/4004_dfg.txt
   
   # 使用绝对路径
   python esimulator_cli.py analyze /full/path/to/4004_dfg.txt
   ```

2. **导入错误**：
   ```bash
   # 确保在项目根目录运行
   cd /Users/xuxiaolan/PycharmProjects/ESIMULATOR
   python esimulator_cli.py analyze dfg_files/4004_dfg.txt
   ```

3. **可视化失败**：
   ```bash
   # 安装matplotlib
   pip install matplotlib
   ```

## 📈 性能和规模

- **小文件 (<100个信号)**：几秒内完成
- **中等文件 (100-1000个信号)**：通常1分钟内
- **大文件 (>1000个信号)**：可能需要几分钟
- **批量处理**：支持目录级别的批量分析


**开发环境设置**：
```bash
# 安装开发依赖
pip install -e .[dev]

# 运行测试
pytest tests/

# 代码格式化
black esimulator/
```

---
