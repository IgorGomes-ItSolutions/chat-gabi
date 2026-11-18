"""Cadastro local de contas mensais. Não executa pagamentos."""

import sqlite3
from decimal import Decimal, InvalidOperation
from pathlib import Path


BANCO_PADRAO = Path(__file__).resolve().parent / "instance" / "financeiro.sqlite3"


def _conectar(caminho_banco):
    caminho = Path(caminho_banco)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(caminho)
    conexao.row_factory = sqlite3.Row
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS contas_recorrentes (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL CHECK(length(trim(nome)) BETWEEN 1 AND 120),
            valor_centavos INTEGER NOT NULL CHECK(valor_centavos > 0),
            dia_vencimento INTEGER NOT NULL CHECK(dia_vencimento BETWEEN 1 AND 31)
        )
    """)
    conexao.commit()
    return conexao


def cadastrar_conta(nome, valor, dia_vencimento, *, caminho_banco=BANCO_PADRAO):
    """Salva obrigação mensal; valor aceita '120.50' ou '120,50'.

    Não registra pagamento nem guarda dados bancários. Dias 29 a 31
    representam o último dia do mês quando não existirem naquele mês.
    """
    if not isinstance(nome, str) or not 1 <= len(nome.strip()) <= 120:
        raise ValueError("Informe um nome com 1 a 120 caracteres.")
    if type(dia_vencimento) is not int or not 1 <= dia_vencimento <= 31:
        raise ValueError("O dia de vencimento deve ser um inteiro de 1 a 31.")
    if isinstance(valor, (bool, float)):
        raise ValueError("Informe o valor como texto ou Decimal, sem usar float.")
    try:
        decimal = Decimal(str(valor).strip().replace(",", "."))
        if not decimal.is_finite() or not Decimal("0") < decimal <= Decimal("999999999.99"):
            raise ValueError("O valor deve ser positivo e até 999999999,99.")
        centavos = decimal * 100
        if centavos != centavos.to_integral_value():
            raise ValueError("O valor deve ter no máximo duas casas decimais.")
    except (InvalidOperation, TypeError):
        raise ValueError("Informe um valor monetário válido.") from None
    conexao = _conectar(caminho_banco)
    try:
        with conexao:
            cursor = conexao.execute(
                "INSERT INTO contas_recorrentes (nome, valor_centavos, dia_vencimento) VALUES (?, ?, ?)",
                (nome.strip(), int(centavos), dia_vencimento),
            )
            return cursor.lastrowid
    finally:
        conexao.close()


def listar_contas(*, caminho_banco=BANCO_PADRAO):
    """Retorna contas mensais na ordem de cadastro, com valores em centavos."""
    conexao = _conectar(caminho_banco)
    try:
        return [dict(linha) for linha in conexao.execute(
            "SELECT id, nome, valor_centavos, dia_vencimento FROM contas_recorrentes ORDER BY id"
        )]
    finally:
        conexao.close()
