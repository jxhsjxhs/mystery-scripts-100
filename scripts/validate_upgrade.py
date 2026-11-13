#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校验 6 组「讨论精彩程度升级」稿与导师回归报告。
用法：python3 scripts/validate_upgrade.py [drafts|approved|all]
  drafts   —— 只校验 upgrade/drafts/w*.md（派导师之前）
  approved —— 校验 upgrade/approved/w*.md + upgrade/regression/w*.md（合并之前）
  all      —— 全部校验（默认）
有硬错误时 exit 1。
"""
import re, os, json, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(BASE, 'upgrade')
GROUPS = ['w1', 'w2', 'w3', 'w4', 'w5', 'w6']

# 五个固定标签（与《升级规范.md》第四节模板逐字一致）
LABELS = ['讨论焦点', '分幕争点', '两难抉择', '高光引导（主持人宣读）', '对抗钩子']

SPOILER_HARD = [
    '真相是', '凶手是', '真凶', '谜底', '幕后黑手', '解法',
    '身份对调', '替身演员', '数字分身', '调包者', '失忆是假',
    '隐藏秘密', '个人目标', '结局是', '最终反转', '反转答案',
    '其实是', '原来是', '竟是', '居然是', '实际上是', '最后发现',
]
SPOILER_SOFT = ['幕后', '其实', '原来', '凶手', '结局']

LATIN_OK = {
    'KPI', 'HR', 'HRBP', 'PPT', 'IP', 'U', 'BP', 'HC', 'AI', 'DM', 'GM',
    'NO', 'VS', 'WIFI', 'WI', 'FI', 'MAC', 'DVR', 'BUG',
}


def load_groups():
    return json.load(open(os.path.join(UP, '分组.json'), encoding='utf-8'))


def load_materials():
    """sid -> {name, roles}; roles 来自素材表「角色（名字 → 公开身份 ｜ 表面立场）」段。"""
    info = {}
    for g in GROUPS:
        p = os.path.join(UP, 'materials', g + '.md')
        if not os.path.exists(p):
            continue
        txt = open(p, encoding='utf-8').read()
        for blk in re.split(r'(?=^## \[[A-Z]\d{2}\])', txt, flags=re.M):
            m = re.match(r'^## \[([A-Z]\d{2})\] 《(.+?)》', blk.strip())
            if not m:
                continue
            sid, name = m.group(1), m.group(2)
            mm = re.search(r'^- 角色[^\n]*\n((?:\s{4}-\s+[^\n]*\n)+)', blk, re.M)
            roles = []
            if mm:
                roles = [x.strip() for x in re.findall(
                    r'^\s{4}-\s+([^：:｜\n]+?)[：:]', mm.group(1), re.M)]
            info[sid] = dict(name=name, roles=roles)
    return info


def section(blk, label):
    """取 **标签** 之后、下一个 **标签** 之前的正文。"""
    m = re.search(r'\*\*%s\*\*\s*\n(.*?)(?=\n\*\*[^*]+\*\*|\Z)' % re.escape(label),
                  blk, re.S)
    return m.group(1).strip() if m else None


def split_blocks(text):
    out = []
    for blk in re.split(r'(?=^## \[[A-Z]\d{2}\])', text, flags=re.M):
        m = re.match(r'^## \[([A-Z]\d{2})\] 《(.+?)》', blk.strip())
        if m:
            out.append((m.group(1), m.group(2), blk.strip()))
    return out


def check_stage(stage, g, expected, mat):
    """校验某一组某一阶段的稿件，返回 (硬错误列表, 软警告列表, 实际编号列表)。"""
    path = os.path.join(UP, stage, g + '.md')
    bad, soft, seen = [], [], []
    if not os.path.exists(path):
        return ['[%s/%s] 缺文件 %s' % (stage, g, os.path.relpath(path, BASE))], soft, seen
    txt = open(path, encoding='utf-8').read()
    for sid, name, blk in split_blocks(txt):
        seen.append(sid)
        tag = '[%s/%s %s]' % (stage, g, sid)
        if sid not in expected:
            bad.append('%s 编号不在本组清单' % tag)
            continue
        mn = mat.get(sid, {})
        if mn.get('name') and mn['name'] != name:
            bad.append('%s 剧名与素材表不一致（稿=%s / 素材=%s）' % (tag, name, mn['name']))
        for lb in LABELS:
            if ('**%s**' % lb) not in blk:
                bad.append('%s 缺标签 **%s**' % (tag, lb))

        # 分幕争点：恰好 第一/第二/第三幕 三行
        s = section(blk, '分幕争点')
        acts = re.findall(r'^\s*-\s*(第[一二三]幕)[：:]', s or '', re.M)
        if acts != ['第一幕', '第二幕', '第三幕']:
            bad.append('%s 分幕争点须恰好 第一/第二/第三幕 三行（实际 %s）' % (tag, acts))

        # 两难抉择 ≥2 行
        s = section(blk, '两难抉择')
        if len(re.findall(r'^\s*-\s+\S', s or '', re.M)) < 2:
            bad.append('%s 两难抉择须 ≥2 行' % tag)

        # 对抗钩子 ≥2 行、每行含 ↔、角色名逐字出自素材表
        s = section(blk, '对抗钩子')
        hooks = re.findall(r'^\s*-\s+.+$', s or '', re.M)
        if len(hooks) < 2:
            bad.append('%s 对抗钩子须 ≥2 行' % tag)
        roles = mn.get('roles', [])
        for ln in hooks:
            if '↔' not in ln:
                bad.append('%s 对抗钩子行缺 ↔：%s' % (tag, ln[:32]))
                continue
            mm = re.match(r'^\s*-\s*(.+?)\s*↔\s*(.+?)\s*[：:]\s*(.*)$', ln)
            if not mm:
                bad.append('%s 对抗钩子行格式不对：%s' % (tag, ln[:32]))
                continue
            for who in (mm.group(1).strip(), mm.group(2).strip()):
                if who not in roles:
                    bad.append('%s 角色名「%s」不在公开角色名表 %s' % (tag, who, roles))

        # 零剧透 / 全中文：先把合法角色名抠掉，避免「幕后人」等误报
        prose = blk
        for r in roles:
            prose = prose.replace(r, '')
        for w in SPOILER_HARD:
            if w in prose:
                bad.append('%s 剧透词「%s」' % (tag, w))
        for w in SPOILER_SOFT:
            if w in prose:
                soft.append('%s 软提示「%s」' % (tag, w))
        tmp = prose
        for w in LATIN_OK:
            tmp = tmp.replace(w, '')
        lat = sorted(set(re.findall(r'[A-Za-z]{2,}', tmp)))
        if lat:
            bad.append('%s 非白名单拉丁字母 %s' % (tag, lat[:6]))

    if seen != expected:
        bad.append('[%s/%s] 编号顺序或数量不符：稿 %d 本 / 期望 %d 本；'
                   '缺 %s / 多 %s' % (
                       stage, g, len(seen), len(expected),
                       [x for x in expected if x not in seen],
                       [x for x in seen if x not in expected]))
    return bad, soft, seen


def check_regression(g, expected):
    path = os.path.join(UP, 'regression', g + '.md')
    bad = []
    if not os.path.exists(path):
        return ['[regression/%s] 缺文件 %s' % (g, os.path.relpath(path, BASE))]
    lines = [x.strip() for x in open(path, encoding='utf-8').read().splitlines() if x.strip()]
    if len(lines) != len(expected):
        bad.append('[regression/%s] 行数 %d ≠ 期望 %d' % (g, len(lines), len(expected)))
    sids = []
    for ln in lines:
        parts = ln.split('|', 1)
        if len(parts) != 2:
            bad.append('[regression/%s] 行格式不对：%s' % (g, ln[:40]))
            continue
        sid, val = parts[0].strip(), parts[1].strip()
        sids.append(sid)
        if val != '通过' and not val.startswith('修订：'):
            bad.append('[regression/%s] %s 判定值须为「通过」或「修订：…」（实际 %s）' % (g, sid, val[:20]))
    if sids != expected:
        bad.append('[regression/%s] 编号顺序或数量不符：缺 %s / 多 %s' % (
            g, [x for x in expected if x not in sids], [x for x in sids if x not in expected]))
    return bad


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if stage not in ('drafts', 'approved', 'all'):
        print('用法：python3 scripts/validate_upgrade.py [drafts|approved|all]')
        sys.exit(2)
    groups = load_groups()
    mat = load_materials()
    bad, soft = [], []
    stages = ['drafts', 'approved'] if stage == 'all' else [stage]
    for g in GROUPS:
        expected = groups[g]
        for st in stages:
            b, s, _ = check_stage(st, g, expected, mat)
            bad += b
            soft += s
        if stage in ('approved', 'all'):
            bad += check_regression(g, expected)
        n = len(expected)
        print('  %s：期望 %2d 本；' % (g, n), end='')
        for st in stages:
            p = os.path.join(UP, st, g + '.md')
            print(' %s=%s' % (st, '有' if os.path.exists(p) else '缺'), end='')
        print()

    print('\n硬错误合计：%d' % len(bad))
    for x in bad[:60]:
        print('  ✗ ' + x)
    if len(bad) > 60:
        print('  … 另有 %d 条' % (len(bad) - 60))
    print('软提示合计：%d' % len(soft))
    for x in soft[:10]:
        print('  · ' + x)
    if bad:
        sys.exit(1)
    print('✅ 升级稿 / 回归报告结构、编号、剧名、角色名、零剧透、全中文全部通过。')


if __name__ == '__main__':
    main()
