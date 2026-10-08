#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 index.html 提取日程数据，生成 schedule.ics（iCalendar 订阅文件）。

用法：python3 gen_ics.py
产出：schedule.ics —— 交给系统日历订阅，就能用原生桌面小组件看日程。

设计：数据源只有一个（index.html 里的 TPL / WEEKS / SCHOOL_EVENTS），
      本脚本用 JavaScriptCore 把那段 JS 跑一遍取出 JSON，不做重复定义。
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

HORIZON_DAYS = 120          # 往后生成多少天
TZID = 'Asia/Shanghai'
CAL_NAME = '备考日程'

# 星期 → 模板（Monday=0 ... Sunday=6）
PATTERN = {0: 'workday', 1: 'workday', 2: 'wednesday',
           3: 'workday', 4: 'workday', 5: 'saturday', 6: 'sunday'}

KIND_LABEL = {'study': '学习', 'body': '健身', 'love': '个人时间',
              'school': '学校', 'life': '生活', 'rest': '自由', 'base': '底线'}


# ---------- 1. 从 index.html 取出数据 ----------
def load_data():
    html = open(HTML, encoding='utf-8').read()
    script = re.findall(r'<script>(.*?)</script>', html, re.S)[-1]

    stub = """
function El(){this.textContent='';this.innerHTML='';this.className='';this.style={};this.dataset={};}
var document={getElementById:function(){return new El();},querySelectorAll:function(){return [];},addEventListener:function(){}};
var localStorage={getItem:function(){return null;},setItem:function(){}};
var window={scrollTo:function(){}};
function setInterval(){}
"""
    expr = "JSON.stringify({TPL:TPL, WEEKS:WEEKS, SCHOOL_EVENTS:SCHOOL_EVENTS})"
    body = stub + script

    tmp = os.path.join('/tmp', '_beikao_dump.js')

    # macOS：用 JavaScriptCore（osascript）。末尾表达式即返回值。
    if shutil.which('osascript'):
        open(tmp, 'w', encoding='utf-8').write(body + '\n' + expr + ';\n')
        r = subprocess.run(['osascript', '-l', 'JavaScript', tmp],
                           capture_output=True, text=True)
    # Linux/CI：用 node。需要显式打印。
    elif shutil.which('node'):
        open(tmp, 'w', encoding='utf-8').write(body + '\nconsole.log(' + expr + ');\n')
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
            cur = b' '          # 续行以一个空格开头
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
    tpl, weeks, school = data['TPL'], data['WEEKS'], data['SCHOOL_EVENTS']

    # WEEKS 里的具体日期优先（覆盖模板）
    override = {}
    for w in weeks:
        for d in w['days']:
            override[d['date']] = d['blocks']

    today = datetime.date.today()
    now_stamp = datetime.datetime.now().strftime('%Y%m%dT%H%M%SZ')
    events = []
    stats = {}

    for i in range(HORIZON_DAYS):
        day = today + datetime.timedelta(days=i)
        key = day.isoformat()

        blocks = override.get(key)
        if blocks is None:
            tname = PATTERN[day.weekday()]
            blocks = tpl.get(tname, [])
            src = tname
        else:
            src = 'override'

        for b in blocks:
            sm, em = to_min(b['s']), to_min(b['e'])
            start = datetime.datetime.combine(day, datetime.time()) + datetime.timedelta(minutes=sm)
            end = datetime.datetime.combine(day, datetime.time()) + datetime.timedelta(minutes=em)
            # 生活类不加前缀，学习/健身类加，方便在日历里一眼分辨
            label = b['t']
            events.append({
                'uid': uid(key, b['s'], label),
                'start': start, 'end': end,
                'summary': label,
                'desc': KIND_LABEL.get(b['k'], b['k']),
                'cat': KIND_LABEL.get(b['k'], b['k']),
            })
            stats[src] = stats.get(src, 0) + 1

    # 学校考试（全天事件）
    for e in school:
        d = datetime.datetime.strptime(e['date'], '%Y-%m-%d').date()
        if d < today or d > today + datetime.timedelta(days=HORIZON_DAYS):
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
    print('  来源分布: ' + '  '.join('%s=%d' % (k, v) for k, v in sorted(stats.items())))
