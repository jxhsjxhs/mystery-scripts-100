#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从《总审核意见书》抽取硬项（23 段背景 + 75 个题材标签）-> review/审核硬项.json

供两处使用：
  1) 派写手时把每题材值精确贴进 prompt；
  2) 补丁回收后由 verify_patches.py 逐项核对「逐字照抄」是否到位。
输出：{"tags": {"T01": "叙诡·双生身份互换", ...}, "backgrounds": {"T09": "城郊...", ...}}
"""
import re, os, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(BASE, 'review', '总审核意见书.md')
OUT = os.path.join(BASE, 'review', '审核硬项.json')


def main():
    text = open(AUDIT, encoding='utf-8').read()

    # ---- 2.2 题材标签：匹配 `T01 | `- 题材：叙诡·双生身份互换` |` ----
    tags = {}
    tag_re = re.compile(r'([A-Z]\d{2})\s*\|\s*`-\s*题材[：:]\s*([^`]+?)`')
    for m in tag_re.finditer(text):
        sid, value = m.group(1), m.group(2).strip().strip('`').strip()
        if value:
            tags[sid] = value

    # ---- 2.1 背景改写：匹配 `**T09　227 字 → 191 字**` + 紧随的一段正文 ----
    backgrounds = {}
    bg_re = re.compile(r'\*\*([A-Z]\d{2})　\d+\s*字\s*→\s*\d+\s*字\*\*\s*\n+([^\n]+)')
    for m in bg_re.finditer(text):
        sid, para = m.group(1), m.group(2).strip()
        if para:
            backgrounds[sid] = para

    data = {'tags': dict(sorted(tags.items())),
            'backgrounds': dict(sorted(backgrounds.items()))}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    # ---- 摘要打印 ----
    by_letter = {}
    for sid in tags:
        by_letter.setdefault(sid[0], []).append(sid)
    print(f'题材标签 {len(tags)} 个：', {k: len(v) for k, v in sorted(by_letter.items())})
    print(f'背景改写 {len(backgrounds)} 段：', ' '.join(sorted(backgrounds)))
    bad = [s for s, v in backgrounds.items() if not (100 <= len(re.sub(r'\s', '', v)) <= 200)]
    print('背景字数越界：', bad or '无')
    print('已写 ->', os.path.relpath(OUT, BASE))
    return data


if __name__ == '__main__':
    main()
