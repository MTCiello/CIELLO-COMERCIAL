"""Rotinas automáticas do Ciello OS no Agendador de Tarefas do Windows, sem janela preta.

  "Ciello Bom Dia"  todo dia às 7h, o briefing do gerente (central/briefing.py) -> estado/briefing/
  "Ciello Piloto"   de hora em hora, o piloto automático da rede social (central/piloto.py rodar)

  rotinas.pyw ligar      cria ou atualiza as duas tarefas (o instalador faz isso se a opção estiver marcada)
  rotinas.pyw desligar   apaga as duas tarefas (o desinstalador também apaga)
  rotinas.pyw status     diz se estão ligadas
  rotinas.pyw rodar bom-dia|piloto   o que o Agendador chama: roda a rotina escondida e anota em estado/rotinas.log

O Agendador abre o pythonw.exe (sem console), e este arquivo roda o python.exe com CREATE_NO_WINDOW: assim nem a
rotina nem o que ela chama (Claude Code, ffmpeg, node) abrem janela de CMD.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
ROTINAS = {
    "bom-dia": ("Ciello Bom Dia", ["/SC", "DAILY", "/ST", "07:00"], ["central/briefing.py"]),
    "piloto": ("Ciello Piloto", ["/SC", "HOURLY", "/MO", "1", "/ST", "00:05"], ["central/piloto.py", "rodar"]),
}


def python(janela=False):
    pasta = RAIZ / ".venv" / "Scripts"
    exe = pasta / ("python.exe" if janela else "pythonw.exe")
    if exe.exists():
        return str(exe)
    atual = Path(sys.executable)
    outro = atual.with_name("python.exe" if janela else "pythonw.exe")
    return str(outro if outro.exists() else atual)


def schtasks(*args):
    r = subprocess.run(["schtasks", *args], capture_output=True, text=True, errors="replace", creationflags=SEM_JANELA)
    return r.returncode, (r.stdout + r.stderr).strip()


def ligar():
    if os.name != "nt":
        return 1, "As rotinas automáticas usam o Agendador de Tarefas do Windows."
    linhas, falhas = [], 0
    for chave, (nome, quando, _) in ROTINAS.items():
        alvo = f'"{python()}" "{Path(__file__).resolve()}" rodar {chave}'
        codigo, saida = schtasks("/Create", "/F", "/TN", nome, "/TR", alvo, *quando)
        falhas += bool(codigo)
        linhas.append(f"{nome}: {'ligada' if not codigo else 'não deu para criar (' + saida + ')'}")
    linhas.append("O Bom dia sai todo dia às 7h em estado/briefing/ e o piloto roda de hora em hora, sem abrir janela.")
    return falhas, "\n".join(linhas)


def desligar():
    if os.name != "nt":
        return 0, "Nada para desligar fora do Windows."
    linhas = []
    for nome, _, _ in ROTINAS.values():
        codigo, _ = schtasks("/Delete", "/F", "/TN", nome)
        linhas.append(f"{nome}: {'desligada' if not codigo else 'já estava desligada'}")
    return 0, "\n".join(linhas)


def status():
    if os.name != "nt":
        return 0, "As rotinas automáticas usam o Agendador de Tarefas do Windows."
    return 0, "\n".join(f"{nome}: {'ligada' if schtasks('/Query', '/TN', nome)[0] == 0 else 'desligada'}"
                        for nome, _, _ in ROTINAS.values())


def rodar(chave):
    nome, _, args = ROTINAS[chave]
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    log = RAIZ / "estado" / "rotinas.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(f"\n==== {nome} · {time.strftime('%Y-%m-%d %H:%M:%S')} ====\n")
        f.flush()
        r = subprocess.run([python(janela=True), *args], cwd=RAIZ, env=env, stdout=f, stderr=subprocess.STDOUT,
                           creationflags=SEM_JANELA)
    return r.returncode, ""


def main(argv):
    if argv[:1] == ["rodar"] and argv[1:2] and argv[1] in ROTINAS:
        return rodar(argv[1])[0]
    acoes = {"ligar": ligar, "desligar": desligar, "status": status}
    if not argv or argv[0] not in acoes:
        print(__doc__)
        return 2
    codigo, texto = acoes[argv[0]]()
    if sys.stdout:
        print(texto)
    return codigo


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
