#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汇总 8 位学生评审的 100 本评分，校验 → 算 8 人均分 → 降序排名。
产出：eval/评分汇总.json、eval/总榜.md、eval/pm_input.md
用法：python3 scripts/aggregate_scores.py
      python3 scripts/aggregate_scores.py --check   # 只校验不写
"""
import re, os, json, sys, glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SC = os.path.join(BASE, 'eval', 'scores')
EV = os.path.join(BASE, 'eval')

STUDENTS = [
    ('s01', '林砚舟', '中文系·文学社社长', '文笔、意象、氛围文学性'),
    ('s02', '周予安', '数学系·推理社骨干', '诡计严谨、线索可回看、逻辑闭环'),
    ('s03', '苏晚棠', '戏剧学院·话剧社导演', '角色立体度、可表演性、开场代入'),
    ('s04', '陈知微', '心理系研一', '人物动机、隐藏立场、情感张力'),
    ('s05', '赵一诺', '学生会·组局达人', '好不好组、人数门槛、时长、破冰'),
    ('s06', '何小满', '美院·插画氛围控', '画面感、题材辨识度、出片率'),
    ('s07', '钱多多', '脱口秀社团·气氛组', '笑点、破冰、尬不尬'),
    ('s08', '郑知行', '经管学院·实习派', '现实共鸣、职场逻辑、黑色幽默分寸'),
]

VOL = [('horror', 'H', '恐怖本'), ('twist', 'T', '反转本'),
       ('comedy', 'C', '搞笑本'), ('office', 'O', '职场厮杀本')]
VMAP = {'H': '恐怖本', 'T': '反转本', 'C': '搞笑本', 'O': '职场厮杀本'}

SPOILER = ['真相', '真凶', '凶手', '谜底', '解法', '幕后黑手', '其实是', '原来是',
           '竟是', '居然是', '隐藏秘密', '个人目标', '身份对调', '数字分身',
           '替身演员', '失忆是假', '调包者', '结局是']


def name_map():
    nm = {}
    for vol, pre, label in VOL:
        p = os.path.join(EV, 'mat_%s.md' % vol)
        for line in open(p, encoding='utf-8'):
            m = re.match(r'^## \[([A-Z]\d{2})\] 《(.+?)》', line)
            if m:
                nm[m.group(1)] = m.group(2)
    return nm


def expected_ids():
    ids = []
    for vol, pre, label in VOL:
        ids += ['%s%02d' % (pre, i) for i in range(1, 26)]
    return ids


def check_all():
    problems = []
    data = {}   # sid -> {sNN:(score,comment)}
    ALL = expected_ids()
    for code, sname, _, _ in STUDENTS:
        for vol, pre, label in VOL:
            path = os.path.join(SC, '%s_%s.md' % (code, pre))
            if not os.path.exists(path):
                problems.append('缺文件 %s' % os.path.relpath(path, BASE))
                continue
            lines = [l for l in open(path, encoding='utf-8').read().splitlines() if l.strip()]
            if len(lines) != 25:
                problems.append('%s 行数 %d != 25' % (os.path.relpath(path, BASE), len(lines)))
            seen = []
            for ln in lines:
                parts = ln.split('|')
                if len(parts) != 3:
                    problems.append('%s 格式错：%s' % (os.path.relpath(path, BASE), ln[:40]))
                    continue
                sid, sc, cm = parts[0].strip(), parts[1].strip(), parts[2].strip()
                seen.append(sid)
                if not re.match(r'^%s\d{2}$' % pre, sid):
                    problems.append('%s 编号错：%s' % (os.path.relpath(path, BASE), sid))
                if not re.match(r'^\d+$', sc) or not (60 <= int(sc) <= 98):
                    problems.append('%s 分数错：%s %s' % (os.path.relpath(path, BASE), sid, sc))
                if not cm or len(cm) > 24:
                    problems.append('%s 评语长度：%s %d字' % (os.path.relpath(path, BASE), sid, len(cm)))
                for w in SPOILER:
                    if w in cm:
                        problems.append('%s 剧透词「%s」：%s' % (os.path.relpath(path, BASE), w, sid))
                if re.search(r'[A-Za-z]', cm):
                    problems.append('%s 评语含拉丁字母：%s' % (os.path.relpath(path, BASE), sid))
                if sid in ALL:
                    data.setdefault(sid, {})[code] = (int(sc) if re.match(r'^\d+$', sc) else 60, cm)
            exp = ['%s%02d' % (pre, i) for i in range(1, 26)]
            if sorted(seen) != sorted(exp):
                miss = set(exp) - set(seen)
                dup = [x for x in set(seen) if seen.count(x) > 1]
                if miss:
                    problems.append('%s 缺编号 %s' % (os.path.relpath(path, BASE), ','.join(sorted(miss))))
                if dup:
                    problems.append('%s 重编号 %s' % (os.path.relpath(path, BASE), ','.join(dup)))
    # 每本必须集齐 8 人
    for sid in ALL:
        if len(data.get(sid, {})) != 8:
            problems.append('%s 只有 %d 位评审打分' % (sid, len(data.get(sid, {}))))
    return problems, data, ALL


def build(data, ALL, NM):
    rows = []
    for sid in ALL:
        scores = [data[sid][c][0] for c, _, _, _ in STUDENTS]
        avg = round(sum(scores) / 8.0, 2)
        rows.append({
            'sid': sid, 'name': NM.get(sid, sid), 'vol': VMAP[sid[0]],
            'scores': {c: data[sid][c][0] for c, _, _, _ in STUDENTS},
            'comments': {c: data[sid][c][1] for c, _, _, _ in STUDENTS},
            'avg': avg, 'total': sum(scores),
            'high': max(scores), 'low': min(scores),
        })
    # 降序：均分 → 总分 → 编号（确定性）
    ranked = sorted(rows, key=lambda r: (-r['avg'], -r['total'], r['sid']))
    for i, r in enumerate(ranked, 1):
        r['rank'] = i
    # 分卷名次
    for vol, pre, label in VOL:
        sub = [r for r in ranked if r['sid'][0] == pre]
        for i, r in enumerate(sub, 1):
            r['vol_rank'] = i
    return ranked


def vol_stats(ranked):
    out = {}
    for vol, pre, label in VOL:
        sub = [r for r in ranked if r['sid'][0] == pre]
        avgs = [r['avg'] for r in sub]
        out[label] = {
            'mean': round(sum(avgs) / len(avgs), 2),
            'top10': sum(1 for r in sub if r['rank'] <= 10),
            'top25': sum(1 for r in sub if r['rank'] <= 25),
            'best': sub[0]['sid'] if sub else '',
            'best_name': sub[0]['name'] if sub else '',
            'best_avg': sub[0]['avg'] if sub else 0,
        }
    return out


def main():
    check_only = '--check' in sys.argv
    problems, data, ALL = check_all()
    NM = name_map()
    if problems:
        print('校验发现 %d 个问题：' % len(problems))
        for p in problems[:80]:
            print('  -', p)
        if len(problems) > 80:
            print('  ... 还有 %d 个' % (len(problems) - 80))
        sys.exit(1)
    ranked = build(data, ALL, NM)
    vs = vol_stats(ranked)
    if check_only:
        print('校验通过：8 位学生 × 4 卷 × 25 本 = 800 条评分齐全，格式/分数/剧透/中文全部合规。')
        return
    # JSON
    payload = {
        'students': [{'code': c, 'name': n, 'role': r, 'focus': f}
                     for c, n, r, f in STUDENTS],
        'vol_stats': vs,
        'ranking': ranked,
    }
    with open(os.path.join(EV, '评分汇总.json'), 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    # 总榜.md
    lines = ['# 百局 · 100 本剧本杀学生评审总榜', '',
             '> 8 位人设各异的学生评审各自独立打分（60–98），按 8 人均分从高到低排名。',
             '> 完整评语与 PM 总结见 [PM评审总结.md](PM评审总结.md)。', '',
             '| 名次 | 编号 | 剧名 | 卷 | 均分 | 分卷名次 |',
             '| --- | --- | --- | --- | --- | --- |']
    for r in ranked:
        lines.append('| %d | %s | 《%s》 | %s | %.2f | %d |'
                     % (r['rank'], r['sid'], r['name'], r['vol'], r['avg'], r['vol_rank']))
    open(os.path.join(EV, '总榜.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    # pm_input.md
    p = ['# PM 汇总输入（由 aggregate_scores.py 机器生成，分数与名次不得改动）', '',
         '## 一、评审团（8 位学生，人设互不相同）', '']
    for c, n, r, f in STUDENTS:
        p.append('- %s %s（%s）：最看重 %s。' % (c, n, r, f))
    p += ['', '## 二、总体分布', '',
          '- 100 本，8 人独立打分，共 800 条有效评分。',
          '- 全榜最高均分：%.2f（%s 《%s》）。' % (ranked[0]['avg'], ranked[0]['sid'], ranked[0]['name']),
          '- 全榜最低均分：%.2f（%s 《%s》）。' % (ranked[-1]['avg'], ranked[-1]['sid'], ranked[-1]['name']),
          '- 全榜平均：%.2f。' % round(sum(r['avg'] for r in ranked) / 100, 2), '',
          '## 三、分卷统计', '',
          '| 卷 | 平均均分 | 进前十 | 进前二十五 | 卷内第一 |',
          '| --- | --- | --- | --- | --- |']
    for label, s in vs.items():
        p.append('| %s | %.2f | %d | %d | %s 《%s》 %.2f |'
                 % (label, s['mean'], s['top10'], s['top25'], s['best'], s['best_name'], s['best_avg']))
    p += ['', '## 四、TOP 10（写「十佳逐本荐语」用，编号/剧名/名次必须逐字照抄）', '',
          '| 名次 | 编号 | 剧名 | 卷 | 均分 |',
          '| --- | --- | --- | --- | --- |']
    for r in ranked[:10]:
        p.append('| %d | %s | 《%s》 | %s | %.2f |' % (r['rank'], r['sid'], r['name'], r['vol'], r['avg']))
    p += ['', '## 五、BOTTOM 10（仅供你写总览时参考，不要写进总结里点名）', '']
    for r in ranked[-10:]:
        p.append('- 第 %d 名 %s 《%s》 %.2f' % (r['rank'], r['sid'], r['name'], r['avg']))
    p += ['', '## 六、全体名次表（写「五、全体名次表」用，100 行，顺序/编号/剧名/均分逐字照抄）', '',
          '| 名次 | 编号 | 剧名 | 卷 | 均分 | 八人分数 |',
          '| --- | --- | --- | --- | --- | --- |']
    for r in ranked:
        sc = '/'.join(str(r['scores'][c]) for c, _, _, _ in STUDENTS)
        p.append('| %d | %s | 《%s》 | %s | %.2f | %s |'
                 % (r['rank'], r['sid'], r['name'], r['vol'], r['avg'], sc))
    p += ['', '## 七、八人评语抽样（供你把握各家口味，零剧透）', '']
    for r in ranked[:5]:
        for c, _, _, _ in STUDENTS[:3]:
            p.append('- %s %s：%s' % (r['sid'], c, data[r['sid']][c][1]))
    open(os.path.join(EV, 'pm_input.md'), 'w', encoding='utf-8').write('\n'.join(p) + '\n')
    print('校验通过：800 条评分齐全、格式/分数/剧透/中文全部合规。')
    print('产出：eval/评分汇总.json、eval/总榜.md、eval/pm_input.md')
    print('TOP5：')
    for r in ranked[:5]:
        print('  %2d. %s 《%s》 %.2f' % (r['rank'], r['sid'], r['name'], r['avg']))
    print('BOTTOM3：')
    for r in ranked[-3:]:
        print('  %2d. %s 《%s》 %.2f' % (r['rank'], r['sid'], r['name'], r['avg']))


if __name__ == '__main__':
    main()
