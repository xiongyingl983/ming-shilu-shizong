# -*- coding: utf-8 -*-
"""《明世宗肃皇帝实录》原文(繁体)/白话 逐句核验工具。

数据源：识典古籍 LS0026 各卷 SSR 数据的本地缓存（raw/<chapterId>.json），
其中 lines[].t 是该站原文（繁体），trans{logicSentenceId} 是该站白话译文。
卷次索引 CSV 给出 卷号 → 章节id / 原页 URL。

例：
    python raw_juan.py --juan 300                  # 整卷：原文+白话对照
    python raw_juan.py --juan 300 --kw 严嵩        # 只列含关键词的句对（逐句对照）
    python raw_juan.py --juan 35-37 --fanti-only   # 只出繁体原文
    python raw_juan.py --juan 300 --json           # 结构化输出（便于二次处理）
"""
import argparse, csv, json, os, re, sys

RAW_DEFAULT = r'D:\MyTools\Books\b2s_shizong_work\raw'
IDX_DEFAULT = r'D:\MyTools\Books\明实录世宗实录·白话编年体·卷次索引.csv'

CN = {'元': 1}
for _i, _c in enumerate('一二三四五六七八九'):
    CN[_c] = _i + 1
CN['十'] = 10
NUM = '元一二三四五六七八九十百拾'


def cn2int(s):
    s = (s or '').strip().replace('拾', '十').replace('元', '一')
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


def parse_juan(s):
    out = set()
    for part in s.split(','):
        part = part.strip()
        m = re.match(r'^([%s\d]+)\s*-\s*([%s\d]+)$' % (NUM, NUM), part)
        if m:
            a, b = [int(x) if x.isdigit() else cn2int(x) for x in (m.group(1), m.group(2))]
            out.update(range(min(a, b), max(a, b) + 1))
        elif part:
            out.add(int(part) if part.isdigit() else cn2int(part))
    return out


def load_index(p):
    d = {}
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding='utf-8-sig')):
            try:
                d[int(r['卷号'])] = r
            except Exception:
                pass
    return d


def juan_pairs(raw_dir, cid):
    """返回 [(原文, 白话)]，按原文句序（同 logicSentenceId 只出一次）"""
    fp = os.path.join(raw_dir, cid + '.json')
    if not os.path.exists(fp):
        return [], None
    d = json.load(open(fp, encoding='utf-8'))
    pairs, seen = [], set()
    for p in d.get('paragraphs', []):
        tr = p.get('trans') or {}
        for l in p.get('lines', []):
            if l.get('lt') in (4, 7) or l.get('sid') in ('0', 'None', 'null'):
                continue
            sid = l.get('sid')
            if sid in seen:
                continue
            seen.add(sid)
            pairs.append((l.get('t', ''), (tr.get(sid) or '').strip()))
    return pairs, d.get('name')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--juan', required=True, help='卷号：300 / 三百 / 300-302')
    ap.add_argument('--kw', default='', help='关键词：只列含该词的句对（原文或译文命中）')
    ap.add_argument('--raw', default=RAW_DEFAULT)
    ap.add_argument('--index', default=IDX_DEFAULT)
    ap.add_argument('--fanti-only', action='store_true', help='只出繁体原文')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()

    idx = load_index(a.index)
    want = sorted(parse_juan(a.juan))
    result = []
    for n in want:
        r = idx.get(n)
        if not r:
            print('卷之%d：卷次索引里没有' % n, file=sys.stderr)
            continue
        cid = r.get('识典chapterId') or r.get('章节id') or ''
        pairs, name = juan_pairs(a.raw, cid)
        rows = []
        for fan, bai in pairs:
            if a.kw and (a.kw not in fan and a.kw not in bai):
                continue
            rows.append({'原文': fan, '白话': bai})
        result.append({'juan': n, 'juan_title': r.get('卷题', ''), 'ym': r.get('首见年月', ''),
                       'url': r.get('网页地址', ''), 'chapter_id': cid,
                       'pairs': rows, 'pairs_total': len(pairs)})
    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return
    for b in result:
        print('=' * 70)
        print('卷之%d　%s　【%s】' % (b['juan'], b['juan_title'], b['ym']))
        if b['url']:
            print(b['url'])
        print('命中 %d / 全卷 %d 句' % (len(b['pairs']), b['pairs_total']))
        print('=' * 70)
        for row in b['pairs']:
            if a.fanti_only:
                print(row['原文'])
            else:
                print('原：' + row['原文'])
                print('白：' + (row['白话'] or '（该站无译文）'))
                print('-' * 50)
        print()


if __name__ == '__main__':
    main()
