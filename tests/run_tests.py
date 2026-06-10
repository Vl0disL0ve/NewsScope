#!/usr/bin/env python
"""
Запуск всех тестов из папки tests/
Использование:
    python tests/run_tests.py
    python tests/run_tests.py crud
    python tests/run_tests.py parser
    python tests/run_tests.py clustering
"""

import subprocess
import sys
from pathlib import Path

def run_test(test_name: str):
    """Запускает конкретный тест"""
    test_file = Path(__file__).parent / f"test_{test_name}.py"
    if not test_file.exists():
        print(f"❌ Тест {test_name} не найден")
        return False
    
    result = subprocess.run([sys.executable, str(test_file)])
    return result.returncode == 0

def run_all_tests():
    """Запускает все тесты по порядку"""
    tests = ["crud", "parser", "clustering"]
    results = {}
    
    print("\n" + "=" * 60)
    print("🚀 ЗАПУСК ВСЕХ ТЕСТОВ")
    print("=" * 60)
    
    for test in tests:
        print(f"\n▶️ Запуск {test.upper()}...")
        results[test] = run_test(test)
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ:")
    for test, passed in results.items():
        status = "✅ ПРОЙДЕН" if passed else "❌ ПРОВАЛЕН"
        print(f"   {test.upper()}: {status}")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        run_test(test_name)
    else:
        run_all_tests()