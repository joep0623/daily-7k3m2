# 备考日程

一个零依赖的单文件网页，用来查看考研备考日程。

## 文件说明

- `index.html` —— 全部内容都在这一个文件里（样式、逻辑、数据）。不需要装任何东西，双击就能打开。

## 每周怎么更新

每周日复盘时，把下周的安排告诉 Claude，Claude 会：

1. 修改 `index.html` 里的 `WEEKS` 数组，在**最前面**加一个新周对象（旧周保留，可以回看）
2. 本地 commit

你只需要在自己电脑上点一下 **Push**（用 GitHub Desktop），或把 `index.html` 重新上传到 GitHub 仓库覆盖旧文件。

### 数据格式

在 `index.html` 的 `<script>` 顶部，找到这段：

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

## 部署到 GitHub Pages

1. 登录 github.com，New repository
2. 仓库名建议用不好猜的，比如 `daily-7k3m2x`；选 **Public**；Create
3. 在仓库页点 **uploading an existing file**，把 `index.html` 拖进去，Commit
4. **Settings → Pages** → Source 选 `Deploy from a branch`，Branch 选 `main` / `(root)`，Save
5. 等 1–2 分钟，访问 `https://你的用户名.github.io/仓库名/`

## 加到主屏幕

- **iPhone / iPad**：Safari 打开网址 → 分享 → 添加到主屏幕
- **安卓**：Chrome 打开网址 → 右上角菜单 → 添加到主屏幕
- **Mac**：Safari 打开后「添加到程序坞」
- **Windows**：Edge/Chrome 打开后「安装为应用」
