"""Confere o Metricool antes de trabalhar: as redes que o OS usa estão conectadas na marca?

O Metricool é a ponte entre o Claude e as redes. Quando algo é desconectado lá (o Instagram perdeu o login, a marca
mudou), os agentes precisam saber antes de começar, não no meio do agendamento. Quem fala com o Metricool é o
Claude (conector), então o agente chama `getBrandSettings`, salva a resposta e passa para este script:

    python central/metricool_conferir.py estado/metricool-marcas.json     confere e grava estado/metricool.json
    python central/metricool_conferir.py --sem-conector                   o Claude não achou o conector do Metricool
    python central/metricool_conferir.py estado                           a última conferência (e se está velha)

Sai com código 0 quando está tudo certo e 2 quando falta algo: o agente para e avisa o que está desconectado.
Cada marca do Metricool é um perfil (a CIELLO é uma marca; outro cliente seria outra).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conexoes  # noqa: E402
import dados  # noqa: E402

ARQUIVO = "metricool.json"
VALIDADE_H = 24  # depois disso a conferência é velha e o agente confere de novo
NOMES = {"instagram": "Instagram", "facebook": "Facebook", "tiktok": "TikTok", "youtube": "YouTube", "twitter": "X (Twitter)",
         "linkedin": "LinkedIn", "pinterest": "Pinterest", "threads": "Threads", "bluesky": "Bluesky", "twitch": "Twitch", "gmb": "Google Meu Negócio"}
# o nome da rede dentro de networksData (instagramData, facebookPageData…) ou no próprio objeto da marca (versões antigas)
CHAVES = {"instagram": ("instagramData", "instagram", "instagramBusiness"), "facebook": ("facebookData", "facebookPageData", "facebook"),
          "tiktok": ("tiktokData", "tiktok"), "youtube": ("youtubeData", "youtube"), "twitter": ("twitterData", "twitter"),
          "linkedin": ("linkedinData", "linkedinCompany", "linkedin"), "pinterest": ("pinterestData", "pinterest"),
          "threads": ("threadsData", "threads"), "bluesky": ("blueskyData", "bluesky"), "twitch": ("twitchData", "twitch"), "gmb": ("gmbData", "gmb")}


def agora() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def marcas(resposta) -> list[dict]:
    """[{id, nome, redes: {rede: conta}, fuso}] a partir da resposta do getBrandSettings."""
    lista = resposta.get("data", resposta) if isinstance(resposta, dict) else resposta
    if isinstance(lista, dict):
        lista = [lista]
    out = []
    for m in lista or []:
        if not isinstance(m, dict):
            continue
        nd = m.get("networksData") if isinstance(m.get("networksData"), dict) else {}
        redes = {}
        for rede, chaves in CHAVES.items():
            for k in chaves:
                v = nd.get(k) if k in nd else m.get(k)
                if v and not isinstance(v, bool | int | float):
                    redes[rede] = v if isinstance(v, str) else str(v.get("username") or v.get("name") or v.get("id") or "conectado")
                    break
                if v is True:
                    redes[rede] = "conectado"
                    break
        out.append({"id": str(m.get("id") or m.get("blogId") or ""), "nome": m.get("label") or m.get("name") or "", "redes": redes,
                    "fuso": m.get("timezone") or ""})
    return out


def precisa() -> list[str]:
    """As redes ligadas no OS que passam pelo Metricool (Ponte com o Claude ou API do Metricool)."""
    return [r for r, v in conexoes.redes().items() if v.get("ativa") and v.get("via") in ("claude", "metricool")]


def _escolher(ms: list[dict], marca: str | None) -> dict | None:
    if marca:
        alvo = str(marca).lower()
        return next((m for m in ms if m["id"] == str(marca) or m["nome"].lower() == alvo), None)
    blog = conexoes.credenciais("metricool").get("blog_id") if "metricool" in conexoes.PROVEDORES else None
    return next((m for m in ms if blog and m["id"] == str(blog)), None) or (ms[0] if ms else None)


def conferir(resposta, marca: str | None = None) -> dict:
    ms = marcas(resposta)
    m = _escolher(ms, marca)
    usa = precisa()
    if m is None:
        r = {"ok": False, "marca": None, "conectadas": [], "faltam": usa,
             "mensagem": f"a marca {marca} não está nesta conta do Metricool" if marca else "nenhuma marca no Metricool"}
    else:
        faltam = [x for x in usa if x not in m["redes"]]
        r = {"ok": not faltam, "marca": {"id": m["id"], "nome": m["nome"], "fuso": m["fuso"]}, "conectadas": sorted(m["redes"]),
             "contas": m["redes"], "faltam": faltam,
             "mensagem": "" if not faltam else f"{', '.join(NOMES.get(x, x) for x in faltam)} não {'está conectado' if len(faltam) == 1 else 'estão conectados'} na marca {m['nome']} do Metricool"}
    r.update(quando=agora(), precisa=usa, marcas=[{"id": x["id"], "nome": x["nome"], "redes": sorted(x["redes"])} for x in ms])
    _gravar(r)
    return r


def sem_conector() -> dict:
    r = {"ok": False, "quando": agora(), "marca": None, "conectadas": [], "precisa": precisa(), "faltam": precisa(), "marcas": [],
         "mensagem": "o conector do Metricool não está ligado no Claude (claude.ai → Configurações → Conectores)"}
    _gravar(r)
    return r


def _gravar(r: dict):
    dados.estado(ARQUIVO).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")


def ultima() -> dict:
    """A última conferência, com 'velha' = mais de VALIDADE_H horas (ou nunca feita)."""
    try:
        r = json.loads(dados.estado(ARQUIVO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"ok": None, "velha": True, "mensagem": "o Metricool ainda não foi conferido"}
    try:
        idade = dt.datetime.now() - dt.datetime.fromisoformat(r.get("quando", ""))
    except ValueError:
        idade = dt.timedelta(days=999)
    return {**r, "velha": idade > dt.timedelta(hours=VALIDADE_H)}


def problema() -> dict | None:
    """Para o Bom dia, a janela Conexões e o piloto: o que está desconectado agora (None = tudo certo ou nunca conferido)."""
    r = ultima()
    if r.get("ok") is False:
        return {"id": "metricool", "nome": "Metricool", "mensagem": r.get("mensagem", ""), "desde": r.get("quando", "")}
    return None


def texto(r: dict) -> str:
    if r.get("ok") is None:
        return "Metricool ainda não conferido."
    marca = (r.get("marca") or {}).get("nome") or "?"
    con = ", ".join(NOMES.get(x, x) for x in r.get("conectadas", [])) or "nenhuma rede"
    if r.get("ok"):
        return f"OK: marca {marca} com {con}. Pode começar."
    return f"PARE: {r.get('mensagem')}. Conectadas agora: {con}. Avise o usuário e reconecte em app.metricool.com → Conexões antes de seguir."


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    args = sys.argv[1:]
    marca = None
    if "--marca" in args:
        i = args.index("--marca")
        marca = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
    if args == ["--sem-conector"]:
        r = sem_conector()
    elif args == ["estado"]:
        r = ultima()
        print(texto(r) + (" (conferência de mais de 24 h: confira de novo)" if r.get("velha") and r.get("ok") is not None else ""))
        sys.exit(0 if r.get("ok") and not r.get("velha") else 2)
    elif len(args) == 1:
        fonte = sys.stdin if args[0] == "-" else Path(args[0]).open(encoding="utf-8")
        try:
            r = conferir(json.load(fonte), marca)
        except ValueError:
            sys.exit("A resposta do getBrandSettings não é um JSON válido.")
    else:
        print(__doc__)
        sys.exit(1)
    print(texto(r))
    sys.exit(0 if r["ok"] else 2)


if __name__ == "__main__":
    main()
