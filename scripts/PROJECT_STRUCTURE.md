# ESIMULATOR 项目结构总览 (自动生成基础版)

该文档概述当前项目的目录结构、模块职责与核心依赖关系。生成日期: 2025-08-16

## 目录树

```text
ESIMULATOR/
├── pyproject.toml            # 项目元数据与依赖
├── README.md                 # 总体说明
├── LICENSE                   # 许可证(MIT)
├── esimulator_cli.py         # 统一CLI入口
├── analyze_linearity_v2.py   # 兼容入口 (旧脚本风格)
├── demo_comparison_v2.py     # 兼容对比演示入口
├── dfg_files/                # 输入DFG样例
├── verilog_files/            # 原始Verilog文件
├── results/                  # 分析输出与可视化结果
├── docs/                     # 文档集合
├── tests/                    # 测试用例
├── backup_before_reorganize/ # 重组前备份
├── src/                      # 原始实现保留 (逐步迁移中)
│   ├── analyzers/            # 旧分析模块 (含 CorrectedLinearityAnalyzer)
│   ├── parsers/              # 早期解析器实现
│   ├── visualization/        # DFG 可视化脚本 (dot / html)
│   └── visualizers/          # 旧可视化工具
└── esimulator/               # 新核心包 (V2 架构)
    ├── __init__.py           # 包导出 LinearityAnalyzer/DFGParser/ReportGenerator
    ├── core/                 # 核心逻辑
    │   ├── linearity_analyzer.py  # 新版 LinearityAnalyzer
    │   ├── dfg_parser.py          # 解析器抽离
    │   └── report_generator.py    # 报告生成
    ├── cli/                  # 细分 CLI 子命令实现
    ├── utils/                # 通用工具函数
    └── examples/             # 示例代码
```

## 核心模块说明

| 模块 | 位置 | 主要职责 | 依赖 | 备注 |
|------|------|----------|------|------|
| LinearityAnalyzer | `esimulator/core/linearity_analyzer.py` | 表达式级线性分析 | re, dataclasses | 取代旧 CorrectedLinearityAnalyzer |
| DFGParser | `esimulator/core/dfg_parser.py` | DFG文本解析 | re | 仅解析不判断线性 |
| ReportGenerator | `esimulator/core/report_generator.py` | 报告文本/JSON输出 | os, json | 统一输出接口 |
| CLI 主入口 | `esimulator_cli.py` | 分发子命令 | argparse | 使用内部 cli/* 命令 |
| 可视化 (DOT/HTML) | `src/visualization/dfg_linearity_viz.py` | 生成 DOT / 交互 HTML | re, json | 独立脚本, 暂未整合到包 |
| 旧分析器 | `src/analyzers/dfg_linearity_corrector.py` | 旧命名/兼容实现 | re, dataclasses | 保留回溯 |

## 依赖关系（逻辑）

```text
DFG 文件(.txt)
   │
   ▼
DFGParser  --> 解析 -> 中间结构(signals/binds)
   │                                 │
   │                                 └─► 可视化脚本 (构建节点/边)
   ▼
LinearityAnalyzer (构建表达式树/判定线性)
   │
   ├─► ReportGenerator  (生成文本 / JSON)
   └─► (未来) 可视化适配层 -> 图形/网页展示
```

## 设计原则

1. 向后兼容：旧脚本与新 CLI 并存，不破坏已有调用
2. 职责分离：解析、分析、输出、展示各自独立
3. 渐进迁移：`src/` 中旧实现逐步吸收/淘汰
4. 可扩展性：后续可添加新分析 passes / 新格式输出

## 待改进建议

- 将 `dfg_linearity_viz.py` 重构为包内可复用模块 (esimulator/visual)
- 增加自动化测试覆盖 LinearityAnalyzer 行为 (更多 DFG 样例)
- 引入类型检查 (mypy) 与 CI
- 增设 `docs/API_REFERENCE.md` 生成式文档
- 提供 `esimulator.visual.html` 封装, 供 API 直接输出 HTML 字符串
- 拆分大型 `linearity_analyzer.py` 为 parser + classifier + metrics 多文件

## 自动化文档计划 (下一步可执行)

1. 脚本扫描 `esimulator/core`，提取类/方法 docstring 生成 API 文档
2. 生成 `docs/API_REFERENCE.md`
3. 在 README 增加 “结构与依赖” 小节引用该文档链接

---
(此文件为初版结构说明，可继续迭代自动化生成程度。)
