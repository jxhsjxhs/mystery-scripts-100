#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给 8 个 agent 备「零剧透素材」：从终稿里只投影出允许写手看的信息，
刻意不含 隐藏秘密 / 核心诡计 / 反转 / 真相 / 结局。
用法：python3 scripts/gen_materials.py   （用带 Pillow 的解释器或任意 python3 均可，本脚本不依赖 PIL）
"""
import re, os, glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'commercial', 'guidance')
os.makedirs(OUT, exist_ok=True)

VOL = [('horror', 'H', '恐怖本'), ('twist', 'T', '反转本'),
       ('comedy', 'C', '搞笑本'), ('office', 'O', '职场厮杀本')]


def sec(p, nm):
    m = re.search(r'###\s*%s[^\n]*\n(.*?)(?=\n###|\Z)' % nm, p, re.S)
    return m.group(1).strip() if m else ''


def clean_public_role(line):
    """角色行 -> 只保留 名字 + 公开身份 + 表面立场，切掉隐藏秘密/个人目标。"""
    m = re.match(r'^(.*?)[。；]\s*表面立场[：:]\s*(.*?)[。；]', line, re.S)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return line.split('。')[0].strip(), ''


def produce(vol, pre):
    path = glob.glob(os.path.join(BASE, vol, '*.md'))[0]
    text = open(path, encoding='utf-8').read()
    lines = ['# %s · 零剧透素材表（编号 01–25）\n' % vol,
             '> 仅供「写手 agent」使用：本表**已刻意删除**隐藏秘密 / 核心诡计 / 反转 / 真相 / 结局。',
             '> 写手**不要打开 %s/*.md 终稿全文**（含真相，读了极易写漏）。素材表里没有的信息，就不要写。\n' % vol]
    for p in re.split(r'(?=^## \[%s\d{2}\] )' % pre, text, flags=re.M):
        m = re.match(r'^## \[(%s\d{2})\] 《(.+?)》' % pre, p.strip())
        if not m:
            continue
        sid, name = m.group(1), m.group(2)
        def fld(f):
            mm = re.search(r'-\s*%s[：:]\s*(.+?)\s*$' % f, p, re.M)
            return mm.group(1) if mm else ''
        bg = sec(p, '背景')
        roles = re.findall(r'-\s*\*\*(.+?)\*\*[：:]([^\n]*)', sec(p, '角色'))
        pub = [clean_public_role(body.strip()) for _, body in roles]
        lines.append('\n## [%s] 《%s》' % (sid, name))
        lines.append('- 题材：%s ｜ 人数：%s ｜ 时长：%s ｜ 难度：%s' % (
            fld('题材'), fld('人数'), fld('时长'), fld('难度')))
        lines.append('- 公开背景：%s' % bg)
        lines.append('- 角色（名字→公开身份 / 表面主张，仅此而已）：')
        for nm, body in zip([r[0] for r in roles], pub):
            ident, stance = body
            lines.append('  - %s：%s｜%s' % (nm.strip(), ident, stance))
    return '\n'.join(lines) + '\n'


def main():
    for vol, pre, _ in VOL:
        txt = produce(vol, pre)
        path = os.path.join(OUT, '素材_%s.md' % vol)
        open(path, 'w', encoding='utf-8').write(txt)
        n = len(re.findall(r'^## \[', txt, re.M))
        print('%s -> %s （%d 套）' % (vol, path, n))


if __name__ == '__main__':
    main()
