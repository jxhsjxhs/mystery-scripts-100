#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给 8 位学生评审备「零剧透评审素材」：从已验证零剧透的 commercial/pack_<vol>.md
投影出每本的 编号/剧名/题材/人数/时长/难度/一句话卖点/盒背文案(公开)/角色预告；
若 upgrade/讨论升级汇总.md 存在，则把本轮「讨论升级 / 高光辩论」正文一并并入
（该正文按升级契约零剧透、全中文，安全）。
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


def load_upgrades():
    """读 upgrade/讨论升级汇总.md，返回 {sid: 正文}；文件不存在则返回空字典。"""
    p = os.path.join(BASE, 'upgrade', '讨论升级汇总.md')
    if not os.path.exists(p):
        return {}
    txt = open(p, encoding='utf-8').read()
    out = {}
    for blk in re.split(r'(?=^## \[[A-Z]\d{2}\])', txt, flags=re.M):
        m = re.match(r'^## \[([A-Z]\d{2})\][^\n]*\n(.*)', blk.strip(), re.S)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def produce(vol, pre, label, upgrades):
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
        up = upgrades.get(sid, '')
        if up:
            # 只取「讨论焦点」一句作升级信号：让学生知道本轮加了什么辩论高光即可，
            # 不把整块升级正文灌进素材（避免评审表过大导致一次性读入零输出）。
            fm = re.search(r'\*\*讨论焦点\*\*[：:]\s*(.+)', up)
            brief = fm.group(1).strip() if fm else re.sub(r'\s*\n\s*', ' ', up)[:80]
            brief = re.sub(r'\s+', '', brief)
            lines.append('- 讨论升级：%s' % brief)
        lines.append('')
    out = os.path.join(OUT, 'mat_%s.md' % vol)
    open(out, 'w', encoding='utf-8').write('\n'.join(lines))
    print('%s -> %s（%d 本）' % (vol, os.path.relpath(out, BASE), n))
    return n


def main():
    total = 0
    upgrades = load_upgrades()
    print('讨论升级汇总：%d 本' % len(upgrades))
    for vol, pre, label in VOL:
        total += produce(vol, pre, label, upgrades)
    print('合计：%d 本评审素材。' % total)


if __name__ == '__main__':
    main()
