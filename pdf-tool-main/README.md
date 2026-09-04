# PDF 工具

基于 Python、PySide6 与 QFluentWidgets 的跨平台 PDF 与文档处理桌面应用，界面为简体中文。项目采用分层架构：

- `ui/`：QFluentWidgets 页面与主窗口，只负责界面交互
- `services/`：PDF 处理、OCR、文档互转等业务逻辑
- `utils/`：错误处理、路径/文件工具、依赖检测、后台线程任务
- `main.py`：仅作为程序入口，不再包含业务代码

---

## 功能一览

### PDF 工具

- 合并 PDF
- 拆分 PDF（逐页保存或提取页码范围）
- 提取文本（TXT / DOCX）
- 提取图片（PNG / JPG / TIFF / WebP）
- 压缩 PDF
- 旋转页面
- 文字水印 / 图片水印
- 添加或移除 PDF 密码
- 页面排序
- 查看与编辑元数据
- 删除空白页
- 修复损坏 PDF
- 图片转 PDF
- 裁剪页边距
- OCR 识别
- 比较 PDF
- 遮盖敏感内容
- 添加页码
- 添加签名
- N 合 1 拼版
- 书签管理 / 按书签拆分

### 文档互转

- PDF 转 Word
- PDF 转 Excel
- PDF 转 PPT
- PDF 转 TXT
- PDF 转图片（PNG / JPG）
- 图片转 PDF
- Office（Word / Excel / PPT）转 PDF
- PDF 转 HTML
- PDF 转 EPUB

---

## 项目结构

```text
pdf-tool/
├── main.py                     # Qt 入口
├── bootstrap.py                # 一键创建 .venv、安装依赖并启动
├── requirements.txt
├── ui/
│   ├── main_window.py          # QFluentWidgets 主窗口与导航
│   ├── settings_dialog.py      # 全局设置对话框
│   ├── selftest_page.py        # 程序自测页面
│   ├── common/
│   │   ├── job_page.py         # 通用后台任务页
│   │   ├── notifications.py    # InfoBar / 弹窗
│   │   └── tool_page.py        # 紧凑输入区/输出/参数页
│   └── pages/
│       ├── pdf_tools.py        # PDF 工具动态页面
│       ├── document_convert.py # 文档互转页面
│       └── custom_pages.py     # 排序、遮盖、书签等专用页
├── services/
│   ├── pdf_service.py          # 合并/拆分/压缩/旋转/密码等
│   ├── overlay_service.py      # 水印/页码/签名/遮盖/N合1
│   ├── content_service.py      # 提取/OCR/比较/信息
│   ├── convert_service.py      # PDF转Word/Excel/PPT/HTML/EPUB等
│   └── document_service.py     # 图片转PDF、Office转PDF
└── utils/
    ├── deps.py                 # Tesseract / LibreOffice / Python包检测
    ├── errors.py               # 统一错误转换
    ├── files.py                # 路径与文件类型工具
    ├── logger.py               # 统一日志与全局异常钩子
    ├── selftest.py             # 环境自测
    ├── settings.py             # settings.json 配置
    └── workers.py              # QThread 后台任务
```

---

## 界面与运维

- 左侧侧栏采用紧凑标签：每条标签都带 📌 置顶按钮；点击后置顶，最多 5 个，最新置顶排在最上方，其余标签在下方滚动区显示。
- 右侧工具输入区已极致压缩，只保留一个“＋ 添加输入文件”按钮，文件数量以紧凑文本展示。
- “程序设置”可配置启动时自测、日志文件上限，配置保存在项目根目录 `settings.json`。
- 全局异常与业务异常统一写入 `logs/app.log`，设置对话框中可导出日志。
- “运行自测”会检测 Python 依赖、Tesseract、LibreOffice、目录权限和 UI 模块导入情况，并以中文列出风险点。

---

## 运行

推荐一键启动：

```bat
python bootstrap.py
```

手动方式：

```bash
python -m venv .venv
```

Windows：

```bash
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

Linux / macOS：

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

---

## 外部系统依赖

以下依赖不能通过 pip 安装：

- **LibreOffice**：Office 转 PDF 使用。Windows 安装后工具自动检测 `C:\Program Files\LibreOffice\program\soffice.exe`；Linux 可安装 `libreoffice`；macOS 安装到 Applications 即可。
- **Tesseract OCR**：OCR 功能需要。Windows 推荐 https://github.com/UB-Mannheim/tesseract/wiki 。

缺失时界面会给出中文提示，不影响其他功能。

---

## 已知限制

- PDF 转 Word / Excel 是文本、段落与基础表格识别，无法做到商业级高保真版式还原。
- PDF 转 PPT 采用页面渲染成图片后放入幻灯片，文字不可再次编辑。
- PDF 转 HTML / EPUB 导出文本与可提取的内嵌图片，复杂双栏、公式与图文混排不保证完整还原。
- 扫描版或纯图片 PDF 没有文本层，转 Word / Excel / TXT / HTML / EPUB 时可能为空。
- 加密 PDF 需先移除密码，程序不做密码破解。
- OCR 需要本机 Tesseract 与对应语言包。

---

## 许可证

MIT。
