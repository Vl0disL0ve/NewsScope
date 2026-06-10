"""
Скрипт для скачивания моделей перед первым запуском
Запусти один раз: python download_models.py
"""

import os
from sentence_transformers import SentenceTransformer
from pathlib import Path

def download_embeddings_model():
    print("📥 Скачиваю модель для эмбеддингов...")
    print("   Модель: paraphrase-multilingual-MiniLM-L12-v2")
    print("   Размер: ~470 MB")
    print("   Это может занять несколько минут...")
    
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    
    # Сохраняем локально
    model_path = Path("ml_models/paraphrase-multilingual-MiniLM-L12-v2")
    model_path.mkdir(parents=True, exist_ok=True)
    model.save(str(model_path))
    
    print(f"✅ Модель сохранена в {model_path}")
    return model

def check_ollama():
    """Проверяет, установлен ли Ollama"""
    import subprocess
    import sys
    
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Ollama установлен: {result.stdout.strip()}")
            return True
        else:
            print("❌ Ollama не найден")
            return False
    except FileNotFoundError:
        print("❌ Ollama не установлен")
        return False

def download_llm_model():
    """Скачивает LLM модель через Ollama"""
    import subprocess
    
    model_name = "gemma2:2b"
    print(f"\n📥 Скачиваю LLM модель: {model_name}")
    print("   Размер: ~1.6 GB")
    print("   Это может занять 5-10 минут...")
    
    result = subprocess.run(["ollama", "pull", model_name], capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ Модель {model_name} загружена")
        return True
    else:
        print(f"❌ Ошибка: {result.stderr}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 УСТАНОВКА МОДЕЛЕЙ ДЛЯ AI")
    print("=" * 50)
    
    # 1. SentenceTransformer
    print("\n1️⃣ Эмбеддинг модель:")
    download_embeddings_model()
    
    # 2. Проверка Ollama
    print("\n2️⃣ LLM модель (Ollama):")
    if check_ollama():
        download_llm_model()
    else:
        print("\n⚠️ Установи Ollama с https://ollama.com")
        print("   После установки запусти:")
        print("   ollama pull gemma2:2b")
    
    print("\n" + "=" * 50)
    print("🎉 ГОТОВО! Теперь можно запускать кластеризацию")
    print("=" * 50)