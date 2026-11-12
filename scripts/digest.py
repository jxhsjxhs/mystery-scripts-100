#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为总审核 agent 准备输入：
1) review/初稿概览.md —— 全部 100 套的结构化概览（每套核心诡计/反转/真相首句+角色+线索数+背景字数）
2) review/初稿机器诊断.md —— 全量硬指标诊断（编号/人数/字段/线索/背景/角色唯一/题材互异/托底词待核）

整卷优先读 drafts/<vol>_draft.md；若该卷未合并完，自动拼接 p1/p2/p3 批次。
幂等：重跑覆盖输出。"""
import re, os, sys, glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFTS = os.path.join(BASE, 'drafts')
REVIEW = os.path.join(BASE, 'review')
os.makedirs(REVIEW, exist_ok=True)

VOL = {
    'horror': ('H', '恐怖本', '夜枭'),
    'twist':  ('T', '反转本', '叙诡生'),
    'comedy': ('C', '搞笑本', '哈哈镜'),
    'office': ('O', '职场厮杀本', '工位修罗'),
}
FIELDS = ['题材','人数','时长','难度','背景','角色','核心诡计','关键线索','流程','反转点','真相','结局','主持人']

def split_blocks(text, letter):
    parts = re.split(r'(?=^## \[' + letter + r'\d{2}\] )', text, flags=re.M)
    out = {}
    for p in parts:
        m = re.match(r'^## \[' + letter + r'(\d{2})\] 《', p.strip())
        if m:
            out[letter + m.group(1)] = p.rstrip()
    return out

def load(vol, mode='draft'):
    letter = VOL[vol][0]
    blocks = {}
    if mode == 'final':
        # 终稿模式：读各卷目录下的终稿 .md（combine.py 同源）
        for f in sorted(glob.glob(os.path.join(BASE, vol, '*.md'))):
            blocks.update(split_blocks(open(f, encoding='utf-8').read(), letter))
        return blocks
    whole = os.path.join(DRAFTS, f'{vol}_draft.md')
    if os.path.exists(whole):
        blocks.update(split_blocks(open(whole, encoding='utf-8').read(), letter))
    for b in ('p1','p2','p3'):
        f = os.path.join(DRAFTS, f'{vol}_{b}.md')
        if os.path.exists(f):
            blocks.update(split_blocks(open(f, encoding='utf-8').read(), letter))
    return blocks

def first_sentence(s):
    s = s.strip().replace('\n', ' ')
    m = re.split(r'[。！？!?]', s)
    return (m[0].strip() + '。') if m and m[0].strip() else s[:60]

def section(text, name):
    m = re.search(r'###\s*' + name + r'[^\n]*\n(.*?)(?=\n###|\Z)', text, flags=re.S)
    return m.group(1).strip() if m else ''

def field(text, name):
    m = re.search(r'-\s*' + name + r'[：:]\s*(.+)', text)
    return m.group(1).strip() if m else ''

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ('draft', 'final') else 'draft'
    label = '终稿' if mode == 'final' else '初稿'
    allblocks = {}
    for vol in VOL:
        allblocks[vol] = load(vol, mode)

    # ---------- 概览 ----------
    ov = [f'# 剧本杀 100 套 · {label}结构化概览（供总审核通读）', '',
          f'> 由 scripts/digest.py 从四卷{label}自动提取。每套给出：编号/剧名/人数/难度/题材、',
          '> 核心诡计首句、反转点首句、真相首句、角色名清单、线索条数、背景字数。',
          '> 审核意见请按「卷 + 具体编号」给出可执行的修改指令。', '']
    for vol, (letter, cn, writer) in VOL.items():
        blocks = allblocks[vol]
        ov.append(f'## {cn} {letter}01–{letter}25（写手：{writer}）　已落地 {len(blocks)} 套')
        ov.append('')
        for i in range(1, 26):
            sid = f'{letter}{i:02d}'
            if sid not in blocks:
                ov.append(f'- **[{sid}] 尚未落地**')
                continue
            p = blocks[sid]
            title = re.match(r'^## \[' + letter + r'\d{2}\] 《(.+?)》', p.strip())
            title = title.group(1) if title else '?'
            n = field(p, '人数') or '?'
            diff = field(p, '难度') or '?'
            theme = field(p, '题材') or '?'
            mech = first_sentence(section(p, '核心诡计'))
            twist = first_sentence(section(p, '反转点'))
            truth = first_sentence(section(p, '真相'))
            rm = section(p, '角色')
            roles = [r.strip() for r in re.findall(r'-\s*\*\*(.+?)\*\*[：:]', rm)]
            clue = section(p, '关键线索')
            nclue = len(re.findall(r'^\s*\d+\.', clue, flags=re.M))
            bg = re.sub(r'\s', '', section(p, '背景'))
            ov.append(f'### [{sid}] 《{title}》｜{n}｜{diff}｜{theme}')
            ov.append(f'- 卖点/机制：{mech}')
            ov.append(f'- 反转/高潮：{twist}')
            ov.append(f'- 真相/结局：{truth}')
            ov.append(f'- 角色：{"、".join(roles) if roles else "（解析不到）"}')
            ov.append(f'- 线索 {nclue} 条｜背景 {len(bg)} 字')
            ov.append('')
    ov_name = '终稿概览.md' if mode == 'final' else '初稿概览.md'
    open(os.path.join(REVIEW, ov_name), 'w', encoding='utf-8').write('\n'.join(ov))

    # ---------- 机器诊断 ----------
    dg = [f'# {label}机器诊断（scripts/digest.py 自动生成）', '',
          '> 客观硬指标。命中项请总审核 agent 结合概览人工复核。', '']
    total = 0
    global_names = {}
    dup_names = []
    problems = []
    dist_all = {2:0, 3:0, 4:0}
    trope_hits = []
    for vol, (letter, cn, writer) in VOL.items():
        blocks = allblocks[vol]
        ids = [f'{letter}{i:02d}' for i in range(1, 26)]
        have = [i for i in ids if i in blocks]
        total += len(have)
        dist = {2:0,3:0,4:0}
        themes = set()
        for sid in have:
            p = blocks[sid]
            mn = re.search(r'(\d+)\s*人', field(p, '人数'))
            n = int(mn.group(1)) if mn else 0
            if n in dist: dist[n] += 1; dist_all[n] += 1
            themes.add(field(p, '题材'))
            # 字段
            for f in FIELDS:
                if f not in p: problems.append(f'[{sid}] 缺字段 {f}')
            # 角色
            rm = section(p, '角色')
            roles = [r.strip() for r in re.findall(r'-\s*\*\*(.+?)\*\*[：:]', rm)]
            if len(roles) != n: problems.append(f'[{sid}] 人数{n} 但角色行{len(roles)}（全角冒号?）')
            for r in roles:
                if r in global_names: dup_names.append(f'{r}（{global_names[r]} 与 {sid}）')
                global_names[r] = sid
            for r in roles:
                line = next((l for l in rm.split('\n') if l.strip().startswith('- **'+r)), '')
                for kw in ('表面立场','隐藏秘密','个人目标'):
                    if kw not in line: problems.append(f'[{sid}] 角色「{r}」缺 {kw}')
            # 线索
            clue = section(p, '关键线索')
            nc = len(re.findall(r'^\s*\d+\.', clue, flags=re.M))
            if nc < 3: problems.append(f'[{sid}] 关键线索仅 {nc} 条（<3）')
            # 背景
            bg = re.sub(r'\s','',section(p,'背景'))
            if not (100 <= len(bg) <= 200): problems.append(f'[{sid}] 背景 {len(bg)} 字（规范 100–200）')
            # 三幕
            fl = section(p, '流程')
            for act in ('第一幕','第二幕','第三幕'):
                if act not in fl: problems.append(f'[{sid}] 流程缺 {act}')
            # 托底词待核（仅标真相段，供人工判断「一刀切」）
            tr = section(p, '真相')
            for kw in ('做梦','其实是梦','失忆','外星人','一切都是幻觉'):
                if kw in tr: trope_hits.append(f'[{sid}] 真相段含「{kw}」——请确认非一刀切托底')
        dg.append(f'## {cn}（{letter}）')
        dg.append(f'- 已落地 {len(have)}/25 套' + (f'，缺：{", ".join(i for i in ids if i not in blocks)}' if len(have)<25 else '，编号连续 ✓'))
        dg.append(f'- 人数分布：2人={dist[2]} / 3人={dist[3]} / 4人={dist[4]}（规范 2≥6、3≥8、4≥6）')
        dg.append(f'- 题材互异：{len(themes)} 种')
        dg.append('')
    dg.append('## 全局')
    dg.append(f'- 四卷合计已落地 **{total}/100** 套')
    dg.append(f'- 全局人数分布：2人={dist_all[2]} / 3人={dist_all[3]} / 4人={dist_all[4]}')
    dg.append(f'- 全局角色名 {len(global_names)} 个，跨卷重名 {len(dup_names)} 处')
    for d in dup_names[:30]: dg.append(f'  - 重名：{d}')
    dg.append(f'- 硬字段/线索/背景/三幕 违规项：{len(problems)}')
    for x in problems[:60]: dg.append(f'  - {x}')
    dg.append(f'- 真相段「托底词」待人工复核：{len(trope_hits)} 处')
    for x in trope_hits[:30]: dg.append(f'  - {x}')
    dg.append('')
    dg_name = '终稿机器诊断.md' if mode == 'final' else '初稿机器诊断.md'
    open(os.path.join(REVIEW, dg_name), 'w', encoding='utf-8').write('\n'.join(dg))
    print(f'概览 -> review/{ov_name}（{total} 套）')
    print(f'诊断 -> review/{dg_name}（落地 {total}/100，硬违规 {len(problems)}，重名 {len(dup_names)}，托底词待核 {len(trope_hits)}）')

if __name__ == '__main__':
    main()
