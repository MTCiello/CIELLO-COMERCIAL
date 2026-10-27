"""Conferência do Metricool: python -m unittest discover -s central/testes -p "test_*.py" """
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import conexoes  # noqa: E402
import metricool_conferir as mc  # noqa: E402

# o formato que o getBrandSettings devolve (marca com TikTok e YouTube, sem Instagram)
RESPOSTA = {"data": [{"id": 1234567, "label": "lumi", "timezone": "America/Sao_Paulo",
                      "networksData": {"tiktokData": "lumi", "youtubeData": "UC5A"}},
                     {"id": 42, "label": "outra", "networksData": {"instagramData": {"username": "outra.loja"}}}]}


class TesteMetricoolConferir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = mock.patch.object(mc.dados, "pasta_dados", lambda: Path(self.tmp.name))
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def test_marcas_le_networksdata(self):
        ms = mc.marcas(RESPOSTA)
        self.assertEqual(ms[0], {"id": "1234567", "nome": "lumi", "redes": {"tiktok": "lumi", "youtube": "UC5A"}, "fuso": "America/Sao_Paulo"})
        self.assertEqual(ms[1]["redes"], {"instagram": "outra.loja"})

    def test_instagram_desconectado_para_e_vira_caida(self):
        r = mc.conferir(RESPOSTA)  # o padrão do OS: Instagram ligado pela Ponte com o Claude
        self.assertFalse(r["ok"])
        self.assertEqual(r["faltam"], ["instagram"])
        self.assertIn("Instagram não está conectado na marca lumi", r["mensagem"])
        self.assertTrue(mc.texto(r).startswith("PARE"))
        self.assertIn("metricool-conferencia", [c["id"] for c in conexoes.caidas()])  # Bom dia e piloto enxergam
        self.assertNotIn("metricool", [c["id"] for c in conexoes.caidas()])  # e o TikTok e o YouTube seguem publicando
        self.assertFalse(mc.ultima()["velha"])

    def test_rede_em_lista_ou_numero_nao_quebra(self):
        ms = mc.marcas({"data": [{"id": 9, "label": "x", "networksData": {"instagram": ["conta"], "youtube": 12345, "tiktok": []}}]})
        self.assertEqual(ms[0]["redes"], {"instagram": "conta", "youtube": "12345"})

    def test_outra_marca_com_instagram_passa(self):
        r = mc.conferir(RESPOSTA, marca="outra")
        self.assertTrue(r["ok"])
        self.assertIsNone(mc.problema())
        self.assertEqual(conexoes.caidas(), [])

    def test_sem_conector_e_nunca_conferido(self):
        self.assertIsNone(mc.ultima()["ok"])
        self.assertTrue(mc.ultima()["velha"])
        r = mc.sem_conector()
        self.assertFalse(r["ok"])
        self.assertIn("conector", mc.problema()["mensagem"])

    def test_estado_gravado_em_json(self):
        mc.conferir(RESPOSTA)
        d = json.loads((Path(self.tmp.name) / "estado" / "metricool.json").read_text(encoding="utf-8"))
        self.assertEqual([m["nome"] for m in d["marcas"]], ["lumi", "outra"])


if __name__ == "__main__":
    unittest.main()
