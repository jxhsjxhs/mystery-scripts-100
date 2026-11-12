#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把评审结果写进 100 本的介绍里（幂等，可重复跑）。
- 读 eval/评分汇总.json（名次/均分/分卷名次/8 人评语）+ eval/PM评审总结.md（总荐语/十佳荐语）
- 每本追加「学生评审名片」到：盒面文案.md、主持人手册.md、本盒完整内容.md
- 生成 评审总榜.md（项目根，带 PM 总结 + 100 行名次表）
- 更新 README.md 的「学生评审」段落
- 更新 盒装本/盒装本总索引.md：每行追加 均分/名次
用法：python3 scripts/finalize_review.py
"""
import re, os, json, glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(BASE, 'eval')
BOX = os.path.join(BASE, '盒装本')
VMAP = {'H': '恐怖本', 'T': '反转本', 'C': '搞笑本', 'O': '职场厮杀本'}

MARK_START = '<!-- 学生评审名片 START -->'
MARK_END = '<!-- 学生评审名片 END -->'


def load_pm():
    path = os.path.join(EV, 'PM评审总结.md')
    if not os.path.exists(path):
        raise SystemExit('缺少 eval/PM评审总结.md，请先派 PM agent 产出。')
    txt = open(path, encoding='utf-8').read()
    # 〇、评审团总荐语：取引用行
    blurb = ''
    m = re.search(r'##\s*〇、评审团总荐语[^\n]*\n+>\s*(.+)', txt)
    if m:
        blurb = m.group(1).strip()
    # 二、十佳逐本荐语：表格行 | 名次 | 编号 | 剧名 | 荐语 |
    praise = {}
    sec = re.search(r'##\s*二、十佳逐本荐语(.*?)(?=\n##\s|\Z)', txt, re.S)
    if sec:
        for line in sec.group(1).splitlines():
            mm = re.match(r'^\|\s*(\d+)\s*\|\s*([A-Z]\d{2})\s*\|\s*《(.+?)》\s*\|\s*(.+?)\s*\|?\s*$', line)
            if mm:
                praise[mm.group(2)] = mm.group(4).strip().strip('|').strip()
    if not blurb:
        raise SystemExit('PM 总结里没找到「〇、评审团总荐语」的引用行。')
    if len(praise) < 10:
        raise SystemExit('PM 总结里十佳荐语只解析到 %d 条，应为 10 条。' % len(praise))
    return blurb, praise, txt


def review_card(r, blurb, praise, students):
    lines = [MARK_START, '## 学生评审名片', '',
             '> 本项目邀请 8 位人设各异的学生评审独立打分，按 8 人均分从高到低排名。', '',
             '| 项目 | 结果 |', '| --- | --- |',
             '| 综合均分 | **%.2f / 100** |' % r['avg'],
             '| 全榜名次 | **第 %d 名 / 100** |' % r['rank'],
             '| 本卷名次 | 第 %d 名 / 25（%s） |' % (r['vol_rank'], r['vol']),
             '| 八人分数 | %s |' % ' ／ '.join(
                 '%s %d' % (next(n for c, n, _, _ in students if c == code), r['scores'][code])
                 for code, _, _, _ in students), '']
    if r['sid'] in praise:
        lines += ['**评审团总荐语**：%s' % blurb, '',
                  '**PM 十佳荐语**：%s' % praise[r['sid']], '']
    else:
        lines += ['**评审团总荐语**：%s' % blurb, '']
    lines += ['**学生短评（零剧透）**：', '']
    for code, name, _, focus in students:
        lines.append('- %s（%s，看 %s）：%s' % (name, code, focus, r['comments'][code]))
    lines += ['', MARK_END]
    return '\n'.join(lines)


def inject(path, card, where):
    """幂等：已有名片块则整体替换，否则按 where 追加/插入。"""
    txt = open(path, encoding='utf-8').read()
    if MARK_START in txt and MARK_END in txt:
        a = txt.index(MARK_START)
        b = txt.index(MARK_END) + len(MARK_END)
        txt = txt[:a] + card + txt[b:]
    elif where == 'head':
        # 盒面文案：放在标题+提示行之后、正文之前
        m = re.match(r'^(# [^\n]*\n+(?:> [^\n]*\n+)?)(.*)$', txt, re.S)
        if m:
            txt = m.group(1) + '\n' + card + '\n\n' + m.group(2)
        else:
            txt = card + '\n\n' + txt
    elif where == 'dm':
        # 主持人手册：放在「〇、商业化包装」之前
        anchor = '## 一、基本信息'
        if anchor in txt:
            txt = txt.replace(anchor, card + '\n\n' + anchor, 1)
        else:
            txt = card + '\n\n' + txt
    else:
        txt = txt.rstrip() + '\n\n' + card + '\n'
    open(path, 'w', encoding='utf-8').write(txt)


def main():
    payload = json.load(open(os.path.join(EV, '评分汇总.json'), encoding='utf-8'))
    students = [(s['code'], s['name'], s['role'], s['focus']) for s in payload['students']]
    ranked = payload['ranking']
    blurb, praise, pm_txt = load_pm()

    # 1) 每本注入
    n = 0
    for r in ranked:
        folder = os.path.join(BOX, '%s_%s' % (r['sid'], r['name']))
        if not os.path.isdir(folder):
            print('! 缺盒目录 %s' % folder)
            continue
        card = review_card(r, blurb, praise, students)
        for fn, where in [('盒面文案.md', 'head'), ('主持人手册.md', 'dm'),
                          ('本盒完整内容.md', 'tail')]:
            p = os.path.join(folder, fn)
            if os.path.exists(p):
                inject(p, card, where)
        n += 1
    print('已注入 %d 本盒装本的介绍（盒面文案 / 主持人手册 / 本盒完整内容）。' % n)

    # 2) 项目根 评审总榜.md —— PM 总结已含「五、全体名次表」100 行，不重复追加机器表
    out = [pm_txt.rstrip(), '', '---', '',
           '> 机器生成的权威名次表（含卷内名次与八人分数）见 [eval/总榜.md](eval/总榜.md)；',
           '> 逐本分数与评语见 [eval/评分汇总.json](eval/评分汇总.json)。',
           '> 每一本的介绍里都已写入综合均分、全榜名次、本卷名次与零剧透短评。', '']
    open(os.path.join(BASE, '评审总榜.md'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('已生成 评审总榜.md（PM 总结 + 100 行名次表，无重复表）。')

    # 3) README.md 追加/替换「学生评审」段
    rp = os.path.join(BASE, 'README.md')
    rt = open(rp, encoding='utf-8').read()
    seg = [
        '## 学生评审总榜（8 位学生 + PM 汇总）', '',
        '本项目邀请 **8 位人设互不相同的学生评审**各自独立给 100 本打分（60–98）：',
        '',
        '| 学生 | 身份 | 最看重 |', '| --- | --- | --- |',
    ]
    for c, name, role, focus in students:
        seg.append('| %s | %s | %s |' % (name, role, focus))
    seg += ['',
            '**评审团总荐语**：%s' % blurb, '',
            '由 1 位 PM agent 汇总，按 **8 人均分从高到低**排出 100 本总榜：',
            '完整榜与 PM 总结见 [评审总榜.md](评审总榜.md)，原始分数见 [eval/评分汇总.json](eval/评分汇总.json)。',
            '**每一本的介绍里都已写入**综合均分、全榜名次、本卷名次、8 人分数与零剧透短评。', '']
    block = '\n'.join(seg)
    if '## 学生评审总榜（8 位学生 + PM 汇总）' in rt:
        a = rt.index('## 学生评审总榜（8 位学生 + PM 汇总）')
        nxt = re.search(r'\n## ', rt[a + 5:])
        b = a + 5 + nxt.start() if nxt else len(rt)
        rt = rt[:a] + block + '\n' + rt[b:]
    else:
        rt = rt.rstrip() + '\n\n---\n\n' + block
    open(rp, 'w', encoding='utf-8').write(rt)
    print('已更新 README.md 的「学生评审总榜」段。')

    # 4) 盒装本总索引：每行追加 均分/名次（幂等）
    ip = os.path.join(BOX, '盒装本总索引.md')
    if os.path.exists(ip):
        it = open(ip, encoding='utf-8').read()
        rmap = {r['sid']: r for r in ranked}
        # 表头：含「编号」且尚未含「均分」→ 追加列名
        def headcol(m):
            line = m.group(0)
            if '均分' in line:
                return line
            return line.rstrip().rstrip('|').rstrip() + ' | 均分 / 全榜名次 |'
        it = re.sub(r'^\|\s*编号\s*\|[^\n]*$', headcol, it, flags=re.M)
        # 分隔行：数 --- 段数，7 段 → 补成 8 段
        def sepcor(m):
            line = m.group(0)
            n = line.count('---')
            if n != 7:
                return line
            return line.rstrip() + '---|'
        it = re.sub(r'^\|(?:---\|)+\s*$', sepcor, it, flags=re.M)
        # 数据行：| H01 | ... |  → 末尾追加均分/名次
        def addcol(m):
            line = m.group(0)
            sid = m.group(2)
            r = rmap.get(sid)
            if not r or ' / 第' in line:
                return line
            return line.rstrip().rstrip('|').rstrip() + ' | %.2f / 第%d名 |' % (r['avg'], r['rank'])
        it = re.sub(r'^(\|\s*([HTCO]\d{2})\s*\|[^\n]*)$', addcol, it, flags=re.M)
        open(ip, 'w', encoding='utf-8').write(it)
        print('已更新 盒装本/盒装本总索引.md（追加均分/名次列）。')
    print('完成。')


if __name__ == '__main__':
    main()
