"""Biblioteca: python -m unittest discover -s central/testes -p "test_*.py" """
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ["CIELLO_COMERCIAL"] = str(Path(__file__).resolve().parents[2] / "exemplo" / "comercial")  # a empresa fictícia
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import biblioteca  # noqa: E402
import conteudo  # noqa: E402


class TesteBiblioteca(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = self.raiz = Path(self.tmp.name)
        for rel, dado in {
            "roteiros/2026-10-24-ia-que-trabalha.json": json.dumps({"capa": {"linhas": [["IA que", "x"], ["trabalha", "y"]]}, "scenes": [{"say": "Oi"}]}),
            "midia/2026-10-19-antigo.mp4": b"v" * 10, "midia/final/2026-10-24-ia-que-trabalha.mp4": b"f" * 10,
            "midia/estudio/2026-10-24-ia-que-trabalha-o98-15.mp4": b"e" * 10, "midia/capas/2026-10-24-ia-que-trabalha.jpg": b"j",
            "radar/2026-10-24.md": "# Radar", "estado/voz/amostras/2026-10-24-134059.webm": b"w" * 4188,
            "audio/ia-que-trabalha/narracao.wav": b"a", "estado/segredo.json": "{}", "midia/capas/_teste-verificacao.jpg": b"t",
        }.items():
            p = r / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(dado if isinstance(dado, bytes) else dado.encode("utf-8"))
        self.p = mock.patch.object(biblioteca.dados, "pasta_dados", lambda: r)
        self.p.start()
        self.p2 = mock.patch.object(conteudo, "RAIZ", r)
        self.p2.start()

    def tearDown(self):
        self.p.stop()
        self.p2.stop()
        self.tmp.cleanup()

    def test_secoes_com_titulo_do_roteiro_e_grupo(self):
        s = biblioteca.listar()["secoes"]
        videos = {x["rel"]: x for x in s["videos"]}
        self.assertEqual(set(videos), {"midia/2026-10-19-antigo.mp4", "midia/final/2026-10-24-ia-que-trabalha.mp4",
                                       "midia/estudio/2026-10-24-ia-que-trabalha-o98-15.mp4"})
        self.assertEqual(videos["midia/estudio/2026-10-24-ia-que-trabalha-o98-15.mp4"]["titulo"], "IA que trabalha")
        self.assertEqual(videos["midia/final/2026-10-24-ia-que-trabalha.mp4"]["grupo"], "Final")
        self.assertEqual([x["rel"] for x in s["capas"]], ["midia/capas/2026-10-24-ia-que-trabalha.jpg"])  # o _teste da verificação não entra
        self.assertEqual(len(s["roteiros"]), 1)
        self.assertEqual(s["pesquisas"][0]["grupo"], "Radar de tendências")
        self.assertEqual({x["grupo"] for x in s["vozes"]}, {"Sua gravação", "Narração"})
        self.assertIn("Gravação das 13:40", [x["titulo"] for x in s["vozes"]])

    def test_posts_juntam_video_capa_e_narracao_do_roteiro(self):
        d = biblioteca.listar()
        self.assertEqual(len(d["posts"]), 1)
        q = d["posts"][0]
        self.assertEqual(q["post"], "2026-10-24-ia-que-trabalha")
        self.assertEqual(q["titulo"], "IA que trabalha")
        self.assertEqual(q["roteiro"], "roteiros/2026-10-24-ia-que-trabalha.json")
        self.assertEqual([v["rel"] for v in q["videos"]], ["midia/final/2026-10-24-ia-que-trabalha.mp4",  # o final vem primeiro
                                                           "midia/estudio/2026-10-24-ia-que-trabalha-o98-15.mp4"])
        self.assertEqual(q["capa"], "midia/capas/2026-10-24-ia-que-trabalha.jpg")
        self.assertEqual([a["rel"] for a in q["audios"]], ["audio/ia-que-trabalha/narracao.wav"])
        self.assertTrue(q["etapas"]["final"] and q["etapas"]["capa"])
        self.assertFalse(q["publicado"])
        self.assertEqual({k: d["resumo"][k] for k in ("posts", "prontos", "producao", "videos")}, {"posts": 1, "prontos": 1, "producao": 0, "videos": 3})

    def test_nome_parecido_fica_no_post_certo(self):
        (self.raiz / "roteiros" / "2026-10-24-ia-que-trabalha-2.json").write_text("{}", encoding="utf-8")
        (self.raiz / "midia" / "2026-10-24-ia-que-trabalha-2.mp4").write_bytes(b"x")
        (self.raiz / "historico.md").write_text("| Data | Tema | Origem | Vídeo | Status |\n|---|---|---|---|---|\n"
                                                "| 24/10 | x | y | 2026-10-24-ia-que-trabalha-2 | Publicado |\n", encoding="utf-8")
        ps = {x["post"]: x for x in biblioteca.listar()["posts"]}
        self.assertEqual([v["rel"] for v in ps["2026-10-24-ia-que-trabalha-2"]["videos"]], ["midia/2026-10-24-ia-que-trabalha-2.mp4"])
        self.assertNotIn("midia/2026-10-24-ia-que-trabalha-2.mp4", [v["rel"] for v in ps["2026-10-24-ia-que-trabalha"]["videos"]])
        self.assertTrue(ps["2026-10-24-ia-que-trabalha-2"]["publicado"])

    def test_so_abre_arquivo_das_pastas_da_biblioteca(self):
        self.assertIsNotNone(biblioteca.caminho("midia/final/2026-10-24-ia-que-trabalha.mp4"))
        for rel in ("estado/segredo.json", "../fora.txt", "/etc/passwd", "midia\\x.mp4", "midia/nao-existe.mp4"):
            self.assertIsNone(biblioteca.caminho(rel), rel)
        self.assertTrue(biblioteca.ler("roteiros/2026-10-24-ia-que-trabalha.json")["ok"])
        self.assertFalse(biblioteca.ler("midia/final/2026-10-24-ia-que-trabalha.mp4")["ok"])  # vídeo não vira texto


if __name__ == "__main__":
    unittest.main()
