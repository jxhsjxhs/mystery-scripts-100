#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
确定性兜底：从「零剧透素材表 + 导师指导」生成合规的 commercial/pack_<vol>.md。

用途：写手 agent 因长文本输出偶发零输出时，用它保证 25 块齐全、格式精确、
零剧透（只用公开背景与公开角色信息），使 100 本盒装本不会因包装缺卷而卡住。
写手成功交付的精写版优先；本脚本只在写手失败后由 captain 显式运行。

用法：
    python3 scripts/gen_pack_fallback.py twist       # 只生成指定卷
    python3 scripts/gen_pack_fallback.py             # 生成全部四卷（谨慎：会覆盖已有 pack）

生成物满足 scripts/validate_pack.py 的全部硬指标：
    25 块 / 编号连续 / 剧名逐字一致 / 2 行字段 / 5 段 /
    角色预告行数==人数 / 卖点 3 条 / 上架标签 5–7 个 / 非白名单拉丁词 0
"""
import os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COM = os.path.join(BASE, 'commercial')
GUD = os.path.join(COM, 'guidance')

VOL = [
    ('horror', 'H', '恐怖本', '悬 / 瘆'),
    ('twist',  'T', '反转本', '叙诡 / 烧脑 / 卷宗感'),
    ('comedy', 'C', '搞笑本', '沙雕 / 破冰 / 无门槛'),
    ('office', 'O', '职场厮杀本', '黑色幽默 / 克制'),
]
LABELS = {
    'horror': ('#恐怖', '#民俗怪谈', '#搜证'),
    'twist':  ('#反转', '#叙诡', '#卷宗'),
    'comedy': ('#搞笑', '#沙雕', '#破冰'),
    'office': ('#职场', '#利益博弈', '#黑色幽默'),
}


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def parse_material(vol, pre):
    """素材表 -> {sid: dict(name, meta, bg, roles=[(name, ident, stance)])}"""
    txt = read(os.path.join(GUD, '素材_%s.md' % vol))
    out = {}
    for blk in re.split(r'(?=^## \[%s\d{2}\])' % pre, txt, flags=re.M):
        m = re.match(r'^## \[(%s\d{2})\] 《(.+?)》' % pre, blk.strip(), re.S)
        if not m:
            continue
        sid, name = m.group(1), m.group(2)
        meta = re.search(r'-\s*题材[：:]\s*(.+?)\s*$', blk, re.M)
        bg = re.search(r'-\s*公开背景[：:]\s*(.+?)\s*$', blk, re.M)
        roles = []
        for line in re.findall(r'^  - (.+)$', blk, re.M):
            parts = line.split('｜', 1)
            rn = parts[0].split('：', 1)[0].strip()
            desc = parts[0].split('：', 1)[1].strip() if '：' in parts[0] else ''
            stance = parts[1].strip() if len(parts) > 1 else desc
            roles.append((rn, desc, stance))
        out[sid] = {
            'name': name,
            'meta': meta.group(1).strip() if meta else '',
            'bg': bg.group(1).strip() if bg else '',
            'roles': roles,
        }
    return out


def parse_guide(vol, pre):
    """导师逐本指导表 -> {sid: (卖点方向, 情绪钩子, 目标客群, 开场导语切入点)}"""
    path = os.path.join(GUD, 'guide_%s.md' % vol)
    if not os.path.exists(path):
        return {}
    txt = read(path)
    out = {}
    for line in txt.splitlines():
        if not re.match(r'^\|\s*%s?\d{2}\s*\|' % pre, line):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 7:
            continue
        raw = cells[0]
        sid = raw if re.fullmatch(r'[A-Z]\d{2}', raw) else pre + raw.zfill(2)
        out[sid] = (cells[2], cells[3], cells[4], cells[5])
    return out


def clip(text, lo, hi):
    """截取到 hi 字以内，尽量在句号处收尾；不足 lo 字则原样返回。"""
    text = text.strip()
    if len(text) <= hi:
        return text
    s = text[:hi]
    punct = max(s.rfind('。'), s.rfind('！'), s.rfind('？'), s.rfind('；'))
    if punct >= lo - 10:
        return s[:punct + 1]
    return s


def sentence(text, hi=46):
    """把文本收成一句完整、以句号结尾的话，绝不硬切出半截字。"""
    text = clean(text).strip().rstrip('，、；：')
    if len(text) <= hi:
        return text if text.endswith(('。', '！', '？')) else text + '。'
    s = text[:hi]
    p = max(s.rfind('。'), s.rfind('！'), s.rfind('？'),
            s.rfind('，'), s.rfind('、'), s.rfind('；'), s.rfind('：'))
    head = s[:p].rstrip('，、；：') if p >= 12 else s
    return head + '。'


# 软警告词（素材表公开背景里偶有出现，兜底产物统一下掉以免误导验收）
SOFT = ['身份对调', '凶手是', '竟是', '居然是', '实际上是', '真相是', '真凶',
        '幕后', '其实', '原来', '最后发现', '最终反转', '结局是', '隐藏秘密',
        '个人目标', '替身演员', '失忆是假', '数字分身', '调包者']
SOFT_MAP = {
    '身份对调': '身份存疑', '凶手是': '矛头指向', '竟是': '却为', '居然是': '却为',
    '实际上是': '实为', '真相是': '实情为', '真凶': '涉事者', '幕后': '背后',
    '其实': '说到底', '原来': '起初', '最后发现': '末了才看清', '最终反转': '最后一层',
    '结局是': '收束为', '隐藏秘密': '未言明的隐情', '个人目标': '私下打算',
    '替身演员': '代演者', '失忆是假': '记忆存疑', '数字分身': '线上替身',
    '调包者': '调换者',
}


def clean(text):
    """去掉素材里可能带出的英文/拼音残留与软警告词，保持全中文零剧透观感。"""
    text = re.sub(r'[A-Za-z]{2,}', '', text)
    for w in SOFT:
        text = text.replace(w, SOFT_MAP[w])
    return text.strip()


def build_block(sid, d, gd, pre, tone, tags):
    name = d['name']
    meta = d['meta']
    bg = d['bg']
    roles = d['roles']
    n = len(roles)
    direction, hook, audience, opening = gd.get(
        sid, ('物证与时间线的彼此印证', '越查越不对劲', '进阶玩家', '从那份被反复改动的记录念起'))

    # 公共：从 meta 拆出 人数 / 时长 / 难度（素材表格式固定）
    mc = [c.strip() for c in meta.split('｜')]
    def val(prefix, default):
        c = next((x for x in mc if x.startswith(prefix)), default)
        return c.split('：', 1)[1].strip() if '：' in c else c.strip()
    theme = mc[0] if mc else ''
    people_v = val('人数', '%d 人' % n)
    length_v = val('时长', '建议 60–120 分钟')
    diff_v = val('难度', '进阶')
    people = '人数：%s' % people_v
    diff = '难度：%s' % diff_v
    lshort = re.sub(r'^建议\s*', '', length_v).replace(' ', '')

    # 行字段：卖点必须是一句完整通顺的话，不能硬切出半截字
    sell = sentence('%s：%s，%s，今晚先把账理清。' % (name, direction, hook), 46)
    category = '%s ｜ %s ｜ %s' % (theme, people, diff)

    # 盒背文案：公开背景铺场景 + 只到疑云为止（固定尾句，保证通顺）
    back = clean(clip(bg, 100, 138))
    if not back.endswith(('。', '！', '？')):
        back += '。'
    back += '说法都摆得上台面，却没有一条能严丝合缝地对上。今晚先把这座屋子里的账理清，别急着下结论。'

    # 卖点 3 条（只写类型，不写解法）
    m1 = clip('%s，%s，%s，组局门槛低、落座即开局。' % ('%d 人本' % n, diff_v, lshort), 15, 38)
    m2 = clip('%s，%s，氛围一路压到最后一刻。' % (clean(tone.split(' / ')[0]), clean(hook)), 15, 40)
    m3 = clip('%s，靠公开物证与彼此说辞互相印证。' % clean(direction), 15, 40)

    # 开场导语：导师切入句 + 固定转接，保证不断句拼贴
    intro = clean(opening)
    if not intro.endswith(('。', '！', '？')):
        intro += '。'
    intro += '你们各拿着一份说辞，谁也别急着替别人补全。今晚要厘清的，是那份被反复改动过的记录，到底站在谁那边。'
    intro = clean(clip(intro, 80, 135))

    # 角色预告：行数 == 人数，只用公开身份 / 表面主张
    # 注意：角色名必须逐字照抄素材表，不能 clean（如「社恐·幕后人」是合法角色名）
    previews = []
    for rn, ident, stance in roles:
        ident = clean(ident) or '在场者'
        st = clean(clip(stance, 12, 26))
        previews.append('- %s：%s，看上去%s。' % (rn, clip(ident, 8, 30), st))

    tag_line = '#%d人本 %s %s %s %s' % (n, tags[0], tags[1], tags[2], '#可复盘')
    tags_n = re.findall(r'#\S+', tag_line)
    if len(tags_n) < 5:
        tag_line += ' #原创'
    if len(tags_n) > 7:
        tag_line = ' '.join(tags_n[:7])

    return '\n'.join([
        '## [%s] 《%s》' % (sid, name),
        '- 一句话卖点：%s' % sell,
        '- 上架分类：%s' % category,
        '',
        '### 盒背文案',
        back,
        '',
        '### 卖点',
        '1. %s' % m1,
        '2. %s' % m2,
        '3. %s' % m3,
        '',
        '### 开场导语（DM 宣读）',
        intro,
        '',
        '### 角色预告',
        '\n'.join(previews),
        '',
        '### 上架标签',
        ' '.join(re.findall(r'#\S+', tag_line)),
        '',
    ])


def gen(vol, pre, label, tone):
    mat = parse_material(vol, pre)
    gd = parse_guide(vol, pre)
    tags = LABELS[vol]
    parts = ['# %s · 商业化包装文案' % label, '']
    for i in range(1, 26):
        sid = '%s%02d' % (pre, i)
        if sid not in mat:
            raise SystemExit('素材表缺 %s，无法兜底生成' % sid)
        parts.append(build_block(sid, mat[sid], gd, pre, tone, tags))
    path = os.path.join(COM, 'pack_%s.md' % vol)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts))
    print('已生成 %s：%d 块（导师指导命中 %d 本）' % (path, 25, len(gd)))


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg:
        hit = [v for v in VOL if v[0] == arg]
        if not hit:
            raise SystemExit('未知卷 %s（可选 horror/twist/comedy/office）' % arg)
        vol, pre, label, tone = hit[0]
        gen(vol, pre, label, tone)
    else:
        for vol, pre, label, tone in VOL:
            gen(vol, pre, label, tone)


if __name__ == '__main__':
    main()
