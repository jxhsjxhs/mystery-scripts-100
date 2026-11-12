#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校验评审结果已完整写进 100 本的介绍里。
用法：python3 scripts/verify_review.py
"""
import re, os, json, glob, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(BASE, 'eval')
BOX = os.path.join(BASE, '盒装本')
MARK = '<!-- 学生评审名片 START -->'
SPOILER = ['真相', '真凶', '凶手', '谜底', '解法', '幕后黑手', '其实是', '原来是',
           '竟是', '居然是', '隐藏秘密', '个人目标', '身份对调', '数字分身',
           '替身演员', '失忆是假', '调包者', '结局是']


def main():
    probs = []
    payload = json.load(open(os.path.join(EV, '评分汇总.json'), encoding='utf-8'))
    ranked = payload['ranking']
    if len(ranked) != 100:
        probs.append('评分汇总.json 排名只有 %d 本' % len(ranked))
    ranks = [r['rank'] for r in ranked]
    if ranks != list(range(1, 101)):
        probs.append('名次不是 1–100 连续')
    # 均分降序
    for a, b in zip(ranked, ranked[1:]):
        if a['avg'] < b['avg']:
            probs.append('排序错：%s %.2f 在 %s %.2f 之前' % (a['sid'], a['avg'], b['sid'], b['avg']))
            break
    pm_path = os.path.join(EV, 'PM评审总结.md')
    blurb_ok = os.path.exists(pm_path)
    if not blurb_ok:
        probs.append('缺 eval/PM评审总结.md')
    else:
        # PM 是唯一由模型手写、且会印进 100 本介绍的文字：逐项严查
        pt = open(pm_path, encoding='utf-8').read()
        for sec in ['〇、评审团总荐语', '一、评审方法与总览', '二、十佳逐本荐语',
                    '三、分卷观察', '四、选本建议', '五、全体名次表']:
            if sec not in pt:
                probs.append('PM 总结缺「%s」' % sec)
        # 零剧透（PM 全文）
        for w in SPOILER:
            if w in pt:
                probs.append('PM 总结含剧透词「%s」' % w)
                break
        # 全中文（去掉编号/代号/分数/HTML注释/markdown 结构后无连续拉丁字母）
        body = re.sub(r'<!--[^>]*-->', '', pt)
        body = re.sub(r'\[[^\]]*\]\([^)]*\)', '', body)          # markdown 链接
        body = re.sub(r'[A-Za-z]\d{2}|s\d{2}|PM|DM|START|END|KPI|PPT|HR|HRBP|BP|IP|HC|AI|WI|FI|NO|VS|WIFI|\d+\.\d+|\d+', '', body)
        body = re.sub(r'(?m)^\|[-:\s|]+\|$', '', body)             # 表格分隔行
        body = re.sub(r'[#>|`*_~\-]', '', body)                     # markdown 符号
        if re.search(r'[A-Za-z]{2,}', body):
            probs.append('PM 总结含连续拉丁字母')
        # 按章节切片，避免十佳正则把第五节 100 行名次表也算进去
        sec2 = re.search(r'##\s*二、十佳逐本荐语(.*?)(?=\n##\s|\Z)', pt, re.S)
        sec5 = re.search(r'##\s*五、全体名次表(.*?)(?=\n##\s|\Z)', pt, re.S)
        # 十佳表：10 行，名次 1–10，编号/剧名与 JSON TOP10 逐字一致
        top10 = ranked[:10]
        praises = re.findall(r'^\|\s*(\d+)\s*\|\s*([A-Z]\d{2})\s*\|\s*《(.+?)》\s*\|',
                             sec2.group(1) if sec2 else '', re.M)
        if len(praises) != 10:
            probs.append('PM 十佳表解析到 %d 行（应 10）' % len(praises))
        else:
            for i, ((rk, sid, nm), r) in enumerate(zip(praises, top10), 1):
                if int(rk) != i or sid != r['sid'] or nm != r['name']:
                    probs.append('PM 十佳第 %d 行不一致：%s %s《%s》' % (i, rk, sid, nm))
                    break
        # 全体名次表：100 行，逐行与 JSON 排名一致
        allrows = re.findall(r'^\|\s*(\d+)\s*\|\s*([A-Z]\d{2})\s*\|\s*《(.+?)》\s*\|\s*([^|]+?)\s*\|\s*([\d.]+)\s*\|',
                             sec5.group(1) if sec5 else '', re.M)
        rank_rows = allrows
        if len(rank_rows) != 100:
            probs.append('PM 全体名次表解析到 %d 行（应 100）' % len(rank_rows))
        else:
            for (rk, sid, nm, vol, avg), r in zip(rank_rows, ranked):
                if (int(rk) != r['rank'] or sid != r['sid'] or nm != r['name']
                        or vol.strip() != r['vol'] or abs(float(avg) - r['avg']) > 0.005):
                    probs.append('PM 名次表第 %s 行与 JSON 不一致' % rk)
                    break

    nbox = 0
    for r in ranked:
        folder = os.path.join(BOX, '%s_%s' % (r['sid'], r['name']))
        if not os.path.isdir(folder):
            probs.append('%s 缺盒目录' % r['sid'])
            continue
        nbox += 1
        for fn in ['盒面文案.md', '主持人手册.md', '本盒完整内容.md']:
            p = os.path.join(folder, fn)
            if not os.path.exists(p):
                probs.append('%s 缺 %s' % (r['sid'], fn))
                continue
            t = open(p, encoding='utf-8').read()
            if MARK not in t or t.count(MARK) != 1:
                probs.append('%s %s 评审名片缺失或重复' % (r['sid'], fn))
            if ('第 %d 名 / 100' % r['rank']) not in t:
                probs.append('%s %s 名次不一致' % (r['sid'], fn))
            if ('%.2f / 100' % r['avg']) not in t:
                probs.append('%s %s 均分不一致' % (r['sid'], fn))
            # 名片块内零剧透
            if MARK in t:
                card = t[t.index(MARK):t.index('<!-- 学生评审名片 END -->')]
                for w in SPOILER:
                    if w in card:
                        probs.append('%s %s 名片含剧透词「%s」' % (r['sid'], fn, w))
                        break
                # 中文检查：名片里除编号/代号/固定缩写外不应有连续拉丁字母
                body = re.sub(r'<!--[^>]*-->', '', card)          # 去掉 HTML 注释里的 START/END
                body = re.sub(r'[A-Za-z]\d{2}|s\d{2}|PM|DM', '', body)
                if re.search(r'[A-Za-z]{2,}', body):
                    probs.append('%s %s 名片含连续拉丁字母' % (r['sid'], fn))

    # 项目根产物
    for f in ['评审总榜.md', 'README.md']:
        if not os.path.exists(os.path.join(BASE, f)):
            probs.append('缺 %s' % f)
    if os.path.exists(os.path.join(BASE, '评审总榜.md')):
        t = open(os.path.join(BASE, '评审总榜.md'), encoding='utf-8').read()
        # 精确核对：每个名次+编号+剧名都要在总榜里出现（PM 的十佳表与附表都算，故按条目查而非数行数）
        for r in ranked:
            if ('| %d | %s | 《%s》' % (r['rank'], r['sid'], r['name'])) not in t:
                probs.append('评审总榜.md 缺第 %d 名 %s' % (r['rank'], r['sid']))
                break
    ip = os.path.join(BOX, '盒装本总索引.md')
    if os.path.exists(ip):
        t = open(ip, encoding='utf-8').read()
        n = len(re.findall(r'\|\s*[\d.]+\s*/\s*第\d+名\s*\|', t))
        if n != 100:
            probs.append('盒装本总索引.md 带均分/名次的行 %d（应 100）' % n)

    print('盒装本目录：%d 本' % nbox)
    if probs:
        print('硬问题：%d' % len(probs))
        for p in probs[:60]:
            print('  -', p)
        if len(probs) > 60:
            print('  ... 还有 %d 个' % (len(probs) - 60))
        sys.exit(1)
    print('硬问题：0')
    print('✅ 100 本介绍全部带评审名片、名次/均分与 JSON 一致、名片零剧透且全中文；总榜与索引齐全。')


if __name__ == '__main__':
    main()
