import json
import sqlite3
from contextlib import contextmanager
from uuid import uuid4

from flask import abort

from dados_conta import arquivo_da_conta


@contextmanager
def conectar():
    caminho = arquivo_da_conta("conversas.sqlite3", "conversas.sqlite3")
    banco = sqlite3.connect(caminho)
    banco.row_factory = sqlite3.Row
    try:
        with banco:
            banco.execute("BEGIN IMMEDIATE")
            banco.execute("""
                CREATE TABLE IF NOT EXISTS conversas (
                    id TEXT PRIMARY KEY, titulo TEXT NOT NULL
                )
            """)
            banco.execute("""
                CREATE TABLE IF NOT EXISTS mensagens (
                    conversa TEXT NOT NULL, papel TEXT NOT NULL, mensagem TEXT NOT NULL
                )
            """)
            banco.execute("CREATE INDEX IF NOT EXISTS mensagens_conversa ON mensagens (conversa)")
            importar_historico(banco, caminho.with_name("historico.json"))
            yield banco
    finally:
        banco.close()


def importar_historico(banco, arquivo):
    if not arquivo.exists():
        return
    conversa = "historico-anterior"
    if banco.execute("SELECT 1 FROM conversas WHERE id = ?", (conversa,)).fetchone():
        return
    mensagens = json.loads(arquivo.read_text(encoding="utf-8"))
    if mensagens:
        banco.execute("INSERT INTO conversas VALUES (?, ?)", (conversa, "Conversa anterior"))
        banco.executemany(
            "INSERT INTO mensagens VALUES (?, ?, ?)",
            [(conversa, item["papel"], item["mensagem"]) for item in mensagens],
        )


def listar_conversas():
    with conectar() as banco:
        return banco.execute("SELECT id, titulo FROM conversas ORDER BY rowid DESC").fetchall()


def ler_conversa(conversa):
    if not conversa:
        return []
    with conectar() as banco:
        if not banco.execute("SELECT 1 FROM conversas WHERE id = ?", (conversa,)).fetchone():
            abort(404)
        return [dict(item) for item in banco.execute(
            "SELECT papel, mensagem FROM mensagens WHERE conversa = ? ORDER BY rowid",
            (conversa,),
        )]


def criar_conversa(mensagem):
    conversa = uuid4().hex
    titulo = " ".join(mensagem.split())
    if len(titulo) > 64:
        titulo = titulo[:63] + "…"
    with conectar() as banco:
        banco.execute("INSERT INTO conversas VALUES (?, ?)", (conversa, titulo))
        banco.execute("INSERT INTO mensagens VALUES (?, ?, ?)", (conversa, "usuario", mensagem))
    return conversa


def adicionar_mensagem(conversa, papel, mensagem):
    with conectar() as banco:
        banco.execute("INSERT INTO mensagens VALUES (?, ?, ?)", (conversa, papel, mensagem))
