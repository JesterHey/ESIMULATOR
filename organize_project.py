#!/usr/bin/env python3
"""
项目文件整理脚本
将混乱的文件结构整理成清晰的项目结构
"""

import os
import shutil
from pathlib import Path

def organize_project():
    """整理项目结构"""
    
    base_dir = Path("/Users/xuxiaolan/PycharmProjects/ESIMULATOR")
    
    # 创建目录结构
    directories = {
        "src": "源代码模块",
        "src/analyzers": "各类分析器", 
        "src/parsers": "解析器模块",
        "src/visualizers": "可视化工具",
        "results": "分析结果文件",
        "results/reports": "文本报告",
        "results/data": "结构化数据",
        "results/visualizations": "图表文件",
        "docs": "文档",
        "examples": "示例文件"
    }
    
    print("=== 项目结构整理 ===")
    
    # 创建目录
    for dir_path, description in directories.items():
        full_path = base_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"创建目录: {dir_path} - {description}")
    
    # 文件移动映射
    file_moves = {
        # 分析器
        "analyzers/correct_linearity_analyzer.py": "src/analyzers/",
        "signal_connection_analyzer.py": "src/analyzers/",
        "dfg_linearity_analyzer.py": "src/analyzers/",
        "verilog_linearity_analyzer.py": "src/analyzers/",
        
        # 解析器
        "improved_dfg_parser.py": "src/parsers/",
        "dfg_parser.py": "src/parsers/",
        "dfg_to_python.py": "src/parsers/",
        
        # 可视化工具
        "visualizers/dag_structure_visualizer.py": "src/visualizers/",
        "signal_visualization.py": "src/visualizers/",
        
        # 核心分析工具
        "src/dag_structure_analyzer.py": "src/",
        "improved_dfg_to_dag.py": "src/",
        "dfg_to_dag_converter.py": "src/",
        
        # 报告文件
        "4004_signal_connection_analysis.txt": "results/reports/",
        "4004_ALU_Linearity_Summary.md": "results/reports/",
        "results/correct_linearity_analysis.txt": "results/reports/",
        "results/dag_structure_report.txt": "results/reports/",
        
        # 数据文件
        "4004_signal_connections.json": "results/data/",
        
        # 图表文件
        "4004_signal_distribution.png": "results/visualizations/",
        "4004_fan_in_out_analysis.png": "results/visualizations/",
        "4004_critical_path.png": "results/visualizations/",
        "4004_signal_hierarchy.png": "results/visualizations/",
        
        # 文档
        "DFG_to_DAG_Analysis_Summary.md": "docs/",
        "README_DFG_Framework.md": "docs/"
    }
    
    print(f"\n=== 移动文件 ===")
    
    # 移动文件
    for src_path, dest_dir in file_moves.items():
        src_full = base_dir / src_path
        dest_full = base_dir / dest_dir
        
        if src_full.exists():
            try:
                shutil.move(str(src_full), str(dest_full))
                print(f"移动: {src_path} -> {dest_dir}")
            except Exception as e:
                print(f"移动失败: {src_path} - {e}")
        else:
            print(f"文件不存在: {src_path}")
    
    # 创建主README
    create_main_readme(base_dir)
    
    # 创建项目索引
    create_project_index(base_dir)
    
    print(f"\n=== 整理完成 ===")
    print_project_structure(base_dir)

def create_main_readme(base_dir: Path):
    """创建主README文件"""
    readme_content = """# Intel 4004 ALU DFG到DAG分析项目

## 项目简介

本项目实现了将DFG（Data Flow Graph）文本转换为有向无环图（DAG）并进行拓扑排序的完整解决方案，专注于分析Intel 4004 ALU中不同信号之间的连接关系。

## 项目结构

```
ESIMULATOR/
├── src/                          # 源代码
│   ├── analyzers/               # 分析器模块
│   │   ├── correct_linearity_analyzer.py    # 正确的线性/非线性分析
│   │   ├── signal_connection_analyzer.py    # 信号连接分析
│   │   └── ...
│   ├── parsers/                 # 解析器模块  
│   │   ├── improved_dfg_parser.py          # 改进的DFG解析器
│   │   └── ...
│   ├── visualizers/             # 可视化工具
│   │   ├── dag_structure_visualizer.py     # DAG结构可视化
│   │   └── ...
│   ├── dag_structure_analyzer.py # DAG结构分析器
│   └── improved_dfg_to_dag.py   # 改进的DFG到DAG转换器
├── results/                      # 分析结果
│   ├── reports/                 # 文本报告
│   ├── data/                    # 结构化数据
│   └── visualizations/          # 图表文件
├── docs/                        # 文档
├── dfg_files/                   # DFG输入文件
├── verilog_files/              # Verilog源文件
└── examples/                   # 示例文件
```

## 核心功能

### 1. 正确的线性/非线性分析
- **线性运算**: 加法(+), 减法(-), 位移(<<, >>), 位拼接, 位选择
- **非线性运算**: 逻辑运算(&, |, ^, ~), 乘法(*), 除法(/), 比较运算

### 2. DAG结构分析  
- 拓扑排序
- 强连通分量检测
- 信号层次分析
- 关键路径识别

### 3. 信号连接关系分析
- 信号分类和统计
- 扇入扇出分析
- 连接类型识别
- 关键信号识别

### 4. 可视化
- DAG结构图
- 信号分布图
- 关键路径图
- 层次结构图

## 快速开始

1. **运行线性分析**:
   ```bash
   python src/analyzers/correct_linearity_analyzer.py
   ```

2. **生成DAG结构**:
   ```bash
   python src/dag_structure_analyzer.py
   ```

3. **信号连接分析**:
   ```bash
   python src/analyzers/signal_connection_analyzer.py
   ```

## 分析结果

### 线性度分析
- Intel 4004 ALU包含465个运算操作
- 线性运算: 294个 (63.2%)
- 非线性运算: 171个 (36.8%)

### DAG结构
- 58个主要信号
- 182个连接关系
- 最复杂信号: `alu.acc_out` (复杂度13)

### 关键发现
- 检测到1个包含49个节点的强连通分量
- 最长关键路径包含12个节点
- 75.3%的连接为组合逻辑, 24.7%为时序逻辑

## 技术特点

- ✅ 正确的数学线性定义
- ✅ 完整的DAG结构展示
- ✅ 清晰的项目组织结构
- ✅ 环路友好的图分析算法
- ✅ 多维度可视化支持

## 贡献

欢迎提交Issue和Pull Request来改进此项目。

## 许可证

MIT License
"""
    
    with open(base_dir / "README.md", 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("创建: README.md")

def create_project_index(base_dir: Path):
    """创建项目文件索引"""
    index_content = """# 项目文件索引

## 核心模块

### 分析器 (src/analyzers/)
- `correct_linearity_analyzer.py` - 正确的线性/非线性运算分析
- `signal_connection_analyzer.py` - 信号连接关系分析  
- `dfg_linearity_analyzer.py` - DFG线性度分析（早期版本）
- `verilog_linearity_analyzer.py` - Verilog源码线性分析

### 解析器 (src/parsers/)
- `improved_dfg_parser.py` - 改进的DFG解析器
- `dfg_parser.py` - 基础DFG解析器
- `dfg_to_python.py` - DFG到Python转换

### 可视化工具 (src/visualizers/)
- `dag_structure_visualizer.py` - DAG结构可视化（NetworkX版）
- `signal_visualization.py` - 信号关系可视化

### 核心工具 (src/)
- `dag_structure_analyzer.py` - DAG结构分析器（文本版）
- `improved_dfg_to_dag.py` - 改进的DFG到DAG转换器
- `dfg_to_dag_converter.py` - 基础DFG到DAG转换器

## 分析结果

### 报告文件 (results/reports/)
- `correct_linearity_analysis.txt` - 正确线性分析报告
- `dag_structure_report.txt` - DAG结构详细报告
- `4004_signal_connection_analysis.txt` - 信号连接分析报告
- `4004_ALU_Linearity_Summary.md` - ALU线性度总结

### 数据文件 (results/data/)
- `4004_signal_connections.json` - 信号连接结构化数据

### 可视化文件 (results/visualizations/)
- `4004_signal_distribution.png` - 信号类型分布图
- `4004_fan_in_out_analysis.png` - 扇入扇出分析图
- `4004_critical_path.png` - 关键路径可视化
- `4004_signal_hierarchy.png` - 信号层次结构图

## 文档 (docs/)
- `DFG_to_DAG_Analysis_Summary.md` - 项目完整总结报告
- `README_DFG_Framework.md` - DFG框架说明

## 输入数据
- `dfg_files/4004_dfg.txt` - Intel 4004 ALU的DFG文件
- `verilog_files/alu1.v` - ALU Verilog源码

## 使用说明

1. **基础分析流程**:
   ```bash
   # 1. 线性分析
   python src/analyzers/correct_linearity_analyzer.py
   
   # 2. 信号连接分析  
   python src/analyzers/signal_connection_analyzer.py
   
   # 3. DAG结构分析
   python src/dag_structure_analyzer.py
   ```

2. **高级分析**:
   ```bash
   # 强连通分量分析
   python src/improved_dfg_to_dag.py
   
   # 可视化生成
   python src/visualizers/signal_visualization.py
   ```

## 主要成果

- ✅ 解决了线性/非线性定义问题
- ✅ 提供了清晰的DAG结构展示
- ✅ 建立了整洁的项目文件结构
- ✅ 完成了Intel 4004 ALU的全面分析
"""
    
    with open(base_dir / "docs/PROJECT_INDEX.md", 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    print("创建: docs/PROJECT_INDEX.md")

def print_project_structure(base_dir: Path):
    """打印项目结构"""
    print(f"\n=== 最终项目结构 ===")
    
    def print_tree(path: Path, prefix: str = "", is_last: bool = True):
        if path.name.startswith('.'):
            return
            
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{path.name}")
        
        if path.is_dir():
            children = [p for p in path.iterdir() if not p.name.startswith('.')]
            children.sort()
            
            for i, child in enumerate(children):
                is_last_child = i == len(children) - 1
                extension = "    " if is_last else "│   "
                print_tree(child, prefix + extension, is_last_child)
    
    print_tree(base_dir)

if __name__ == "__main__":
    organize_project()
