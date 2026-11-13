#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 6 组导师回归定稿（upgrade/approved/w*.md）合并进四卷终稿。
- 每块包成 `### 讨论升级 / 高光辩论` 段，幂等追加到对应套的末尾（在 DM Notes 之后）。
- 另外生成 `upgrade/讨论升级汇总.md`（sid → 升级正文），供 gen_eval_materials.py
  把本轮升级内容带进 8 学生重新评审的素材表。
- 11 本评分 ≥85 的高分本不改动。
用法：python3 scripts/apply_upgrade.py
"""
import re, os, glob, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(BASE, 'upgrade')
VOL = [('horror', 'H'), ('twist', 'T'), ('comedy', 'C'), ('office', 'O')]
SECTION_HEAD = '### 讨论升级 / 高光辩论'
GROUPS = ['w1', 'w2', 'w3', 'w4', 'w5', 'w6']


def load_approved():
    """返回 sid -> {name, body}；body 为去掉 `## [SID] 《名》` 首行后的五个标签正文。"""
    out = {}
    for g in GROUPS:
        p = os.path.join(UP, 'approved', g + '.md')
        if not os.path.exists(p):
            raise SystemExit('缺导师回归定稿：%s' % os.path.relpath(p, BASE))
        txt = open(p, encoding='utf-8').read()
        for blk in re.split(r'(?=^## \[[A-Z]\d{2}\])', txt, flags=re.M):
            m = re.match(r'^## \[([A-Z]\d{2})\] 《(.+?)》\s*\n(.*)', blk.strip(), re.S)
            if not m:
                continue
            sid, name, body = m.group(1), m.group(2), m.group(3).strip()
            # 剥掉可能残留的文件头注释行
            body = re.sub(r'^#\s*第.*?组[^\n]*\n', '', body).strip()
            if sid in out:
                raise SystemExit('重复编号：%s 出现在多份回归定稿里' % sid)
            out[sid] = dict(name=name, body=body)
    return out


def write_summary(approved):
    """生成 upgrade/讨论升级汇总.md：每本 `## [SID] 《名》` + 升级正文。"""
    lines = [
        '# 百局 · 讨论升级汇总（低分升级本）\n',
        '> 由 `scripts/apply_upgrade.py` 从 6 份导师回归定稿生成，供 `gen_eval_materials.py` 并入评审素材。',
        '> 内容按《升级规范.md》零新增 / 零剧透 / 全中文，只有评分低于 85 的 89 本在此。\n',
    ]
    for sid in sorted(approved):
        a = approved[sid]
        lines.append('## [%s] 《%s》' % (sid, a['name']))
        lines.append(a['body'])
        lines.append('')
    p = os.path.join(UP, '讨论升级汇总.md')
    open(p, 'w', encoding='utf-8').write('\n'.join(lines))
    return len(approved)


def apply_volume(vol, pre, approved):
    paths = glob.glob(os.path.join(BASE, vol, '*.md'))
    if not paths:
        raise SystemExit('缺终稿卷：%s' % vol)
    path = paths[0]
    text = open(path, encoding='utf-8').read()
    heads = list(re.finditer(r'^## \[(%s\d{2})\] ' % pre, text, flags=re.M))
    changed, skipped = 0, 0
    # 从后往前改，保持位置稳定
    for i in range(len(heads) - 1, -1, -1):
        m = heads[i]
        sid = m.group(1)
        start = m.start()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        block = text[start:end]
        if sid not in approved:
            skipped += 1
            continue
        # 幂等：先剥掉旧的升级段（它是本块最后一节）
        block = re.sub(r'\n*###\s*讨论升级[^\n]*\n.*', '', block, flags=re.S).rstrip()
        body = approved[sid]['body']
        block = block + '\n\n' + SECTION_HEAD + '\n\n' + body + '\n'
        text = text[:start] + block + text[end:]
        changed += 1
    open(path, 'w', encoding='utf-8').write(text)
    return changed, skipped, os.path.relpath(path, BASE)


def main():
    approved = load_approved()
    n = write_summary(approved)
    print('讨论升级汇总：%d 本 -> %s' % (n, 'upgrade/讨论升级汇总.md'))
    total_c = total_s = 0
    for vol, pre in VOL:
        c, s, rel = apply_volume(vol, pre, approved)
        total_c += c
        total_s += s
        print('  %-8s -> %-28s 升级 %2d 本 / 保持原样 %2d 本' % (vol, rel, c, s))
    print('合计：升级 %d 本、原样 %d 本，共 %d 本。' % (total_c, total_s, total_c + total_s))


if __name__ == '__main__':
    main()
