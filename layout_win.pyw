import os
import sys
import ctypes
import time
import json
import urllib.request
# Используем специализированные библиотеки для Windows
import keyboard  
import pyperclip 

API_URL_FIX = "http://127.0.0.1:18888/fix"
API_URL_INVERT = "http://127.0.0.1:18888/invert"

def call_fastapi_service(url, text):
    try:
        data = json.dumps({"text": text}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=1.5) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8')).get("result", "")
    except Exception as e:
        print(f"[Ошибка сети]: {e}")
    return ""

def process_selected_text(endpoint_url):
    try:
        # 1. Сохраняем старый буфер обмена
        old_clip = pyperclip.paste()
        pyperclip.copy("")
        time.sleep(0.05)

        # 2. Имитируем Ctrl+C. 
        # Библиотека keyboard сама отпустит физические Scroll Lock/Pause, чтобы не мешать Windows
        keyboard.press('ctrl')
        time.sleep(0.02)
        keyboard.send(46) 
        time.sleep(0.02)
        keyboard.release('ctrl')
        
        time.sleep(0.08)  # Пауза, чтобы Windows успела записать текст в буфер

        selected = pyperclip.paste()

        # Предохранитель от пустого выделения
        if not selected or not selected.strip():
            pyperclip.copy(old_clip)
            print("[Лог]: Текст не выделен.")
            return

        #print(f"[Лог]: Отправка текста на сервер: {selected[:20]}...")
        fixed = call_fastapi_service(endpoint_url, selected)

        # 3. Если текст изменился — производим замену
        if fixed and fixed != selected:
            pyperclip.copy(fixed)
            time.sleep(0.05)
            
            # Вставляем исправленный текст
            keyboard.press('ctrl')
            time.sleep(0.02)
            keyboard.send(47)
            time.sleep(0.02)
            keyboard.release('ctrl')
            time.sleep(0.08)
            #print(f"[Лог]: Успешно заменено на: {fixed[:20]}...")
            
        # 4. Восстанавливаем исходный буфер обмена пользователя
        pyperclip.copy(old_clip)
    except Exception as e:
        print(f"[Критическая ошибка]: {e}")

if __name__ == "__main__":
    # Автоматический запрос прав администратора для Windows


    print("==================================================")
    print("            WINDOWS-КЛИЕНТ ЗАПУЩЕН")
    print(" Перехват: Scroll Lock (Invert) / Pause (Fix)")
    print("==================================================")

    # Регистрируем глобальные горячие клавиши напрямую через ОС (работает без зависаний потоков)
    keyboard.add_hotkey('scroll lock', lambda: process_selected_text(API_URL_INVERT))
    keyboard.add_hotkey('pause', lambda: process_selected_text(API_URL_FIX))

    # Удерживаем скрипт запущенным
    keyboard.wait()
