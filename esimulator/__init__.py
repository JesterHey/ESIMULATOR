"""
ESIMULATOR - DFG线性分析工具包
"""

__version__ = "2.0.0"
__author__ = "ESIMULATOR Team"
__description__ = "Data Flow Graph线性分析工具"

from .core.linearity_analyzer import LinearityAnalyzer
from .core.dfg_parser import DFGParser
from .core.report_generator import ReportGenerator

__all__ = [
    'LinearityAnalyzer',
    'DFGParser', 
    'ReportGenerator'
]
