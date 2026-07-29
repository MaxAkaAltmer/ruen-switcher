import urllib.request
import time
import json
import subprocess
import threading
from pynput import keyboard

# Настройки подключения к вашему systemd-сервису
API_URL_FIX = "http://localhost:18888/fix"
API_URL_INVERT = "http://localhost:18888/invert"

def call_fastapi_service(url, text):
    try:
        data = json.dumps({"text": text}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=1.5) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8')).get("result", "")
    except Exception:
        pass
    return ""

def process_selected_text(endpoint_url):
    try:
        old_clip = subprocess.check_output(['xclip', '-selection', 'clipboard', '-o'], stderr=subprocess.DEVNULL, text=True)
    except Exception:
        old_clip = ""

    # Очищаем буфер перед копированием
    subprocess.run(['xclip', '-selection', 'clipboard', '/dev/null'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Копируем выделенный текст
    subprocess.run(['xdotool', 'key', '--clearmodifiers', 'ctrl+c'])
    time.sleep(0.06)

    try:
        selected = subprocess.check_output(['xclip', '-selection', 'clipboard', '-o'], stderr=subprocess.DEVNULL, text=True)
    except Exception:
        selected = ""

    # ПРЕДОХРАНИТЕЛЬ: если из-за автоповтора вызвался второй поток,
    # текст уже снят/заменен, буфер пуст — поток просто молча завершается!
    if not selected or not selected.strip():
        if old_clip:
            p = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE, text=True)
            p.communicate(input=old_clip)
        return

    fixed = call_fastapi_service(endpoint_url, selected)

    if fixed and fixed != selected:
        p = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE, text=True)
        p.communicate(input=fixed)
        subprocess.run(['xdotool', 'key', '--clearmodifiers', 'ctrl+v'])
        time.sleep(0.06) 

    if old_clip:
        p = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE, text=True)
        p.communicate(input=old_clip)

def on_press(key):
    try:
        # 1. Нажатие Scroll Lock -> Инверсия раскладки
        if key == keyboard.Key.scroll_lock:
            threading.Thread(target=process_selected_text, args=(API_URL_INVERT,), daemon=True).start()
            
        # 2. Нажатие Pause / Break -> Умное исправление опечаток
        elif key == keyboard.Key.pause:
            threading.Thread(target=process_selected_text, args=(API_URL_FIX,), daemon=True).start()
    except Exception:
        pass


if __name__ == "__main__":
    print("==================================================")
    print(" УЛЬТРА-ЛЕГКИЙ КЛИЕНТ БЕЗ ЛИШНИХ ПРОВЕРОК ЗАПУЩЕН")
    print("==================================================")
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()



