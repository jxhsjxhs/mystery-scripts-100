#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 6 组写手生成「讨论精彩程度升级」零剧透素材表。

低分本 = eval/评分汇总.json 中 avg < 85 的 89 本（升级前的权威榜）。
按「卷序 + 编号」排序后切成 6 组（15/15/15/15/15/14），每组一个素材文件。

素材只含：编号 / 剧名 / 题材 / 人数 / 时长 / 难度 / 公开背景 /
          角色公开信息（名字 + 公开身份 + 表面立场）/ 核心诡计 / 关键线索 / 三幕流程。
刻意不含：反转点 / 真相与结局 / 隐藏秘密 / 个人目标（这些是答案，不能进写手视野）。

产出：
  upgrade/分组.json           —— 组号 → 编号列表
  upgrade/低分本清单.md        —— 89 本清单（编号 / 剧名 / 均分 / 原名次）
  upgrade/materials/w1..w6.md —— 6 份写手/导师共用的零剧透素材表
用法：python3 scripts/gen_upgrade_materials.py
"""
import re, os, json, glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'upgrade')
MAT = os.path.join(OUT, 'materials')
os.makedirs(MAT, exist_ok=True)

VOL = [('horror', 'H', '恐怖本'), ('twist', 'T', '反转本'),
       ('comedy', 'C', '搞笑本'), ('office', 'O', '职场厮杀本')]
VORDER = {'H': 0, 'T': 1, 'C': 2, 'O': 3}


def sec(p, nm):
    m = re.search(r'###\s*%s[^\n]*\n(.*?)(?=\n###|\Z)' % nm, p, re.S)
    return m.group(1).strip() if m else ''


def clean_public(body):
    """角色行 -> 只保留 名字 + 公开身份 + 表面立场，切掉隐藏秘密/个人目标。"""
    m = re.match(r'^(.*?)[。；]\s*表面立场[：:]\s*(.*?)[。；]', body.strip(), re.S)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return body.split('。')[0].strip(), ''


def load_scripts():
    out = {}
    for vol, pre, label in VOL:
        path = glob.glob(os.path.join(BASE, vol, '*.md'))[0]
        text = open(path, encoding='utf-8').read()
        for p in re.split(r'(?=^## \[%s\d{2}\] )' % pre, text, flags=re.M):
            m = re.match(r'^## \[(%s\d{2})\] 《(.+?)》' % pre, p.strip())
            if not m:
                continue
            sid, name = m.group(1), m.group(2)

            def fld(f):
                mm = re.search(r'-\s*%s[：:]\s*(.+?)\s*$' % f, p, re.M)
                return mm.group(1) if mm else ''

            roles = []
            for nm, body in re.findall(r'-\s*\*\*(.+?)\*\*[：:]([^\n]*)', sec(p, '角色')):
                ident, stance = clean_public(body)
                roles.append('    - %s：%s｜%s' % (nm.strip(), ident, stance))
            clues = [ln.strip() for ln in sec(p, '关键线索').splitlines() if ln.strip()]
            flow = [ln.strip() for ln in sec(p, '流程').splitlines() if ln.strip()]
            out[sid] = dict(
                name=name, vol=vol, pre=pre, label=label,
                meta='- 题材：%s ｜ 人数：%s ｜ 时长：%s ｜ 难度：%s' % (
                    fld('题材'), fld('人数'), fld('时长'), fld('难度')),
                bg='- 公开背景：%s' % re.sub(r'\s*\n\s*', '', sec(p, '背景')),
                mech='- 核心机制：%s' % re.sub(r'\s*\n\s*', '', sec(p, '核心诡计'))[:300],
                roles=roles, clues=clues, flow=flow)
    return out


def main():
    payload = json.load(open(os.path.join(BASE, 'eval', '评分汇总.json'), encoding='utf-8'))
    ranked = payload['ranking']
    low = [r for r in ranked if r['avg'] < 85]
    low.sort(key=lambda r: (VORDER[r['sid'][0]], int(r['sid'][1:])))
    sids = [r['sid'] for r in low]
    rmap = {r['sid']: r for r in low}

    # 6 组：15/15/15/15/15/14
    n, k = len(sids), 6
    sizes = [n // k + (1 if i < n % k else 0) for i in range(k)]
    groups, cur = {}, 0
    for i, sz in enumerate(sizes, 1):
        groups['w%d' % i] = sids[cur:cur + sz]
        cur += sz
    json.dump(groups, open(os.path.join(OUT, '分组.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)

    # 清单
    lst = ['# 讨论精彩程度升级 · 低分本清单（评分 < 85）\n',
           '> 升级前权威榜 `eval/评分汇总.json` 中均分低于 85 的本，共 **%d** 本。' % n,
           '> 其余 11 本（均分 ≥ 85）保持原版，不参与本轮升级。\n',
           '| 编号 | 剧名 | 均分 | 原全榜名次 | 组别 |', '| --- | --- | --- | --- | --- |']
    gmap = {s: g for g, ss in groups.items() for s in ss}
    for s in sids:
        r = rmap[s]
        lst.append('| %s | 《%s》 | %.2f | 第 %d 名 | %s |' % (s, r['name'], r['avg'], r['rank'], gmap[s]))
    open(os.path.join(OUT, '低分本清单.md'), 'w', encoding='utf-8').write('\n'.join(lst) + '\n')

    scripts = load_scripts()
    VLABEL = {'H': '恐怖本', 'T': '反转本', 'C': '搞笑本', 'O': '职场厮杀本'}
    for g, ss in groups.items():
        lines = [
            '# 第 %s 组 · 讨论精彩程度升级素材（%d 本）\n' % (g[-1], len(ss)),
            '> 本表**刻意剔除**反转 / 真相 / 结局 / 隐藏秘密 / 个人目标，写手与导师只依据本表写作。',
            '> 不要凭空新增人物、道具或设定；所有争点必须能从下面的公开信息里长出来。',
            '> 输出必须零剧透、全中文。\n',
        ]
        for s in ss:
            d = scripts[s]
            lines += ['## [%s] 《%s》' % (s, d['name']), d['meta'], d['bg'], d['mech'],
                      '- 角色（名字 → 公开身份 ｜ 表面立场）：'] + d['roles']
            lines.append('- 关键线索（公开物证）：')
            lines += ['  %s' % c for c in d['clues']]
            lines.append('- 三幕流程（原文）：')
            lines += ['  %s' % c for c in d['flow']]
            lines.append('')
        open(os.path.join(MAT, '%s.md' % g), 'w', encoding='utf-8').write('\n'.join(lines))

    print('低分本 %d 本，按卷序切 6 组：%s' % (n, {g: len(ss) for g, ss in groups.items()}))
    for g, ss in groups.items():
        p = os.path.join(MAT, '%s.md' % g)
        print('  %s -> %s（%d 本，%d 行）' % (
            g, os.path.relpath(p, BASE), len(ss),
            len(open(p, encoding='utf-8').read().splitlines())))
    print('清单 -> %s' % os.path.relpath(os.path.join(OUT, '低分本清单.md'), BASE))
    # 自检：素材里不含答案字段
    bad = []
    for g in groups:
        # 只看正文（跳过以 > 开头的说明行，说明行里会点名被剔除的字段名）
        body = '\n'.join(l for l in open(os.path.join(MAT, '%s.md' % g), encoding='utf-8')
                         if not l.lstrip().startswith('>'))
        for w in ['隐藏秘密', '个人目标', '### 反转点', '### 真相', '### 结局']:
            if w in body:
                bad.append('%s 含 %s' % (g, w))
    print('零剧透自检：', '；'.join(bad) if bad else '通过 ✓')


if __name__ == '__main__':
    main()
