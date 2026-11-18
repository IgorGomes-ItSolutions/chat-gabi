import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from flask import Flask
from acesso import configurar_acesso


class AcessoTest(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.app = Flask(__name__, instance_path=pasta.name, template_folder=str(Path(__file__).parent / "templates"))
        self.app.config["TESTING"] = True
        configurar_acesso(self.app)
        self.app.add_url_rule("/", "index", lambda: "Conversa privada")
        self.app.add_url_rule("/chat", "chat", lambda: "Mensagem privada", methods=["POST"])
        self.app.add_url_rule("/api/historico", "historico", lambda: "Histórico privado")
        self.cliente = self.app.test_client()

    def token(self):
        with self.cliente.session_transaction() as sessao:
            return sessao["csrf"]

    def cadastrar(self):
        self.cliente.get("/primeiro-acesso")
        return self.cliente.post("/primeiro-acesso", data={"csrf_token": self.token(), "usuario": "Igor", "senha": "senha-de-teste-123", "confirmacao": "senha-de-teste-123"})

    def sair(self):
        self.cliente.get("/entrar")
        self.cliente.post("/sair", data={"csrf_token": self.token()})

    def test_dados_protegidos_sem_login(self):
        self.assertEqual(self.cliente.get("/").status_code, 302)
        self.assertEqual(self.cliente.get("/api/historico").status_code, 401)
        self.assertEqual(self.cliente.post("/chat", json={"mensagem": "oi"}).status_code, 401)

    def test_primeiro_acesso_hash_login_e_saida(self):
        self.assertEqual(self.cadastrar().status_code, 302)
        self.assertEqual(self.cliente.get("/").data, b"Conversa privada")
        with closing(sqlite3.connect(self.app.config["ACESSO_BANCO"])) as conexao:
            senha_hash = conexao.execute("SELECT senha_hash FROM contas").fetchone()[0]
        self.assertNotEqual(senha_hash, "senha-de-teste-123")
        self.sair()
        self.assertEqual(self.cliente.get("/api/historico").status_code, 401)
        self.cliente.get("/entrar")
        retorno = self.cliente.post("/entrar", data={"csrf_token": self.token(), "usuario": "Igor", "senha": "senha-de-teste-123"})
        self.assertEqual(retorno.status_code, 302)
        self.assertEqual(self.cliente.get("/").status_code, 200)

    def test_csrf_obrigatorio(self):
        self.cliente.get("/primeiro-acesso")
        self.assertEqual(self.cliente.post("/primeiro-acesso", data={"usuario": "Igor", "senha": "senha-de-teste-123"}).status_code, 400)
        self.cadastrar()
        self.assertEqual(self.cliente.post("/chat", json={"mensagem": "oi"}).status_code, 400)
        self.assertEqual(self.cliente.post("/sair").status_code, 400)
        self.assertEqual(self.cliente.post("/sair", headers={"X-CSRF-Token": "inválido"}).status_code, 400)

    def test_cadastro_local_de_segunda_conta(self):
        self.assertEqual(self.cliente.get("/primeiro-acesso", environ_overrides={"REMOTE_ADDR": "192.168.1.20"}).status_code, 403)
        self.cadastrar()
        self.assertEqual(self.cliente.get("/primeiro-acesso").status_code, 302)
        self.sair()
        self.assertIn("Criar conta", self.cliente.get("/entrar").get_data(as_text=True))
        dados = {"csrf_token": self.token(), "usuario": "Segunda conta", "senha": "senha-de-teste-123", "confirmacao": "senha-de-teste-123"}
        self.assertEqual(self.cliente.post("/cadastro", data=dados).status_code, 302)
        with closing(sqlite3.connect(self.app.config["ACESSO_BANCO"])) as conexao:
            self.assertEqual(conexao.execute("SELECT COUNT(*) FROM contas").fetchone()[0], 2)

    def test_senha_errada_e_limite(self):
        self.cadastrar()
        self.sair()
        self.cliente.get("/entrar")
        dados = {"csrf_token": self.token(), "usuario": "Igor", "senha": "incorreta"}
        for _ in range(5):
            self.assertIn("incorretos", self.cliente.post("/entrar", data=dados).get_data(as_text=True))
        self.assertEqual(self.cliente.post("/entrar", data=dados).status_code, 429)
        self.assertEqual(self.cliente.get("/").status_code, 302)

    def test_validacao_e_headers(self):
        pagina = self.cliente.get("/primeiro-acesso")
        self.assertEqual(pagina.headers["Cache-Control"], "no-store")
        dados = {"csrf_token": self.token(), "usuario": "Igor", "senha": "curta", "confirmacao": "curta"}
        self.assertIn("10 a 128", self.cliente.post("/primeiro-acesso", data=dados).get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
