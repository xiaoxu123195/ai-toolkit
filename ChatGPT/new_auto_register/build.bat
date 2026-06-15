@echo off
chcp 65001 >nul
REM ============================================================
REM  打包 gptregister.exe (Windows, PyInstaller, 单文件)
REM  用自带 tkinter 的标准 Python 3.13 构建; 依赖系统 node 运行。
REM ============================================================
setlocal

set "PY=C:\Python313\python.exe"
if not exist "%PY%" set "PY=py -3.13"

echo [1/3] 安装/更新依赖...
%PY% -m pip install -U curl_cffi pyyaml pyinstaller ttkbootstrap || goto :err

echo [2/3] 清理旧产物...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist gptregister.spec del /q gptregister.spec

echo [3/3] 打包 gptregister.exe ...
%PY% -m PyInstaller --noconfirm --onefile --windowed --name gptregister ^
  --add-data "openai_sentinel_quickjs.js;." ^
  --collect-all curl_cffi ^
  --collect-all ttkbootstrap ^
  gui.py || goto :err

echo.
echo 完成! 产物: dist\gptregister.exe
echo 把 config.yaml 放到 gptregister.exe 同级目录(首次运行也会自动生成)。
echo 运行机器需已安装 node 并在 PATH 中。
goto :eof

:err
echo.
echo 构建失败, 请查看上面的错误输出。
exit /b 1
