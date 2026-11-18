import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class ChatFinanceiroTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Importa o app real com serviços externos isolados: sem API ou memória real.
        dependencias = {}
        for nome, atributos in {
            "config": {"NOME_ASSISTENTE": "CHAT GABI", "PERSONALIDADE": "Teste"},
            "memoria": {"obter_memoria": Mock(return_value={})},
            "cerebro": {"analisar_mensagem": Mock(return_value="")},
            "ia": {"perguntar_ia": Mock(return_value="Conversa normal")},
        }.items():
            modulo = types.ModuleType(nome)
            modulo.__dict__.update(atributos)
            dependencias[nome] = modulo
        especificacao = importlib.util.spec_from_file_location("gabi_test_app", Path(__file__).with_name("app.py"))
        cls.modulo = importlib.util.module_from_spec(especificacao)
        with patch.dict(sys.modules, dependencias):
            especificacao.loader.exec_module(cls.modulo)
            cls.financeiro_chat = sys.modules["financeiro_chat"]

    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.modulo.app.instance_path = pasta.name
        self.banco = Path(pasta.name) / "contas" / "1" / "financeiro.sqlite3"
        self.modulo.app.config.update(TESTING=True, FINANCEIRO_BANCO=self.banco)
        self.cliente = self.modulo.app.test_client()
        with self.cliente.session_transaction() as sessao:
            sessao["usuario"] = "teste"
            sessao["conta_id"] = 1
            sessao["csrf"] = "token-teste"
        self.cliente.environ_base["HTTP_X_CSRF_TOKEN"] = "token-teste"
        self.modulo.perguntar_ia.reset_mock()

    def enviar(self, mensagem, **opcoes):
        return self.cliente.post("/chat", json={"mensagem": mensagem}, **opcoes)

    def test_cadastro_listagem_sem_ia_ou_historico(self):
        self.assertIn("cadastrada", self.enviar("/conta Internet; 120,50; 10").json["resposta"])
        resposta = self.enviar("/contas").json["resposta"]
        self.assertIn("R$ 120,50", resposta)
        self.assertIn("Internet", resposta)
        self.modulo.perguntar_ia.assert_not_called()

    def test_erros_nao_cadastram(self):
        for mensagem in ("/conta", "/conta Luz; -1; 10", "/conta Luz; 10; 32", "/conta Luz; 10; abc", "/conta Luz; 10; 10; extra"):
            self.assertEqual(self.enviar(mensagem).status_code, 200)
        self.assertFalse(self.banco.exists())

    def test_conversa_comum_preservada(self):
        self.assertEqual(self.enviar("Olá").json["resposta"], "CHAT GABI: Conversa normal")
        self.modulo.perguntar_ia.assert_called_once()

    def test_acesso_remoto_bloqueado(self):
        resposta = self.enviar("/conta Luz; 100; 10", environ_overrides={"REMOTE_ADDR": "192.168.1.20"})
        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(self.banco.exists())

    def test_json_invalido_e_mensagem_vazia(self):
        for dados in ([], None, {"mensagem": 123}):
            self.assertEqual(self.cliente.post("/chat", json=dados).status_code, 400)
        self.assertIn("não escreveu", self.enviar(" ").json["resposta"])

    def test_falha_banco_responde_sem_ia(self):
        with patch.object(self.financeiro_chat, "listar_contas", side_effect=OSError("teste")):
            self.assertIn("Não consegui", self.enviar("/contas").json["resposta"])
        self.modulo.perguntar_ia.assert_not_called()

    def test_pagina_historico_e_escape(self):
        mensagens = [{"papel": "usuario", "mensagem": "<script>alert('teste')</script>"}]
        inicial = self.enviar(mensagens[0]["mensagem"]).json["url_conversa"]
        pagina = self.cliente.get(inicial)
        self.assertEqual(pagina.status_code, 200)
        html = pagina.get_data(as_text=True)
        self.assertIn("Novo chat", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>alert", html)
        consulta = "/api/historico?conversa=" + inicial.rsplit("/", 1)[-1]
        self.assertEqual(self.cliente.get(consulta).json["mensagens"][0], mensagens[0])
        with self.cliente.session_transaction() as sessao:
            sessao["conta_id"] = 2
        self.assertEqual(self.cliente.get(inicial).status_code, 404)
        self.assertEqual(self.cliente.get(consulta).status_code, 404)

    def test_logout_bloqueia_conversa_e_historico(self):
        self.assertEqual(self.cliente.post("/sair").status_code, 302)
        self.assertEqual(self.cliente.get("/api/historico").status_code, 401)
        self.assertEqual(self.enviar("/contas").status_code, 401)


if __name__ == "__main__":
    unittest.main()
