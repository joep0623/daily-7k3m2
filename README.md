# 备考日程

考研备考日程网页。零依赖单文件，四端可用。

**线上地址：https://joep0623.github.io/daily-7k3m2/**

---

## 每周怎么更新

每周日复盘时，把下周的安排告诉 Claude，剩下的不用你管：

1. Claude 修改 `index.html` 里的 `WEEKS` 数组（在**最前面**加一个新周对象，旧周保留可回看）
2. Claude 本地 commit
3. Claude 直接 `git push`（走 SSH 443，不需要你操作）

**你唯一要做的事：周日把下周安排说出来。**

如果哪天想自己推：打开 GitHub Desktop 点 **Push origin** 也行，两条路都通。

---

## 数据格式

在 `index.html` 的 `<script>` 顶部：

```js
const WEEKS = [
  {
    id: 0,
    title: '第 0 周 · 启动周',
    range: '10/8 – 10/11',
    note: '本周目标不是冲量，是把系统搭起来。',
    days: [
      {
        date: '2026-10-08',        // 必须是 YYYY-MM-DD
        label: '周四',              // 显示用的星期
        tag: '启动日',              // 可选，日期后面的小字
        blocks: [
          B('15:00','15:30','装墨墨背单词','study'),
          // B(开始, 结束, 内容, 类型)
        ],
        notes: ['今天的提醒，会显示在时间轴下方']
      },
    ]
  }
];
```

**类型（决定颜色）**：`study` 学习 · `body` 健身 · `love` 约会 · `school` 学校 · `life` 生活 · `rest` 自由 · `base` 底线

**跨夜时间**：`B('24:00','24:30', ...)` 表示次日 00:00–00:30。凌晨 0:00–7:00 会自动算作前一天。

**初试日期**：文件顶部 `const EXAM_DATE = '2028-12-23';` —— 改这一行，倒计时自动重算。

**阶段划分**：`const STAGES = [...]` —— 页面自动识别今天落在哪个阶段并高亮。

---

## 日历订阅（桌面小组件用）

网页在手机上要打开才能看。想直接在桌面小组件里看日程，订阅这个日历：

```
https://joep0623.github.io/daily-7k3m2/schedule.ics
```

系统日历自带原生的桌面小组件，会显示「当前事件 + 下一个事件」——正好是你要的。

**为什么用日历而不是做 App 小组件**：iOS 的小组件只有原生 App 能做。而系统日历订阅是**四端通用**（iPhone/安卓/Mac/Windows）+ 零安装 + 原生刷新。

### 文件从哪来

`gen_ics.py` 从 `index.html` 里提取数据生成，**数据源只有一个**，不会两套不同步。

```bash
cd ~/Documents/备考日程
python3 gen_ics.py     # 重新生成 schedule.ics
```

**每周更新完日程后要跑一次**，然后 commit + push。

---

## 部署现状（已上线）

| 项 | 值 |
|---|---|
| 仓库 | https://github.com/joep0623/daily-7k3m2 |
| 线上地址 | https://joep0623.github.io/daily-7k3m2/ |
| 分支 | `main`（`/(root)`） |
| 可见性 | Public（免费版 Pages 只支持公开仓库） |
| 本地路径 | `~/Documents/备考日程/` |

---

## ⚠️ 网络配置（重要，换电脑或重装系统要重做）

这台机器**直连 `github.com:443` 是间歇性不通的**（被限流），但 `ssh.github.com:443` 稳定可达。
所以 git 走的是 SSH over 443 隧道。

`~/.ssh/config` 里必须有这段：

```
Host github.com
  HostName ssh.github.com
  Port 443
  User git
```

验证命令：

```bash
ssh -T git@github.com
# 应返回：Hi joep0623! You've successfully authenticated...
```

如果以后 push 卡住，先跑上面这条命令自检。

---

## 加到主屏幕

- **iPhone / iPad**：Safari 打开网址 → 分享 → 添加到主屏幕
- **安卓**：Chrome 打开网址 → 右上角菜单 → 添加到主屏幕
- **Mac**：Safari 打开后「添加到程序坞」
- **Windows**：Edge/Chrome 打开后「安装为应用」
