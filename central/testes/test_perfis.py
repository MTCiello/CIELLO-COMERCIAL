"""Perfis (uma marca do Metricool por perfil): python -m unittest discover -s central/testes -p "test_*.py" """
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import metricool_conferir as mc  # noqa: E402
import perfis  # noqa: E402

# getBrandSettings: a marca principal só com TikTok e YouTube (Instagram desconectado) e um cliente com Instagram
MARCAS = {"data": [{"id": 6611209, "label": "ciellotec", "timezone": "America/Sao_Paulo",
                    "networksData": {"tiktokData": "ciellotec", "youtubeData": "UC5A"}},
                   {"id": 42, "label": "padaria", "networksData": {"instagramData": "padaria.sol"}}]}


def amanha(h="10:00"):
    return f"{(dt.date.today() + dt.timedelta(days=1)).isoformat()}T{h}:00"


# getScheduledPosts: um Reel em rascunho para o Instagram, que está desconectado
AGENDADOS = {"data": [{"publicationDate": {"dateTime": amanha(), "timezone": "America/Sao_Paulo"}, "text": "Pare de usar o Claude só pra texto\n...",
                       "providers": [{"network": "instagram", "status": "PENDING"}], "draft": True}]}


class TestePerfis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        (base / "comercial").mkdir()
        (base / "comercial" / "empresa.json").write_text(json.dumps({"nome": "CIELLO", "publico": "pequenas empresas de Chapecó"}), encoding="utf-8")
        self.p = [mock.patch.object(mc.dados, "pasta_dados", lambda: base), mock.patch.dict(os.environ, {"CIELLO_COMERCIAL": str(base / "comercial")})]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()
        self.tmp.cleanup()

    def test_sem_conferencia_nao_tem_perfil(self):
        r = perfis.listar()
        self.assertEqual(r["perfis"], [])
        self.assertIn("ainda não foi conferido", r["mensagem"])

    def test_cada_marca_vira_perfil_e_o_primeiro_usa_a_empresa(self):
        mc.conferir(MARCAS)
        ps = perfis.listar()["perfis"]
        self.assertEqual([p["id"] for p in ps], ["6611209", "42"])
        self.assertEqual(ps[0]["nome"], "CIELLO")
        self.assertEqual(ps[1]["nome"], "padaria")
        self.assertEqual(ps[0]["identidade"]["publico"], "pequenas empresas de Chapecó")
        redes = {r["rede"]: r["estado"] for r in ps[0]["redes"]}
        self.assertEqual(redes, {"instagram": "desconectado", "tiktok": "conectado", "youtube": "conectado"})
        self.assertEqual(ps[0]["resumo"]["conectadas"], 2)
        self.assertTrue(any("Instagram desconectado" in a for a in ps[0]["alertas"]))

    def test_saude_le_as_linhas_do_metricool(self):
        mc.conferir(MARCAS)
        ids = perfis.metricas("6611209")
        self.assertIn("TKEV07", ids)
        self.assertNotIn("IGEV01", ids)  # Instagram não está na marca: não pede
        linha = {i: None for i in ids}
        dias = []
        for dia, seg, novos, videos in (("20261022", "1.0", "0.0", None), ("20261024", "3.0", "2.0", "1.0")):
            v = dict(linha, TKEV07=seg, TKEV08=novos, TKEV01=videos, YTEV01="0.0", YTEV05="1.0", YTEV06="1.0")
            dias.append([v[i] for i in ids] + [dia])
        r = perfis.gravar_saude("6611209", {"rows": dias}, AGENDADOS)
        self.assertEqual(r["redes"]["tiktok"]["seguidores"], 3)  # o último dia
        self.assertEqual(r["redes"]["tiktok"]["ganho_7d"], 2)
        self.assertEqual(r["redes"]["tiktok"]["posts_7d"], 1)
        self.assertEqual(r["redes"]["youtube"]["ganho_7d"], 0)  # ganhou 1, perdeu 1
        p = perfis.listar()["perfis"][0]
        self.assertEqual(p["resumo"]["seguidores"], 3)
        self.assertEqual(p["resumo"]["agendados_rascunho"], 1)
        ig = next(r for r in p["redes"] if r["rede"] == "instagram")
        self.assertEqual(ig["agendados"], 1)
        self.assertIn("não vai sair", ig["aviso"])
        yt = next(r for r in p["redes"] if r["rede"] == "youtube")
        self.assertEqual(yt["aviso"], "Nenhum post nos últimos 7 dias")

    def test_identidade_e_esteira_ficam_no_cadastro(self):
        mc.conferir(MARCAS)
        self.assertTrue(perfis.salvar_identidade("42", {"nome": "Padaria Sol", "tom": "acolhedor", "pilares": "pães, bastidores", "publico": "bairro",
                                                        "assinatura": "Passa aqui!"})["ok"])
        self.assertFalse(perfis.salvar_esteira("42", {"por_semana": "30", "redes": ["instagram"]})["ok"])
        self.assertTrue(perfis.salvar_esteira("42", {"por_semana": "4", "redes": ["instagram"], "ativa": True})["ok"])
        p = next(x for x in perfis.listar()["perfis"] if x["id"] == "42")
        self.assertEqual(p["nome"], "Padaria Sol")
        self.assertEqual(p["identidade"]["pilares"], ["pães", "bastidores"])
        self.assertTrue(p["identidade_completa"])
        self.assertEqual({r["rede"]: r["estado"] for r in p["redes"]}["tiktok"], "fora")  # não está na esteira: não é alerta
        self.assertEqual(p["alertas"], [])
        pedido = perfis.pedido_mes("42")
        self.assertTrue(pedido["ok"])
        self.assertIn("4 posts por semana", pedido["pedido"])
        self.assertIn("brandId 42", pedido["pedido"])
        self.assertIn("rascunho", pedido["pedido"])

    def test_pedido_do_mes_exige_esteira_e_rede_conectada(self):
        mc.conferir(MARCAS)
        self.assertFalse(perfis.pedido_mes("6611209")["ok"])
        perfis.salvar_esteira("6611209", {"por_semana": 3, "redes": ["instagram"]})
        self.assertIn("nenhuma rede", perfis.pedido_mes("6611209")["saida"])
        perfis.salvar_esteira("6611209", {"por_semana": 3, "redes": ["instagram", "tiktok"]})
        r = perfis.pedido_mes("6611209")
        self.assertTrue(r["ok"])
        self.assertIn("Não use Instagram", r["pedido"])


if __name__ == "__main__":
    unittest.main()
