@echo off
REM Windowsタスクスケジューラから呼び出す用のラッパー。
REM このバッチファイルがあるフォルダ(feed-auto\scripts)に移動してから実行し、
REM 標準出力・エラーを feed-auto\logs\task_scheduler.log に追記する。

cd /d "%~dp0"
python post_to_instagram.py >> "%~dp0..\logs\task_scheduler.log" 2>&1
