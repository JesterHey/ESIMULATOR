#!/usr/bin/env python3
"""
报告生成器模块
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class ReportGenerator:
    """分析报告生成器"""
    
    def __init__(self, output_dir: str = "results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_text_report(self, analysis_result: Dict[Any, Any], filename: 'Optional[str]' = None) -> str:
        """生成文本格式报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linearity_analysis_{timestamp}.txt"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("ESIMULATOR DFG线性分析报告\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            summary = analysis_result.get('summary', {})
            f.write("分析摘要:\n")
            f.write("-" * 15 + "\n")
            f.write(f"总表达式数: {summary.get('total_expressions', 0)}\n")
            f.write(f"线性表达式: {summary.get('linear_expressions', 0)} ({summary.get('linearity_ratio', 0):.1%})\n")
            f.write(f"非线性表达式: {summary.get('nonlinear_expressions', 0)} ({1-summary.get('linearity_ratio', 0):.1%})\n\n")
            
            # 表达式类型分布
            type_dist = analysis_result.get('expression_type_distribution', {})
            if type_dist:
                f.write("表达式类型分布:\n")
                f.write("-" * 20 + "\n")
                for expr_type, count in type_dist.items():
                    percentage = count / summary.get('total_expressions', 1) * 100
                    f.write(f"{expr_type:<15}: {count:>3} ({percentage:>5.1f}%)\n")
                f.write("\n")
            
            # 复杂度分布
            complexity_dist = analysis_result.get('complexity_distribution', {})
            if complexity_dist:
                f.write("复杂度分布:\n")
                f.write("-" * 15 + "\n")
                for complexity, count in complexity_dist.items():
                    percentage = count / summary.get('total_expressions', 1) * 100
                    f.write(f"{complexity:<10}: {count:>3} ({percentage:>5.1f}%)\n")
                f.write("\n")
            
            # 非线性原因分析
            nonlinear_reasons = analysis_result.get('nonlinear_reasons', {})
            if nonlinear_reasons:
                f.write("非线性原因分析:\n")
                f.write("-" * 20 + "\n")
                for reason, count in nonlinear_reasons.items():
                    f.write(f"{reason}: {count}\n")
                f.write("\n")
            
            # 详细信号分析
            detailed = analysis_result.get('detailed_analyses', {})
            if detailed:
                f.write("详细信号分析:\n")
                f.write("-" * 20 + "\n")
                for signal, analysis in sorted(detailed.items()):
                    linearity = "线性" if analysis.get('is_linear') else "非线性"
                    reason = analysis.get('reason', '未知')
                    f.write(f"{signal:<20}: {linearity:<6} - {reason}\n")
        
        return filepath
    
    def generate_json_report(self, analysis_result: Dict[Any, Any], filename: 'Optional[str]' = None, operator_linearity_tags: 'Optional[Dict[str, int]]' = None) -> str:
        """生成JSON格式报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linearity_analysis_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # 添加元数据
        report_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'tool_version': '2.0.0',
                'analysis_type': 'dfg_linearity'
            },
            'analysis_result': analysis_result
        }
        if operator_linearity_tags is not None:
            report_data['metadata']['operator_linearity_tags'] = operator_linearity_tags
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def generate_summary_report(self, analysis_result: Dict[Any, Any]) -> str:
        """生成简要摘要报告"""
        summary = analysis_result.get('summary', {})
        
        report = f"""
DFG线性分析摘要
===============
总表达式数: {summary.get('total_expressions', 0)}
线性表达式: {summary.get('linear_expressions', 0)} ({summary.get('linearity_ratio', 0):.1%})
非线性表达式: {summary.get('nonlinear_expressions', 0)} ({1-summary.get('linearity_ratio', 0):.1%})

主要非线性原因:
"""
        
        nonlinear_reasons = analysis_result.get('nonlinear_reasons', {})
        for reason, count in sorted(nonlinear_reasons.items(), key=lambda x: x[1], reverse=True)[:3]:
            report += f"- {reason}: {count}个\n"
        
        return report.strip()
    
    def save_analysis_data(self, analysis_result: Dict[Any, Any], filename: str = "analysis_data.json") -> str:
        """保存原始分析数据"""
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, indent=2, ensure_ascii=False)
        
        return filepath

    # ---------------------- 新增导出：图与 Bind 掩码 ----------------------
    def generate_graph_json(self, analysis_result: Dict[Any, Any], dfg_file: str, filename: str) -> str:
        """根据分析结果与原始 DFG 内容，导出 *_dfg_linearity_graph.json。
        结构符合 src/analyzers/graph_loader.load_graph_from_json 所需：
          { nodes: {name: {is_linear, reason, operators, expression_type}}, edges: [[src, dst], ...] }
        边：从表达式中的 Terminal 源指向 bind 目标。
        """
        from esimulator.core.dfg_parser import DFGParser
        parser = DFGParser()
        parsed = parser.parse_file(dfg_file)

        detailed = analysis_result.get('detailed_analyses', {})
        nodes = {}
        for name, ana in detailed.items():
            nodes[name] = {
                'is_linear': bool(ana.get('is_linear', False)),
                'reason': ana.get('reason', ''),
                'operators': list(ana.get('operators', [])),
                'expression_type': ana.get('expression_type', 'unknown'),
            }

        # 提取 Terminal 依赖作为边
        import re
        edges = []
        for dest, expr in parsed.get('signals', {}).items():
            for m in re.finditer(r"\(Terminal\s+([^\)\s]+)\)", expr):
                src = m.group(1)
                edges.append([src, dest])

        payload = { 'nodes': nodes, 'edges': edges }
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return filepath

    def generate_bind_masks_json(self, analysis_result: Dict[Any, Any], dfg_file: str, filename: str,
                                 *, linearity_mode: str = 'arith', omit_trivial: bool = False,
                                 include_human_labels: bool = True, verilog_file: str = None, module_prefix: str = "") -> str:
        """导出 *_dfg_bind_masks.json，供 src/simulated_annealing.py 的 Bind 掩码 SA 使用。
        约定字段（兼容 SA 脚本读取）：
          - binds: [
              {
                dest: <信号名>,
                workset_order: [<op_id>...],
                workset_mask: [0/1...],  # 1 表示线性/可翻转位
                fusable_adj: [[op_id_a, op_id_b], ...],
                operator_count: <int>,
                sources: [<Terminal 源>...]
              }, ...
            ]
        生成策略：
          - 运算符次序：按 DFG 文本中出现顺序；同时将 Concat/Partselect 计入工作集。
          - 掩码：Plus/Minus/UnaryMinus/Concat/Partselect 记为 1，其余 0。
          - 可融合边：以顺序相邻形成链式邻接，保证基本连通性。
        """
        # 使用增强版解析器导出，包含 AST + 掩码 + 可融合 + 元信息
        try:
            from src.analyzers.dfg_linearity_corrector import CorrectedLinearityAnalyzer
        except Exception:
            # 回退：保持旧实现（不推荐）
            from esimulator.core.dfg_parser import DFGParser
            parser = DFGParser()
            parsed = parser.parse_file(dfg_file)
            linear_ops = { 'Plus', 'Minus', 'UnaryMinus', 'Concat', 'Partselect' }
            import re
            binds = []
            for dest, expr in parsed.get('signals', {}).items():
                ops = re.findall(r"\(Operator\s+(\w+)\s+Next:", expr)
                concat_count = len(re.findall(r"\(Concat\b", expr))
                partsel_count = len(re.findall(r"\(Partselect\b", expr))
                ops += [ 'Concat' ] * max(0, concat_count - ops.count('Concat'))
                ops += [ 'Partselect' ] * max(0, partsel_count - ops.count('Partselect'))
                order = [ f"{dest}#op{i}:{name}" for i, name in enumerate(ops) ]
                mask = [ 1 if name in linear_ops else 0 for name in ops ]
                adj = []
                for i in range(len(order) - 1):
                    adj.append([ order[i], order[i+1] ])
                sources = list({ m.group(1) for m in re.finditer(r"\(Terminal\s+([^\)\s]+)\)", expr) })
                binds.append({
                    'dest': dest,
                    'workset_order': order,
                    'workset_mask': mask,
                    'fusable_adj': adj,
                    'operator_count': len(order),
                    'sources': sources,
                })
            payload = { 'binds': binds }
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            return filepath

        # 首选：增强版解析器
        analyzer = CorrectedLinearityAnalyzer(
            linearity_mode=linearity_mode,
            verilog_file=verilog_file if verilog_file else "",
            module_prefix=module_prefix
        )
        filepath = os.path.join(self.output_dir, filename)
        analyzer.export_bind_masks(dfg_file, filepath, omit_trivial=omit_trivial, include_human_labels=include_human_labels)
        filepath = os.path.join(self.output_dir, filename)
        return filepath
