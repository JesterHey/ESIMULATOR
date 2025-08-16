#!/usr/bin/env python3
"""DFG 线性/非线性可视化 (Graphviz DOT)

直接解析 DFG 文本:
 1. 提取 Term -> 类型
 2. 提取 Bind 目的信号与表达式 tree
 3. 判定表达式线性/非线性:
        - 若存在 Branch 或 非线性运算符 => 非线性
        - 否则视为线性
 4. 依赖边: 表达式中引用的 Terminal X 指向目的信号 dest

使用:
    python3 src/visualization/dfg_linearity_viz.py \
            --dfg dfg_files/4004_dfg.txt \
            --out results/4004_dfg_linearity.dot

渲染 (可选 Graphviz 已安装):
    dot -Tpng results/4004_dfg_linearity.dot -o results/4004_dfg_linearity.png
"""
import argparse
import os
import re
import json
from typing import Dict, List, Tuple, Set, Optional

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

LINEAR_OPS = { 'Plus','Minus','UnaryMinus','Sll','Srl','Concat','Partselect' }
NONLINEAR_OPS = { 'And','Or','Xor','Xnor','Unot','Unor','Uand','Uxor','Times','Divide','Mod','Power','Eq','NotEq','Lt','Gt','Lte','Gte','Land','Lor' }

def classify_shape(types: List[str]) -> str:
    for t in PRIORITY:
        if t in types:
            return SHAPE_MAP[t]
    return 'oval'

def parse_dfg(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        txt = f.read()
    # Terms
    term_pat = re.compile(r'\(Term name:([^\s]+) type:\[(.*?)\]')
    signals: Dict[str, List[str]] = {}
    for m in term_pat.finditer(txt):
        name = m.group(1)
        types = [t.strip().strip("'") for t in m.group(2).split(',') if t.strip()]
        signals[name] = types
    # Binds
    bind_pat = re.compile(r'\(Bind dest:([^\s]+).*?tree:(.*?)\)(?=\n\(Bind|\n\n|\Z)', re.DOTALL)
    binds: Dict[str, str] = {}
    for m in bind_pat.finditer(txt):
        dest = m.group(1)
        tree = m.group(2).strip()
        binds[dest] = tree
    return signals, binds

def classify_expression(tree: str) -> Tuple[bool, List[str]]:
    reasons: Set[str] = set()
    # Branch => 非线性
    if 'Branch' in tree:
        reasons.add('Branch')
    # Operator 集合
    for op in re.findall(r'\(Operator (\w+) ', tree):
        if op in NONLINEAR_OPS:
            reasons.add(op)
    is_linear = len(reasons) == 0
    return is_linear, sorted(reasons)

def extract_deps(tree: str) -> Set[str]:
    deps: Set[str] = set()
    for t in re.findall(r'Terminal ([^\s)]+)', tree):
        deps.add(t)
    return deps

def build_graph(signals: Dict[str, List[str]], binds: Dict[str, str]):
    nodes: Dict[str, Dict] = {}
    edges: List[Tuple[str,str]] = []
    for name, types in signals.items():
        tree = binds.get(name)
        if tree:
            is_lin, reasons = classify_expression(tree)
            nodes[name] = {
                'types': types,
                'tree': tree,
                'is_linear': is_lin,
                'reasons': reasons
            }
        else:
            nodes[name] = {
                'types': types,
                'tree': None,
                'is_linear': None,
                'reasons': []
            }
    # deps
    for dest, tree in binds.items():
        deps = extract_deps(tree)
        for d in deps:
            if d == dest:
                continue
            if d not in nodes:
                nodes[d] = {'types': ['External'], 'tree': None, 'is_linear': None, 'reasons': []}
            edges.append((d, dest))
    return nodes, edges

def filter_nodes(nodes: Dict[str, Dict], edges: List[Tuple[str,str]], keep: Optional[str]) -> Tuple[Dict[str, Dict], List[Tuple[str,str]]]:
    """keep: None|'linear'|'nonlinear' -> filter node set."""
    if keep not in (None,'linear','nonlinear'):
        return nodes, edges
    if keep is None:
        return nodes, edges
    if keep == 'linear':
        allow = {n for n,v in nodes.items() if v['is_linear'] is True}
    else:
        allow = {n for n,v in nodes.items() if v['is_linear'] is False}
    # ensure isolated allowed nodes retained
    new_nodes = {n:v for n,v in nodes.items() if n in allow}
    new_edges = [(s,d) for s,d in edges if s in new_nodes and d in new_nodes]
    return new_nodes, new_edges

def focus_subgraph(nodes: Dict[str, Dict], edges: List[Tuple[str,str]], root: str, depth: int) -> Tuple[Dict[str, Dict], List[Tuple[str,str]]]:
    if root not in nodes:
        return nodes, edges  # fallback
    fwd = {}
    adj = {}
    rev = {}
    for s,d in edges:
        adj.setdefault(s, set()).add(d)
        rev.setdefault(d, set()).add(s)
    visited = {root}
    frontier = {root}
    for _ in range(depth):
        nxt = set()
        for n in frontier:
            for m in adj.get(n,[]):
                if m not in visited:
                    visited.add(m)
                    nxt.add(m)
        frontier = nxt
        if not frontier:
            break
    # Optionally also include immediate predecessors of visited nodes for context
    preds = set()
    for v in list(visited):
        preds.update(rev.get(v,[]))
    visited |= preds
    new_nodes = {n:v for n,v in nodes.items() if n in visited}
    new_edges = [(s,d) for s,d in edges if s in new_nodes and d in new_nodes]
    return new_nodes, new_edges

def compute_metrics(nodes: Dict[str, Dict], edges: List[Tuple[str,str]]) -> Dict:
    total_expr = sum(1 for v in nodes.values() if v['is_linear'] is not None)
    linear_expr = sum(1 for v in nodes.values() if v['is_linear'] is True)
    nonlinear_expr = sum(1 for v in nodes.values() if v['is_linear'] is False)
    reason_freq: Dict[str,int] = {}
    for v in nodes.values():
        if v['is_linear'] is False:
            for r in v['reasons']:
                reason_freq[r] = reason_freq.get(r,0)+1
    # longest linear chain (approx: treat as DAG ignoring cycles)
    adj = {}
    for s,d in edges:
        if nodes.get(s,{}).get('is_linear') is True and nodes.get(d,{}).get('is_linear') is True:
            adj.setdefault(s, set()).add(d)
    memo: Dict[str,int] = {}
    path_next: Dict[str,Optional[str]] = {}
    visiting=set()
    def dfs(n:str)->int:
        if n in memo:
            return memo[n]
        if n in visiting:  # cycle break
            memo[n]=1
            path_next[n]=None
            return 1
        visiting.add(n)
        best_len=1
        best_child=None
        for m in adj.get(n,[]):
            l=dfs(m)+1
            if l>best_len:
                best_len=l
                best_child=m
        visiting.remove(n)
        memo[n]=best_len
        path_next[n]=best_child
        return best_len
    for n,v in nodes.items():
        if v.get('is_linear') is True:
            dfs(n)
    longest_len=0
    start_node=None
    for n,l in memo.items():
        if l>longest_len:
            longest_len=l
            start_node=n
    longest_path=[]
    cur=start_node
    while cur is not None:
        longest_path.append(cur)
        cur=path_next.get(cur)
    return {
        'total_expressions': total_expr,
        'linear_expressions': linear_expr,
        'nonlinear_expressions': nonlinear_expr,
        'linearity_ratio': linear_expr/total_expr if total_expr else 0,
        'nonlinearity_ratio': nonlinear_expr/total_expr if total_expr else 0,
        'nonlinear_reason_frequency': reason_freq,
        'longest_linear_chain_length': longest_len,
        'longest_linear_chain_path': longest_path
    }

def write_dot(nodes: Dict[str, Dict], edges: List[Tuple[str,str]], out_path: str):
    lines = ["digraph DFG {","  rankdir=LR;","  splines=true;","  node [style=filled,fontname=Helvetica];"]
    for name, info in nodes.items():
        types = info['types']
        shape = classify_shape(types)
        is_lin = info['is_linear']
        if is_lin is True:
            color = COLOR_LINEAR
            status = 'L'
        elif is_lin is False:
            color = COLOR_NONLINEAR
            status = 'NL'
        else:
            color = COLOR_UNKNOWN
            status = '?'
        reasons = ','.join(info['reasons']) if info['reasons'] else ''
        label = f"{name}\n{status}" + (f"\n{reasons}" if reasons else '')
        esc = label.replace('"','\\"')
        lines.append(f"  \"{name}\" [label=\"{esc}\", shape={shape}, fillcolor=\"{color}\"];")
    for s,d in edges:
        lines.append(f"  \"{s}\" -> \"{d}\";")
    lines.append('}')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path,'w',encoding='utf-8') as f:
        f.write('\n'.join(lines))

def write_html(nodes: Dict[str, Dict], edges: List[Tuple[str,str]], metrics: Dict, out_path: str):
        """生成交互式 HTML 可视化 (纯前端, 无外部依赖)."""
        # 构造节点 / 边数据
        node_list: List[Dict] = []
        index_map: Dict[str,int] = {}
        for idx, (name, info) in enumerate(nodes.items()):
                index_map[name] = idx
                node_list.append({
                        'id': name,
                        'linear': info['is_linear'],
                        'reasons': info['reasons'],
                        'types': info['types']
                })
        link_list: List[Dict] = []
        for s, d in edges:
                if s in index_map and d in index_map:
                        link_list.append({'source': s, 'target': d})

        data_js = json.dumps({'nodes': node_list, 'links': link_list, 'metrics': metrics}, ensure_ascii=False)
        placeholder = '__DATA_PLACEHOLDER__'
        # 使用普通三引号字符串避免 f-string 对 { } 的干扰
        html = """<!DOCTYPE html><html lang='zh-cn'><head><meta charset='UTF-8'/><title>DFG 线性可视化</title>
<style>
body{font-family:Helvetica,Arial,sans-serif;margin:0;display:flex;height:100vh;}
#panel{width:300px;background:#f5f5f5;border-right:1px solid #ccc;padding:12px;overflow:auto;}
#graph{flex:1;position:relative;}
svg{width:100%;height:100%;background:#ffffff;}
.node circle{stroke:#333;stroke-width:1px;cursor:pointer;}
.node text{font-size:10px;pointer-events:none;}
.link{stroke:#999;stroke-opacity:0.6;}
.legend-item{display:flex;align-items:center;margin-bottom:4px;font-size:12px;}
.legend-color{width:14px;height:14px;margin-right:6px;border:1px solid #333;}
#search{width:100%;padding:4px;margin-bottom:8px;}
button{margin-right:6px;margin-bottom:6px;}
</style></head><body>
<div id='panel'>
    <h3 style='margin-top:0'>DFG 线性/非线性</h3>
    <input id='search' placeholder='搜索节点 (回车)' />
    <div>
        <button id='btnAll'>全部</button><button id='btnLin'>线性</button><button id='btnNon'>非线性</button>
    </div>
    <div class='legend-item'><div class='legend-color' style='background:#4CAF50'></div>线性</div>
    <div class='legend-item'><div class='legend-color' style='background:#F44336'></div>非线性</div>
    <div class='legend-item'><div class='legend-color' style='background:#9E9E9E'></div>未知/外部</div>
    <h4>统计</h4>
    <pre id='metrics' style='white-space:pre-wrap;font-size:11px;background:#fff;border:1px solid #ddd;padding:6px;'></pre>
    <p style='font-size:11px;color:#666'>拖拽节点可重新布局。双击节点高亮邻居。</p>
</div>
<div id='graph'><svg id='svg'><g id='links'></g><g id='nodes'></g></svg></div>
<script>
const graphData = __DATA_PLACEHOLDER__;
const COLOR_LINEAR='#4CAF50',COLOR_NON='#F44336',COLOR_UNKNOWN='#9E9E9E';
const width = window.innerWidth - 300, height = window.innerHeight;
const svg = document.getElementById('svg');
const ns='http://www.w3.org/2000/svg';
let nodes = graphData.nodes.map(n=>Object.assign({},n));
let links = graphData.links.map(l=>Object.assign({},l));
const nodeById = new Map(nodes.map(n=>[n.id,n]));
links.forEach(l=>{l.source=nodeById.get(l.source);l.target=nodeById.get(l.target);});
nodes.forEach(n=>{n.x=Math.random()*width; n.y=Math.random()*height; n.vx=0; n.vy=0;});
const linkForce = ()=>{links.forEach(l=>{const dx=l.target.x-l.source.x;const dy=l.target.y-l.source.y;let dist=Math.sqrt(dx*dx+dy*dy)||0.01;const k=0.02*(dist-80);const nx=dx/dist, ny=dy/dist; l.target.vx-=k*nx; l.target.vy-=k*ny; l.source.vx+=k*nx; l.source.vy+=k*ny;});};
const repelForce = ()=>{for(let i=0;i<nodes.length;i++){for(let j=i+1;j<nodes.length;j++){const a=nodes[i],b=nodes[j];let dx=b.x-a.x,dy=b.y-a.y;let d2=dx*dx+dy*dy+0.01; if(d2>40000) continue; const f=3000/d2; const dist=Math.sqrt(d2); const nx=dx/dist, ny=dy/dist; a.vx-=f*nx; a.vy-=f*ny; b.vx+=f*nx; b.vy+=f*ny;}}};
const centerForce=()=>{const cx=width/2, cy=height/2; nodes.forEach(n=>{n.vx+=(cx-n.x)*0.001; n.vy+=(cy-n.y)*0.001;});};
function step(){linkForce(); repelForce(); centerForce(); nodes.forEach(n=>{n.vx*=0.85; n.vy*=0.85; n.x+=n.vx; n.y+=n.vy;}); draw(); requestAnimationFrame(step);} 
const gLinks=document.getElementById('links');
const gNodes=document.getElementById('nodes');
function colorOf(n){ if(n.linear===true) return COLOR_LINEAR; if(n.linear===false) return COLOR_NON; return COLOR_UNKNOWN; }
function draw(){
    gLinks.innerHTML='';
    links.forEach(l=>{const line=document.createElementNS(ns,'line'); line.setAttribute('class','link'); line.setAttribute('x1',l.source.x); line.setAttribute('y1',l.source.y); line.setAttribute('x2',l.target.x); line.setAttribute('y2',l.target.y); line.setAttribute('stroke','#999'); line.setAttribute('stroke-width','1'); gLinks.appendChild(line);});
    gNodes.innerHTML='';
    nodes.forEach(n=>{const g=document.createElementNS(ns,'g'); g.setAttribute('class','node'); g.setAttribute('transform',`translate(${n.x},${n.y})`);
        const c=document.createElementNS(ns,'circle'); c.setAttribute('r',Math.max(6, Math.min(14, (n.reasons&&n.reasons.length?10:8)))); c.setAttribute('fill',colorOf(n)); c.dataset.id=n.id; g.appendChild(c);
        const t=document.createElementNS(ns,'text'); t.setAttribute('text-anchor','middle'); t.setAttribute('dy',20); t.textContent=n.id.split('.').pop(); g.appendChild(t);
        g.addEventListener('mousedown',startDrag); g.addEventListener('dblclick',()=>highlightNeighbors(n.id));
        g.addEventListener('mouseenter',()=>showTooltip(n)); g.addEventListener('mouseleave',hideTooltip);
        gNodes.appendChild(g);});
}
let dragging=null; function startDrag(e){dragging=findNodeFromEvent(e); if(!dragging) return; e.preventDefault();}
svg.addEventListener('mousemove',e=>{if(!dragging) return; const pt=svg.createSVGPoint(); pt.x=e.clientX; pt.y=e.clientY; const svgP=pt.matrixTransform(svg.getScreenCTM().inverse()); dragging.x=svgP.x; dragging.y=svgP.y; dragging.vx=dragging.vy=0; draw();});
svg.addEventListener('mouseup',()=>{dragging=null;}); svg.addEventListener('mouseleave',()=>{dragging=null;});
function findNodeFromEvent(e){const target=e.target; if(target.tagName==='circle'){const id=target.dataset.id; return nodes.find(n=>n.id===id);} return null;}
function highlightNeighbors(id){ const neigh=new Set([id]); links.forEach(l=>{if(l.source.id===id) neigh.add(l.target.id); if(l.target.id===id) neigh.add(l.source.id);});
    gNodes.querySelectorAll('g.node circle').forEach(c=>{ if(neigh.has(c.dataset.id)) c.setAttribute('stroke-width','3'); else c.setAttribute('stroke-width','0.5'); }); }
let tip=document.createElement('div'); tip.style.position='fixed'; tip.style.pointerEvents='none'; tip.style.background='rgba(0,0,0,0.75)'; tip.style.color='#fff'; tip.style.padding='4px 6px'; tip.style.fontSize='11px'; tip.style.borderRadius='4px'; tip.style.display='none'; document.body.appendChild(tip);
function showTooltip(n){ tip.innerHTML=`<b>${n.id}</b><br/>状态:${n.linear===true?'线性':(n.linear===false?'非线性':'?')}<br/>类型:${n.types.join(',')}<br/>原因:${(n.reasons||[]).join(',')||'-'}`; tip.style.display='block'; }
function hideTooltip(){ tip.style.display='none'; }
svg.addEventListener('mousemove',e=>{ if(tip.style.display!=='none'){ tip.style.left=(e.clientX+12)+'px'; tip.style.top=(e.clientY+12)+'px'; }});
function applyFilter(mode){ nodes.forEach(n=>{ n._hidden = (mode==='linear' && n.linear!==true) || (mode==='nonlinear' && n.linear!==false);}); }
function redrawFilter(){ nodes = nodes.filter(()=>true); draw(); gNodes.querySelectorAll('g.node').forEach(g=>{const id=g.querySelector('circle').dataset.id; const n=nodeById.get(id); if(n._hidden) g.style.display='none'; else g.style.display='';}); }
document.getElementById('btnAll').onclick=()=>{nodes.forEach(n=>n._hidden=false); redrawFilter();};
document.getElementById('btnLin').onclick=()=>{applyFilter('linear'); redrawFilter();};
document.getElementById('btnNon').onclick=()=>{applyFilter('nonlinear'); redrawFilter();};
document.getElementById('search').addEventListener('keydown',e=>{ if(e.key==='Enter'){ const q=e.target.value.trim(); gNodes.querySelectorAll('g.node circle').forEach(c=>{c.setAttribute('stroke','#333'); c.setAttribute('stroke-width','1');}); if(q){ const n=nodes.find(n=>n.id.endsWith(q)||n.id===q); if(n){ highlightNeighbors(n.id); } } }});
document.getElementById('metrics').textContent = JSON.stringify(graphData.metrics, null, 2);
draw(); step();
</script></body></html>"""

        out_dir = os.path.dirname(out_path)
        if out_dir:
                os.makedirs(out_dir, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
                f.write(html.replace(placeholder, data_js))

def process_single(dfg_path: str, out_dot: str, json_out: Optional[str], keep: Optional[str], focus: Optional[str], depth: int, html_out: Optional[str], silent=False):
    signals, binds = parse_dfg(dfg_path)
    nodes, edges = build_graph(signals, binds)
    # focus
    if focus:
        nodes, edges = focus_subgraph(nodes, edges, focus, depth)
    # filter
    nodes, edges = filter_nodes(nodes, edges, keep)
    metrics = compute_metrics(nodes, edges)
    write_dot(nodes, edges, out_dot)
    if json_out:
        os.makedirs(os.path.dirname(json_out), exist_ok=True)
        with open(json_out,'w',encoding='utf-8') as jf:
            json.dump({'nodes': nodes, 'edges': edges, 'metrics': metrics}, jf, indent=2, ensure_ascii=False)
    if html_out:
        write_html(nodes, edges, metrics, html_out)
    if not silent:
        print(f'[OK] DOT: {out_dot}')
        if json_out:
            print(f'[OK] JSON: {json_out}')
        if html_out:
            print(f'[OK] HTML: {html_out}')
        print('  Metrics:', json.dumps(metrics, ensure_ascii=False))

def main():
    ap = argparse.ArgumentParser(description='DFG 线性/非线性 Graphviz 可视化 (增强版)')
    ap.add_argument('--dfg', required=True, help='DFG 文件路径 或 目录 (目录则批量处理 .txt)')
    ap.add_argument('--out', required=True, help='输出 DOT 文件路径 (目录批处理时作为输出目录)')
    ap.add_argument('--json-out', help='输出 JSON 文件路径 (目录批处理时忽略此值改为同名 .json)')
    ap.add_argument('--html-out', help='输出交互式 HTML 文件 (目录批处理时为每个文件生成同名 .html)')
    ap.add_argument('--filter', choices=['linear','nonlinear'], help='仅保留线性或非线性节点')
    ap.add_argument('--focus', help='以某个信号为根聚焦子图')
    ap.add_argument('--depth', type=int, default=2, help='聚焦子图的向前深度 (默认2)')
    args = ap.parse_args()

    if os.path.isdir(args.dfg):
        out_dir = args.out if os.path.isdir(args.out) or not os.path.exists(args.out) else args.out
        os.makedirs(out_dir, exist_ok=True)
        for fname in os.listdir(args.dfg):
            if not fname.endswith('.txt'):
                continue
            dfg_path = os.path.join(args.dfg, fname)
            stem = os.path.splitext(fname)[0]
            dot_path = os.path.join(out_dir, f'{stem}.dot')
            json_path = os.path.join(out_dir, f'{stem}.json') if args.json_out else None
            html_path = os.path.join(out_dir, f'{stem}.html') if args.html_out else None
            process_single(dfg_path, dot_path, json_path, args.filter, args.focus, args.depth, html_path, silent=False)
        print('批处理完成')
    else:
        process_single(args.dfg, args.out, args.json_out, args.filter, args.focus, args.depth, args.html_out)
        print(f"可用: dot -Tpng {args.out} -o {args.out.rsplit('.',1)[0]}.png")

if __name__ == '__main__':
    main()
