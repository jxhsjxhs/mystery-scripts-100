#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 4 位写手的修订补丁套用到初稿整卷 -> 生成各卷终稿文件。

输入（唯一权威源）：drafts/<vol>_draft.md
补丁：drafts/patches/<vol>.patch.md（格式见 review/补丁格式.md）
输出：horror/恐怖本25套.md 等（每卷一个 .md，供 validate.py final / combine.py 读取）

补丁块标题 = `## [编号] 字段名`，字段名可为：
  行字段  题材 / 人数 / 时长 / 难度      -> 整行替换为 `- 字段：新值`
  段字段  背景/角色/核心诡计/关键线索/流程/反转点/真相/主持人 -> 整段正文替换
  替换    -> 正文每行 `旧串 => 新串`，对该套整块做字面替换（按补丁行顺序，越具体越靠前）
"""
import re, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOL = [
    ('horror', 'H', '恐怖本25套.md'),
    ('twist',  'T', '反转本25套.md'),
    ('comedy', 'C', '搞笑本25套.md'),
    ('office', 'O', '职场厮杀本25套.md'),
]
# 注意：长字段名放前面，避免 `反转点` 被短字段抢匹配；`替换` 单独处理
FIELDS = ['替换', '核心诡计', '关键线索', '主持人', '反转点', '背景', '角色',
          '流程', '真相', '题材', '人数', '时长', '难度']

SECTION_HEAD = {
    '背景':     r'###\s*背景[^\n]*\n',
    '角色':     r'###\s*角色[^\n]*\n',
    '核心诡计': r'###\s*核心诡计[^\n]*\n',
    '关键线索': r'###\s*关键线索[^\n]*\n',
    '流程':     r'###\s*流程[^\n]*\n',
    '反转点':   r'###\s*反转点[^\n]*\n',
    '真相':     r'###\s*真相[^\n]*\n',
    '主持人':   r'###\s*主持人[^\n]*\n',
}
LINE_FIELDS = {'题材', '人数', '时长', '难度'}


def load_patches(path):
    text = open(path, encoding='utf-8').read()
    parts = re.split(r'(?=^##\s*\[[A-Z]\d{2}\])', text, flags=re.M)
    patches = {}
    for p in parts:
        m = re.match(r'^##\s*\[([A-Z]\d{2})\]\s*(\S+)[^\n]*\n(.*)', p, flags=re.S)
        if not m:
            continue
        sid, ftag, body = m.group(1), m.group(2), m.group(3).strip()
        fm = re.search('|'.join(FIELDS), ftag)
        if not fm:
            print(f'  ! 无法识别字段「{ftag}」(编号 {sid})，跳过')
            continue
        patches.setdefault(sid, []).append((fm.group(0), body))
    return patches


def apply_to_script(block, sid, fixes):
    for field, body in fixes:
        # 替换：字面词替换，按补丁行顺序执行（写手须把最具体的放在最前）
        if field == '替换':
            for line in body.splitlines():
                if '=>' in line:
                    old, new = line.split('=>', 1)
                    old, new = old.strip(), new.strip()
                    if old:
                        block = block.replace(old, new)
            continue

        if field in LINE_FIELDS:
            # 容错：写手可能误带反引号、或误写完整 `- 题材：xxx`
            b = body.strip().strip('`').strip()
            first = b.splitlines()[0].strip() if b else ''
            first = re.sub(r'^-\s*' + re.escape(field) + r'[：:]\s*', '', first)
            new = f'- {field}：{first}'
            block, n = re.subn(r'^\s*-\s*' + field + r'[：:].*$',
                               lambda m, v=new: v, block, count=1, flags=re.M)
            if n == 0:
                print(f'  ! {sid} 找不到行字段 {field}')
        else:
            head = SECTION_HEAD[field]
            # 容错：写手若把 `### 段标题` 也写进正文，去掉它避免重复标题
            body_clean = re.sub(r'^###[^\n]*\n', '', body.strip()).strip()
            pat = r'(' + head + r')(.*?)(?=\n###|\Z)'
            block, n = re.subn(pat,
                               lambda m, v=body_clean: m.group(1) + v + '\n',
                               block, count=1, flags=re.S)
            if n == 0:
                print(f'  ! {sid} 找不到段 {field}')
    return block


def main():
    total_changed = 0
    for vol, pre, fname in VOL:
        base_path = os.path.join(BASE, 'drafts', 'patches', vol + '.patch.md')
        soft_path = os.path.join(BASE, 'drafts', 'patches', vol + '.soft.md')
        draft_path = os.path.join(BASE, 'drafts', vol + '_draft.md')
        if not os.path.exists(base_path):
            print(f'缺基础补丁: {base_path} —— 跳过 {vol}')
            continue
        # 合并两类补丁：基础硬项(题材/背景，captain 逐字照抄审核意见书 2.1/2.2)
        # + 写手软项(第三节编号级编辑意见，<vol>.soft.md)。基础在前、软项在后。
        patches = {}
        for pf in (base_path, soft_path):
            if os.path.exists(pf):
                for sid, fixes in load_patches(pf).items():
                    patches.setdefault(sid, []).extend(fixes)
        text = open(draft_path, encoding='utf-8').read()
        parts = re.split(r'(?=^## \[' + pre + r'\d{2}\] )', text, flags=re.M)
        out, changed = [], set()
        for p in parts:
            m = re.match(r'^## \[' + pre + r'\d{2}\] ', p)
            if m:
                sid = re.match(r'^## \[(' + pre + r'\d{2})\] ', p).group(1)
                if sid in patches:
                    out.append(apply_to_script(p, sid, patches[sid]))
                    changed.add(sid)
                else:
                    out.append(p)
            else:
                out.append(p)
        final = ''.join(out)
        # 文件头「初稿」->「终稿」
        final = final.replace('/ 初稿）', '/ 终稿）').replace('· 初稿）', '· 终稿）')
        os.makedirs(os.path.join(BASE, vol), exist_ok=True)
        dest = os.path.join(BASE, vol, fname)
        open(dest, 'w', encoding='utf-8').write(final)
        total_changed += len(changed)
        print(f'{vol}: 改动 {len(changed)} 套 -> {os.path.relpath(dest, BASE)}')
        for sid in sorted(patches):
            if sid not in changed:
                print(f'  ! 补丁编号 {sid} 未匹配到正文')
    print(f'合计改动 {total_changed} 套')


if __name__ == '__main__':
    main()
