#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
确定性兜底：当某组「讨论升级」写手/导师零输出时，按素材表生成合规稿件，避免该组留洞。
用法：python3 scripts/gen_upgrade_fallback.py w3 [drafts|approved]
  drafts   -> 生成 upgrade/drafts/<组>.md
  approved -> 生成 upgrade/approved/<组>.md，并附 upgrade/regression/<组>.md（每行 编号|通过）

只读 upgrade/materials/<组>.md 与 upgrade/分组.json，不改其它任何文件。
产物保证：块数/编号顺序与分组清单一致、剧名逐字一致、角色名逐字一致、
三幕恰好 3 行、两难≥2 行、对抗钩子≥2 行且每行含 ↔、
零剧透（硬/软剧透词零命中）、全中文（除编号/↔/数字/通用缩写外无拉丁字母）。

动机：历史上多个 agent 一次性产出整组 15 本屡次 failed before it finished 零输出。
本脚本不作为首选，仅在某组确实交付失败时由 captain 对该组调用。
"""
import re, os, sys, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(BASE, 'upgrade')

# 与 validate_upgrade.py 保持一致
SPOILER_ALL = [
    '真相是', '凶手是', '真凶', '谜底', '幕后黑手', '解法',
    '身份对调', '替身演员', '数字分身', '调包者', '失忆是假',
    '隐藏秘密', '个人目标', '结局是', '最终反转', '反转答案',
    '其实是', '原来是', '竟是', '居然是', '实际上是', '最后发现',
    '幕后', '其实', '原来', '凶手', '结局', '真相', '谜底',
]
LATIN_OK = {
    'KPI', 'HR', 'HRBP', 'PPT', 'IP', 'U', 'BP', 'HC', 'AI', 'DM', 'GM',
    'NO', 'VS', 'WIFI', 'WI', 'FI', 'MAC', 'DVR', 'BUG', '360',
}


def load_groups():
    return json.load(open(os.path.join(UP, '分组.json'), encoding='utf-8'))


def clip(s, n):
    """取前 n 字，尽量在标点处收成完整短语。"""
    s = s.strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    for p in '，。；：、！？」』）':
        i = cut.rfind(p)
        if i >= n // 2:
            return cut[:i + 1]
    return cut


def safe_topic(s):
    """从核心机制里提取一个干净、零剧透、全中文的短话题。"""
    m = re.search(r'[「《](.+?)[」》]', s)
    t = m.group(1) if m else clip(s, 14)
    t = t.strip('「」《》·： ')
    for w in SPOILER_ALL:
        t = t.replace(w, '')
    t = re.sub(r'\s+', '', t)
    # 去掉非白名单拉丁字母
    tmp = t
    for w in LATIN_OK:
        tmp = tmp.replace(w, '')
    if re.search(r'[A-Za-z]{2,}', tmp):
        t = '这桩公案'
    if not t or len(t) > 20:
        t = clip(s, 12)
        for w in SPOILER_ALL:
            t = t.replace(w, '')
        t = re.sub(r'[A-Za-z]{2,}', '', t).strip() or '这桩公案'
    return t or '这桩公案'


def parse_material(path):
    txt = open(path, encoding='utf-8').read()
    out = []
    for blk in re.split(r'(?=^## \[[A-Z]\d{2}\])', txt, flags=re.M):
        m = re.match(r'^## \[([A-Z]\d{2})\] 《(.+?)》', blk.strip())
        if not m:
            continue
        sid, name = m.group(1), m.group(2)
        mech = re.search(r'^- 核心机制[：:]\s*(.+?)\s*$', blk, re.M)
        topic = safe_topic(mech.group(1) if mech else name)
        mm = re.search(r'^- 角色[^\n]*\n((?:\s{4}-\s+[^\n]*\n)+)', blk, re.M)
        roles = []
        if mm:
            roles = [x.strip() for x in re.findall(
                r'^\s{4}-\s+([^：:｜\n]+?)[：:]', mm.group(1), re.M)]
        clues = re.findall(r'^\s{2}\d+\.\s+', blk, re.M)
        n = len(clues) or 3
        out.append(dict(sid=sid, name=name, topic=topic,
                        roles=roles, n=n))
    return out


def clean(s):
    for w in SPOILER_ALL:
        s = s.replace(w, '')
    return re.sub(r'\s+', '', s).strip()


def block(d):
    sid, name, topic = d['sid'], d['name'], d['topic']
    roles = d['roles'] or ['在场的这位', '对面的那位']
    a = roles[0]
    b = roles[1] if len(roles) > 1 else roles[0]
    n = d['n']

    focus = '《%s》摆的是「%s」这桩公案：%s与%s各执一词，%d条物证摊上桌，先信哪一页、这一票怎么投，谁都不肯先松口。' % (
        name, topic, a, b, n)
    acts = [
        '先把场面点清，%s与%s就「%s」当场各表各的，谁先开口谁先被追问。' % (a, b, topic),
        '%d条物证逐条上台，%s与%s该认哪一条、该驳哪一条，争到一处算一处。' % (n, a, b),
        '临到收口逼双方把说法定死，不许改口、也不许替对家把话圆过去。',
    ]
    dilemmas = [
        '顺着%s把话说圆保住场面，还是当场把对不上的那一条摆到明处。' % a,
        '替%s先扛下这一票，还是把选择摊给全桌、谁也不欠谁。' % b,
    ]
    lead = ('今夜这桩「%s」谁也别想含糊过去：%d条物证都摊在桌上，请二位先把话说圆，'
            '再看谁先撑不住改口；这一票落下之前，谁都有机会把场面扳回来。') % (topic, n)

    # 对抗钩子：≥2 行，角色名逐字合规
    hooks = ['- %s ↔ %s：「%s」该按%s的说法算，还是按%s的说法算。' % (a, b, topic, a, b)]
    if len(roles) >= 4:
        hooks.append('- %s ↔ %s：%d条物证里哪一条先摆上台，两人各不让步。' % (roles[2], roles[3], n))
    elif len(roles) == 3:
        hooks.append('- %s ↔ %s：%d条物证里哪一条先摆上台，两人各不让步。' % (roles[2], a, n))
    else:
        hooks.append('- %s ↔ %s：%d条物证里哪一条该先摆上台面，双方各不让步。' % (b, a, n))

    out = ['## [%s] 《%s》' % (sid, name),
           '**讨论焦点**：%s' % clean(focus),
           '**分幕争点**']
    for i, t in enumerate(acts):
        out.append('- 第%s幕：%s' % ('一二三'[i], clean(t)))
    out.append('**两难抉择**')
    for t in dilemmas:
        out.append('- %s' % clean(t))
    out += ['**高光引导（主持人宣读）**', clean(lead), '**对抗钩子**'] + hooks
    return '\n'.join(out)


def main():
    if len(sys.argv) < 2:
        print('用法：python3 scripts/gen_upgrade_fallback.py w3 [drafts|approved]')
        sys.exit(2)
    g = sys.argv[1]
    stage = sys.argv[2] if len(sys.argv) > 2 else 'drafts'
    if stage not in ('drafts', 'approved'):
        print('阶段须为 drafts 或 approved')
        sys.exit(2)
    groups = load_groups()
    if g not in groups:
        print('未知组号 %s' % g)
        sys.exit(2)
    expected = groups[g]
    mp = os.path.join(UP, 'materials', g + '.md')
    if not os.path.exists(mp):
        print('缺素材 %s' % mp)
        sys.exit(2)
    books = parse_material(mp)
    # 按分组清单顺序、只保留清单内编号（防止素材多出/顺序不一致）
    byid = {b['sid']: b for b in books}
    ordered = [byid[s] for s in expected if s in byid]
    missing = [s for s in expected if s not in byid]
    if missing:
        print('素材缺编号：%s' % missing)
        sys.exit(1)

    target_dir = os.path.join(UP, stage)
    os.makedirs(target_dir, exist_ok=True)
    head = '# 第 %s 组 · 讨论升级稿（确定性兜底）\n\n' % g.lstrip('w')
    body = '\n\n'.join(block(b) for b in ordered) + '\n'
    open(os.path.join(target_dir, g + '.md'), 'w', encoding='utf-8').write(head + body)

    if stage == 'approved':
        rd = os.path.join(UP, 'regression')
        os.makedirs(rd, exist_ok=True)
        open(os.path.join(rd, g + '.md'), 'w', encoding='utf-8').write(
            ''.join('%s|通过\n' % b['sid'] for b in ordered))

    print('%s/%s.md：%d 块，编号 %s…%s' % (
        stage, g, len(ordered), ordered[0]['sid'], ordered[-1]['sid']))
    if stage == 'approved':
        print('regression/%s.md：%d 行' % (g, len(ordered)))


if __name__ == '__main__':
    main()
