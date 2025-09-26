# client_auto.py
import websocket, json, uuid, time, io, base64, os
from tkinter import Tk, messagebox
from PIL import Image
import pyautogui

# Lê configuração de config.json (ver exemplo abaixo)
CONFIG_PATH = "config.json"
DEFAULT = {
    "SERVER_WS": "ws://localhost:8080",
    "INTERVAL": 5,
    "CLIENT_NAME": "Cliente Remoto",
    "ASK_FIRST_TIME": True,
    "JPEG_QUALITY": 60
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except:
            cfg = DEFAULT
    else:
        cfg = DEFAULT
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    return cfg

cfg = load_config()
SERVER_WS = cfg.get("SERVER_WS")
INTERVAL = float(cfg.get("INTERVAL", 5))
CLIENT_NAME = cfg.get("CLIENT_NAME", "Cliente Remoto")
ASK_FIRST = bool(cfg.get("ASK_FIRST_TIME", True))
JPEG_QUALITY = int(cfg.get("JPEG_QUALITY", 60))

CLIENT_ID = str(uuid.uuid4())[:8]

def ask_permission_once():
    if not ASK_FIRST:
        return True
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    allowed = messagebox.askyesno("Assistência Remota", 
        "O programa irá enviar capturas do ecrã ao técnico.\nDeseja permitir?")
    root.destroy()
    return allowed

def capture_jpeg_base64(quality=60, max_w=None):
    img = pyautogui.screenshot()
    # opcional: reduzir resolução para economizar largura de banda
    if max_w and img.width > max_w:
        ratio = max_w / img.width
        img = img.resize((int(img.width*ratio), int(img.height*ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return b64

def on_open(ws):
    # regista-se como client
    ws.send(json.dumps({"type":"register_client","name":CLIENT_NAME, "clientId": CLIENT_ID}))
    print("Registo enviado.")

def on_message(ws, message):
    # possibilidade de receber comandos remotos (ex.: parar, mudar intervalo)
    try:
        msg = json.loads(message)
    except:
        return
    if msg.get("type") == "command":
        cmd = msg.get("cmd")
        if cmd == "stop":
            print("Recebido stop. Fechando.")
            ws.close()

def run():
    if not ask_permission_once():
        print("Utilizador negou envio. A terminar.")
        return

    ws = websocket.WebSocketApp(SERVER_WS, on_open=on_open, on_message=on_message)
    # abrir em thread para podermos fazer loop de envio
    def _run():
        ws.run_forever()
    import threading
    t = threading.Thread(target=_run, daemon=True)
    t.start()

    # esperar até WS abrir
    while not ws.sock or not getattr(ws.sock, "connected", False):
        time.sleep(0.1)

    print("Conetado ao servidor. Iniciando envio automático de screenshots.")
    try:
        while True:
            b64 = capture_jpeg_base64(quality=JPEG_QUALITY, max_w=1280)
            payload = {"type":"screenshot","clientId":CLIENT_ID,"image":b64}
            try:
                ws.send(json.dumps(payload))
            except Exception as e:
                print("Erro ao enviar:", e)
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("Terminado manualmente.")
    except Exception as e:
        print("Erro principal:", e)
    finally:
        try:
            ws.close()
        except:
            pass

if __name__ == "__main__":
    run()
