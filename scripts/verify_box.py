#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量生成后校验「盒装本/」下 100 本成品的完整性与质量。
必须用带 Pillow 的 bundled python 运行（系统 python 无 PIL）。

用法：
  /Users/sakuro/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3 \
      scripts/verify_box.py

检查项：
  1. 100 本目录齐全（H/T/C/O 各 25）
  2. 每本 9 类固定文件齐全：封面.png / 线索卡.png / 说明书.md /
     线索卡清单.md / 主持人手册.md / 结局卡.md / 本盒完整内容.md /
     盒面文案.md（商业化包装注入）
  3. 角色卡/*.png 与 角色剧本/*.md 数量相等，且等于该本人数（2/3/4）
  4. PNG 非空白：尺寸合规、颜色数 > 200、灰度 std > 8（用 PIL 抽样）
  5. 信息隔离：公开物料（说明书/线索卡清单/盒面文案）不得含「隐藏秘密/个人目标」
     这类只该出现在 DM 手册与角色剧本里的字样；角色剧本须含「只有你知道的秘密」
  6. 盒面文案注入覆盖 100 本
  7. 总索引存在且含 100 行表格
输出统计；有问题 exit 1。
"""
import os, re, sys, glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, '盒装本')

try:
    from PIL import Image, ImageStat
except ImportError:
    print('❌ 需要 Pillow：请用 bundled python 运行本脚本'); sys.exit(1)

VOL = [('H', '恐怖本', 25), ('T', '反转本', 25),
       ('C', '搞笑本', 25), ('O', '职场厮杀本', 25)]
FIXED = ['封面.png', '线索卡.png', '说明书.md', '线索卡清单.md',
         '主持人手册.md', '结局卡.md', '本盒完整内容.md', '盒面文案.md']

problems = []
total_boxes = total_cards = total_scripts = 0
img_checked = 0
pack_injected = 0


def png_ok(path):
    """返回 (ok, info)：尺寸>0、颜色数>200、灰度 std>8。"""
    global img_checked
    try:
        im = Image.open(path).convert('RGB')
        w, h = im.size
        small = im.resize((min(w, 160), min(h, 160)))
        colors = len(small.getcolors(maxcolors=200000) or [])
        gray = small.convert('L')
        std = ImageStat.Stat(gray).stddev[0]
        img_checked += 1
        if w < 100 or h < 100:
            return False, '%s 尺寸过小 %dx%d' % (os.path.basename(path), w, h)
        if colors <= 200:
            return False, '%s 颜色数仅 %d（疑似空白）' % (os.path.basename(path), colors)
        if std <= 8:
            return False, '%s 灰度 std=%.1f（疑似纯色）' % (os.path.basename(path), std)
        return True, '%dx%d colors=%d std=%.1f' % (w, h, colors, std)
    except Exception as e:
        return False, '%s 打不开：%s' % (os.path.basename(path), e)


def read(path):
    return open(path, encoding='utf-8').read() if os.path.exists(path) else ''


for pre, label, expect in VOL:
    dirs = sorted(glob.glob(os.path.join(OUT, '%s[0-9][0-9]_*' % pre)))
    if len(dirs) != expect:
        problems.append('%s 目录数 %d != %d' % (label, len(dirs), expect))
    for folder in dirs:
        sid = os.path.basename(folder).split('_')[0]
        total_boxes += 1
        # 2. 固定文件
        for f in FIXED:
            if not os.path.exists(os.path.join(folder, f)):
                problems.append('%s 缺 %s' % (sid, f))
        # 3. 角色卡 / 角色剧本 数量 == 人数
        cards = glob.glob(os.path.join(folder, '角色卡', '*.png'))
        scripts = glob.glob(os.path.join(folder, '角色剧本', '*.md'))
        total_cards += len(cards)
        total_scripts += len(scripts)
        # 人数从说明书或主持人手册推断
        allmd = read(os.path.join(folder, '主持人手册.md')) + read(os.path.join(folder, '说明书.md'))
        nm = re.search(r'人数：\s*(\d+)\s*人', allmd) or re.search(r'（(\d+)\s*名角色）', allmd)
        n = int(nm.group(1)) if nm else 0
        if n not in (2, 3, 4):
            problems.append('%s 人数无法判定（读到 %d）' % (sid, n))
        else:
            if len(cards) != n:
                problems.append('%s 角色卡 %d 张 != 人数 %d' % (sid, len(cards), n))
            if len(scripts) != n:
                problems.append('%s 角色剧本 %d 份 != 人数 %d' % (sid, len(scripts), n))
            if len(cards) != len(scripts):
                problems.append('%s 卡 %d / 剧本 %d 不等' % (sid, len(cards), len(scripts)))
        # 4. 图片非空白
        for p in [os.path.join(folder, '封面.png'), os.path.join(folder, '线索卡.png')] + cards:
            if os.path.exists(p):
                ok, info = png_ok(p)
                if not ok:
                    problems.append('%s %s' % (sid, info))
        # 5. 信息隔离：公开物料不得含秘密字段名
        for f in ['说明书.md', '线索卡清单.md', '盒面文案.md', '结局卡.md']:
            t = read(os.path.join(folder, f))
            for w in ['隐藏秘密', '个人目标']:
                if w in t and f != '结局卡.md':
                    # 盒面文案是给顾客看的，绝不能出现；说明书/线索清单也不该
                    problems.append('%s 公开物料 %s 含「%s」' % (sid, f, w))
        # 角色剧本须含秘密段
        for sp in scripts:
            t = read(sp)
            if '只有你知道的秘密' not in t:
                problems.append('%s 角色剧本 %s 缺秘密段' % (sid, os.path.basename(sp)))
        # 6. 包装注入
        ct = read(os.path.join(folder, '盒面文案.md'))
        if ct.strip():
            pack_injected += 1
        if '商业化包装' not in read(os.path.join(folder, '本盒完整内容.md')):
            problems.append('%s 本盒完整内容.md 未注入商业化包装' % sid)
        if '商业化包装' not in read(os.path.join(folder, '主持人手册.md')):
            problems.append('%s 主持人手册.md 未注入商业化包装' % sid)

# 7. 总索引
idx = os.path.join(OUT, '盒装本总索引.md')
if not os.path.exists(idx):
    problems.append('缺 盒装本总索引.md')
else:
    rows = len(re.findall(r'^\| [HTCO]\d{2} \|', read(idx), re.M))
    if rows != 100:
        problems.append('总索引表格行 %d != 100' % rows)

print('=' * 60)
print('盒装本总数：%d（期望 100）' % total_boxes)
print('角色卡 PNG：%d 张｜角色剧本 MD：%d 份' % (total_cards, total_scripts))
print('PNG 非空白校验：%d 张' % img_checked)
print('商业化包装注入：%d 本（期望 100）' % pack_injected)
print('硬问题：%d' % len(problems))
print('=' * 60)
for p in problems:
    print('  ✗ ' + p)
if not problems:
    print('✅ 100 本盒装本物料齐全、图片真实、信息隔离、包装全覆盖。')
sys.exit(1 if problems else 0)
