"""Lançador do Ciello OS: é o que o ícone da área de trabalho e do menu Iniciar abre.

1. Se o Ciello OS já está aberto, só traz a janela de novo.
2. De tempos em tempos (padrão: 12 h) procura atualização no GitHub; se tiver, pergunta se quer atualizar.
3. Liga o servidor (central/escritorio/servidor.py) escondido, sem janela de CMD, e o servidor abre o Ciello OS numa
   janela própria do Edge/Chrome. Para desligar: menu Iniciar do Ciello OS, botão Desligar. O que o servidor escreve
   fica em estado/servidor.log.
"""
import os
import socket
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(AQUI))
import atualizacao  # noqa: E402

PORTA = 3200


def no_ar(porta=PORTA):
    try:
        with socket.create_connection(("127.0.0.1", porta), timeout=0.5):
            return True
    except OSError:
        return False


def python_console():
    return atualizacao.python_do_assistente(RAIZ)


def janela_do_app(url):
    """Mesma regra do servidor: Edge ou Chrome em modo app; senão, o navegador padrão."""
    candidatos = []
    for var in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        base = os.environ.get(var)
        if base:
            candidatos += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                           os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
    for exe in candidatos:
        if os.path.exists(exe):
            subprocess.Popen([exe, f"--app={url}", "--start-maximized"])
            return
    import webbrowser
    webbrowser.open(url)


def ligar_servidor():
    """python.exe com CREATE_NO_WINDOW: o console existe, mas sem janela, e o que o servidor roda (scripts, Claude Code,
    ffmpeg) herda esse console escondido em vez de abrir janela preta."""
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    servidor = RAIZ / "central" / "escritorio" / "servidor.py"
    log = RAIZ / "estado" / "servidor.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as saida:
        subprocess.Popen([python_console(), str(servidor)], cwd=RAIZ, env=env, stdin=subprocess.DEVNULL, stdout=saida,
                         stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for _ in range(60):  # até 30 s: na primeira vez o Windows Defender confere o Python
        if no_ar():
            return True
        time.sleep(0.5)
    return False


def avisar_que_nao_abriu():
    raiz_tk = tk.Tk()
    raiz_tk.withdraw()
    try:
        raiz_tk.iconbitmap(default=str(AQUI / "marca" / "ciello.ico"))
    except tk.TclError:
        pass
    messagebox.showerror("Ciello OS", "O Ciello OS não ligou.\n\nO motivo fica anotado em "
                         f"{RAIZ / 'estado' / 'servidor.log'}.\n\nSe faltar alguma biblioteca, abra no menu Iniciar: "
                         "Ciello OS > Reinstalar dependências.", parent=raiz_tk)
    raiz_tk.destroy()


def perguntar_atualizacao():
    """Procura (sem travar por mais de 6 s) e pergunta. Sem internet, segue em frente calado."""
    if not atualizacao.hora_de_verificar():
        info = atualizacao.estado().get("ultima_consulta") or {}
    else:
        info = atualizacao.verificar(tempo=6)
    if not info.get("nova"):
        return
    raiz_tk = tk.Tk()
    raiz_tk.withdraw()
    try:
        raiz_tk.iconbitmap(default=str(AQUI / "marca" / "ciello.ico"))
    except tk.TclError:
        pass
    sim = messagebox.askyesno("Ciello OS", f"Tem versão nova do Ciello OS: {info.get('versao')}.\n\n"
                              f"{info.get('titulo', '')}\n\nQuer ver e atualizar agora?\n"
                              "(Os seus dados não são tocados.)", parent=raiz_tk)
    raiz_tk.destroy()
    if sim:
        exe = Path(sys.executable)
        subprocess.run([str(exe), str(AQUI / "atualizador.pyw")], cwd=RAIZ)


def main():
    if no_ar():
        janela_do_app(f"http://127.0.0.1:{PORTA}")
        return
    try:
        perguntar_atualizacao()
    except Exception:  # noqa: BLE001  atualização nunca impede o Ciello OS de abrir
        pass
    if not ligar_servidor():
        avisar_que_nao_abriu()


if __name__ == "__main__":
    main()
