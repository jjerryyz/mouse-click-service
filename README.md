# 鼠标点击服务

Windows 系统托盘应用，定时模拟鼠标点击，防止系统休眠或保持活动状态。

## 功能特性

- 系统托盘运行，不占用任务栏空间
- 右键菜单控制启动/停止服务
- 双击托盘图标快速切换状态
- 显示运行状态和点击统计
- 可自定义点击间隔时间

## 安装

```bash
# 使用 uv 安装依赖
uv sync
```

## 使用方法

### 基本运行

```bash
uv run python mouse_click_service.py
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-i, --interval` | 点击间隔时间（秒） | 60 |
| `--no-auto-start` | 启动后不自动开始服务 | 自动启动 |

### 示例

```bash
# 每 30 秒点击一次
uv run python mouse_click_service.py -i 30

# 启动但不自动开始服务（手动控制）
uv run python mouse_click_service.py --no-auto-start
```

## 托盘菜单

右键点击系统托盘图标可见菜单：

- **启动服务/停止服务** - 切换服务状态
- **显示状态** - 显示当前状态信息通知
- **退出** - 停止服务并退出程序

双击图标可快速切换服务状态。

## 图标状态

- 绿色圆点：服务运行中
- 红色圆点：服务已停止

## 日志

运行日志保存在 `mouse_click_service.log` 文件中。

## 打包为可执行文件

可以使用 PyInstaller 打包为独立的 exe 文件：

```bash
uv pip install pyinstaller
uv run pyinstaller --noconsole --onefile --icon=NONE mouse_click_service.py
```

打包后的 exe 文件在 `dist` 目录下。
