@echo off
set CURRENT_DIR=%CD%
echo ***** Current directory: %CURRENT_DIR% *****
set PYTHONPATH=%CURRENT_DIR%

rem set HF_ENDPOINT=https://hf-mirror.com
python -m streamlit run .\webui\main.py --server.port 9999 --browser.gatherUsageStats=False --server.enableCORS=True