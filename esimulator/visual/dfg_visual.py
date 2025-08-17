#!/usr/bin/env python3
"""DFG 线性/非线性可视化模块化版本

封装自原脚本 `src/visualization/dfg_linearity_viz.py` 的核心逻辑:
 - 解析 DFG (若外部未提供已解析结构)
 - 构建节点/边 + 线性标注
 - 输出 Graphviz DOT
 - 生成交互式 HTML (纯原生 JS 力导布局)

提供面向编程接口, 便于在 CLI / 其它模块中复用。
"""
from __future__ import annotations
import os, re, json
from typing import Dict, List, Tuple, Set, Optional, Any

# 复用核心线性分析逻辑
try:
    from esimulator.core.linearity_analyzer import LinearityAnalyzer
except Exception:
    # 回退：若运行环境路径问题，延迟导入在函数内部再尝试
    LinearityAnalyzer = None  # type: ignore

COLOR_LINEAR = '#4CAF50'
COLOR_NONLINEAR = '#F44336'
COLOR_UNKNOWN = '#9E9E9E'

PRIORITY = ["Reg", "Output", "Input", "Wire", "Inout"]
SHAPE_MAP = {
    'Reg': 'doublecircle',
    'Output': 'box',
    'Input': 'diamond',
    'Wire': 'ellipse',
    'Inout': 'hexagon'
}

# 不再在此硬编码线性/非线性集合，统一由 LinearityAnalyzer 提供

# -------------------- 解析与构建 --------------------

def parse_dfg(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        txt = f.read()
    term_pat = re.compile(r'\(Term name:([^\s]+) type:\[(.*?)\]')
    signals: Dict[str, List[str]] = {}
    for m in term_pat.finditer(txt):
        name = m.group(1)
        types = [t.strip().strip("'") for t in m.group(2).split(',') if t.strip()]
        signals[name] = types
    bind_pat = re.compile(r'\(Bind dest:([^\s]+).*?tree:(.*?)\)(?=\n\(Bind|\n\n|\Z)', re.DOTALL)
    binds: Dict[str, str] = {}
    for m in bind_pat.finditer(txt):
        dest = m.group(1)
        tree = m.group(2).strip()
        binds[dest] = tree
    return signals, binds

def _ensure_analyzer(analyzer: Optional[Any]):
    global LinearityAnalyzer
    if analyzer is not None:
        return analyzer
    if LinearityAnalyzer is None:
        from esimulator.core.linearity_analyzer import LinearityAnalyzer as _LA  # lazy import
        LinearityAnalyzer = _LA  # type: ignore
    return LinearityAnalyzer()

def analyze_expr_with_core(tree: str, analyzer: Optional[Any]=None):
    """使用核心 LinearityAnalyzer 的私有逻辑分析单个表达式。

    注意：核心类方法是 _analyze_signal_expression(signal, tree)，这里虚拟一个信号名占位。
    返回: (is_linear, reasons_list, extra_dict)
    reasons_list 仅包含触发非线性判断的运算符 / 'Branch' 标签，便于可视化与旧格式兼容。
    extra_dict 包含 complexity / expression_type / full_reason / operators
    """
    analyzer = _ensure_analyzer(analyzer)
    # 访问其内部方法（受控使用）
    try:
        analysis = analyzer._analyze_signal_expression('__temp__', tree)  # type: ignore
    except Exception:
        return False, ['解析错误'], {'complexity': 'error', 'expression_type': 'unknown', 'reason': '解析错误', 'operators': []}

    is_lin = analysis['is_linear']
    ops = analysis.get('operators', []) or []
    full_reason = analysis.get('reason', '')
    nonlinear_ops = getattr(analyzer, 'nonlinear_operators', set())
    reasons: List[str] = []
    if not is_lin:
        # 提取触发因子
        for op in ops:
            if op in nonlinear_ops and op not in reasons:
                reasons.append(op)
        if 'Branch' in tree and 'Branch' not in reasons:
            reasons.append('Branch')
        if not reasons and full_reason:
            reasons.append(full_reason[:12])  # fallback 短标签
    return is_lin, reasons, {
        'complexity': analysis.get('complexity'),
        'expression_type': analysis.get('expression_type'),
        'reason': full_reason,
        'operators': ops
    }

def extract_deps(tree: str) -> Set[str]:
    return set(re.findall(r'Terminal ([^\s)]+)', tree))

def build_graph_data(signals: Dict[str, List[str]], binds: Dict[str,str], *, analyzer_report: Optional[Dict]=None):
    """构建可视化节点/边；若提供 analyzer_report 则直接使用其中的 detailed_analyses。"""
    nodes: Dict[str, Dict] = {}
    edges: List[Tuple[str,str]] = []
    detailed = analyzer_report.get('detailed_analyses') if analyzer_report else None
    analyzer = None if detailed else _ensure_analyzer(None)
    for name, types in signals.items():
        tree = binds.get(name)
        if tree:
            if detailed and name in detailed:
                da = detailed[name]
                is_lin = da['is_linear']
                reasons: List[str] = []
                if not is_lin:
                    nonlinear_ops = getattr(_ensure_analyzer(analyzer), 'nonlinear_operators', set())
                    for op in da.get('operators', []):
                        if op in nonlinear_ops and op not in reasons:
                            reasons.append(op)
                    if '(Branch ' in tree and 'Branch' not in reasons:
                        reasons.append('Branch')
                nodes[name] = {
                    'types': types,
                    'tree': tree,
                    'is_linear': is_lin,
                    'reasons': reasons,
                    'complexity': da.get('complexity'),
                    'expression_type': da.get('expression_type'),
                    'full_reason': da.get('reason'),
                    'operators': da.get('operators')
                }
            else:
                is_lin, reasons, extra = analyze_expr_with_core(tree, analyzer)
                nodes[name] = {
                    'types': types,
                    'tree': tree,
                    'is_linear': is_lin,
                    'reasons': reasons,
                    'complexity': extra.get('complexity'),
                    'expression_type': extra.get('expression_type'),
                    'full_reason': extra.get('reason'),
                    'operators': extra.get('operators')
                }
        else:
            nodes[name] = {
                'types': types,
                'tree': None,
                'is_linear': None,
                'reasons': [],
                'complexity': None,
                'expression_type': None,
                'full_reason': None,
                'operators': []
            }
    for dest, tree in binds.items():
        for d in extract_deps(tree):
            if d == dest:
                continue
            if d not in nodes:
                nodes[d] = {'types': ['External'], 'tree': None, 'is_linear': None, 'reasons': [], 'complexity': None, 'expression_type': None, 'full_reason': None, 'operators': []}
            edges.append((d, dest))
    return nodes, edges

# -------------------- 过滤/聚焦/指标 --------------------

def filter_nodes(nodes: Dict[str, Dict], edges: List[Tuple[str,str]], keep: Optional[str]):
    if keep not in (None,'linear','nonlinear'): return nodes, edges
    if keep is None: return nodes, edges
    if keep == 'linear': allow = {n for n,v in nodes.items() if v['is_linear'] is True}
    else: allow = {n for n,v in nodes.items() if v['is_linear'] is False}
    new_nodes = {n:v for n,v in nodes.items() if n in allow}
    new_edges = [(s,d) for s,d in edges if s in new_nodes and d in new_nodes]
    return new_nodes, new_edges

def focus_subgraph(nodes: Dict[str, Dict], edges: List[Tuple[str,str]], root: str, depth: int):
    if root not in nodes: return nodes, edges
    adj, rev = {}, {}
    for s,d in edges:
        adj.setdefault(s,set()).add(d)
        rev.setdefault(d,set()).add(s)
    visited={root}
    frontier={root}
    for _ in range(depth):
        nxt=set()
        for n in frontier:
            for m in adj.get(n,[]):
                if m not in visited:
                    visited.add(m); nxt.add(m)
        frontier=nxt
        if not frontier: break
    preds=set()
    for v in list(visited): preds.update(rev.get(v,[]))
    visited|=preds
    new_nodes={n:v for n,v in nodes.items() if n in visited}
    new_edges=[(s,d) for s,d in edges if s in new_nodes and d in new_nodes]
    return new_nodes, new_edges

def compute_metrics(nodes: Dict[str, Dict], edges: List[Tuple[str,str]]):
    total_expr=sum(1 for v in nodes.values() if v['is_linear'] is not None)
    linear_expr=sum(1 for v in nodes.values() if v['is_linear'] is True)
    nonlinear_expr=sum(1 for v in nodes.values() if v['is_linear'] is False)
    reason_freq={}
    for v in nodes.values():
        if v['is_linear'] is False:
            # 使用更详细的 operators / reasons 统计
            counted = set()
            for op in v.get('operators', []) or []:
                if op not in counted:
                    reason_freq[op]=reason_freq.get(op,0)+1; counted.add(op)
            for r in v.get('reasons', []) or []:
                if r not in counted:
                    reason_freq[r]=reason_freq.get(r,0)+1; counted.add(r)
    adj={}
    for s,d in edges:
        if nodes.get(s,{}).get('is_linear') is True and nodes.get(d,{}).get('is_linear') is True:
            adj.setdefault(s,set()).add(d)
    memo={}; path_next={}; visiting=set()
    def dfs(n:str)->int:
        if n in memo: return memo[n]
        if n in visiting: memo[n]=1; path_next[n]=None; return 1
        visiting.add(n)
        best=1; child=None
        for m in adj.get(n,[]):
            l=dfs(m)+1
            if l>best: best=l; child=m
        visiting.remove(n)
        memo[n]=best; path_next[n]=child; return best
    for n,v in nodes.items():
        if v.get('is_linear') is True: dfs(n)
    longest_len=0; start=None
    for n,l in memo.items():
        if l>longest_len: longest_len=l; start=n
    path=[]; cur=start
    while cur is not None: path.append(cur); cur=path_next.get(cur)
    return {
        'total_expressions': total_expr,
        'linear_expressions': linear_expr,
        'nonlinear_expressions': nonlinear_expr,
        'linearity_ratio': linear_expr/total_expr if total_expr else 0,
        'nonlinearity_ratio': nonlinear_expr/total_expr if total_expr else 0,
        'nonlinear_reason_frequency': reason_freq,
        'longest_linear_chain_length': longest_len,
        'longest_linear_chain_path': path
    }

# -------------------- 输出 --------------------

def classify_shape(types: List[str]) -> str:
    for t in PRIORITY:
        if t in types: return SHAPE_MAP[t]
    return 'oval'

def write_dot(nodes: Dict[str, Dict], edges: List[Tuple[str,str]], out_path: str, *, detailed: bool=False):
    lines=["digraph DFG {","  rankdir=LR;","  splines=true;","  node [style=filled,fontname=Helvetica];"]
    for name, info in nodes.items():
        shape = classify_shape(info['types'])
        is_lin = info['is_linear']
        if is_lin is True:
            color = COLOR_LINEAR; status = 'L'
        elif is_lin is False:
            color = COLOR_NONLINEAR; status = 'NL'
        else:
            color = COLOR_UNKNOWN; status = '?'
        reasons = ','.join(info['reasons']) if info['reasons'] else ''
        extra_line = ''
        if detailed:
            if is_lin is False:
                extra_line = (info.get('full_reason') or '')[:40]
            else:
                comp = info.get('complexity')
                if comp and comp not in ('simple','error'):
                    extra_line = f"C:{comp}"
        label = f"{name}\n{status}" + (f"\n{reasons}" if reasons else '') + (f"\n{extra_line}" if extra_line else '')
        esc = label.replace('"','\\"')
        lines.append(f"  \"{name}\" [label=\"{esc}\", shape={shape}, fillcolor=\"{color}\"];" )
    for s,d in edges:
        lines.append(f"  \"{s}\" -> \"{d}\";")
    lines.append('}')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path,'w',encoding='utf-8') as f: f.write('\n'.join(lines))

def write_interactive_html(nodes: Dict[str, Dict], edges: List[Tuple[str,str]], metrics: Dict, out_path: str):
    node_list=[]; index_map={}
    for idx,(name,info) in enumerate(nodes.items()):
        index_map[name]=idx
        node_list.append({
            'id':name,
            'linear':info['is_linear'],
            'reasons':info['reasons'],
            'types':info['types'],
            'complexity':info.get('complexity'),
            'expr_type':info.get('expression_type'),
            'full_reason':info.get('full_reason'),
            'operators':info.get('operators')
        })
    link_list=[]
    for s,d in edges:
        if s in index_map and d in index_map:
            link_list.append({'source':s,'target':d})
    data_js=json.dumps({'nodes':node_list,'links':link_list,'metrics':metrics}, ensure_ascii=False)
    placeholder='__DATA__'
    html="""<!DOCTYPE html><html lang='zh-cn'><head><meta charset='UTF-8'/><title>DFG 线性可视化</title>
<style>body{font-family:Helvetica,Arial,sans-serif;margin:0;display:flex;height:100vh;}#panel{width:300px;background:#f5f5f5;border-right:1px solid #ccc;padding:12px;overflow:auto;}#graph{flex:1;position:relative;}svg{width:100%;height:100%;background:#ffffff;}.node circle{stroke:#333;stroke-width:1px;cursor:pointer;}.node text{font-size:10px;pointer-events:none;}.link{stroke:#999;stroke-opacity:0.6;}.legend-item{display:flex;align-items:center;margin-bottom:4px;font-size:12px;}.legend-color{width:14px;height:14px;margin-right:6px;border:1px solid #333;}#search{width:100%;padding:4px;margin-bottom:8px;}button{margin-right:6px;margin-bottom:6px;}</style></head><body><div id='panel'><h3 style='margin-top:0'>DFG 线性/非线性</h3><input id='search' placeholder='搜索节点 (回车)' /><div><button id='btnAll'>全部</button><button id='btnLin'>线性</button><button id='btnNon'>非线性</button></div><div class='legend-item'><div class='legend-color' style='background:#4CAF50'></div>线性</div><div class='legend-item'><div class='legend-color' style='background:#F44336'></div>非线性</div><div class='legend-item'><div class='legend-color' style='background:#9E9E9E'></div>未知/外部</div><h4>统计</h4><pre id='metrics' style='white-space:pre-wrap;font-size:11px;background:#fff;border:1px solid #ddd;padding:6px;'></pre><p style='font-size:11px;color:#666'>拖拽节点可重新布局。双击节点高亮邻居。</p></div><div id='graph'><svg id='svg'><g id='links'></g><g id='nodes'></g></svg></div><script>const graphData=__DATA__;const COLOR_LINEAR='#4CAF50',COLOR_NON='#F44336',COLOR_UNKNOWN='#9E9E9E';const width=window.innerWidth-300,height=window.innerHeight;const svg=document.getElementById('svg');const ns='http://www.w3.org/2000/svg';let nodes=graphData.nodes.map(n=>Object.assign({},n));let links=graphData.links.map(l=>Object.assign({},l));const nodeById=new Map(nodes.map(n=>[n.id,n]));links.forEach(l=>{l.source=nodeById.get(l.source);l.target=nodeById.get(l.target);});nodes.forEach(n=>{n.x=Math.random()*width;n.y=Math.random()*height;n.vx=0;n.vy=0;});const linkForce=()=>{links.forEach(l=>{const dx=l.target.x-l.source.x;const dy=l.target.y-l.source.y;let dist=Math.sqrt(dx*dx+dy*dy)||0.01;const k=0.02*(dist-90);const nx=dx/dist,ny=dy/dist;l.target.vx-=k*nx;l.target.vy-=k*ny;l.source.vx+=k*nx;l.source.vy+=k*ny;});};const repelForce=()=>{for(let i=0;i<nodes.length;i++){for(let j=i+1;j<nodes.length;j++){const a=nodes[i],b=nodes[j];let dx=b.x-a.x,dy=b.y-a.y;let d2=dx*dx+dy*dy+0.01;if(d2>50000) continue;const f=3200/d2;const dist=Math.sqrt(d2);const nx=dx/dist,ny=dy/dist;a.vx-=f*nx;a.vy-=f*ny;b.vx+=f*nx;b.vy+=f*ny;}}};const centerForce=()=>{const cx=width/2,cy=height/2;nodes.forEach(n=>{n.vx+=(cx-n.x)*0.001;n.vy+=(cy-n.y)*0.001;});};function step(){linkForce();repelForce();centerForce();nodes.forEach(n=>{n.vx*=0.86;n.vy*=0.86;n.x+=n.vx;n.y+=n.vy;});draw();requestAnimationFrame(step);}const gLinks=document.getElementById('links');const gNodes=document.getElementById('nodes');function colorOf(n){if(n.linear===true) return COLOR_LINEAR;if(n.linear===false) return COLOR_NON;return COLOR_UNKNOWN;}function draw(){gLinks.innerHTML='';links.forEach(l=>{const line=document.createElementNS(ns,'line');line.setAttribute('class','link');line.setAttribute('x1',l.source.x);line.setAttribute('y1',l.source.y);line.setAttribute('x2',l.target.x);line.setAttribute('y2',l.target.y);line.setAttribute('stroke','#999');line.setAttribute('stroke-width','1');gLinks.appendChild(line);});gNodes.innerHTML='';nodes.forEach(n=>{const g=document.createElementNS(ns,'g');g.setAttribute('class','node');g.setAttribute('transform',`translate(${n.x},${n.y})`);const c=document.createElementNS(ns,'circle');c.setAttribute('r',Math.max(6,Math.min(14,(n.reasons&&n.reasons.length?10:8))));c.setAttribute('fill',colorOf(n));c.dataset.id=n.id;g.appendChild(c);const t=document.createElementNS(ns,'text');t.setAttribute('text-anchor','middle');t.setAttribute('dy',20);t.textContent=n.id.split('.').pop();g.appendChild(t);g.addEventListener('mousedown',startDrag);g.addEventListener('dblclick',()=>highlightNeighbors(n.id));g.addEventListener('mouseenter',()=>showTooltip(n));g.addEventListener('mouseleave',hideTooltip);gNodes.appendChild(g);});}let dragging=null;function startDrag(e){dragging=findNodeFromEvent(e);if(!dragging) return;e.preventDefault();}svg.addEventListener('mousemove',e=>{if(!dragging) return;const pt=svg.createSVGPoint();pt.x=e.clientX;pt.y=e.clientY;const svgP=pt.matrixTransform(svg.getScreenCTM().inverse());dragging.x=svgP.x;dragging.y=svgP.y;dragging.vx=dragging.vy=0;draw();});svg.addEventListener('mouseup',()=>{dragging=null;});svg.addEventListener('mouseleave',()=>{dragging=null;});function findNodeFromEvent(e){const target=e.target;if(target.tagName==='circle'){const id=target.dataset.id;return nodes.find(n=>n.id===id);}return null;}function highlightNeighbors(id){const neigh=new Set([id]);links.forEach(l=>{if(l.source.id===id) neigh.add(l.target.id);if(l.target.id===id) neigh.add(l.source.id);});gNodes.querySelectorAll('g.node circle').forEach(c=>{if(neigh.has(c.dataset.id)) c.setAttribute('stroke-width','3');else c.setAttribute('stroke-width','0.5');});}let tip=document.createElement('div');tip.style.position='fixed';tip.style.pointerEvents='none';tip.style.background='rgba(0,0,0,0.75)';tip.style.color='#fff';tip.style.padding='4px 6px';tip.style.fontSize='11px';tip.style.borderRadius='4px';tip.style.display='none';document.body.appendChild(tip);function showTooltip(n){tip.innerHTML=`<b>${n.id}</b>`+`<br/>状态:${n.linear===true?'线性':(n.linear===false?'非线性':'?')}`+`<br/>信号类型:${n.types.join(',')}`+`<br/>表达式类型:${n.expr_type||'-'}`+`<br/>复杂度:${n.complexity||'-'}`+`<br/>运算符:${(n.operators||[]).join(',')||'-'}`+`<br/>判定理由:${n.full_reason|| (n.reasons||[]).join(',')||'-'}`;tip.style.display='block';}function hideTooltip(){tip.style.display='none';}svg.addEventListener('mousemove',e=>{if(tip.style.display!=='none'){tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY+12)+'px';}});function applyFilter(mode){nodes.forEach(n=>{n._hidden=(mode==='linear'&&n.linear!==true)||(mode==='nonlinear'&&n.linear!==false);});}function redrawFilter(){nodes=nodes.filter(()=>true);draw();gNodes.querySelectorAll('g.node').forEach(g=>{const id=g.querySelector('circle').dataset.id;const n=nodeById.get(id);if(n._hidden) g.style.display='none'; else g.style.display='';});}document.getElementById('btnAll').onclick=()=>{nodes.forEach(n=>n._hidden=false);redrawFilter();};document.getElementById('btnLin').onclick=()=>{applyFilter('linear');redrawFilter();};document.getElementById('btnNon').onclick=()=>{applyFilter('nonlinear');redrawFilter();};document.getElementById('search').addEventListener('keydown',e=>{if(e.key==='Enter'){const q=e.target.value.trim();gNodes.querySelectorAll('g.node circle').forEach(c=>{c.setAttribute('stroke','#333');c.setAttribute('stroke-width','1');});if(q){const n=nodes.find(n=>n.id.endsWith(q)||n.id===q);if(n){highlightNeighbors(n.id);}}}});document.getElementById('metrics').textContent=JSON.stringify(graphData.metrics,null,2);draw();step();</script></body></html>"""
    out_dir=os.path.dirname(out_path)
    if out_dir: os.makedirs(out_dir, exist_ok=True)
    with open(out_path,'w',encoding='utf-8') as f: f.write(html.replace(placeholder,data_js))

# -------------------- 高层封装 --------------------

def visualize_from_dfg(dfg_path: str, out_dir: str, stem: Optional[str]=None, *, focus: Optional[str]=None, depth: int=2, keep: Optional[str]=None, html: bool=True, dot: bool=True, detailed_label: bool=False, split_subgraphs: bool=False):
    signals, binds = parse_dfg(dfg_path)
    analyzer = _ensure_analyzer(None)
    report = analyzer.analyze_dfg_file(dfg_path)
    nodes, edges = build_graph_data(signals, binds, analyzer_report=report)
    if focus: nodes, edges = focus_subgraph(nodes, edges, focus, depth)
    if keep: nodes, edges = filter_nodes(nodes, edges, keep)
    metrics = compute_metrics(nodes, edges)
    if not stem: stem=os.path.splitext(os.path.basename(dfg_path))[0]
    os.makedirs(out_dir, exist_ok=True)
    if dot:
        write_dot(nodes, edges, os.path.join(out_dir, f"{stem}.dot"), detailed=detailed_label)
        if split_subgraphs:
            # 线性子图
            lin_nodes = {k:v for k,v in nodes.items() if v['is_linear'] is True}
            lin_edges = [(s,d) for s,d in edges if s in lin_nodes and d in lin_nodes]
            write_dot(lin_nodes, lin_edges, os.path.join(out_dir, f"{stem}_linear.dot"), detailed=detailed_label)
            # 非线性子图
            nlin_nodes = {k:v for k,v in nodes.items() if v['is_linear'] is False}
            nlin_edges = [(s,d) for s,d in edges if s in nlin_nodes and d in nlin_nodes]
            write_dot(nlin_nodes, nlin_edges, os.path.join(out_dir, f"{stem}_nonlinear.dot"), detailed=detailed_label)
    if html and split_subgraphs:
        # HTML 子图（可选；仅输出主图 HTML，避免文件数膨胀，可扩展为 True 再输出）
        pass
    if html:
        write_interactive_html(nodes, edges, metrics, os.path.join(out_dir, f"{stem}.html"))
    return {'nodes':nodes,'edges':edges,'metrics':metrics,'analysis_report':report}
