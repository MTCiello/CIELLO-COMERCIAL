"""Concorrentes, nichos e referências: python -m unittest discover -s central/testes -p "test_*.py" """
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pesquisa  # noqa: E402

EXEMPLO = Path(__file__).resolve().parents[2] / "exemplo"


class TestePesquisa(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = Path(self.tmp.name)
        shutil.copy(EXEMPLO / "comercial" / "concorrentes.json", r / "concorrentes.json")
        shutil.copy(EXEMPLO / "comercial" / "icp.json", r / "icp.json")
        shutil.copy(EXEMPLO / "conhecimento" / "ganchos.csv", r / "ganchos.csv")
        self.ps = [mock.patch.object(pesquisa.vigia, "CONCORRENTES", r / "concorrentes.json"), mock.patch.object(pesquisa.sdr, "ICP", r / "icp.json"),
                   mock.patch.object(pesquisa.ganchos, "CSV", r / "ganchos.csv")]
        for p in self.ps:
            p.start()
        self.r = r

    def tearDown(self):
        for p in self.ps:
            p.stop()
        self.tmp.cleanup()

    def test_listar(self):
        d = pesquisa.listar()
        self.assertEqual([c["nome"] for c in d["concorrentes"]], ["Concorrente Exemplo"])
        self.assertEqual(d["nichos"][0]["prioridade"], 5)  # mais importante primeiro
        self.assertIn("Imobiliária", [n["nome"] for n in d["nichos"]])
        self.assertEqual(len(d["pilares"]), 5)
        views = [float(x["views"] or 0) for x in d["referencias"]]
        self.assertEqual(views, sorted(views, reverse=True))

    def test_cadastrar_e_editar_concorrente(self):
        r = pesquisa.salvar_concorrente({"nome": "Kommo", "instagram": "@kommo.brasil", "urls": "preços | kommo.com/br/precos\nhttps://kommo.com/br/"})
        self.assertTrue(r["ok"])
        c = json.loads((self.r / "concorrentes.json").read_text(encoding="utf-8"))["concorrentes"][-1]
        self.assertEqual(c["instagram"], "kommo.brasil")
        self.assertEqual(c["urls"], [{"rotulo": "preços", "url": "https://kommo.com/br/precos"}, {"rotulo": "kommo.com", "url": "https://kommo.com/br/"}])
        pesquisa.salvar_concorrente({"antigo": "Kommo", "nome": "Kommo CRM", "urls": ""})
        nomes = [x["nome"] for x in pesquisa.listar()["concorrentes"]]
        self.assertEqual(nomes, ["Concorrente Exemplo", "Kommo CRM"])
        self.assertFalse(pesquisa.salvar_concorrente({"nome": " "})["ok"])

    def test_nicho_e_referencia(self):
        self.assertTrue(pesquisa.salvar_nicho({"nome": "Pet shop de bairro", "prioridade": "9", "termos": "pet shop, banho e tosa"})["ok"])
        n = next(x for x in pesquisa.listar()["nichos"] if x["nome"] == "Pet shop de bairro")
        self.assertEqual((n["prioridade"], n["termos"]), (5, ["pet shop", "banho e tosa"]))
        r = pesquisa.salvar_referencia({"gancho": "Testei uma IA no meu WhatsApp", "perfil": "perfil.ia", "views": "120000", "url": "https://x/1"})
        self.assertTrue(r["ok"])
        ref = next(x for x in pesquisa.listar()["referencias"] if x["url"] == "https://x/1")
        self.assertEqual((ref["perfil"], ref["formato"]), ("@perfil.ia", "prova"))
        self.assertFalse(pesquisa.salvar_referencia({"gancho": "outra", "url": "https://x/1"})["ok"])  # repetido


if __name__ == "__main__":
    unittest.main()
