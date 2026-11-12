#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 review/审核硬项.json 生成 4 卷「机校锁定」的基础补丁（题材 + 背景 逐字照抄）。

写到 drafts/patches/<vol>.patch.md（captain 产出的机校锁定硬项）。
4 位写手另写独立的 drafts/patches/<vol>.soft.md 承载「第三节编辑软项」，由
apply_patches.py 先套基础补丁、再套软项补丁（本脚本不碰 soft 文件）。
可重复运行（幂等）。horror 卷零改动 -> 只写标题行，保证 apply_patches.py 不跳过该卷。
"""
import os, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARD = os.path.join(BASE, 'review', '审核硬项.json')
PDIR = os.path.join(BASE, 'drafts', 'patches')

VOL = [
    ('horror', 'H', '恐怖本', '夜枭'),
    ('twist',  'T', '反转本', '叙诡生'),
    ('comedy', 'C', '搞笑本', '哈哈镜'),
    ('office', 'O', '职场厮杀本', '工位修罗'),
]


def main():
    data = json.load(open(HARD, encoding='utf-8'))
    tags, bgs = data['tags'], data['backgrounds']
    os.makedirs(PDIR, exist_ok=True)
    for vol, pre, cn, writer in VOL:
        lines = [f'# {cn} 修订补丁（写手：{writer}）',
                 f'# 下方题材/背景为机校锁定硬项，逐字照抄《总审核意见书》2.1/2.2，请勿改动；写手只在文件末尾追加第三节编辑软项。',
                 '']
        # 题材块
        tcount = 0
        for i in range(1, 26):
            sid = f'{pre}{i:02d}'
            if sid in tags:
                lines += [f'## [{sid}] 题材', tags[sid], '']
                tcount += 1
        # 背景块
        bcount = 0
        for sid in sorted(bgs):
            if sid.startswith(pre):
                lines += [f'## [{sid}] 背景', bgs[sid], '']
                bcount += 1
        path = os.path.join(PDIR, vol + '.patch.md')
        open(path, 'w', encoding='utf-8').write('\n'.join(lines).rstrip() + '\n')
        print(f'{vol}: 题材 {tcount} 块 / 背景 {bcount} 块 -> {os.path.relpath(path, BASE)}')
    print('基础补丁生成完毕。')


if __name__ == '__main__':
    main()
