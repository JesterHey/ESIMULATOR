#!/usr/bin/env python3
"""
报告生成器模块
"""

import json
import os
from datetime import datetime
from typing import Dict, Any

class ReportGenerator:
    """分析报告生成器"""
    
    def __init__(self, output_dir: str = "results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_text_report(self, analysis_result: Dict[Any, Any], filename: str = None) -> str:
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
    
    def generate_json_report(self, analysis_result: Dict[Any, Any], filename: str = None) -> str:
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
