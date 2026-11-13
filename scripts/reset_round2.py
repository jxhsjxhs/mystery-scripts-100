#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二轮评审启动前：归档第一轮评分与结论，清空 eval/scores/ 以待 8 位学生重写。

为什么必须清空：若某位学生 agent 整组零输出，残留的第一轮 sNN_*.md 会被
aggregate_scores.py 当成第二轮数据混算（第一轮就吃过 s08 中间态的竞态亏）。
清空后「缺文件」= 明确的失败信号，可用确定性兜底补齐或重派。

幂等：已归档则不重复覆盖。
用法：python3 scripts/reset_round2.py
"""
import os, glob, shutil

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL = os.path.join(BASE, 'eval')
SCORES = os.path.join(EVAL, 'scores')
ARCH = os.path.join(EVAL, 'round1')


def main():
    os.makedirs(SCORES, exist_ok=True)
    if not os.path.exists(ARCH):
        os.makedirs(ARCH)
    # 1) 归档第一轮评分原件
    n_scores = 0
    for p in sorted(glob.glob(os.path.join(SCORES, 's*.md'))):
        dst = os.path.join(ARCH, 'scores_' + os.path.basename(p))
        if not os.path.exists(dst):
            shutil.copy2(p, dst)
        n_scores += 1
    # 2) 归档第一轮聚合结论
    kept = []
    for name in ['评分汇总.json', '总榜.md', 'pm_input.md', 'PM评审总结.md']:
        p = os.path.join(EVAL, name)
        if os.path.exists(p):
            dst = os.path.join(ARCH, name)
            if not os.path.exists(dst):
                shutil.copy2(p, dst)
            kept.append(name)
    # 3) 清空 scores/ 下的评分文件（保留目录本身与其它文件）
    removed = 0
    for p in sorted(glob.glob(os.path.join(SCORES, 's[0-9][0-9]_*.md'))):
        os.remove(p)
        removed += 1
    left = sorted(os.path.basename(x) for x in glob.glob(os.path.join(SCORES, '*')) if os.path.isfile(x))
    print('第一轮评分归档：%d 份 -> eval/round1/scores_sNN_*.md' % n_scores)
    print('第一轮结论归档：%s -> eval/round1/' % ('、'.join(kept) if kept else '（无）'))
    print('已清空第二轮评分文件：%d 份' % removed)
    print('eval/scores/ 剩余：%s' % (left if left else '空（等待 8 位学生重写）'))


if __name__ == '__main__':
    main()
