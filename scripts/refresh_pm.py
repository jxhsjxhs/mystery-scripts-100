#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 eval/PM评审总结.md 的「数据部分」同步到权威 eval/评分汇总.json，
保留 PM agent 手写的散文、总荐语、十佳荐语、分卷观察语气与选本建议。

用法：python3 scripts/refresh_pm.py
幂等：重复运行产出逐字节不变（表格按 JSON 重建，标题行严格单行匹配）。

通用化说明（第二轮升级后重写）：
  不再写死任何旧数字（72.75 / 81.50 / 81.29 …），一律用正则匹配「数字」后
  替换为当前 JSON 的值；十佳表按当前 TOP10 重建，任何新进榜本若缺手写荐语
  则用通用荐语兜底。因此无论本轮名次怎么整体变动都能收口。
"""
import json, re, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(BASE, 'eval')


def main():
    payload = json.load(open(os.path.join(EV, '评分汇总.json'), encoding='utf-8'))
    ranked = payload['ranking']
    avg_all = round(sum(r['avg'] for r in ranked) / 100, 2)
    hi, lo = ranked[0]['avg'], ranked[-1]['avg']

    def vmean(pre):
        sub = [r for r in ranked if r['sid'].startswith(pre)]
        return round(sum(r['avg'] for r in sub) / len(sub), 2)

    vh, vt, vc, vo = vmean('H'), vmean('T'), vmean('C'), vmean('O')

    p = open(os.path.join(EV, 'PM评审总结.md'), encoding='utf-8').read()

    # 一、总览 / 三、分卷观察：把散文里出现的「任意旧数字」按语义替换成当前值
    def num(sub, pattern, fmt):
        """把 pattern 中捕获组（数字）替换为 fmt 生成的字符串。"""
        return re.sub(pattern, lambda m: fmt(m), sub)

    def fix_prose(seg):
        seg = re.sub(r'(最低均分\s*)\d+\.\d+',
                     lambda m: m.group(1) + '%.2f' % lo, seg)
        seg = re.sub(r'(全榜平均(?:落在|为|是)?\s*)\d+\.\d+',
                     lambda m: m.group(1) + '%.2f' % avg_all, seg)
        seg = re.sub(r'(恐怖本\s*)\d+\.\d+(、反转本\s*)\d+\.\d+',
                     lambda m: m.group(1) + '%.2f' % vh + m.group(2) + '%.2f' % vt, seg)
        seg = re.sub(r'(恐怖本平均均分\s*)\d+\.\d+',
                     lambda m: m.group(1) + '%.2f' % vh, seg)
        seg = re.sub(r'(反转本平均均分\s*)\d+\.\d+',
                     lambda m: m.group(1) + '%.2f' % vt, seg)
        seg = re.sub(r'(搞笑本平均均分\s*)\d+\.\d+',
                     lambda m: m.group(1) + '%.2f' % vc, seg)
        seg = re.sub(r'(职场厮杀本平均均分\s*)\d+\.\d+',
                     lambda m: m.group(1) + '%.2f' % vo, seg)
        return seg

    for title in ['一、评审方法与总览', '三、分卷观察']:
        m = re.search(r'(##[^\n]*%s[^\n]*\n)(.*?)(?=\n##|\Z)' % re.escape(title), p, re.S)
        if m:
            body = m.group(2).strip('\n')
            p = p[:m.start(2)] + '\n' + fix_prose(body).strip('\n') + '\n' + p[m.end(2):]

    # 二、十佳逐本荐语：按当前权威 TOP10 重建，保留同名次/同编号的手写荐语
    top10 = ranked[:10]
    m = re.search(r'(##[^\n]*二、十佳逐本荐语[^\n]*\n)(.*?)(?=\n##|\Z)', p, re.S)
    if m:
        seg = m.group(2)
        old_praise = {}
        for l in seg.splitlines():
            mm = re.match(r'^\|\s*(\d+)\s*\|\s*([A-Z]\d{2})\s*\|\s*《(.+?)》\s*\|\s*(.+?)\s*\|?\s*$', l)
            if mm:
                old_praise[mm.group(2)] = mm.group(4)
        header = ['| 名次 | 编号 | 剧名 | PM 荐语 |', '| --- | --- | --- | --- |']
        rows = []
        for i, r in enumerate(top10, 1):
            praise = old_praise.get(r['sid'])
            if not praise:
                praise = '《%s》一局一世界，围坐即开演，值得先翻这一本。' % r['name']
            rows.append('| %d | %s | 《%s》 | %s |' % (i, r['sid'], r['name'], praise))
        block = '\n' + '\n'.join(header + rows) + '\n'
        p = p[:m.start(2)] + block + p[m.end(2):]

    # 五、全体名次表：整节按权威 100 行重建（校验器逐行比对 JSON 的依据）
    m = re.search(r'##[^\n]*五、全体名次表[^\n]*\n', p)
    if m:
        header = '| 名次 | 编号 | 剧名 | 卷 | 均分 |\n| --- | --- | --- | --- | --- |\n'
        rows = '\n'.join('| %d | %s | 《%s》 | %s | %.2f |' %
                         (r['rank'], r['sid'], r['name'], r['vol'], r['avg']) for r in ranked)
        p = p[:m.end()] + '\n' + header + rows + '\n'

    open(os.path.join(EV, 'PM评审总结.md'), 'w', encoding='utf-8').write(p)
    print('PM 总结已同步权威数据：最高 %.2f / 最低 %.2f / 全榜平均 %.2f' % (hi, lo, avg_all))
    print('四卷均分：恐怖 %.2f / 反转 %.2f / 搞笑 %.2f / 职场 %.2f' % (vh, vt, vc, vo))
    print('十佳第 10 名：%s《%s》 %.2f；第五节名次表 %d 行' %
          (top10[9]['sid'], top10[9]['name'], top10[9]['avg'], len(ranked)))


if __name__ == '__main__':
    main()
