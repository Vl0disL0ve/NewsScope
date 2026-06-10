@echo off
chcp 65001

echo ========================================
echo     ЗАПУСК ТЕСТОВ NewsScope
echo ========================================
echo.
echo Выберите тест:
echo 1 - Все тесты
echo 2 - Только CRUD
echo 3 - Только парсер
echo 4 - Только кластеризация
echo.
set /p choice="Ваш выбор (1-4): "

if "%choice%"=="1" python tests\run_tests.py
if "%choice%"=="2" python tests\run_tests.py crud
if "%choice%"=="3" python tests\run_tests.py parser
if "%choice%"=="4" python tests\run_tests.py clustering

pause