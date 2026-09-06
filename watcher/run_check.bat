@echo off
rem AI 福利雷达单轮检查（给 Windows 计划任务调用）
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python watch.py %* >> watcher.log 2>&1
