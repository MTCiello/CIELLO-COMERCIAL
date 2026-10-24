"""Biblioteca: tudo o que o Ciello OS e a equipe já produziram, num lugar só.

A tela abre pelos posts: cada roteiro vira um cartão com a capa (ou o próprio vídeo), as etapas feitas e, ao abrir,
o vídeo com as versões (final, rascunhos do Estúdio), a capa, a legenda, a narração e o roteiro. As abas de arquivos
continuam para achar qualquer coisa solta: vídeos (finais, rascunhos do Estúdio e os antigos), capas, roteiros, pesquisas (radar, relatórios, Bom dia) e
vozes (testes, gravações e narrações). A janela Biblioteca mostra, toca e abre a pasta de cada arquivo; nada aqui
apaga ou publica.

    python central/biblioteca.py            lista o que tem em cada seção
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conteudo  # noqa: E402
import dados  # noqa: E402

# seção -> [(pasta relativa, padrões, grupo)]: a ordem é a ordem na tela
SECOES = {
    "videos": [("midia/final", ("*.mp4",), "Final"), ("midia/estudio", ("*.mp4",), "Rascunho do Estúdio"), ("midia", ("*.mp4",), "Vídeo")],
    "capas": [("midia/capas", ("*.jpg", "*.jpeg", "*.png"), "Capa")],
    "roteiros": [("roteiros", ("*.json",), "Roteiro")],
    "pesquisas": [("radar", ("*.md",), "Radar de tendências"), ("metricas", ("relatorio-*.md",), "Relatório semanal"),
                  ("estado/briefing", ("*.md",), "Bom dia")],
    "vozes": [("audio", ("*.wav",), "Narração"), ("estado/voz/testes", ("*.wav",), "Teste de voz"),
              ("estado/voz/amostras", ("*.webm", "*.ogg", "*.wav"), "Sua gravação"), ("marca", ("minha-voz*.wav",), "Sua voz")],
}
TEXTO = {".md", ".json"}
LIMITE_TEXTO = 400_000


def raiz() -> Path:
    return dados.pasta_dados()


def _titulos() -> dict[str, str]:
    """stem do roteiro -> título (o vídeo, a capa e a narração usam o mesmo nome do roteiro)."""
    out = {}
    for p in sorted((raiz() / "roteiros").glob("20??-??-??-*.json")):
        out[p.stem] = conteudo.titulo(conteudo.ler_roteiro(p), p.stem)
    return out


def _titulo(p: Path, titulos: dict[str, str]) -> str:
    stem = p.stem
    m = re.match(r"(\d{8})-(\d{2})(\d{2})\d{2}-(\w+)$", stem)  # teste de voz: 20261024-133849-kokoro
    if m:
        return f"Teste {m[4].capitalize()} das {m[2]}:{m[3]}"
    m = re.match(r"\d{4}-\d{2}-\d{2}-(\d{2})(\d{2})\d{2}$", stem)  # gravação: 2026-10-24-134059
    if m:
        return f"Gravação das {m[1]}:{m[2]}"
    for s, t in titulos.items():  # 2026-10-24-tema-o98-15 (rascunho no estilo) também é do roteiro 2026-10-24-tema
        if stem == s or stem.startswith(s + "-"):
            return t
    if p.parent.name == "audio" or p.parent.parent.name == "audio":
        return p.parent.name.replace("-", " ")
    return stem.replace("-", " ").replace("_", " ")


def _data(p: Path, st) -> str:
    for nome, formato in ((p.stem[:10], "%Y-%m-%d"), (p.stem[:8], "%Y%m%d")):
        try:
            return dt.datetime.strptime(nome, formato).date().isoformat()
        except ValueError:
            pass
    return dt.datetime.fromtimestamp(st.st_mtime).date().isoformat()


def _post_do_arquivo(item: dict, stems: list[str]) -> str | None:
    """De qual roteiro é o arquivo: mesmo nome (ou nome + -estilo) ou a pasta audio/<slug>/."""
    p = Path(item["rel"])
    if p.parts[0] == "audio" and len(p.parts) > 2:
        return next((s for s in stems if s[11:] == p.parts[1]), None)
    return next((s for s in stems if p.stem == s or p.stem.startswith(s + "-")), None)


ORDEM_VIDEO = {"Final": 0, "Vídeo": 1, "Rascunho do Estúdio": 2}


def posts(secoes: dict) -> list[dict]:
    """Um cartão por roteiro com tudo o que já saiu dele, do mais novo para o mais antigo."""
    base = raiz()
    arquivos = sorted((base / "roteiros").glob("20??-??-??-*.json"))
    stems = sorted((p.stem for p in arquivos), key=len, reverse=True)  # o nome mais longo ganha (tema-2 antes de tema)
    hist = conteudo.historico(base / "historico.md")
    out = {}
    for p in arquivos:
        try:
            q = conteudo.post(p, hist, base)
        except ValueError:  # data inválida no nome
            continue
        out[p.stem] = {**{k: q[k] for k in ("post", "slug", "data", "dias", "titulo", "etapas", "falta", "proximo", "dono", "pronto", "legenda")},
                       "publicado": bool(re.search(r"publicad", q["status_historico"], re.I)),
                       "roteiro": p.relative_to(base).as_posix(), "videos": [], "capa": None, "audios": []}
    for secao, chave in (("videos", "videos"), ("capas", "capa"), ("vozes", "audios")):
        for item in secoes.get(secao, []):
            s = _post_do_arquivo(item, stems)
            if s not in out:
                continue
            if chave == "capa":
                out[s]["capa"] = out[s]["capa"] or item["rel"]
            else:
                out[s][chave].append({k: item[k] for k in ("rel", "grupo", "nome", "tamanho", "modificado")})
    for x in out.values():
        x["videos"].sort(key=lambda v: (ORDEM_VIDEO.get(v["grupo"], 9), v["nome"]))
    return sorted(out.values(), key=lambda x: x["data"], reverse=True)


def listar() -> dict:
    base, titulos = raiz(), _titulos()
    out, vistos = {}, set()
    for secao, fontes in SECOES.items():
        itens = []
        for pasta, padroes, grupo in fontes:
            d = base / pasta
            if not d.is_dir():
                continue
            arquivos = set()
            for padrao in padroes:
                # audio/ guarda uma pasta por post (audio/<slug>/narracao.wav); o resto é plano
                arquivos |= set(d.rglob(padrao) if pasta == "audio" else d.glob(padrao))
            for p in arquivos:
                if not p.is_file() or p in vistos or p.name.startswith(("_", ".")):
                    continue
                vistos.add(p)
                st = p.stat()
                itens.append({"rel": p.relative_to(base).as_posix(), "nome": p.name, "titulo": _titulo(p, titulos),
                              "grupo": grupo, "data": _data(p, st), "tamanho": st.st_size,
                              "modificado": dt.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="minutes"),
                              "tipo": p.suffix.lower().lstrip(".")})
        itens.sort(key=lambda x: (x["modificado"], x["data"]), reverse=True)
        out[secao] = itens
    ps = posts(out)
    resumo = {"posts": len(ps), "prontos": sum(1 for x in ps if x["etapas"]["final"]),
              "producao": sum(1 for x in ps if not x["etapas"]["final"]), "publicados": sum(1 for x in ps if x["publicado"]),
              **{k: len(v) for k, v in out.items()}}
    return {"secoes": out, "posts": ps, "resumo": resumo, "pasta": str(base)}


def caminho(rel: str) -> Path | None:
    """Só arquivos dentro das pastas da Biblioteca (nada de ../ ou de outra pasta do PC)."""
    if not rel or "\\" in rel or rel.startswith("/"):
        return None
    base = raiz().resolve()
    alvo = (base / rel).resolve()
    permitido = any(alvo.is_relative_to((base / pasta).resolve()) for fontes in SECOES.values() for pasta, _, _ in fontes)
    return alvo if permitido and alvo.is_file() else None


def ler(rel: str) -> dict:
    alvo = caminho(rel)
    if alvo is None or alvo.suffix.lower() not in TEXTO:
        return {"ok": False, "saida": "arquivo não encontrado"}
    texto = alvo.read_text(encoding="utf-8", errors="replace")[:LIMITE_TEXTO]
    if alvo.suffix.lower() == ".json":
        try:
            texto = json.dumps(json.loads(texto), ensure_ascii=False, indent=2)
        except ValueError:
            pass
    return {"ok": True, "texto": texto, "tipo": alvo.suffix.lower().lstrip(".")}


def mostrar(rel: str) -> dict:
    """Abre a pasta do arquivo no Explorador (no Windows, já com ele selecionado)."""
    alvo = caminho(rel)
    if alvo is None:
        return {"ok": False, "saida": "arquivo não encontrado"}
    try:
        if os.name == "nt":
            subprocess.Popen(["explorer", "/select,", str(alvo)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(alvo)])
        else:
            subprocess.Popen(["xdg-open", str(alvo.parent)])
    except OSError as e:
        return {"ok": False, "saida": f"não deu para abrir a pasta: {e}"}
    return {"ok": True, "saida": f"Pasta aberta: {alvo.parent}"}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    for secao, itens in listar()["secoes"].items():
        print(f"{secao}: {len(itens)}")
        for x in itens[:10]:
            print(f"  {x['data']}  {x['grupo']:20} {x['rel']}")


if __name__ == "__main__":
    main()
