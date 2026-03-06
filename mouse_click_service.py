"""
Windows 系统托盘鼠标点击服务
用于防止系统休眠或保持活动状态
"""

import time
import threading
import logging
import sys
from datetime import datetime

try:
    import pyautogui
except ImportError:
    print("请先安装 pyautogui: uv pip install pyautogui")
    sys.exit(1)

try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
except ImportError:
    print("请先安装依赖: uv sync")
    sys.exit(1)

try:
    import keyboard
except ImportError:
    keyboard = None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mouse_click_service.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 禁用 pyautogui 的安全特性（移动到角落不会触发异常）
pyautogui.FAILSAFE = False


def create_icon_image(color='green'):
    """创建托盘图标图像"""
    size = 64
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # 根据状态选择颜色
    if color == 'green':
        fill_color = (76, 175, 80, 255)  # 运行中 - 绿色
    elif color == 'red':
        fill_color = (244, 67, 54, 255)  # 已停止 - 红色
    else:
        fill_color = (158, 158, 158, 255)  # 灰色
    
    # 绘制鼠标形状的图标
    # 外圈
    draw.ellipse([4, 4, size-4, size-4], fill=fill_color)
    # 内部小点（模拟鼠标点击）
    draw.ellipse([size//2-8, size//2-8, size//2+8, size//2+8], fill=(255, 255, 255, 255))
    
    return image


class MouseClickService:
    """鼠标点击服务类"""
    
    def __init__(self, interval: int = 60):
        """
        初始化服务
        
        Args:
            interval: 点击间隔时间（秒），默认 60 秒
        """
        self.interval = interval
        self.running = False
        self._thread = None
        self._click_count = 0
        self._start_time = None
        self._icon = None
        
    def _simulate_click(self):
        """模拟一次鼠标点击（在当前位置点击）"""
        try:
            # 获取当前鼠标位置
            x, y = pyautogui.position()
            
            # 在当前位置执行点击
            pyautogui.click(x, y)
            
            self._click_count += 1
            logger.info(f"第 {self._click_count} 次点击完成 - 位置: ({x}, {y})")
            
        except Exception as e:
            logger.error(f"点击失败: {e}")
    
    def _run_loop(self):
        """运行主循环"""
        logger.info(f"服务启动，点击间隔: {self.interval} 秒")
        
        # 首次启动时等待一段时间，避免与菜单操作冲突
        for _ in range(3):
            if not self.running:
                return
            time.sleep(1)
        
        while self.running:
            self._simulate_click()
            
            # 使用循环等待，方便及时响应停止信号
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)
        
        logger.info("服务已停止")
    
    def start(self):
        """启动服务"""
        if self.running:
            logger.warning("服务已在运行中")
            return
            
        self.running = True
        self._start_time = datetime.now()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("鼠标点击服务已启动")
        
        # 更新图标颜色
        if self._icon:
            self._icon.icon = create_icon_image('green')
    
    def stop(self):
        """停止服务"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info(f"服务停止，共执行 {self._click_count} 次点击")
        
        # 更新图标颜色
        if self._icon:
            self._icon.icon = create_icon_image('red')
    
    def get_status_text(self):
        """获取状态文本"""
        status = "运行中" if self.running else "已停止"
        runtime = ""
        if self._start_time and self.running:
            delta = datetime.now() - self._start_time
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            runtime = f"\n运行时长: {hours:02d}:{minutes:02d}:{seconds:02d}"
        
        return (
            f"状态: {status}\n"
            f"点击次数: {self._click_count}\n"
            f"点击间隔: {self.interval} 秒"
            f"{runtime}"
        )


class TrayApp:
    """系统托盘应用"""
    
    def __init__(self, interval: int = 60, auto_start: bool = True):
        """
        初始化托盘应用
        
        Args:
            interval: 点击间隔时间（秒）
            auto_start: 是否自动启动服务
        """
        self.service = MouseClickService(interval=interval)
        self.auto_start = auto_start
        self._icon = None
        self._hotkey_remove = None  # 仅用于标记是否已注册

    HOTKEY = "ctrl+f10"

    def _toggle_service(self, icon, item):
        """切换服务状态"""
        def do_toggle():
            if self.service.running:
                self.service.stop()
            else:
                self.service.start()
            # 更新菜单
            icon.update_menu()
        
        # 在新线程中执行，避免阻塞
        threading.Thread(target=do_toggle, daemon=True).start()
    
    def _get_toggle_text(self, item):
        """获取切换按钮文本"""
        return "停止服务" if self.service.running else "启动服务"
    
    def _show_status(self, icon, item):
        """显示状态信息（通过通知）"""
        status_text = self.service.get_status_text()
        icon.notify(status_text, "鼠标点击服务状态")
    
    def _quit(self, icon, item):
        """退出程序"""
        self._unregister_hotkey()
        self.service.stop()
        icon.stop()
    
    def _is_running(self, item):
        """检查服务是否在运行"""
        return self.service.running

    def _on_hotkey(self):
        """全局快捷键回调：切换服务状态"""
        def do_toggle():
            if self.service.running:
                self.service.stop()
                new_state = "已停止"
            else:
                self.service.start()
                new_state = "已启动"
            if self._icon:
                self._icon.update_menu()
                self._icon.notify(f"服务{new_state}", "鼠标点击服务 (Ctrl+F10)")

        threading.Thread(target=do_toggle, daemon=True).start()

    def _register_hotkey(self):
        """注册全局快捷键 Ctrl+F10"""
        if keyboard is None:
            return
        try:
            keyboard.add_hotkey(self.HOTKEY, self._on_hotkey)
            self._hotkey_remove = True
            logger.info("已注册全局快捷键 Ctrl+F10")
        except Exception as e:
            logger.warning("注册全局快捷键失败: %s", e)

    def _unregister_hotkey(self):
        """注销全局快捷键"""
        if keyboard is None or not self._hotkey_remove:
            return
        try:
            keyboard.remove_hotkey(self.HOTKEY)
        except Exception:
            pass
        self._hotkey_remove = None

    def run(self):
        """运行托盘应用"""
        # 创建初始图标（红色表示未运行）
        initial_color = 'green' if self.auto_start else 'red'
        icon_image = create_icon_image(initial_color)
        
        # 创建菜单
        menu = pystray.Menu(
            item(
                self._get_toggle_text,
                self._toggle_service,
                default=True  # 双击时执行
            ),
            item('显示状态', self._show_status),
            pystray.Menu.SEPARATOR,
            item(
                '运行中',
                None,
                enabled=False,
                visible=self._is_running,
                checked=lambda item: True
            ),
            pystray.Menu.SEPARATOR,
            item('退出', self._quit)
        )
        
        # 创建托盘图标
        self._icon = pystray.Icon(
            name='mouse_click_service',
            icon=icon_image,
            title='鼠标点击服务',
            menu=menu
        )
        
        # 将图标引用传递给服务
        self.service._icon = self._icon

        # 注册全局快捷键 Ctrl+F10
        self._register_hotkey()

        # 自动启动服务
        if self.auto_start:
            # 使用定时器延迟启动，确保图标已完全初始化
            def delayed_start():
                time.sleep(0.5)
                self.service.start()
                self._icon.update_menu()
            
            threading.Thread(target=delayed_start, daemon=True).start()
        
        logger.info("系统托盘应用已启动")
        
        # 运行托盘（阻塞）
        self._icon.run()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Windows系统托盘鼠标点击服务')
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=60,
        help='点击间隔时间（秒），默认 60 秒'
    )
    parser.add_argument(
        '--no-auto-start',
        action='store_true',
        help='启动后不自动开始点击服务'
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("  鼠标点击服务 (系统托盘模式)")
    print("=" * 50)
    print(f"  点击间隔: {args.interval} 秒")
    print(f"  自动启动: {'否' if args.no_auto_start else '是'}")
    print("  程序将在系统托盘运行，右键图标查看菜单")
    print("=" * 50)
    
    app = TrayApp(
        interval=args.interval,
        auto_start=not args.no_auto_start
    )
    app.run()


if __name__ == '__main__':
    main()
