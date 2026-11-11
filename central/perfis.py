"""Perfis: cada marca do Metricool é um perfil, com as redes conectadas, um resumo de saúde, a identidade e a esteira.

A CIELLO é o primeiro perfil; cada cliente ou marca nova é outro. O cadastro (nome, identidade e esteira de produção)
fica em comercial/perfis.json, fora do git. Os números vêm do Metricool pelo conector do Claude: o agente chama o
conector, salva as respostas em estado/perfis/ e este script lê e grava o resumo em estado/perfis/saude.json.

    python central/perfis.py metricas 6611209                          quais métricas pedir para a marca (e guarda a ordem)
    python central/perfis.py saude 6611209 analise.json agendados.json lê as respostas do Metricool e grava o resumo
    python central/perfis.py --pelo-claude                             pede ao Claude (sem janela) para atualizar tudo
    python central/perfis.py estado                                    os perfis e o que está errado em cada um

Antes de rodar `metricas`, a conferência do Metricool (metricool_conferir.py) diz quais redes cada marca tem.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dados  # noqa: E402
import empresa  # noqa: E402
import metricool_conferir as mc  # noqa: E402

PRINCIPAIS = ["instagram", "tiktok", "youtube"]  # aparecem sempre no perfil, conectadas ou não
VALIDADE_H = 24
# métricas da aba Evolução do Metricool por rede: (campo do resumo, [ids com sinal], como juntar os dias)
METRICAS = {
    "instagram": [("seguidores", ["IGEV01"], "ultimo"), ("ganho_7d", ["IGEV43", "-IGEV44"], "soma"), ("views_7d", ["IGEV05"], "soma"),
                  ("posts_7d", ["IGEV37"], "soma"), ("engajamento", ["IGEV41"], "media")],
    "tiktok": [("seguidores", ["TKEV07"], "ultimo"), ("ganho_7d", ["TKEV08"], "soma"), ("views_7d", ["TKEV02"], "soma"),
               ("posts_7d", ["TKEV01"], "soma"), ("engajamento", ["TKEV9998"], "media")],
    "youtube": [("seguidores", ["YTEV01"], "ultimo"), ("ganho_7d", ["YTEV05", "-YTEV06"], "soma"), ("views_7d", ["YTEV02"], "soma"),
                ("posts_7d", ["YTEV04"], "soma")],
}
ESTEIRA_PADRAO = {"ativa": False, "por_semana": 3, "formatos": "Reels, TikTok e Shorts (o mesmo vídeo)", "redes": PRINCIPAIS}
CAMPOS_IDENTIDADE = ("tom", "publico", "pilares", "assinatura")


def agora() -> dt.datetime:
    return dt.datetime.now().replace(microsecond=0)


# ---------------------------------------------------------------- cadastro (comercial/perfis.json)

def _arquivo() -> Path:
    return empresa.pasta() / "perfis.json"


def _ler_json(p: Path, padrao):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return padrao


def cadastro() -> dict:
    d = _ler_json(_arquivo(), {})
    return d.get("perfis", {}) if isinstance(d, dict) and isinstance(d.get("perfis"), dict) else {}


def _gravar_cadastro(perfis: dict):
    arq = _arquivo()
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps({"perfis": perfis}, ensure_ascii=False, indent=1), encoding="utf-8")


def _limpo(v, n=300) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def salvar_identidade(marca: str, dados_: dict) -> dict:
    marca = _limpo(marca, 40)
    if not marca:
        return {"ok": False, "saida": "perfil sem marca do Metricool"}
    perfis = cadastro()
    p = perfis.setdefault(marca, {})
    if "nome" in dados_:
        p["nome"] = _limpo(dados_["nome"], 60)
    ident = p.setdefault("identidade", {})
    for k in CAMPOS_IDENTIDADE:
        if k in dados_:
            v = dados_[k]
            ident[k] = [x for x in (_limpo(s, 40) for s in (v if isinstance(v, list) else str(v or "").split(","))) if x][:8] if k == "pilares" else _limpo(v)
    _gravar_cadastro(perfis)
    return {"ok": True, "saida": f"Identidade de {p.get('nome') or marca} salva (comercial/perfis.json, fora do git)"}


def salvar_esteira(marca: str, dados_: dict) -> dict:
    marca = _limpo(marca, 40)
    if not marca:
        return {"ok": False, "saida": "perfil sem marca do Metricool"}
    try:
        por_semana = int(str(dados_.get("por_semana", ESTEIRA_PADRAO["por_semana"])).strip() or 0)
    except ValueError:
        return {"ok": False, "saida": "posts por semana precisa ser um número"}
    if not 1 <= por_semana <= 14:
        return {"ok": False, "saida": "posts por semana: de 1 a 14"}
    redes = [r for r in (dados_.get("redes") or []) if r in mc.NOMES]
    if not redes:
        return {"ok": False, "saida": "escolha pelo menos uma rede"}
    perfis = cadastro()
    p = perfis.setdefault(marca, {})
    p["esteira"] = {"ativa": bool(dados_.get("ativa", True)), "por_semana": por_semana,
                    "formatos": _limpo(dados_.get("formatos")) or ESTEIRA_PADRAO["formatos"], "redes": redes}
    _gravar_cadastro(perfis)
    return {"ok": True, "saida": f"Esteira de {p.get('nome') or marca}: {por_semana} posts por semana em {', '.join(mc.NOMES[r] for r in redes)}"}


# ---------------------------------------------------------------- números do Metricool (estado/perfis/)

def _pasta() -> Path:
    p = dados.estado("perfis")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _marcas() -> list[dict]:
    return mc.ultima().get("marcas") or []


def metricas(marca: str) -> list[str]:
    """Os ids para o getAnalyticsDataByMetrics das redes conectadas na marca; a ordem fica guardada para ler a resposta."""
    m = next((x for x in _marcas() if x["id"] == str(marca)), None)
    redes = [r for r in METRICAS if m and r in m.get("redes", [])]
    ids = list(dict.fromkeys(i.lstrip("-") for r in redes for _, lista, _ in METRICAS[r] for i in lista))
    (_pasta() / f"{marca}-metricas.json").write_text(json.dumps(ids), encoding="utf-8")
    return ids


def _num(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def ler_analise(resposta, ids: list[str]) -> dict:
    """{rede: {seguidores, ganho_7d, views_7d, posts_7d, engajamento}} a partir das linhas (um dia por linha, a data no fim)."""
    linhas = resposta.get("rows", []) if isinstance(resposta, dict) else (resposta or [])
    linhas = sorted((x for x in linhas if isinstance(x, list) and len(x) > len(ids)), key=lambda x: str(x[len(ids)]))
    col = {i: [_num(x[n]) for x in linhas] for n, i in enumerate(ids)}
    out = {}
    for rede, campos in METRICAS.items():
        if not any(i.lstrip("-") in col for _, lista, _ in campos for i in lista):
            continue
        r = {}
        for campo, lista, como in campos:
            valores = []
            for i in lista:
                serie = [v for v in col.get(i.lstrip("-"), []) if v is not None]
                if not serie:
                    continue
                sinal = -1 if i.startswith("-") else 1
                if como == "ultimo":
                    valores.append(sinal * serie[-1])
                elif como == "media":
                    valores.append(sinal * sum(serie) / len(serie))
                else:
                    valores.append(sinal * sum(serie))
            r[campo] = round(sum(valores), 2) if valores else None
        out[rede] = r
    return out


def ler_agendados(resposta) -> list[dict]:
    """[{quando, redes, texto, rascunho}] dos posts agendados (ainda não publicados)."""
    lista = resposta.get("data", []) if isinstance(resposta, dict) else (resposta or [])
    out = []
    for p in lista:
        if not isinstance(p, dict):
            continue
        quando = (p.get("publicationDate") or {}).get("dateTime") or ""
        redes = [str(x.get("network")) for x in p.get("providers") or [] if isinstance(x, dict) and x.get("network")]
        out.append({"quando": quando[:16], "redes": redes, "texto": _limpo(p.get("text"), 120), "rascunho": bool(p.get("draft"))})
    return sorted(out, key=lambda x: x["quando"])


def gravar_saude(marca: str, analise, agendados) -> dict:
    ids = _ler_json(_pasta() / f"{marca}-metricas.json", None)
    if ids is None:
        ids = metricas(marca)
    tudo = _ler_json(_pasta() / "saude.json", {})
    r = {"quando": agora().isoformat(), "redes": ler_analise(analise, ids) if analise is not None else {},
         "agendados": ler_agendados(agendados) if agendados is not None else []}
    tudo[str(marca)] = r
    (_pasta() / "saude.json").write_text(json.dumps(tudo, ensure_ascii=False, indent=1), encoding="utf-8")
    return r


def pelo_claude() -> dict:
    """O botão Atualizar da janela Perfis: o Claude confere o Metricool e puxa os números e os agendados de cada marca."""
    import ia
    hoje = agora().date()
    de, ate, fim = (hoje - dt.timedelta(days=6)).isoformat(), hoje.isoformat(), (hoje + dt.timedelta(days=40)).isoformat()
    pedido = ("Atualize os perfis do Ciello OS usando o conector do Metricool. Não agende, não edite e não publique nada.\n"
              "1. Chame getBrandSettings, salve a resposta inteira em estado/metricool-marcas.json e rode "
              "python central/metricool_conferir.py estado/metricool-marcas.json (se o conector não existir, rode "
              "python central/metricool_conferir.py --sem-conector e pare).\n"
              "2. Para cada marca (id) da resposta: rode python central/perfis.py metricas <id>, que imprime a lista de métricas. "
              f"Se a lista não for vazia, chame getAnalyticsDataByMetrics com brandId=<id>, from={de}T00:00:00-03:00, to={ate}T23:59:59-03:00 "
              "e metrics = essa lista, na mesma ordem, e salve a resposta em estado/perfis/<id>-analise.json. "
              f"Chame getScheduledPosts com brandId=<id>, fromDate={hoje.isoformat()}T00:00:00-03:00, toDate={fim}T23:59:59-03:00 e o "
              "timezone da marca, e salve em estado/perfis/<id>-agendados.json. Depois rode "
              "python central/perfis.py saude <id> estado/perfis/<id>-analise.json estado/perfis/<id>-agendados.json "
              "(use - no lugar de um arquivo que você não conseguiu salvar).\n"
              "Responda só as linhas que os scripts imprimiram.")
    r = ia.rodar(pedido, "Atualizar os perfis", timeout=600)
    return {"ok": r["ok"], "saida": r["saida"]}


# ---------------------------------------------------------------- o que a janela mostra

def _velha(quando: str) -> bool:
    try:
        return agora() - dt.datetime.fromisoformat(quando) > dt.timedelta(hours=VALIDADE_H)
    except (TypeError, ValueError):
        return True


def _identidade_padrao(primeiro: bool) -> dict:
    if not primeiro:
        return {"tom": "", "publico": "", "pilares": [], "assinatura": ""}
    e = empresa.perfil()
    exemplo = bool(e.get("exemplo"))
    return {"tom": "", "publico": "" if exemplo else e.get("publico", ""), "pilares": [], "assinatura": "" if exemplo else e.get("assinatura_legenda", "")}


def listar() -> dict:
    """{perfis: [...], conferido, conferido_velho, mensagem}: um perfil por marca do Metricool (e os cadastrados que sumiram)."""
    conf = mc.ultima()
    ms = conf.get("marcas") or []
    cad, saude = cadastro(), _ler_json(_pasta() / "saude.json", {})
    e = empresa.perfil()
    ids = [m["id"] for m in ms] + [k for k in cad if k not in {m["id"] for m in ms}]
    perfis = []
    for n, mid in enumerate(ids):
        m = next((x for x in ms if x["id"] == mid), None)
        c = cad.get(mid, {})
        primeiro = n == 0 and m is not None
        nome = c.get("nome") or (e.get("nome") if primeiro and e.get("nome") and not e.get("exemplo") else "") or (m or {}).get("nome") or mid
        ident = {**_identidade_padrao(primeiro), **(c.get("identidade") or {})}
        esteira = {**ESTEIRA_PADRAO, **(c.get("esteira") or {})}
        s = saude.get(mid) or {}
        conectadas = (m or {}).get("redes", [])
        contas = (conf.get("contas") or {}) if (conf.get("marca") or {}).get("id") == mid else {}
        hoje = agora().isoformat(timespec="minutes")
        futuros = [a for a in s.get("agendados", []) if a["quando"] >= hoje[:16]]
        redes = []
        for rede in list(dict.fromkeys(PRINCIPAIS + conectadas + esteira["redes"])):
            ag = [a for a in futuros if rede in a["redes"]]
            ligada = rede in conectadas
            usada = rede in esteira["redes"]
            numeros = (s.get("redes") or {}).get(rede) if ligada else None
            if ligada:
                estado, aviso = "conectado", ""
                if numeros and not numeros.get("posts_7d"):
                    aviso = "Nenhum post nos últimos 7 dias"
            elif usada or ag:
                estado = "desconectado"
                aviso = (f"{len(ag)} post{'s' if len(ag) > 1 else ''} agendado{'s' if len(ag) > 1 else ''} não vai sair. " if ag else "") + \
                    "Os agentes não produzem nem agendam para esta rede até reconectar."
            else:
                estado, aviso = "fora", "Não entra na esteira deste perfil."
            redes.append({"rede": rede, "nome": mc.NOMES.get(rede, rede), "estado": estado, "conta": contas.get(rede, ""), "numeros": numeros,
                          "agendados": len(ag), "aviso": aviso})
        alertas = []
        if m is None:
            alertas.append(f"A marca {mid} não aparece mais no Metricool. Confira se ela foi apagada ou renomeada.")
        for r in redes:
            if r["estado"] == "desconectado":
                parado = [a for a in futuros if r["rede"] in a["redes"]]
                alertas.append(f"{r['nome']} desconectado." + (f" O post de {_br(parado[0]['quando'])} não vai sair." if parado else "")
                               + f" Reconecte o {r['nome']} na marca {(m or {}).get('nome') or mid} do Metricool.")
        ligadas = [r for r in redes if r["estado"] == "conectado"]
        tem_numeros = any(r["numeros"] for r in ligadas)
        perfis.append({
            "id": mid, "nome": nome, "marca": {"id": mid, "nome": (m or {}).get("nome", ""),
                                               "fuso": (m or {}).get("fuso") or ((conf.get("marca") or {}).get("fuso", "") if (conf.get("marca") or {}).get("id") == mid else "")},
            "redes": redes, "alertas": alertas, "identidade": ident,
            "identidade_completa": all(ident.get(k) for k in CAMPOS_IDENTIDADE), "esteira": esteira, "esteira_definida": "esteira" in c,
            "agendados": futuros[:20], "saude_quando": s.get("quando", ""), "saude_velha": _velha(s.get("quando", "")),
            "resumo": {"conectadas": len(ligadas), "usadas": len([r for r in redes if r["estado"] != "fora"]),
                       "seguidores": sum(int(r["numeros"].get("seguidores") or 0) for r in ligadas if r["numeros"]) if tem_numeros else None,
                       "ganho_7d": sum(int(r["numeros"].get("ganho_7d") or 0) for r in ligadas if r["numeros"]) if tem_numeros else None,
                       "posts_7d": sum(int(r["numeros"].get("posts_7d") or 0) for r in ligadas if r["numeros"]) if tem_numeros else None,
                       "agendados": len(futuros), "agendados_rascunho": len([a for a in futuros if a["rascunho"]])},
        })
    return {"perfis": perfis, "conferido": conf.get("quando", ""), "conferido_velho": bool(conf.get("velha")),
            "mensagem": conf.get("mensagem", "") if conf.get("ok") is None or not ms else "", "nomes": mc.NOMES}


def _br(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]} às {iso[11:16]}" if len(iso) >= 16 else iso


def pedido_mes(marca: str) -> dict:
    """O pedido que a janela manda à equipe: produzir o mês do perfil pela esteira e deixar tudo como rascunho no Metricool."""
    p = next((x for x in listar()["perfis"] if x["id"] == str(marca)), None)
    if p is None:
        return {"ok": False, "saida": "perfil não encontrado"}
    if not p["esteira_definida"]:
        return {"ok": False, "saida": "defina a esteira de produção deste perfil antes"}
    est, ide = p["esteira"], p["identidade"]
    prontas = [r["nome"] for r in p["redes"] if r["rede"] in est["redes"] and r["estado"] == "conectado"]
    faltam = [r["nome"] for r in p["redes"] if r["rede"] in est["redes"] and r["estado"] != "conectado"]
    if not prontas:
        return {"ok": False, "saida": "nenhuma rede da esteira está conectada no Metricool"}
    hoje = agora().date()
    prox = (hoje.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    ident = "; ".join(x for x in [f"tom de voz: {ide['tom']}" if ide.get("tom") else "", f"público: {ide['publico']}" if ide.get("publico") else "",
                                   f"pilares: {', '.join(ide['pilares'])}" if ide.get("pilares") else "",
                                   f"frase no fim das legendas: {ide['assinatura']}" if ide.get("assinatura") else ""] if x)
    texto = (f"Produza o mês de {meses[prox.month - 1]} de {prox.year} do perfil {p['nome']} (marca {p['marca']['nome'] or p['id']} no Metricool, "
             f"brandId {p['id']}) pela esteira dele: {est['por_semana']} posts por semana, formatos {est['formatos']}, nas redes {', '.join(prontas)}. "
             + (f"Identidade do perfil: {ident}. " if ident else "A identidade do perfil ainda não foi preenchida: me pergunte o tom e o público antes de escrever. ")
             + "Siga a rotina /semana para cada post (pauta, roteiro, narração, vídeo, capa e legenda). "
             "Antes de começar, confira o Metricool (python central/metricool_conferir.py estado). "
             "Agende cada post no Metricool como rascunho (draft), nos melhores horários da marca, sem publicar nada: "
             "eu confiro o cronograma do mês e aprovo antes de ir ao ar."
             + (f" Não use {', '.join(faltam)}: está desconectado." if faltam else ""))
    return {"ok": True, "saida": "", "pedido": texto, "titulo": f"Mês de {p['nome']}"}


def texto(r: dict) -> str:
    if not r["perfis"]:
        return r.get("mensagem") or "Nenhum perfil: confira o Metricool primeiro (python central/metricool_conferir.py --pelo-claude)."
    linhas = []
    for p in r["perfis"]:
        con = ", ".join(x["nome"] for x in p["redes"] if x["estado"] == "conectado") or "nenhuma rede"
        linhas.append(f"{p['nome']} (marca {p['marca']['nome'] or p['id']}): {con}" + (f". {' '.join(p['alertas'])}" if p["alertas"] else ". Tudo certo."))
    return "\n".join(linhas)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "metricas":
        print(json.dumps(metricas(args[1])))
    elif len(args) == 4 and args[0] == "saude":
        def abrir(a):
            if a == "-":
                return None
            try:
                return json.loads(Path(a).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                sys.exit(f"{a} não é um JSON válido.")
        r = gravar_saude(args[1], abrir(args[2]), abrir(args[3]))
        redes = ", ".join(f"{mc.NOMES.get(k, k)} {int(v.get('seguidores') or 0)} seguidores" for k, v in r["redes"].items()) or "sem números"
        print(f"Perfil {args[1]}: {redes}; {len(r['agendados'])} agendado(s).")
    elif args == ["--pelo-claude"]:
        r = pelo_claude()
        print(r["saida"])
        sys.exit(0 if r["ok"] else 2)
    elif args == ["estado"]:
        print(texto(listar()))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
