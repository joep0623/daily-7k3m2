#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 index.html 提取日程数据，生成 schedule.ics（iCalendar 订阅文件）。

用法：python3 gen_ics.py
产出：schedule.ics —— 交给系统日历订阅，就能用原生桌面小组件看日程。

设计：数据源只有一个（index.html）。
      本脚本把页面里那段 JS 跑一遍，直接调用页面自己的
      blocksFor() / trainTypeOf()，所以训练循环、周三约会、
      周六家教、周日无计划这些规则不会重复实现一遍。
"""

import json
import os
import re
import shutil
import subprocess
import datetime
import hashlib

REPO = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(REPO, 'index.html')
OUT = os.path.join(REPO, 'schedule.ics')

HORIZON_DAYS = 120
TZID = 'Asia/Shanghai'
CAL_NAME = '备考日程'

KIND_LABEL = {'study': '学习', 'body': '健身', 'love': '个人时间',
              'school': '学校', 'life': '生活', 'rest': '自由', 'base': '底线'}
TRAIN_LABEL = {'push': '推', 'pull': '拉', 'legs': '腿', 'rest': '休息'}


# ---------- 1. 从 index.html 取数据 ----------
def load_data():
    html = open(HTML, encoding='utf-8').read()
    script = re.findall(r'<script>(.*?)</script>', html, re.S)[-1]

    t = datetime.date.today()
    stub = """
function El(){this.textContent='';this.innerHTML='';this.className='';this.style={};this.dataset={};
 this.classList={add:function(){},remove:function(){},toggle:function(){},contains:function(){return false;}};}
var document={getElementById:function(){return new El();},querySelectorAll:function(){return [];},addEventListener:function(){},body:{style:{}}};
var localStorage={getItem:function(){return null;},setItem:function(){}};
var window={scrollTo:function(){}};
function setInterval(){}
"""
    expr = (
        "(function(){\n"
        "  var out = {};\n"
        "  for (var i = 0; i < %d; i++){\n"
        "    var d = new Date(%d, %d, %d + i);\n"
        "    var k = d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')"
        "+'-'+String(d.getDate()).padStart(2,'0');\n"
        "    out[k] = { blocks: blocksFor(k), train: trainTypeOf(k) };\n"
        "  }\n"
        "  return JSON.stringify({WEEKS:WEEKS, SCHOOL_EVENTS:SCHOOL_EVENTS, DAYS:out});\n"
        "})()"
    ) % (HORIZON_DAYS, t.year, t.month - 1, t.day)

    tmp = '/tmp/_beikao_dump.js'
    if shutil.which('osascript'):
        open(tmp, 'w', encoding='utf-8').write(stub + script + '\n' + expr + ';\n')
        r = subprocess.run(['osascript', '-l', 'JavaScript', tmp],
                           capture_output=True, text=True)
    elif shutil.which('node'):
        open(tmp, 'w', encoding='utf-8').write(stub + script + '\nconsole.log(' + expr + ');\n')
        r = subprocess.run(['node', tmp], capture_output=True, text=True)
    else:
        raise SystemExit('找不到 osascript 或 node，无法从 index.html 提取数据')

    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit('提取数据失败：\n' + (r.stderr or '(无输出)'))
    return json.loads(r.stdout)


# ---------- 2. iCalendar 工具 ----------
def esc(s):
    return (str(s).replace('\\', '\\\\').replace(';', '\\;')
            .replace(',', '\\,').replace('\n', '\\n'))


def fold(line):
    """按 RFC 5545，每行折叠到 75 字节以内"""
    raw = line.encode('utf-8')
    if len(raw) <= 75:
        return line
    out, cur = [], b''
    limit = 75
    for ch in line:
        b = ch.encode('utf-8')
        if len(cur) + len(b) > limit:
            out.append(cur)
            cur = b' '
            limit = 74
        cur += b
    out.append(cur)
    return '\r\n'.join(x.decode('utf-8', 'ignore') for x in out)


def to_min(t):
    h, m = t.split(':')
    return int(h) * 60 + int(m)


def stamp(dt):
    return dt.strftime('%Y%m%dT%H%M%S')


def uid(*parts):
    h = hashlib.md5('|'.join(str(p) for p in parts).encode('utf-8')).hexdigest()[:24]
    return h + '@beikao'


# ---------- 3. 生成事件 ----------
def build(data):
    days = data['DAYS']
    school = data['SCHOOL_EVENTS']

    now_stamp = datetime.datetime.now().strftime('%Y%m%dT%H%M%SZ')
    events = []
    stats = {}

    for key in sorted(days.keys()):
        day = datetime.datetime.strptime(key, '%Y-%m-%d').date()
        info = days[key]
        train = info.get('train')

        for b in info['blocks']:
            sm, em = to_min(b['s']), to_min(b['e'])
            start = datetime.datetime.combine(day, datetime.time()) + datetime.timedelta(minutes=sm)
            end = datetime.datetime.combine(day, datetime.time()) + datetime.timedelta(minutes=em)
            cat = KIND_LABEL.get(b['k'], b['k'])
            title = b['t']
            # 健身块带上训练部位，日历里一眼看得出今天练什么
            if b['k'] == 'body' and train and '训练' in title and train != 'rest':
                title = title + '（' + TRAIN_LABEL.get(train, train) + '）'
            events.append({
                'uid': uid(key, b['s'], b['t']),
                'start': start, 'end': end,
                'summary': title,
                'desc': cat,
                'cat': cat,
            })
        stats[info.get('train', '?')] = stats.get(info.get('train', '?'), 0) + 1

    # 学校考试（全天事件）
    horizon_end = datetime.date.today() + datetime.timedelta(days=HORIZON_DAYS)
    for e in school:
        d = datetime.datetime.strptime(e['date'], '%Y-%m-%d').date()
        if d < datetime.date.today() or d > horizon_end:
            continue
        title = '⚠️ 考试：' + e['name'] + '（' + e['kind'] + '）'
        if e.get('place'):
            title += ' @ ' + e['place']
        events.append({
            'uid': uid('exam', e['date'], e['name']),
            'start': datetime.datetime.combine(d, datetime.time()),
            'end': datetime.datetime.combine(d + datetime.timedelta(days=1), datetime.time()),
            'summary': title, 'desc': '学校考试', 'cat': '考试', 'allday': True,
        })

    events.sort(key=lambda x: x['start'])

    lines = [
        'BEGIN:VCALENDAR', 'VERSION:2.0',
        'PRODID:-//beikao//schedule//CN', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
        'X-WR-CALNAME:' + esc(CAL_NAME), 'X-WR-TIMEZONE:' + TZID,
        'REFRESH-INTERVAL;VALUE=DURATION:PT1H', 'X-PUBLISHED-TTL:PT1H',
        'BEGIN:VTIMEZONE', 'TZID:' + TZID,
        'BEGIN:STANDARD', 'TZNAME:CST', 'TZOFFSETFROM:+0800', 'TZOFFSETTO:+0800',
        'DTSTART:19910915T000000', 'END:STANDARD', 'END:VTIMEZONE',
    ]

    for ev in events:
        lines += ['BEGIN:VEVENT', 'UID:' + ev['uid'], 'DTSTAMP:' + now_stamp]
        if ev.get('allday'):
            lines.append('DTSTART;VALUE=DATE:' + ev['start'].strftime('%Y%m%d'))
            lines.append('DTEND;VALUE=DATE:' + ev['end'].strftime('%Y%m%d'))
        else:
            lines.append('DTSTART;TZID=' + TZID + ':' + stamp(ev['start']))
            lines.append('DTEND;TZID=' + TZID + ':' + stamp(ev['end']))
        lines.append('SUMMARY:' + esc(ev['summary']))
        lines.append('DESCRIPTION:' + esc(ev['desc']))
        lines.append('CATEGORIES:' + esc(ev['cat']))
        lines.append('TRANSP:TRANSPARENT')
        lines.append('END:VEVENT')

    lines.append('END:VCALENDAR')

    body = '\r\n'.join(fold(l) for l in lines) + '\r\n'
    open(OUT, 'w', encoding='utf-8', newline='').write(body)
    return len(events), stats


if __name__ == '__main__':
    data = load_data()
    n, stats = build(data)
    size = os.path.getsize(OUT) / 1024
    end = datetime.date.today() + datetime.timedelta(days=HORIZON_DAYS)
    print('✓ 已生成 schedule.ics')
    print('  事件数  : %d' % n)
    print('  文件大小: %.1f KB' % size)
    print('  覆盖范围: %s → %s' % (datetime.date.today(), end))
    print('  日期分布: ' + '  '.join('%s=%d天' % (k, v) for k, v in sorted(stats.items())))
