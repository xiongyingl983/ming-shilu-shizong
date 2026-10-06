# -*- coding: utf-8 -*-
"""扫描白话编年体语料中「机器译文系统性缺陷」，定位可疑段落，便于回原页核校。

⚠ 前提：本语料是**白话译文**。所以：
  · 检索史事必须用**白话词**（不报／没有批复／前往封国／朝廷商议），
    用文言词会严重漏检 —— 实测：留中 2 处、之国 3 处、之藩 0 处、特旨 6 处、勘报 2 处，
    而白话形式的「不报」有 45 处。本脚本的用法同理。

已实测的缺陷类（附实测规模）：
  A. 把原文的「上／帝」误译为先秦诸侯名（齐景公／晋悼公／魏文侯／鲁庄公／齐孝公／卫庄公／哀公…）
     —— 33 词黑名单命中 159 处，散布 108 卷。嘉靖朝叙事里出现先秦诸侯名，几乎必是此缺陷。
  B. **译文自造年号**（非"后世内容混入"）：原文省略年号时，译文会给它补上错误的年号 ——
     实测「万历」28 处、散布 26 卷（集中于卷400 以后）。铁证（原文比对，可用 raw_juan.py 复现）：
       卷之491 原文「四十年至四十一年，每匹銀三十兩」→ 译文「万历四十年到万历四十一年」；
       卷之531 原文「先是，四十二年，北虜入寇」   → 译文「万历四十二年…」；
       卷之566 原文「○癸巳追治四十二年七月」     → 译文「万历四十二年七月中鸡鸣驿事件…」
         （"鸡鸣驿事件"原文所无 = **译文增补**，最危险的一类）。
     → 规则：译文里凡出现非嘉靖年号，一律按该卷所属年号回读原文；**原文层抽查无此问题**。
     ⚠ 卷首《实录序》《进实录表》本是万历年间文书，那里的「万历」属正常，勿误判。
  C. 同一人名译形游移（引用前必须回原页）：曾铣→杨铣/萧铣/仇铣/林铣；仇鸾→萧鸾/吕鸾/江鸾；
     翟鹏→梁鹏/盖鹏；陆炳→纪炳；石天爵→史天爵/李天爵；牛天麟→半天麟；翁万达→王万达；
     董晹→董旸；徐樾→朱樾/徐槌/崔维；石宝→石瑶；许泰→朱泰。
  D. 原站段落以省略号截断（卷311/313/315/322/324 等），非本语料丢失——引用须回原页补全。
  E. 干支与所系月份不合、跨页断行致首条日期缺失（卷45末、47、54、112 等）。

用法：
    python scan_mt_defects.py                 # A+B 两类总览，按卷统计
    python scan_mt_defects.py --cls B         # 只看某一类
    python scan_mt_defects.py --kw 魏文侯     # 某词的逐条上下文
    python scan_mt_defects.py --terms         # 打印黑名单
"""
import argparse, collections, re, sys

TXT_DEFAULT = r'D:\MyTools\Books\明实录世宗实录·白话编年体.txt'

CLASSES = {
    'A': ['齐景公', '晋悼公', '魏文侯', '鲁庄公', '卫庄公', '齐孝公', '郑庄公', '秦孝公',
          '鲁哀公', '齐桓公', '晋文公', '楚庄王', '宋襄公', '秦穆公', '哀公', '悼公',
          '文侯', '武侯', '昭公', '定公', '献公', '缪公', '桓公'],
    'B': ['万历', '神宗', '泰昌', '天启', '崇祯', '贺人龙', '猛如虎'],  # 非本卷年号（见下说明）
    'C': ['石瑶', '陈洗', '朱泰', '李子麟', '王邦奇', '郑永', '乌恩藏', '蔡天佑', '耿铭', '孙铭',
          '杨铣', '萧铣', '仇铣', '林铣', '萧鸾', '吕鸾', '江鸾', '梁鹏', '盖鹏', '纪炳',
          '史天爵', '李天爵', '半天麟', '王万达', '董晹', '徐槌', '崔维', '张辅',
          '杨炳然', '湖镇', '张选', '林迪珍', '李松', '王衡', '王春', '张杲', '王光升', '邹光升',
          '周㧤', '杨经', '沈黙', '胡邦辅', '甘顺', '李顺', '陈甲', '王甲', '沈甲', '陆梁', '桂深', '苏深'],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--txt', default=TXT_DEFAULT)
    ap.add_argument('--cls', default='AB', help='要扫的类：A/B/C 或其组合')
    ap.add_argument('--kw', default='')
    ap.add_argument('--terms', action='store_true')
    a = ap.parse_args()

    if a.terms:
        for k, v in CLASSES.items():
            print('%s 类：' % k + '、'.join(v))
        return

    if a.kw:
        terms = [a.kw]
    else:
        terms = []
        for c in a.cls.upper():
            terms += CLASSES.get(c, [])
        # 去掉被更长词包含的短词，避免重复计数
        terms = [t for t in terms if not any(t != o and t in o for o in terms)]

    lines = open(a.txt, encoding='utf-8-sig').read().replace('\r\n', '\n').split('\n')
    cur, hits, detail = '', collections.Counter(), collections.defaultdict(list)
    for ln in lines:
        m = re.search(r'卷之([0-9一二三四五六七八九十百]+)', ln)
        if m and len(ln) < 60 and '实录' in ln:
            cur = '卷之' + m.group(1)
        for t in terms:
            if t in ln:
                hits[cur] += 1
                if a.kw and len(detail[cur]) < 5:
                    detail[cur].append(ln.strip()[:100])
    print('命中合计 %d 处，涉及 %d 卷（类 %s，%d 词）\n' % (sum(hits.values()), len(hits), a.cls, len(terms)))
    for j, n in hits.most_common(24):
        print('%8s  %3d 处' % (j or '(卷首)', n))
    if a.kw:
        print()
        for j, ls in list(detail.items())[:12]:
            print('---', j)
            for x in ls:
                print('   ', x)
    print('\n提示：卷首（实录序／进实录表）本为万历年间文书，其中的「万历」属正常，勿计入缺陷。')


if __name__ == '__main__':
    main()
