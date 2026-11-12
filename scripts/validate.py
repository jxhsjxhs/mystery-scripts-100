#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 4 卷剧本：套数、人数(2-4)、角色数==人数、字段完整、角色名唯一、编号连续。"""
import re, sys, glob, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOLUMES = {
    'horror': ('H', '恐怖本'),
    'twist':  ('T', '反转本'),
    'comedy': ('C', '搞笑本'),
    'office': ('O', '职场厮杀本'),
}
FIELDS = ['题材', '人数', '时长', '难度', '背景', '角色', '核心诡计',
          '关键线索', '流程', '反转点', '真相', '结局', '主持人']

def parse_file(path):
    text = open(path, encoding='utf-8').read()
    # split by "## [XX] 《名》"
    parts = re.split(r'(?=^## \[[A-Z]\d{2}\] )', text, flags=re.M)
    scripts = []
    for p in parts:
        m = re.match(r'^## \[([A-Z]\d{2})\] 《(.+?)》', p.strip())
        if m:
            scripts.append((m.group(1), m.group(2), p))
    return scripts

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'final'
    all_names = {}
    total = 0
    problems = []
    summary = []
    for vol, (prefix, label) in VOLUMES.items():
        if mode == 'draft':
            paths = glob.glob(os.path.join(BASE, 'drafts', f'{vol}_draft.md'))
        else:
            paths = glob.glob(os.path.join(BASE, vol, '*.md'))
        if not paths:
            problems.append(f'[{vol}] 找不到文件 (mode={mode})')
            continue
        path = paths[0]
        scripts = parse_file(path)
        cnt = len(scripts)
        total += cnt
        counts = {2:0,3:0,4:0}
        ids = []
        for sid, name, body in scripts:
            ids.append(sid)
            # 人数
            mn = re.search(r'-\s*人数[：:]\s*(\d+)\s*人', body)
            if not mn:
                problems.append(f'[{sid}] 缺「人数」字段或格式不对')
                continue
            n = int(mn.group(1))
            if n not in (2,3,4):
                problems.append(f'[{sid}] 人数={n} 超出 2-4')
            else:
                counts[n]+=1
            # 角色段（### 角色 到下一个 ### 之间）
            rm = re.search(r'###\s*角色\s*\n(.*?)(?=\n###|\Z)', body, flags=re.S)
            if not rm:
                problems.append(f'[{sid}] 缺「角色」段')
                continue
            role_block = rm.group(1)
            roles = re.findall(r'-\s*\*\*(.+?)\*\*[：:]', role_block)
            if len(roles) != n:
                problems.append(f'[{sid}] 角色数={len(roles)} 与人数={n} 不符: {roles}')
            # 角色名唯一
            for r in roles:
                r = r.strip()
                if r in all_names:
                    problems.append(f'[{sid}] 角色名「{r}」与 {all_names[r]} 重名')
                else:
                    all_names[r] = sid
            # 字段完整
            for f in FIELDS:
                if f not in body:
                    problems.append(f'[{sid}] 缺字段/标题「{f}」')
            # 关键线索至少3条
            cm = re.search(r'###\s*关键线索.*?\n(.*?)(?=\n###|\Z)', body, flags=re.S)
            if cm:
                clues = re.findall(r'^\s*\d+\.', cm.group(1), flags=re.M)
                if len(clues) < 3:
                    problems.append(f'[{sid}] 关键线索只有 {len(clues)} 条 (<3)')
        # 编号连续
        expected = [f'{prefix}{i:02d}' for i in range(1,26)]
        if ids != expected:
            missing = set(expected)-set(ids)
            extra = set(ids)-set(expected)
            dup = [x for x in set(ids) if ids.count(x)>1]
            problems.append(f'[{vol}] 编号异常 应有25套实得{cnt} 缺{sorted(missing)} 多{sorted(extra)} 重复{dup}')
        summary.append(f'{label}({vol}): {cnt}套 | 2人={counts[2]} 3人={counts[3]} 4人={counts[4]} | 文件 {os.path.basename(path)}')
    print('=== 校验汇总 ===')
    for s in summary: print(' -', s)
    print(f'总计: {total} 套')
    if problems:
        print(f'\n=== 发现 {len(problems)} 个问题 ===')
        for p in problems[:200]:
            print('  !', p)
        sys.exit(1)
    else:
        print('\n✅ 全部通过：100 套、人数 2-4、角色数匹配、字段完整、线索≥3、角色名全局唯一、编号连续。')
        sys.exit(0)

if __name__ == '__main__':
    main()
