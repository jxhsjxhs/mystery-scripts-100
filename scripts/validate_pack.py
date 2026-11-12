#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校验 4 卷商业化包装文案 commercial/pack_<vol>.md 与导师指导 guide_<vol>.md。
用法：python3 scripts/validate_pack.py [pack|guide|all]   （默认 all）

硬错误（计入 exit 1）：
  - pack: 25 块齐全、编号连续、剧名与素材表一致、必备 2 行字段 + 5 段、
          角色预告行数 == 人数、上架标签 5–7 个、卖点 3 条、非白名单拉丁词
  - guide: 25 行指导表、编号连续、剧名一致、5 章节齐全
软警告（打印但不计入 exit 1，需人工扫一眼）：
  - 疑似剧透词命中。写手按契约只读零剧透素材表，本就不接触真相，
    故这些词多为背景氛围的正常用词（如「其实/原来/竟是」），列为提醒而非判死。
"""
import re, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COM = os.path.join(BASE, 'commercial')
GUD = os.path.join(COM, 'guidance')

VOL = [('horror', 'H', '恐怖本'), ('twist', 'T', '反转本'),
       ('comedy', 'C', '搞笑本'), ('office', 'O', '职场厮杀本')]

# 疑似剧透词（软警告）
SPOILER = [
    '原来', '其实', '真相是', '真正的凶手', '幕后', '真凶', '凶手是', '最终反转',
    '结局是', '最后发现', '竟是', '居然是', '实际上是', '身份对调', '替身演员',
    '失忆是假', '数字分身', '调包者', '隐藏秘密', '个人目标',
]
# 拉丁词白名单（职场通用缩写 + 章节标题里必然出现的 DM）
LATIN_OK = {'KPI', 'HR', 'HRBP', 'PPT', 'IP', 'U', 'BP', 'HC', 'AI', 'DM', 'GM',
            'NO', 'VS', 'WIFI', 'WI', 'FI'}
LATIN_RE = re.compile(r'[A-Za-z]{2,}')

SECTIONS = ['盒背文案', '卖点', '开场导语（DM 宣读）', '角色预告', '上架标签']
LINE_FIELDS = ['一句话卖点', '上架分类']
GUIDE_CHAPTERS = ['本卷商业化定位', '逐本指导表', '本卷通用准则', '给写手的', '验收清单']


def material(vol, pre):
    """从零剧透素材表读 编号 -> (剧名, 角色行数)。"""
    path = os.path.join(GUD, '素材_%s.md' % vol)
    txt = open(path, encoding='utf-8').read()
    out = {}
    for blk in re.split(r'(?=^## \[%s\d{2}\])' % pre, txt, flags=re.M):
        m = re.match(r'^## \[(%s\d{2})\] 《(.+?)》' % pre, blk.strip())
        if not m:
            continue
        sid, name = m.group(1), m.group(2)
        # 角色行形如 "  - 冥婚·桂姨：..."，两个空格缩进
        roles = re.findall(r'^  - \S', blk, re.M)
        out[sid] = (name, len(roles))
    return out


def check_pack(vol, pre, label):
    path = os.path.join(COM, 'pack_%s.md' % vol)
    warn = []
    problems = []
    if not os.path.exists(path):
        return ['缺文件：%s' % path], []
    txt = open(path, encoding='utf-8').read()
    mat = material(vol, pre)
    got = {}
    for blk in re.split(r'(?=^## \[%s\d{2}\])' % pre, txt, flags=re.M):
        m = re.match(r'^## \[(%s\d{2})\] 《(.+?)》' % pre, blk.strip(), re.S)
        if not m:
            continue
        sid, name = m.group(1), m.group(2)
        if sid in got:
            problems.append('%s 重复块' % sid)
        got[sid] = (name, blk)
    for i in range(1, 26):
        sid = '%s%02d' % (pre, i)
        if sid not in got:
            problems.append('%s 缺块' % sid)
            continue
        name, blk = got[sid]
        if sid in mat and mat[sid][0] != name:
            problems.append('%s 剧名不符：%s != %s' % (sid, name, mat[sid][0]))
        for f in LINE_FIELDS:
            if not re.search(r'-\s*%s[：:]' % f, blk):
                problems.append('%s 缺字段 %s' % (sid, f))
        for s in SECTIONS:
            if ('### ' + s) not in blk:
                problems.append('%s 缺段「%s」' % (sid, s))
        # 角色预告行数 == 人数
        rm = re.search(r'### 角色预告[^\n]*\n(.*?)(?=\n###|\Z)', blk, re.S)
        if rm and sid in mat:
            lines = [l for l in rm.group(1).splitlines() if l.strip().startswith('- ')]
            if len(lines) != mat[sid][1]:
                problems.append('%s 角色预告 %d 行 != 人数 %d' % (sid, len(lines), mat[sid][1]))
        # 卖点 3 条
        sm = re.search(r'### 卖点[^\n]*\n(.*?)(?=\n###|\Z)', blk, re.S)
        if sm:
            n3 = len(re.findall(r'^\s*\d+\.', sm.group(1), re.M))
            if n3 != 3:
                problems.append('%s 卖点 %d 条 != 3' % (sid, n3))
        # 上架标签 5–7 个
        tm = re.search(r'### 上架标签[^\n]*\n(.*?)(?=\n###|\Z)', blk, re.S)
        if tm:
            tags = re.findall(r'#\S+', tm.group(1))
            if not (5 <= len(tags) <= 7):
                problems.append('%s 上架标签 %d 个（应 5–7）' % (sid, len(tags)))
        # 剧透词 → 软警告。只扫「文案段落」：
        # 「- 上架分类」行含题材标签名（如「数字分身伪在线」），
        # 「### 角色预告」段含角色名（如「社恐·幕后人」），
        # 二者都是公开分类/人名，不是剧透句子，排除掉以免误报。
        prose = blk
        prose = re.sub(r'^\s*-\s*上架分类[：:].*$', '', prose, flags=re.M)
        prose = re.sub(r'### 角色预告[^\n]*\n.*?(?=\n###|\Z)', '', prose, flags=re.S)
        for w in SPOILER:
            if w in prose:
                warn.append('%s 疑似剧透词「%s」' % (sid, w))
        # 非白名单拉丁词 → 硬错误（同样排除角色名行，角色名可含缩写）
        for w in LATIN_RE.findall(prose):
            if w.upper() not in LATIN_OK:
                problems.append('%s 拉丁词「%s」' % (sid, w))
                break
    return problems, warn


def check_guide(vol, pre, label):
    path = os.path.join(GUD, 'guide_%s.md' % vol)
    problems = []
    if not os.path.exists(path):
        return ['缺文件：%s' % path]
    txt = open(path, encoding='utf-8').read()
    mat = material(vol, pre)
    got = {}
    # 兼容编号列写成 H01 或 01 两种
    for m in re.finditer(r'^\|\s*([A-Z]?\d{2})\s*\|\s*《?(.+?)》?\s*\|', txt, re.M):
        raw, name = m.group(1), m.group(2).strip()
        sid = raw if len(raw) == 3 else pre + raw
        got[sid] = name
    for i in range(1, 26):
        sid = '%s%02d' % (pre, i)
        if sid not in got:
            problems.append('%s 指导表缺行' % sid)
        elif sid in mat and got[sid] != mat[sid][0]:
            problems.append('%s 指导表剧名不符：%s != %s' % (sid, got[sid], mat[sid][0]))
    for h in GUIDE_CHAPTERS:
        if h not in txt:
            problems.append('缺章节「%s」' % h)
    return problems


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
    total = 0
    warns = 0
    for vol, pre, label in VOL:
        if mode in ('pack', 'all'):
            ps, ws = check_pack(vol, pre, label)
            total += len(ps)
            warns += len(ws)
            print('[%s pack ] %s' % (label, '✅ 25 块 / 格式 / 零拉丁词合规' if not ps else '❌ %d 项硬错误' % len(ps)))
            for p in ps:
                print('     ✗ ' + p)
            for w in ws:
                print('     ⚠ ' + w)
        if mode in ('guide', 'all'):
            gs = check_guide(vol, pre, label)
            total += len(gs)
            print('[%s guide] %s' % (label, '✅ 25 行 / 5 章齐全' if not gs else '❌ %d 项问题' % len(gs)))
            for g in gs:
                print('     ✗ ' + g)
    print('\n硬错误合计：%d    软警告（剧透词，需扫一眼）：%d' % (total, warns))
    sys.exit(1 if total else 0)


if __name__ == '__main__':
    main()
