# 前端未同步更新排障手册

本文记录本项目 Web Demo 遇到的典型问题：代码已经修改，但浏览器页面仍然显示旧布局、旧 JS 行为或局部更新。下次遇到类似情况时，按本文 checklist 快速定位。

## 典型现象

- HTML 结构看起来部分更新了，但 CSS 布局没有变化。
- 页面文案变了，但按钮行为仍是旧逻辑。
- ES module 拆分后，入口 `app.js` 已更新，但子模块仍运行旧版本。
- 服务已重启，测试也通过，但浏览器刷新后仍像没改。

本次实际案例是 `Agent 调用链`：`index.html` 已出现新结构，但浏览器仍按旧 CSS/旧 JS 模块图渲染，导致用户看到“完全没有改”。

## 根因判断

这种问题通常不是后端业务逻辑问题，而是静态资源同步链路问题：

1. 浏览器缓存了 `/styles.css` 或 `/app.js`。
2. ES module 子依赖仍使用旧缓存，例如 `app.js` 更新了，但 `./js/renderers/result.js` 或 `./js/renderers/trace.js` 没有重新拉取。
3. 本地服务没有返回禁用缓存的响应头。
4. 端口上可能还跑着旧服务进程。

判断原则：如果接口返回的数据正常，但页面表现旧，优先查静态资源版本和缓存头。

## 快速处理 Checklist

### 1. 给入口静态资源加版本号

在 `web_demo/static/index.html` 中确认：

```html
<link rel="stylesheet" href="/styles.css?v=your-version" />
<script type="module" src="/app.js?v=your-version"></script>
```

版本号建议带上本次改动语义，例如：

```text
agent-trace-aligned-20260510
```

### 2. 给 ES module 子依赖也加版本号

只给 `app.js` 加版本号不够。`app.js` 内部 import 的模块也要同步加版本号：

```js
import { nodes } from "./js/dom.js?v=your-version";
import { renderResult } from "./js/renderers/result.js?v=your-version";
```

如果子模块继续 import 其他模块，也要继续传递版本号：

```js
import { renderMarkdown } from "../markdown.js?v=your-version";
import { renderAlignedTrace } from "./trace.js?v=your-version";
```

### 3. 服务端返回 no-store

在 `web_demo/server.py` 的 `WebDemoHandler` 中确认：

```python
def end_headers(self):
    self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
    self.send_header("Pragma", "no-cache")
    self.send_header("Expires", "0")
    super().end_headers()
```

这能避免本地演示阶段浏览器继续复用旧文件。

### 4. 重启目标端口服务

确认杀掉旧的 `8031` 进程后再启动：

```powershell
$pids = netstat -ano | Select-String ":8031" | ForEach-Object { ($_ -split '\s+')[-1] } | Where-Object { $_ -match '^\d+$' -and $_ -ne '0' } | Sort-Object -Unique
foreach ($pidValue in $pids) { Stop-Process -Id ([int]$pidValue) -Force -ErrorAction SilentlyContinue }
Start-Process -FilePath "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -ArgumentList @("-m","web_demo.server","--host","127.0.0.1","--port","8031") -WorkingDirectory "E:\claudeCode\weilaiAgent" -WindowStyle Hidden
```

### 5. 用接口确认浏览器拿到的是新资源

不要只看页面，先验证服务端真实返回：

```powershell
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8031/', timeout=10); html=r.read().decode('utf-8'); print(r.status, r.headers.get('Cache-Control')); print('version=', 'your-version' in html)"
```

继续检查 CSS/JS：

```powershell
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -c "import urllib.request; js=urllib.request.urlopen('http://127.0.0.1:8031/js/renderers/trace.js?v=your-version', timeout=10).read().decode('utf-8'); print('new_logic=', 'renderAlignedTrace' in js)"
```

只有这些检查通过后，才能说明服务端已提供新资源。

## 测试保护

本项目已经增加相关测试，避免再次出现“代码改了但前端未同步”的问题：

- `tests/test_web_demo_markup.py`
  - 检查 `index.html` 是否使用带版本号的 `styles.css` 和 `app.js`。
  - 检查 Agent 调用链是否使用新结构。
- `tests/test_web_demo_frontend_logic.py`
  - 检查入口模块和子模块是否带版本号。
  - 检查 Agent 调用链是否使用对齐渲染逻辑。
- `tests/test_web_server_config.py`
  - 检查 `WebDemoHandler.end_headers` 是否返回 `Cache-Control: no-store`。

建议修改前端后至少运行：

```powershell
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests\test_web_demo_markup.py tests\test_web_demo_frontend_logic.py tests\test_web_server_config.py -q
```

交付前运行全量测试：

```powershell
$basetemp = Join-Path (Get-Location) ("pytest-tmp-" + [guid]::NewGuid().ToString("N"))
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests --basetemp=$basetemp
```

## 排查顺序

遇到“前端没变”时，不要先猜 CSS 写错，按下面顺序排查：

1. `git diff` 确认文件确实改了。
2. `index.html` 确认入口资源版本号变了。
3. `app.js` 确认所有子模块 import 版本号同步变了。
4. `server.py` 确认有 `no-store`。
5. 重启端口服务，避免旧进程占用。
6. 用 `urllib` 检查 HTML/CSS/JS 返回内容。
7. 再打开浏览器刷新页面验证。

## 经验结论

前端模块化以后，缓存问题会从“一个 CSS/JS 文件没更新”变成“入口更新了，但某个子模块没更新”。所以本项目后续只要改动 `web_demo/static/js/**` 中的渲染逻辑，就应该同步更新静态资源版本号，并用测试锁住版本链路。
