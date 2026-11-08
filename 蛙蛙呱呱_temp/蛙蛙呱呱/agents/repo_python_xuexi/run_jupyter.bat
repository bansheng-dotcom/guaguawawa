@echo off
call "%~dp0venv\Scripts\activate.bat"
start jupyter lab "%~dp0notebooks"
