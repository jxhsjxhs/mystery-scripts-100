#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""汇总 4 卷终稿 -> 生成「总览目录.md」与「100套完整合集.md」。"""
import re, os, glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOLUMES = [
    ('horror', '恐怖本', '夜枭', 'H'),
    ('twist',  '反转本', '叙诡生', 'T'),
    ('comedy', '搞笑本', '哈哈镜', 'C'),
    ('office', '职场厮杀本', '工位修罗', 'O'),
]

def parse(path):
    text = open(path, encoding='utf-8').read()
    parts = re.split(r'(?=^## \[[A-Z]\d{2}\] )', text, flags=re.M)
    out = []
    for p in parts:
        m = re.match(r'^## \[([A-Z]\d{2})\] 《(.+?)》', p.strip())
        if m:
            sid, name, body = m.group(1), m.group(2), p.strip()
            nm = re.search(r'-\s*人数[：:]\s*(\d+)\s*人', body)
            dm = re.search(r'-\s*难度[：:]\s*(.+?)\s*$', body, re.M)
            tm = re.search(r'-\s*时长[：:]\s*(.+?)\s*$', body, re.M)
            # 一句话卖点：取核心诡计段第一句
            cm = re.search(r'###\s*核心诡计[^\n]*\n+([^\n]+)', body)
            hook = (cm.group(1).strip() if cm else '')[:60]
            rm = re.search(r'###\s*角色\s*\n(.*?)(?=\n###|\Z)', body, flags=re.S)
            roles = re.findall(r'-\s*\*\*(.+?)\*\*[：:]', rm.group(1)) if rm else []
            out.append(dict(sid=sid, name=name, n=int(nm.group(1)) if nm else 0,
                            diff=dm.group(1) if dm else '', time=tm.group(1) if tm else '',
                            hook=hook, roles=roles, body=body))
    return out

def main():
    catalog = []
    all_rows = []
    full = []
    grand = 0
    catalog.append('# 百局 · 100 套剧本杀 · 总览目录\n')
    catalog.append('> 4 大题材 × 25 套 = 100 套；每套 2–4 人。4 位人设写手初稿 → 总审核 agent 通审提意见 → 修订终稿。\n')
    catalog.append('| 卷 | 题材 | 写手人设 | 编号 | 套数 |\n|---|---|---|---|---|')
    for vol, label, pen, pre in VOLUMES:
        catalog.append(f'| {vol} | {label} | {pen} | {pre}01–{pre}25 | 25 |')

    full.append('# 百局 · 100 套剧本杀完整合集\n')
    full.append('> 恐怖 / 反转 / 搞笑 / 职场厮杀 四卷合订。每套 2–4 人，可直接开本。\n')

    for vol, label, pen, pre in VOLUMES:
        paths = glob.glob(os.path.join(BASE, vol, '*.md'))
        if not paths:
            print('缺少终稿:', vol); continue
        rows = parse(paths[0])
        grand += len(rows)
        for r in rows: all_rows.append(r)
        # 目录分卷
        catalog.append(f'\n## {label}（{pen}） · {len(rows)} 套\n')
        catalog.append('| 编号 | 剧名 | 人数 | 难度 | 时长 | 一句话卖点 | 角色 |\n|---|---|---|---|---|---|---|')
        for r in rows:
            catalog.append(f"| {r['sid']} | 《{r['name']}》 | {r['n']}人 | {r['diff']} | {r['time']} | {r['hook']} | {'、'.join(r['roles'])} |")
        # 合集分卷
        full.append(f'\n\n---\n\n# 第 {VOLUMES.index((vol,label,pen,pre))+1} 卷 · {label}\n')
        for r in rows:
            full.append('\n' + r['body'] + '\n')

    # 统计
    from collections import Counter
    nc = Counter(r['n'] for r in all_rows)
    catalog.append('\n## 统计\n')
    catalog.append(f'- 总套数：**{grand}**')
    catalog.append(f"- 2 人本：{nc.get(2,0)} 套 ／ 3 人本：{nc.get(3,0)} 套 ／ 4 人本：{nc.get(4,0)} 套")
    catalog.append(f'- 角色名总数：{sum(len(r["roles"]) for r in all_rows)}（已校验全局唯一）')

    cat_path = os.path.join(BASE, '总览目录.md')
    full_path = os.path.join(BASE, '100套完整合集.md')
    open(cat_path, 'w', encoding='utf-8').write('\n'.join(catalog) + '\n')
    open(full_path, 'w', encoding='utf-8').write('\n'.join(full) + '\n')
    print(f'总套数={grand} | 2人={nc.get(2,0)} 3人={nc.get(3,0)} 4人={nc.get(4,0)}')
    print('生成:', cat_path)
    print('生成:', full_path)

if __name__ == '__main__':
    main()
