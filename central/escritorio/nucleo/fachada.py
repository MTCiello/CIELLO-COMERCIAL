"""O que a tela do escritório vê: só os agentes da casa, cada um uma vez.

O vigia acompanha mais coisa do que os 13 residentes: a sessão do Claude Code em que você conversa, colegas de equipe
e os ajudantes de Task/Agent que não são de nenhum residente (general-purpose, Explore...). No pixel-agents original
cada um vira um boneco, e no Ciello isso aparecia como agentes a mais na sala do Gerente e "gêmeos" (o ajudante nasce
com o mesmo personagem de quem o chamou) espalhados pelo escritório.

Aqui a regra é outra: quem coordena é o Gerente. A sessão em que você conversa e tudo o que ela faz sem um residente
(subtarefas, colegas, ferramentas) aparece no próprio Gerente, na sala dele. Nenhum boneco a mais nasce. Os residentes
continuam recebendo as tarefas que são deles (residentes.py).

A fachada fica entre a Loja e as telas: cada mensagem que sairia para a tela passa por traduzir(), que devolve as
mensagens que a tela deve receber de fato (nenhuma, a mesma, ou outra no lugar).
"""
from __future__ import annotations

from typing import Callable

from .agentes import SUBAGENTE

# mensagens que só fazem sentido para um boneco próprio: quem não é da casa não tem boneco, então somem
SO_DO_BONECO = frozenset({"agentCreated", "agentClosed", "agentTeamInfo", "agentContextUsage"})


class Fachada:
    def __init__(self, gerente: Callable[[], int | None], da_casa: Callable[[int], bool]):
        self.gerente = gerente      # id do residente Gerente (None: sem Gerente, tudo passa como no original)
        self.da_casa = da_casa      # o id é de um residente?
        self.ferramentas: dict[int, dict[str, str | None]] = {}  # quem -> {ferramenta mostrada no Gerente: tarefa mãe}
        self.ocupados: set[int] = set()                         # quem está trabalhando pelo Gerente agora

    # ---------------------------------------------------------- quem aparece
    def visiveis(self, ids):
        """Os agentes que viram boneco na tela (para o existingAgents)."""
        if self.gerente() is None:
            return list(ids)
        return [i for i in ids if self.da_casa(i)]

    def _pelo_gerente(self, aid) -> bool:
        g = self.gerente()
        return g is not None and isinstance(aid, int) and (aid == g or not self.da_casa(aid))

    # ---------------------------------------------------------- tradução
    def traduzir(self, msg: dict) -> list[dict]:
        aid = msg.get("id")
        if not self._pelo_gerente(aid):
            return [msg]
        g, tipo = self.gerente(), msg.get("type")
        if aid != g and tipo in SO_DO_BONECO:
            return self._saiu(aid) if tipo == "agentClosed" else []
        if tipo == "agentStatus":
            return self._status(aid, g, msg)
        if tipo == "agentToolStart":
            return [self._comecou(aid, g, msg["toolId"], None, msg)]
        if tipo == "agentToolDone":
            return self._acabou(aid, g, [msg["toolId"]])
        if tipo == "agentToolsClear":
            if aid == g and not (self.ocupados - {g}):
                self.ferramentas.pop(g, None)
                return [msg]
            return self._acabou(aid, g, list(self.ferramentas.get(aid, {})))
        if tipo in ("agentToolPermission", "agentToolPermissionClear"):
            return [{**msg, "id": g}]
        if tipo == "subagentToolStart":
            return [self._comecou(aid, g, msg["toolId"], msg.get("parentToolId"), msg)]
        if tipo == "subagentToolDone":
            return self._acabou(aid, g, [msg["toolId"]])
        if tipo == "subagentToolPermission":
            return [{"type": "agentToolPermission", "id": g}]
        if tipo == "subagentClear":
            mae = msg.get("parentToolId")
            return self._acabou(aid, g, [t for t, m in self.ferramentas.get(aid, {}).items() if m == mae])
        return [{**msg, "id": g}]

    def _comecou(self, aid, g, tid, mae, msg) -> dict:
        self.ferramentas.setdefault(aid, {})[tid] = mae
        nome = msg.get("toolName") or ""
        # Task/Agent sem residente: o Gerente mostra a subtarefa no balão, sem criar um ajudante ao lado dele
        return {"type": "agentToolStart", "id": g, "toolId": tid, "status": msg.get("status") or "",
                "toolName": "" if nome in SUBAGENTE else nome, **({"permissionActive": True} if msg.get("permissionActive") else {})}

    def _acabou(self, aid, g, tids) -> list[dict]:
        minhas = self.ferramentas.get(aid, {})
        saida = []
        for t in tids:
            if t in minhas:
                minhas.pop(t)
                saida.append({"type": "agentToolDone", "id": g, "toolId": t})
        return saida

    def _status(self, aid, g, msg) -> list[dict]:
        if msg.get("status") == "active":
            self.ocupados.add(aid)
            return [{**msg, "id": g}]
        self.ocupados.discard(aid)
        if self.ocupados:  # outra sessão (ou o próprio Gerente) ainda trabalha: ele continua ocupado
            return self._acabou(aid, g, list(self.ferramentas.get(aid, {})))
        saida = self._limpar_todos(g)
        return saida + [{**msg, "id": g}]

    def _limpar_todos(self, g) -> list[dict]:
        tinha = any(self.ferramentas.values())
        self.ferramentas.clear()
        return [{"type": "agentToolsClear", "id": g}] if tinha else []

    def _saiu(self, aid) -> list[dict]:
        """A sessão fechou: o que ela fazia some do Gerente; se ninguém mais trabalha, ele volta para a rotina."""
        g = self.gerente()
        saida = self._acabou(aid, g, list(self.ferramentas.get(aid, {})))
        self.ferramentas.pop(aid, None)
        if aid in self.ocupados:
            self.ocupados.discard(aid)
            if not self.ocupados:
                saida += self._limpar_todos(g)
                saida.append({"type": "agentStatus", "id": g, "status": "waiting", "silencioso": True})
        return saida
