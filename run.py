import threading
import time
import webbrowser
import config
from app import create_app


def _open_browser():
    time.sleep(1.5)
    webbrowser.open(f"http://{config.HOST}:{config.PORT}")


if __name__ == "__main__":
    app = create_app()
    threading.Thread(target=_open_browser, daemon=True).start()
    print(f"\n  WH INFO rodando em http://{config.HOST}:{config.PORT}")
    print(f"  Dados em: {config.DATA_DIR}\n")
    app.run(host=config.HOST, port=config.PORT, debug=False, use_reloader=False)
