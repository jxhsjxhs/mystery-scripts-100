#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并初稿：优先 <vol>_draft.md（已是整卷）；否则按 p1/p2/p3 批次拼接。
输出 drafts/<vol>_draft.md（整卷），不改动其它目录。"""
import re, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFTS = os.path.join(BASE, 'drafts')

VOL = {
    'horror':  ('H', '恐怖本 · 25 套（写手：夜枭 / 初稿）'),
    'twist':   ('T', '反转本 · 25 套（写手：叙诡生 / 初稿）'),
    'comedy':  ('C', '搞笑本 · 25 套（写手：哈哈镜 / 初稿）'),
    'office':  ('O', '职场厮杀本 · 25 套（写手：工位修罗 / 初稿）'),
}

def split_blocks(text, letter):
    parts = re.split(r'(?=^## \[' + letter + r'\d{2}\] )', text, flags=re.M)
    out = {}
    for p in parts:
        m = re.match(r'^## \[' + letter + r'(\d{2})\] 《', p.strip())
        if m:
            out[letter + m.group(1)] = p.rstrip() + '\n'
    return out

def collect(vol):
    letter, header = VOL[vol]
    whole = os.path.join(DRAFTS, f'{vol}_draft.md')
    blocks = {}
    if os.path.exists(whole):
        blocks.update(split_blocks(open(whole, encoding='utf-8').read(), letter))
    for b in ('p1','p2','p3'):
        f = os.path.join(DRAFTS, f'{vol}_{b}.md')
        if os.path.exists(f):
            blocks.update(split_blocks(open(f, encoding='utf-8').read(), letter))
    return letter, header, blocks

def main(vols):
    for vol in vols:
        letter, header, blocks = collect(vol)
        ids = [f'{letter}{i:02d}' for i in range(1, 26)]
        missing = [i for i in ids if i not in blocks]
        if missing:
            print(f'[{vol}] 未完成，缺 {len(missing)} 套: {", ".join(missing)}')
            print(f'  已有: {", ".join(sorted(blocks))}')
            continue
        body = '# ' + header + '\n\n' + '\n'.join(blocks[i] for i in ids)
        out = os.path.join(DRAFTS, f'{vol}_draft.md')
        open(out, 'w', encoding='utf-8').write(body)
        print(f'[{vol}] 合并完成 -> {out}  ({len(blocks)} 套 / {len(body)} 字符)')

if __name__ == '__main__':
    main(sys.argv[1:] if len(sys.argv) > 1 else list(VOL))
