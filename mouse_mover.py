#!/usr/bin/env python3
"""
鼠标防休眠脚本
每5秒钟将鼠标向右移动10像素，防止电脑进入休眠状态
"""

import time
import sys

try:
    import pyautogui
except ImportError:
    print("需要安装 pyautogui 库")
    print("请运行: pip3 install pyautogui")
    sys.exit(1)

def main():
    print("鼠标防休眠脚本已启动")
    print("每5秒钟将鼠标向右移动10像素")
    print("按 Ctrl+C 停止脚本")
    
    # 设置 pyautogui 的安全设置
    pyautogui.FAILSAFE = True  # 将鼠标移到左上角可以中断脚本
    pyautogui.PAUSE = 0.1      # 每次操作后暂停0.1秒
    
    try:
        while True:
            # 获取当前鼠标位置
            x, y = pyautogui.position()
            # 向右移动10像素
            pyautogui.moveTo(x + 10, y, duration=0.1)
            print(f"鼠标已移动到: ({x + 10}, {y})")
            # 等待5秒
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n脚本已停止")
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    main()