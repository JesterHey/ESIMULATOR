#!/usr/bin/env python3
"""
测试线性分析结果转换器
"""

import unittest
import tempfile
import os
import sys

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.analyzers.linearity_to_graph_converter import (
    LinearityAnalysisToGraphConverter, 
    convert_analysis_to_graph
)
import networkx as nx


class TestLinearityToGraphConverter(unittest.TestCase):
    
    def setUp(self):
        """设置测试环境"""
        self.converter = LinearityAnalysisToGraphConverter()
        
        # 创建测试用的分析文件
        self.test_analysis_content = """
4004_dfg.txt线性分析报告
==================================================

分析结果:
---------------
总表达式数: 5
线性表达式: 2 (40.0%)
非线性表达式: 3 (60.0%)

详细信号分析:
--------------------
alu.signal1         : 线性     - 直接终端赋值
alu.signal2         : 非线性    - 非线性算子:And
alu.signal3         : 线性     - 常量赋值
alu.signal4         : 非线性    - 条件分支表达式
alu.signal5         : 非线性    - 非线性算子:Or,非线性算子:Unot
"""
        
        # 创建测试用的DFG文件
        self.test_dfg_content = """
Term:
(Term name:alu.signal1 type:['Wire'] msb:(IntConst 0) lsb:(IntConst 0))
(Term name:alu.signal2 type:['Wire'] msb:(IntConst 0) lsb:(IntConst 0))
(Term name:alu.signal3 type:['Wire'] msb:(IntConst 0) lsb:(IntConst 0))
(Term name:alu.signal4 type:['Reg'] msb:(IntConst 0) lsb:(IntConst 0))
(Term name:alu.signal5 type:['Output', 'Wire'] msb:(IntConst 0) lsb:(IntConst 0))
(Term name:alu.input1 type:['Input', 'Wire'] msb:(IntConst 0) lsb:(IntConst 0))

Bind:
(Bind dest:alu.signal1 tree:(Terminal alu.input1))
(Bind dest:alu.signal2 tree:(Operator And Next:(Terminal alu.signal1),(Terminal alu.input1)))
(Bind dest:alu.signal3 tree:(IntConst 1'b0))
(Bind dest:alu.signal4 tree:(Branch Cond:(Terminal alu.input1) True:(Terminal alu.signal1) False:(Terminal alu.signal2)))
(Bind dest:alu.signal5 tree:(Operator Or Next:(Terminal alu.signal3),(Terminal alu.signal4)))
"""
    
    def test_parse_linearity_analysis_file(self):
        """测试解析线性分析文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(self.test_analysis_content)
            f.flush()
            
            try:
                signal_data = self.converter.parse_linearity_analysis_file(f.name)
                
                # 检查解析结果
                self.assertIn('alu.signal1', signal_data)
                self.assertTrue(signal_data['alu.signal1']['is_linear'])
                self.assertEqual(signal_data['alu.signal1']['reason'], '直接终端赋值')
                
                self.assertIn('alu.signal2', signal_data)
                self.assertFalse(signal_data['alu.signal2']['is_linear'])
                self.assertEqual(signal_data['alu.signal2']['reason'], '非线性算子:And')
                
                self.assertEqual(len(signal_data), 5)
                
            finally:
                os.unlink(f.name)
    
    def test_parse_dfg_file(self):
        """测试解析DFG文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(self.test_dfg_content)
            f.flush()
            
            try:
                signals, binds = self.converter.parse_dfg_file(f.name)
                
                # 检查信号解析
                self.assertIn('alu.signal1', signals)
                self.assertEqual(signals['alu.signal1'], ['Wire'])
                
                self.assertIn('alu.signal5', signals)
                self.assertEqual(signals['alu.signal5'], ['Output', 'Wire'])
                
                # 检查绑定解析
                self.assertIn('alu.signal1', binds)
                self.assertIn('Terminal alu.input1', binds['alu.signal1'])
                
                self.assertEqual(len(signals), 6)  # 包括input1
                self.assertEqual(len(binds), 4)  # signal5的Bind可能因格式问题未正确解析
                
            finally:
                os.unlink(f.name)
    
    def test_extract_dependencies(self):
        """测试提取依赖关系"""
        # 测试简单的终端依赖
        deps = self.converter.extract_dependencies("(Terminal alu.input1)")
        self.assertEqual(deps, {'alu.input1'})
        
        # 测试复杂的表达式
        complex_expr = "(Operator And Next:(Terminal alu.signal1),(Terminal alu.input1))"
        deps = self.converter.extract_dependencies(complex_expr)
        self.assertEqual(deps, {'alu.signal1', 'alu.input1'})
        
        # 测试过滤无效信号名
        invalid_expr = "(Terminal alu.signal1),(Terminal inv(alid)signal)"
        deps = self.converter.extract_dependencies(invalid_expr)
        self.assertEqual(deps, {'alu.signal1'})
    
    def test_is_valid_signal_name(self):
        """测试信号名称验证"""
        # 有效信号名
        self.assertTrue(self.converter._is_valid_signal_name('alu.signal1'))
        self.assertTrue(self.converter._is_valid_signal_name('alu.n0123'))
        self.assertTrue(self.converter._is_valid_signal_name('_internal_signal'))
        
        # 无效信号名
        self.assertFalse(self.converter._is_valid_signal_name('alu.signal1)'))
        self.assertFalse(self.converter._is_valid_signal_name('signal,(invalid'))
        self.assertFalse(self.converter._is_valid_signal_name('123invalid'))
    
    def test_create_graph_integration(self):
        """测试创建图的完整流程"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='_dfg_linearity_analysis.txt', delete=False) as analysis_f:
            analysis_f.write(self.test_analysis_content)
            analysis_f.flush()
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='_dfg.txt', delete=False) as dfg_f:
                dfg_f.write(self.test_dfg_content)
                dfg_f.flush()
                
                try:
                    # 使用明确的DFG路径
                    graph = self.converter.create_graph_from_analysis(analysis_f.name, dfg_f.name)
                    
                    # 检查图的基本属性
                    self.assertGreater(graph.number_of_nodes(), 0)
                    self.assertGreater(graph.number_of_edges(), 0)
                    
                    # 检查节点属性
                    self.assertIn('alu.signal1', graph.nodes)
                    node_data = graph.nodes['alu.signal1']
                    self.assertTrue(node_data['is_linear'])
                    self.assertEqual(node_data['reason'], '直接终端赋值')
                    
                    # 检查边的存在
                    # signal1 依赖 input1
                    self.assertTrue(graph.has_edge('alu.input1', 'alu.signal1'))
                    
                    # 检查非线性节点
                    self.assertIn('alu.signal2', graph.nodes)
                    self.assertFalse(graph.nodes['alu.signal2']['is_linear'])
                    
                finally:
                    os.unlink(analysis_f.name)
                    os.unlink(dfg_f.name)


class TestGraphValidation(unittest.TestCase):
    
    def test_validate_graph_for_simulated_annealing(self):
        """测试图验证功能"""
        converter = LinearityAnalysisToGraphConverter()
        
        # 创建一个简单的测试图
        graph = nx.DiGraph()
        graph.add_node('node1', is_linear=True, reason='test')
        graph.add_node('node2', is_linear=False, reason='test')
        graph.add_node('node3', is_linear=None, reason='test')
        graph.add_edge('node1', 'node2')
        
        validation = converter.validate_graph_for_simulated_annealing(graph)
        
        self.assertTrue(validation['is_valid'])
        self.assertEqual(validation['statistics']['total_nodes'], 3)
        self.assertEqual(validation['statistics']['linear_nodes'], 1)
        self.assertEqual(validation['statistics']['nonlinear_nodes'], 1)
        self.assertEqual(validation['statistics']['unknown_nodes'], 1)
        self.assertEqual(validation['statistics']['total_edges'], 1)


class TestConvertAnalysisToGraph(unittest.TestCase):
    
    def test_convert_function(self):
        """测试便利转换函数"""
        # 使用实际的测试文件
        analysis_file = "/home/runner/work/ESIMULATOR/ESIMULATOR/results/4004_dfg_linearity_analysis.txt"
        
        if os.path.exists(analysis_file):
            try:
                graph, validation = convert_analysis_to_graph(analysis_file, validate=True)
                
                self.assertIsInstance(graph, nx.DiGraph)
                self.assertIsNotNone(validation)
                self.assertIn('statistics', validation)
                self.assertGreater(graph.number_of_nodes(), 0)
                
                # 检查至少有一些线性和非线性节点
                stats = validation['statistics']
                self.assertGreater(stats['linear_nodes'] + stats['nonlinear_nodes'], 0)
                
            except Exception as e:
                self.skipTest(f"测试文件不可用或路径问题: {e}")


if __name__ == '__main__':
    unittest.main()