# -*- coding: utf-8 -*-
"""章文件质量门（book-to-skill 交付前自检）：
  1) 九节齐全、顺序正确
  2) 每章字数下限、卷号引用数下限
  3) 抽查「短引」是否超长（防整段照抄）
  4) 与 references/data-provenance.md 对齐：卷号引用应落在该章覆盖范围内
用法： python verify_chapters.py [--dir .../ming-shilu-shizong/chapters]
"""
import argparse, os, re, sys

SEC = ['核心要义', '框架与判断规则', '关键概念', '心智模型', '反模式', '工作例证', '关键要点', '与其他章的关系']
CN = {'元': 1}
for _i, _c in enumerate('一二三四五六七八九'):
    CN[_c] = _i + 1
CN['十'] = 10
NUM = '0-9元一二三四五六七八九十百拾'


def cn2int(s):
    s = (s or '').strip().replace('拾', '十').replace('元', '一')
    if s.isdigit():
        return int(s)
    tot = 0
    if '百' in s:
        a, rest = s.split('百', 1)
        tot += (CN.get(a, 1) if a else 1) * 100
        s = rest
    if s.startswith('十'):
        return tot + 10 + (CN.get(s[1:], 0) if len(s) > 1 else 0)
    if '十' in s:
        a, b = s.split('十', 1)
        return tot + (CN.get(a, 1) if a else 1) * 10 + (CN.get(b, 0) if b else 0)
    return tot + (CN.get(s, 0) if s else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=r'C:\Users\XiongYingLi\AppData\Local\hermes\skills\research\ming-shilu-shizong\chapters')
    ap.add_argument('--min-chars', type=int, default=1200)
    ap.add_argument('--min-cites', type=int, default=8)
    a = ap.parse_args()
    files = sorted(f for f in os.listdir(a.dir) if f.endswith('.md'))
    print('章文件 %d 个：%s\n' % (len(files), a.dir))
    ok = True
    print('%-28s %6s %6s %6s %-22s %s' % ('file', '字数', '节', '引用', '覆盖范围', '问题'))
    for f in files:
        t = open(os.path.join(a.dir, f), encoding='utf-8').read()
        nchar = len(re.sub(r'\s', '', t))
        miss = [s for s in SEC if ('## ' + s) not in t]
        # 顺序
        idxs = [t.find('## ' + s) for s in SEC if ('## ' + s) in t]
        ordered = idxs == sorted(idxs)
        cites = re.findall(r'卷之?([%s]+)' % NUM, t)
        cover = re.search(r'覆盖范围[:：]\s*(.+)', t)
        cover = cover.group(1).strip() if cover else ''
        juan = [cn2int(x) for x in cites]
        rng = re.search(r'([%s]+)\s*[—\-–~至]\s*([%s]+)' % (NUM, NUM), cover)
        inrange = True
        if rng and juan:
            lo, hi = cn2int(rng.group(1)), cn2int(rng.group(2))
            out = [j for j in juan if not (lo - 2 <= j <= hi + 2)]
            inrange = len(out) <= max(2, len(juan) * 0.1)
        # 长引抽查：连续 >150 字且无句读分隔的引用块
        longs = [ln for ln in t.split('\n') if ln.strip().startswith('「') and len(ln) > 150]
        probs = []
        if miss:
            probs.append('缺节:' + ','.join(miss))
        if not ordered:
            probs.append('节序乱')
        if nchar < a.min_chars:
            probs.append('字数%s<%d' % (nchar, a.min_chars))
        if len(cites) < a.min_cites:
            probs.append('引用%s<%d' % (len(cites), a.min_cites))
        if not inrange:
            probs.append('引用越界')
        if longs:
            probs.append('长引%d处' % len(longs))
        if probs:
            ok = False
        print('%-28s %6d %6d %6d %-22s %s' % (f, nchar, len(SEC) - len(miss), len(cites), cover[:20],
                                              '、'.join(probs) if probs else 'OK'))
    print('\n门禁结果：', 'PASS' if ok else 'FAIL（见上表问题列）')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
