#!/usr/bin/env python3
"""
文件工具模块
"""

import os
import json
from typing import List, Dict, Any

def find_dfg_files(directory: str) -> List[str]:
    """在目录中查找DFG文件"""
    dfg_files = []
    if not os.path.exists(directory):
        return dfg_files
    
    for filename in os.listdir(directory):
        if filename.endswith('.txt') and 'dfg' in filename.lower():
            dfg_files.append(os.path.join(directory, filename))
    
    return dfg_files

def load_json_file(filepath: str) -> Dict[Any, Any]:
    """加载JSON文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json_file(data: Dict[Any, Any], filepath: str) -> None:
    """保存JSON文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def ensure_directory(directory: str) -> None:
    """确保目录存在"""
    os.makedirs(directory, exist_ok=True)
