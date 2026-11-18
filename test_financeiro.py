import tempfile
import unittest
from pathlib import Path

from financeiro import cadastrar_conta, listar_contas


class CadastroFinanceiroTest(unittest.TestCase):
    def setUp(self):
        self.temporario = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporario.cleanup)
        self.banco = Path(self.temporario.name) / "dados" / "teste.sqlite3"

    def cadastrar(self, nome="Internet", valor="120,50", dia=10):
        return cadastrar_conta(nome, valor, dia, caminho_banco=self.banco)

    def test_cadastro_persistente_e_valor_exato(self):
        identificador = self.cadastrar()
        self.assertEqual(listar_contas(caminho_banco=self.banco), [{
            "id": identificador, "nome": "Internet", "valor_centavos": 12050,
            "dia_vencimento": 10,
        }])

    def test_valores_invalidos_nao_criam_banco(self):
        for valor in ("0", "-1", "1.001", "NaN", "Infinity", "abc", "1.234,56", True, 1.1, "1000000000"):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                self.cadastrar(valor=valor)
        self.assertFalse(self.banco.exists())

    def test_dias_invalidos(self):
        for dia in (0, 32, True, "10", 10.5):
            with self.subTest(dia=dia), self.assertRaises(ValueError):
                self.cadastrar(dia=dia)

    def test_nome_invalido(self):
        for nome in ("", "  ", None, "x" * 121):
            with self.subTest(nome=nome), self.assertRaises(ValueError):
                self.cadastrar(nome=nome)

    def test_nome_sql_e_dias_limite(self):
        nome = "Luz'); DROP TABLE contas_recorrentes; --"
        self.cadastrar(nome=nome, valor="0.01", dia=1)
        self.cadastrar(dia=31)
        contas = listar_contas(caminho_banco=self.banco)
        self.assertEqual(len(contas), 2)
        self.assertEqual(contas[0]["nome"], nome)
        self.assertEqual(contas[0]["valor_centavos"], 1)

    def test_lista_inicial_vazia(self):
        self.assertEqual(listar_contas(caminho_banco=self.banco), [])


if __name__ == "__main__":
    unittest.main()
