@echo off
chcp 65001 >nul
title ACM考勤统计系统 - 模拟登录获取认证

echo ========================================
echo ACM考勤统计系统 - 模拟登录获取认证
echo ========================================
echo.

echo 正在检查环境...
if not exist "Constant.ini" (
    echo ❌ 错误: 未找到 Constant.ini 配置文件
    echo 请确保在正确的项目目录中运行此脚本
    pause
    exit /b 1
)

if not exist "chromedriver-win64\chromedriver.exe" (
    echo ❌ 错误: 未找到 ChromeDriver
    echo 请确保 chromedriver-win64 文件夹在项目目录中
    pause
    exit /b 1
)

if not exist "模拟登录获取认证.py" (
    echo ❌ 错误: 未找到 模拟登录获取认证.py 脚本
    pause
    exit /b 1
)

echo ✅ 环境检查通过
echo.

echo 正在启动模拟登录获取认证脚本...
echo 注意: 脚本将在新窗口中运行
echo.

python "模拟登录获取认证.py"

echo.
echo 认证信息获取脚本执行完成
echo 按任意键退出...
pause >nul

