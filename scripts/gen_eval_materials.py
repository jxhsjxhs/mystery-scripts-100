#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给 8 位学生评审备「零剧透评审素材」：从已验证零剧透的 commercial/pack_<vol>.md
投影出每本的 编号/剧名/题材/人数/时长/难度/一句话卖点/盒背文案(公开)/角色预告。
输出 eval/mat_<vol>.md（4 份，各 25 本，紧凑）。不含任何真相/反转/结局/隐藏秘密。
用法：python3 scripts/gen_eval_materials.py
"""
import re, os, glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'eval')
os.makedirs(OUT, exist_ok=True)

VOL = [('horror', 'H', '恐怖本'), ('twist', 'T', '反转本'),
       ('comedy', 'C', '搞笑本'), ('office', 'O', '职场厮杀本')]


def sec(blk, nm):
    m = re.search(r'###\s*%s[^\n]*\n(.*?)(?=\n###|\Z)' % nm, blk, re.S)
    return m.group(1).strip() if m else ''


def produce(vol, pre, label):
    path = glob.glob(os.path.join(BASE, 'commercial', 'pack_%s.md' % vol))[0]
    text = open(path, encoding='utf-8').read()
    lines = [
        '# %s · 零剧透评审素材（%s01–%s25）\n' % (label, pre, pre),
        '> 仅供学生评审 agent 使用。本表已剔除真相/反转/结局/隐藏秘密。',
        '> 严禁打开终稿全文或主持人手册。评语要印在盒面上，读完只想买、猜不出答案。\n',
    ]
    n = 0
    for blk in re.split(r'(?=^## \[%s\d{2}\])' % pre, text, flags=re.M):
        m = re.match(r'^## \[(%s\d{2})\] 《(.+?)》' % pre, blk.strip())
        if not m:
            continue
        sid, name = m.group(1), m.group(2)
        sell = re.search(r'-\s*一句话卖点[：:]\s*(.+?)\s*$', blk, re.M)
        cat = re.search(r'-\s*上架分类[：:]\s*(.+?)\s*$', blk, re.M)
        back = sec(blk, '盒背文案')
        # 盒背文案可能多行，压成一段
        back = re.sub(r'\s*\n\s*', '', back).strip()
        roles = [ln.strip() for ln in sec(blk, '角色预告').splitlines()
                 if re.match(r'^\s*-\s+', ln)]
        n += 1
        lines.append('## [%s] 《%s》' % (sid, name))
        lines.append('- 一句话卖点：%s' % (sell.group(1).strip() if sell else ''))
        lines.append('- 上架分类：%s' % (cat.group(1).strip() if cat else ''))
        lines.append('- 公开背景：%s' % back)
        for r in roles:
            lines.append('  %s' % r)
        lines.append('')
    out = os.path.join(OUT, 'mat_%s.md' % vol)
    open(out, 'w', encoding='utf-8').write('\n'.join(lines))
    print('%s -> %s（%d 本）' % (vol, os.path.relpath(out, BASE), n))
    return n


def main():
    total = 0
    for vol, pre, label in VOL:
        total += produce(vol, pre, label)
    print('合计：%d 本评审素材。' % total)


if __name__ == '__main__':
    main()
