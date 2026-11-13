#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 4 卷终稿（100 套设定稿）展开成「可直接开本 / 可直接商业化」的盒装本成品包。
每本一个文件夹，含：
  封面.png              真实绘制的盒绘封面
  角色卡/<角色>.png      每个角色一张（姓名 / 身份 / 公开主张 / 你的任务），不含隐藏秘密
  线索卡.png            一本一张线索卡组图（全部物证）
  说明书.md             玩家/店家通用规则说明
  角色剧本/<角色>.md    第一人称角色剧本（信息隔离，仅发该玩家）
  线索卡清单.md         编号物证 + 揭示时机
  主持人手册.md         DM 专用：发本顺序 / 三幕流程 / 真相 / 结局 / 节奏
  结局卡.md             可念读的主/分支结局
  盒面文案.md           宣传语 / 卖点 / 开场导语（由 8 个 agent 的商业化包装注入，无剧透）
  本盒完整内容.md        GM 总览合订（含商业化包装）
用法：
  python3 scripts/build_box.py          # 全量 100 本
  python3 scripts/build_box.py H01      # 只生成 1 本（样板）
依赖：Pillow（若系统 python 无 Pillow，请用带 Pillow 的解释器执行，见 README.md）
"""
import re, os, glob, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, '盒装本')
FONT_B = '/System/Library/Fonts/STHeiti Medium.ttc'
FONT_R = '/System/Library/Fonts/Hiragino Sans GB.ttc'

from PIL import Image, ImageDraw, ImageFont

VOL = [
    ('horror', 'H', '恐怖本', '夜枭'),
    ('twist', 'T', '反转本', '叙诡生'),
    ('comedy', 'C', '搞笑本', '哈哈镜'),
    ('office', 'O', '职场厮杀本', '工位修罗'),
]
VMAP = {p: (v, label, pen) for v, p, label, pen in VOL}
THEME = {
    'H': dict(bg=(16, 24, 22), acc=(190, 54, 48), gold=(216, 182, 116), ink=(238, 232, 220), tag='怪谈 · 惊魂'),
    'T': dict(bg=(18, 24, 44), acc=(92, 108, 188), gold=(186, 200, 232), ink=(234, 238, 250), tag='叙诡 · 一念翻转'),
    'C': dict(bg=(48, 30, 14), acc=(238, 160, 40), gold=(255, 214, 120), ink=(255, 244, 222), tag='沙雕 · 爆笑'),
    'O': dict(bg=(20, 30, 42), acc=(214, 120, 54), gold=(224, 198, 150), ink=(236, 240, 246), tag='职场 · 厮杀'),
}

# 商业化包装（由 8 个 agent 产出，见 commercial/ 目录）：sid -> 文本
PACK = {}


def load_packaging():
    """读取商业化包装：各卷 commercial/pack_<vol>.md 的 ## [SID] 块，
    以及单本 commercial/<SID>.md（单本优先）。"""
    cdir = os.path.join(BASE, 'commercial')
    if not os.path.isdir(cdir):
        return
    for pf in glob.glob(os.path.join(cdir, 'pack_*.md')):
        txt = open(pf, encoding='utf-8').read()
        for blk in re.split(r'(?=^## \[[A-Z]\d{2}\])', txt, flags=re.M):
            m = re.match(r'^## \[([A-Z]\d{2})\][^\n]*\n(.*)', blk.strip(), re.S)
            if m and m.group(2).strip():
                PACK.setdefault(m.group(1), m.group(2).strip())
    for pf in glob.glob(os.path.join(cdir, '*.md')):
        sid = os.path.splitext(os.path.basename(pf))[0]
        if re.match(r'^[A-Z]\d{2}$', sid):
            PACK[sid] = open(pf, encoding='utf-8').read().strip()


def commercial_text(sid):
    return PACK.get(sid, '')


def font(sz, bold=True):
    return ImageFont.truetype(FONT_B if bold else FONT_R, sz, index=0)


def wrap(draw, text, f, maxw):
    """按像素宽度折行（中文逐字），保留显式换行。"""
    lines = []
    for para in str(text).split('\n'):
        cur = ''
        for ch in para:
            if cur and draw.textlength(cur + ch, font=f) > maxw:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
        lines.append(cur)
    return lines


def safe(s):
    return re.sub(r'[《》/\\:*?"<>|\r\n\t]', '', str(s)).strip()


def parse_vol(vol, pre):
    path = glob.glob(os.path.join(BASE, vol, '*.md'))[0]
    text = open(path, encoding='utf-8').read()
    out = {}
    for p in re.split(r'(?=^## \[%s\d{2}\] )' % pre, text, flags=re.M):
        m = re.match(r'^## \[(%s\d{2})\] 《(.+?)》' % pre, p.strip())
        if not m:
            continue
        sid, name = m.group(1), m.group(2)
        d = dict(sid=sid, name=name, vol=vol, label=VMAP[pre][1], pen=VMAP[pre][2], pre=pre)
        for f in ['题材', '人数', '时长', '难度']:
            mm = re.search(r'-\s*%s[：:]\s*(.+?)\s*$' % f, p, re.M)
            d[f] = mm.group(1) if mm else ''

        def sec(nm):
            mm = re.search(r'###\s*%s[^\n]*\n(.*?)(?=\n###|\Z)' % nm, p, re.S)
            return mm.group(1).strip() if mm else ''

        d['背景'] = sec('背景')
        d['核心诡计'] = sec('核心诡计')
        d['反转点'] = sec('反转点')
        d['真相'] = sec('真相')
        d['升级'] = sec('讨论升级')
        d['dm_notes'] = re.findall(r'^\s*(?:\d+\.|-\s+)\s*(.+)$', sec('主持人'), re.M)
        d['clues'] = [c.strip() for c in re.findall(r'^\s*\d+\.\s*(.+)$', sec('关键线索'), re.M)]
        flow = re.findall(r'-\s*(第[一二三]幕)[：:]\s*(.+)$', sec('流程'), re.M)
        d['flow'] = flow if flow else [('第一幕', '开场搜证'), ('第二幕', '深入比对'), ('第三幕', '还原与投票')]
        roles = []
        for nm, body in re.findall(r'-\s*\*\*(.+?)\*\*[：:]([^\n]*)', sec('角色')):
            body = body.strip()
            mm = re.match(r'^(.*?)[。；]\s*表面立场[：:]\s*(.*?)[。；]\s*隐藏秘密[：:]\s*(.*?)[。；]\s*个人目标[：:]\s*(.*)$', body, re.S)
            if mm:
                ident, stance, secret, goal = (x.strip() for x in mm.groups())
            else:
                ident, stance, secret, goal = body, '', '', ''
            roles.append(dict(name=nm.strip(), ident=ident, stance=stance, secret=secret, goal=goal))
        d['roles'] = roles
        d['n'] = len(roles)
        out[sid] = d
    return out


# ---------------- 图片 ----------------

def draw_cover(d, th, path):
    W, H = 900, 1260
    im = Image.new('RGB', (W, H), th['bg'])
    dr = ImageDraw.Draw(im)
    for y in range(H):
        k = y / H
        c = tuple(int(th['bg'][i] * (1 - k * 0.4) + th['acc'][i] * k * 0.22) for i in range(3))
        dr.line([(0, y), (W, y)], fill=c)
    for r in (300, 240, 180):
        dr.ellipse([W - 60 - r, 640 - r, W - 60 + r, 640 + r], outline=th['acc'], width=2)
    dr.rectangle([36, 36, W - 36, H - 36], outline=th['gold'], width=3)
    dr.rectangle([48, 48, W - 48, H - 48], outline=th['acc'], width=1)
    dr.text((70, 78), '百 局   B A I J U   ·   原 创 剧 本 杀', font=font(26), fill=th['gold'])
    dr.text((W - 150, 78), d['sid'], font=font(26, False), fill=th['ink'])
    dr.line([70, 128, W - 70, 128], fill=th['gold'], width=2)
    dr.text((70, 152), '%s  ｜  %s 执笔' % (th['tag'], d['pen']), font=font(30, False), fill=th['acc'])
    name = d['name']
    for sz in (82, 72, 64, 56, 48, 42):
        f = font(sz)
        ls = wrap(dr, name, f, W - 150)
        if len(ls) <= 3:
            break
    y = 400
    for ln in ls:
        dr.text((70, y), ln, font=f, fill=th['ink'])
        y += sz + 16
    dr.line([70, y + 24, 70 + 220, y + 24], fill=th['gold'], width=4)
    by = H - 250
    dr.rounded_rectangle([70, by, W - 70, H - 80], radius=16, fill=(0, 0, 0), outline=th['gold'], width=2)
    info = '人数 %s  ｜  %s  ｜  难度 %s' % (d['人数'], d['时长'], d['难度'])
    for i, ln in enumerate(wrap(dr, info, font(30, False), W - 160)):
        dr.text((100, by + 26 + i * 40), ln, font=font(30, False), fill=th['ink'])
    dr.text((100, by + 110), '题材：%s' % d['题材'], font=font(26, False), fill=th['gold'])
    dr.text((100, H - 118), '2–4 人 · 可直接开本 · 盒装物料齐全', font=font(24, False), fill=th['acc'])
    im.save(path, 'PNG', optimize=True)


def draw_role_card(d, th, role, idx, total, path):
    W, H = 640, 920
    im = Image.new('RGB', (W, H), (240, 234, 220))
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W, 156], fill=th['bg'])
    dr.rectangle([0, 152, W, 158], fill=th['gold'])
    dr.text((36, 30), '%s · 《%s》' % (d['sid'], d['name']), font=font(24, False), fill=th['gold'])
    dr.text((36, 74), '角 色 卡   %d / %d' % (idx, total), font=font(22, False), fill=th['acc'])
    fb = font(52)
    ls = wrap(dr, role['name'], fb, W - 72)
    y = 190
    for ln in ls:
        dr.text((36, y), ln, font=fb, fill=(26, 24, 20))
        y += 62
    y += 8
    dr.line([36, y, W - 36, y], fill=th['acc'], width=2)
    y += 20
    dr.text((36, y), '身份', font=font(24), fill=th['acc']); y += 36
    for ln in wrap(dr, role['ident'] or '本局玩家', font(28, False), W - 72):
        dr.text((36, y), ln, font=font(28, False), fill=(40, 36, 30)); y += 38
    y += 16
    dr.text((36, y), '人前主张', font=font(24), fill=th['acc']); y += 36
    for ln in wrap(dr, role['stance'] or '随机应变', font(27, False), W - 72):
        dr.text((36, y), ln, font=font(27, False), fill=(40, 36, 30)); y += 38
    ty = H - 300
    dr.rounded_rectangle([30, ty, W - 30, H - 90], radius=16, fill=(255, 250, 238), outline=th['acc'], width=3)
    dr.text((54, ty + 20), '◆ 你的任务', font=font(30), fill=th['acc'])
    gy = ty + 70
    for ln in wrap(dr, role['goal'] or '完成你自己的目的', font(28, False), W - 108):
        dr.text((54, gy), ln, font=font(28, False), fill=(30, 26, 20)); gy += 40
    dr.text((54, H - 70), '※ 你另有不可告人的秘密，见《角色剧本》，切勿展示给他人', font=font(19, False), fill=(120, 100, 80))
    im.save(path, 'PNG', optimize=True)


def draw_clue_card(d, th, path):
    clues = d['clues'] or ['（本局无线索卡）']
    W = 760
    H = 150 + len(clues) * 168
    im = Image.new('RGB', (W, H), (238, 232, 216))
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W, 110], fill=th['bg'])
    dr.text((36, 28), '%s · 《%s》' % (d['sid'], d['name']), font=font(26, False), fill=th['gold'])
    dr.text((36, 64), '线 索 卡   （搜证后公开）', font=font(24), fill=th['acc'])
    y = 130
    for i, c in enumerate(clues, 1):
        box_h = 150
        dr.rounded_rectangle([26, y, W - 26, y + box_h], radius=12, fill=(252, 248, 238), outline=th['acc'], width=2)
        dr.ellipse([40, y + 22, 92, y + 74], fill=th['acc'])
        dr.text((55, y + 30), str(i), font=font(30), fill=(255, 255, 255))
        cy = y + 18
        for ln in wrap(dr, c, font(25, False), W - 150):
            dr.text((110, cy), ln, font=font(25, False), fill=(36, 32, 26)); cy += 34
        y += box_h + 14
    im.save(path, 'PNG', optimize=True)


# ---------------- 文档 ----------------

def role_script(d, role):
    flow = '\n'.join('- %s：%s' % (a, b) for a, b in d['flow'])
    return f"""# 《{d['name']}》· 角色剧本 —— {role['name']}

> 本册**仅发给「{role['name']}」的玩家**，请勿传阅、不要让其他玩家看到。
> 本局 {d['n']} 人 ｜ {d['时长']} ｜ 难度 {d['难度']}

## 一、你是谁
{role['ident'] or '本局玩家'}

## 二、全场公开背景（DM 开场宣读，所有人都知道）
{d['背景']}

## 三、你在人前的主张
{role['stance'] or '随机应变，见机行事'}

## 四、只有你知道的秘密（切勿主动说出）
{role['secret'] or '（本角色无额外隐情，靠搜证推进）'}

## 五、你的任务（本局要达成的个人目标）
**{role['goal'] or '找出真相并保护自己'}**

## 六、你开场掌握的信息
- 你的身份、上述秘密与任务；
- 全场公开背景；
- 其余线索须在搜证轮获得，不要预设别人手里有什么。

## 七、分幕行动指引
{flow}

## 八、你要隐瞒 / 你要追查
- **隐瞒**：{role['secret'] or '无'} —— 用对话与搜证周旋，别一上来就摊牌。
- **追查**：与「{role['goal'] or '你的目标'}」相关的物证、他人证词里的矛盾、时间线缺口。

## 九、建议开场自我介绍
> 「我是 {role['name']}，{role['stance'] or '来把事情弄清楚的'}。」

## 十、游戏提醒
- 搜证轮按 DM 指令行动，拿到的线索卡可选择公开或暂扣。
- 真相由 DM 在第三幕统一揭示；投票前不要自行公布完整推理。
- 你的目标是「{role['goal'] or '达成个人目的'}」，但结局由全场投票/搜证结果共同决定。
"""


def clue_list(d):
    rows = '\n'.join('%d. %s' % (i, c) for i, c in enumerate(d['clues'], 1))
    acts = ['第一幕', '第二幕', '第三幕']
    timing = '\n'.join('- 线索 %d：建议%s搜证时放出%s' % (
        i, acts[min(i - 1, 2)], '（指向核心矛盾）' if i <= 2 else '（用于回看验证）')
        for i in range(1, len(d['clues']) + 1))
    return f"""# 《{d['name']}》· 线索卡清单（DM / 印制用）

> 共 {len(d['clues'])} 张线索卡，另有《线索卡.png》组图可直接裁切印刷。
> 建议做成 63×88mm 卡片，正面编号 + 物证描述，背面留白。

## 线索卡内容
{rows}

## 建议揭示时机
{timing}

## 印制建议
- 每条线索单独制卡；编号与《线索卡.png》一一对应。
- 物证类可配实物道具（纸张、票据、照片、器物）提升沉浸。
- 线索须能被搜到、可被回看验证；DM 不要提前放完，按幕逐步解锁。
"""


def upgrade_section(d):
    """把 `### 讨论升级 / 高光辩论` 段渲染成可独立成章的正文；无升级内容时返回空串。"""
    if not d.get('升级'):
        return ''
    return '## 讨论升级 / 高光辩论（本局升级）\n\n' + d['升级'].strip() + '\n'


def rulebook(d):
    up = upgrade_section(d)
    return f"""# 《{d['name']}》· 游戏说明书

> {d['题材']} ｜ {d['人数']} ｜ {d['时长']} ｜ 难度 {d['难度']} ｜ 写手 {d['pen']}

## 盒内物料
1. 盒绘封面（封面.png）
2. 本《说明书》×1
3. 《角色剧本》×{d['n']}（每名玩家 1 册，信息互不相同，**不要交换阅读**）
4. 《角色卡》×{d['n']}（可摆桌面，仅含公开信息）
5. 《线索卡》共 {len(d['clues'])} 张（线索卡.png / 线索卡清单.md）
6. 《主持人手册》×1（**仅 DM 阅读，玩家切勿翻看**）
7. 《结局卡》×1（由 DM 在终局念读）

## 开始前准备
- 指定 1 名主持人（DM），**提前通读《主持人手册》与全部角色剧本**。
- 按人数分发对应角色剧本与角色卡，每人只拿自己那份。
- 摆放线索卡（背面朝上）或按 DM 手册分幕投放；准备纸笔用于记录时间线。
- 关闭与剧情无关的外界信息，建议 {d['时长']} 不中断。

## 游戏规则
1. **读本**：各自阅读角色剧本 5–8 分钟，记住你的身份、秘密与任务；不要念出秘密。
2. **开场**：轮流做自我介绍（可用剧本里的「建议开场自我介绍」）。
3. **搜证**：按 DM 指令进入搜证轮，每轮可获取/查看若干线索卡；可选择公开或暂扣。
4. **讨论**：基于线索互相质询、比对时间线、找出矛盾；可结盟也可欺骗。
5. **分幕推进**：共三幕，每幕 DM 会投放新信息并推进冲突（见 DM 手册）。
6. **投票 / 结局**：第三幕末按本局要求投票或指认；DM 据结果念读《结局卡》主结局或分支结局。

## 胜负与体验
- 本类剧本为**沉浸推理 + 角色扮演**，多数无硬性「输赢」，以「是否达成个人任务」+「是否还原真相」为体验核心。
- 完成本局任务、或投中真相/关键指认，即为本局高光；DM 可在复盘时点明各角色的暗线。

{up}
## 常见问题
- **Q：能把自己的秘密告诉别人吗？** 可以策略性透露，但一旦全盘托出会失去博弈空间，建议留到关键轮次。
- **Q：线索不够怎么办？** 回到角色剧本的「你要追查」与 DM 的节奏提示，重新比对已公开线索。
- **Q：有人提前猜到真相？** DM 按主持人手册「防过早破梗」提示引导，不确认、不否认。
"""


def dm_manual(d):
    flow = '\n'.join('- **%s**：%s' % (a, b) for a, b in d['flow'])
    notes = '\n'.join('- %s' % x for x in d['dm_notes']) or '- （按线索逐步解锁，勿一次放完）'
    clues = '\n'.join('%d. %s' % (i, c) for i, c in enumerate(d['clues'], 1))
    roles_secret = '\n'.join('- **%s**：秘密＝%s；任务＝%s' % (r['name'], r['secret'], r['goal']) for r in d['roles'])
    ct = commercial_text(d['sid'])
    pack = '\n## 〇、商业化包装（宣传 / 开本导语，无剧透）\n' + ct + '\n' if ct else ''
    up = d.get('升级', '').strip()
    up_ch = '\n## 十一、讨论升级 / 高光辩论（本局升级）\n' + up + '\n' if up else ''
    return f"""# 《{d['name']}》· 主持人手册（DM 专用 · 玩家勿看）
{pack}
## 一、基本信息
- 题材：{d['题材']}
- 人数：{d['人数']}（{d['n']} 名角色）
- 时长：{d['时长']} ｜ 难度：{d['难度']}
- 核心机制：{d['核心诡计'][:120]}

## 二、发本顺序
1. 先让玩家抽/选角色，按下列顺序发《角色剧本》与《角色卡》（每人只拿自己那份）：
{chr(10).join('   - %s' % r['name'] for r in d['roles'])}
2. 确认每人都读完且没拿错本，再宣读「全场公开背景」。
3. 线索卡按「建议揭示时机」分幕投放，勿一次性摊开。

## 三、三幕流程详述
{flow}

> 每幕开始：简述本幕目标 → 开放搜证 → 组织一轮轮流发言 → 收束到本幕矛盾点。
> 第三幕末组织投票/指认，再念读《结局卡》。

## 四、线索发放表
{clues}

## 五、反转与高潮
{d['反转点']}

## 六、完整真相（含全部角色秘密 · 仅 DM）
各角色秘密与任务：
{roles_secret}

真相与证据链：
{d['真相']}

## 七、结局（主 / 分支）
见《结局卡.md》，由 DM 按投票结果念读。

## 八、节奏与安全提示
{notes}

## 九、复盘话术（DM 收尾）
- 带玩家回看：哪条线索早就埋了反转伏笔、谁的任务其实和谁冲突。
- 点明本局机制「{d['核心诡计'][:60]}」是如何被物证闭合的。
- 提醒：所有灵异/巧合均有可搜证的人为解释，不做超自然托底。

## 十、物料核对
封面 ×1 ｜ 说明书 ×1 ｜ 角色剧本 ×{d['n']} ｜ 角色卡 ×{d['n']} ｜ 线索卡 ×{len(d['clues'])} ｜ DM 手册 ×1 ｜ 结局卡 ×1
{up_ch}"""


def ending_card(d):
    return f"""# 《{d['name']}》· 结局卡（DM 念读 · 玩家终局前勿看）

> 第三幕投票 / 指认结束后，由 DM 依据结果选择主结局或分支结局念读。

## 真相揭晓
{d['真相']}

## 念读提示
- 先念「证据链」再念「各人下场」，让玩家对回自己手里的线索卡。
- 若触发分支条件（见上文「分支」），改念分支结局。
- 念完后进入复盘：请每位玩家说出自己是否完成了「个人任务」。
"""


def combo(d):
    parts = [
        '# 百局 ·《%s》· 本盒完整内容（GM 总览版）' % d['name'],
        '> 编号 %s ｜ %s ｜ %s ｜ 写手 %s ｜ %s ｜ %s ｜ %s' % (
            d['sid'], d['label'], d['题材'], d['pen'], d['人数'], d['时长'], d['难度']),
        '> 本文件为店家/GM 总览合订；**发给玩家时请只发对应《角色剧本》与《角色卡》，切勿整份下发**。',
        '\n---\n\n## ① 说明书\n' + rulebook(d),
        '\n---\n\n## ② 线索卡清单\n' + clue_list(d),
    ]
    for r in d['roles']:
        parts.append('\n---\n\n## ③ 角色剧本 · %s\n' % r['name'] + role_script(d, r))
    parts.append('\n---\n\n## ④ 主持人手册\n' + dm_manual(d))
    parts.append('\n---\n\n## ⑤ 结局卡\n' + ending_card(d))
    ct = commercial_text(d['sid'])
    if ct:
        parts.append('\n---\n\n## ⑥ 商业化包装（无剧透）\n' + ct)
    up = d.get('升级', '').strip()
    if up:
        num = '⑦' if ct else '⑥'
        parts.append('\n---\n\n## %s 讨论升级 / 高光辩论（本局升级）\n' % num + up)
    return '\n'.join(parts)


def build_one(d, th):
    folder = os.path.join(OUT, '%s_%s' % (d['sid'], safe(d['name'])))
    os.makedirs(os.path.join(folder, '角色卡'), exist_ok=True)
    os.makedirs(os.path.join(folder, '角色剧本'), exist_ok=True)
    draw_cover(d, th, os.path.join(folder, '封面.png'))
    for i, r in enumerate(d['roles'], 1):
        draw_role_card(d, th, r, i, d['n'],
                       os.path.join(folder, '角色卡', '%s.png' % safe(r['name'])))
        open(os.path.join(folder, '角色剧本', '%s.md' % safe(r['name'])), 'w', encoding='utf-8').write(role_script(d, r))
    draw_clue_card(d, th, os.path.join(folder, '线索卡.png'))
    open(os.path.join(folder, '说明书.md'), 'w', encoding='utf-8').write(rulebook(d))
    open(os.path.join(folder, '线索卡清单.md'), 'w', encoding='utf-8').write(clue_list(d))
    open(os.path.join(folder, '主持人手册.md'), 'w', encoding='utf-8').write(dm_manual(d))
    open(os.path.join(folder, '结局卡.md'), 'w', encoding='utf-8').write(ending_card(d))
    open(os.path.join(folder, '本盒完整内容.md'), 'w', encoding='utf-8').write(combo(d))
    ct = commercial_text(d['sid'])
    if ct:
        open(os.path.join(folder, '盒面文案.md'), 'w', encoding='utf-8').write(
            '# 《%s》· 盒面文案 / 宣传物料\n\n'
            '> 可直接用于电商详情页、盒背、海报、店铺介绍；**严禁剧透**（不写真相/反转/凶手）。\n\n%s\n'
            % (d['name'], ct))
    return folder


def main():
    os.makedirs(OUT, exist_ok=True)
    load_packaging()
    only = sys.argv[1].upper() if len(sys.argv) > 1 else None
    total = 0
    head = '100 套「可直接开本」盒装本成品' if not only else '样板预览：%s' % only
    index = ['# 百局 · 盒装本总索引\n',
             '> %s。每本含封面图、角色卡图、线索卡图、分角色剧本、说明书、'
             '主持人手册、结局卡、盒面文案、本盒合订。\n' % head]
    for vol, pre, label, pen in VOL:
        data = parse_vol(vol, pre)
        sids = [s for s in sorted(data) if (not only or s == only)]
        if not sids:
            continue
        th = THEME[pre]
        index.append('\n## %s（%s）· %d 本\n' % (label, pen, len(sids)))
        index.append('| 编号 | 剧名 | 人数 | 时长 | 难度 | 题材 | 成品目录 |\n|---|---|---|---|---|---|---|')
        for sid in sids:
            d = data[sid]
            folder = build_one(d, th)
            total += 1
            rel = os.path.relpath(folder, BASE).replace(os.sep, '/')
            index.append('| %s | 《%s》 | %s | %s | %s | %s | [%s](%s) |' % (
                sid, d['name'], d['人数'], d['时长'], d['难度'], d['题材'], rel, rel))
    open(os.path.join(OUT, '盒装本总索引.md'), 'w', encoding='utf-8').write('\n'.join(index) + '\n')
    print('已生成盒装本：%d 本 -> %s' % (total, OUT))
    print('商业化包装注入：%d 套' % len(PACK))
    print('索引：%s' % os.path.join(OUT, '盒装本总索引.md'))


if __name__ == '__main__':
    main()
