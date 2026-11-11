"""O que orienta a pesquisa, num lugar só: concorrentes, nichos e referências.

- Concorrentes: comercial/concorrentes.json (a vigia baixa as páginas; o pesquisador cadastra os perfis no Metricool).
- Nichos: os pilares do conteúdo (radar.py) e os nichos de cliente do comercial/icp.json (a busca de leads usa).
- Referências: os vídeos que viralizaram em conhecimento/ganchos.csv e onde o radar procura.

A Biblioteca mostra e cadastra; os agentes leem os mesmos arquivos.

    python central/pesquisa.py              resume o que está cadastrado
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ganchos  # noqa: E402
import radar  # noqa: E402
import sdr  # noqa: E402
import vigia  # noqa: E402


def _ler(p: Path, padrao: dict) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return json.loads(json.dumps(padrao))


def _gravar(p: Path, d: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _limpo(v, n=300) -> str:
    return str(v or "").strip()[:n]


def _id(nome: str) -> str:
    t = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")[:40]


def _num(v) -> float:
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def listar() -> dict:
    conc = _ler(vigia.CONCORRENTES, {"concorrentes": []}).get("concorrentes", [])
    icp = _ler(sdr.ICP, {"cidades": [], "segmentos": {}})
    refs = ganchos.ler()
    por_pilar = {}
    for r in refs:
        por_pilar[r.get("pilar") or ""] = por_pilar.get(r.get("pilar") or "", 0) + 1
    nichos = [{"id": k, "nome": v.get("nome") or (v.get("termos") or [k.replace("_", " ")])[0].capitalize(), "prioridade": int(_num(v.get("prioridade"))),
               "termos": v.get("termos", []), "dor": v.get("dor", ""), "valor": v.get("valor", "")}
              for k, v in (icp.get("segmentos") or {}).items()]
    nichos.sort(key=lambda x: (-x["prioridade"], x["nome"]))
    refs = sorted(refs, key=lambda r: _num(r.get("views")), reverse=True)
    return {
        "concorrentes": [{"nome": c.get("nome", ""), "instagram": c.get("instagram", ""), "anuncios": c.get("anuncios", ""),
                          "urls": c.get("urls", [])} for c in conc],
        "pilares": [{"id": k, "nome": v, "referencias": por_pilar.get(k, 0)} for k, v in radar.PILARES.items()],
        "nichos": nichos, "cidades": icp.get("cidades", []),
        "referencias": [{**{k: r.get(k, "") for k in ("data", "perfil", "gancho", "formato", "pilar", "views", "multiplicador", "url", "porque")},
                         "nosso": bool(r.get("nosso")), "formato_rotulo": ganchos.DESCRICAO.get(r.get("formato") or "outro", "")} for r in refs],
        "buscas": {"Google Notícias": radar.NOTICIAS_BUSCAS, "Hacker News": radar.HN_BUSCAS,
                   "Reddit": [f"r/{s}" for s in radar.REDDIT_SUBS], "Blogs oficiais": list(radar.BLOGS)},
    }


def _urls(texto) -> list[dict]:
    """Uma por linha: "rótulo | https://…" ou só o endereço."""
    out = []
    linhas = texto if isinstance(texto, list) else str(texto or "").splitlines()
    for l in linhas:
        if isinstance(l, dict):
            l = f"{l.get('rotulo', '')} | {l.get('url', '')}"
        rot, _, url = str(l).rpartition("|") if "|" in str(l) else ("", "", str(l))
        url = url.strip()
        if not url:
            continue
        if not re.match(r"https?://", url):
            url = "https://" + url
        out.append({"rotulo": rot.strip()[:80] or re.sub(r"^https?://(www\.)?", "", url).split("/")[0], "url": url[:500]})
    return out


def salvar_concorrente(d: dict) -> dict:
    nome = _limpo(d.get("nome"), 80)
    if not nome:
        return {"ok": False, "saida": "Preencha o nome do concorrente."}
    cfg = _ler(vigia.CONCORRENTES, {"concorrentes": []})
    lista = cfg.setdefault("concorrentes", [])
    antigo = _limpo(d.get("antigo"), 80) or nome
    atual = next((c for c in lista if c.get("nome") == antigo), None)
    novo = {"nome": nome, "instagram": _limpo(d.get("instagram"), 60).lstrip("@"), "anuncios": _limpo(d.get("anuncios"), 80), "urls": _urls(d.get("urls"))}
    if atual is None:
        lista.append(novo)
    else:
        atual.update(novo)
    _gravar(vigia.CONCORRENTES, cfg)
    return {"ok": True, "saida": f"{nome} {'atualizado' if atual else 'cadastrado'}. A vigia confere as páginas na próxima rodada; "
                                 "para o pesquisador puxar os reels, cadastre o perfil também como concorrente no Metricool."}


def salvar_nicho(d: dict) -> dict:
    nome = _limpo(d.get("nome"), 60)
    if not nome:
        return {"ok": False, "saida": "Preencha o nome do nicho."}
    icp = _ler(sdr.ICP, {"cidades": [], "segmentos": {}})
    seg = icp.setdefault("segmentos", {})
    chave = _limpo(d.get("id"), 40) or _id(nome)
    termos = [t.strip() for t in re.split(r"[,\n]", str(d.get("termos") or "")) if t.strip()] or [nome.lower()]
    seg[chave] = {**seg.get(chave, {}), "nome": nome, "prioridade": max(1, min(5, int(_num(d.get("prioridade")) or 3))),
                  "termos": termos[:10], "dor": _limpo(d.get("dor")), "valor": _limpo(d.get("valor"))}
    if "cidades" in d:
        icp["cidades"] = [c.strip() for c in re.split(r"[,\n]", str(d.get("cidades") or "")) if c.strip()] or icp.get("cidades", [])
    _gravar(sdr.ICP, icp)
    return {"ok": True, "saida": f"Nicho {nome} salvo. A busca de leads (Comercial) já usa os termos dele."}


def salvar_referencia(d: dict) -> dict:
    gancho = _limpo(d.get("gancho"), 200)
    if not gancho:
        return {"ok": False, "saida": "Escreva o gancho (a primeira frase do vídeo)."}
    linhas = ganchos.ler()
    url = _limpo(d.get("url"), 500)
    if url and any(l.get("url") == url for l in linhas):
        return {"ok": False, "saida": "Esse vídeo já está nas referências."}
    perfil = _limpo(d.get("perfil"), 60)
    nova = ganchos.completar({"data": _limpo(d.get("data"), 10) or dt.date.today().isoformat(), "perfil": ("@" + perfil.lstrip("@")) if perfil else "",
                              "gancho": gancho, "views": str(int(_num(d.get("views")))) if _num(d.get("views")) else "", "url": url,
                              "porque": _limpo(d.get("porque"))})
    ganchos.gravar(linhas + [nova])
    return {"ok": True, "saida": f"Referência guardada ({ganchos.DESCRICAO.get(nova['formato'], nova['formato'])}, pilar {radar.PILARES.get(nova['pilar'], nova['pilar'])})."}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    d = listar()
    print(f"Concorrentes ({len(d['concorrentes'])}): " + ", ".join(c["nome"] for c in d["concorrentes"]))
    print(f"Nichos ({len(d['nichos'])}): " + ", ".join(f"{n['nome']} ({n['prioridade']})" for n in d["nichos"]))
    print(f"Referências: {len(d['referencias'])} vídeos")


if __name__ == "__main__":
    main()
