"""Cadastro e autenticação das contas do CHAT GABI."""
import hmac
import secrets
import sqlite3
import time
from datetime import timedelta
from pathlib import Path
from flask import abort, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


def configurar_acesso(app):
    pasta = Path(app.instance_path)
    pasta.mkdir(parents=True, exist_ok=True)
    chave = pasta / "sessao.key"
    try:
        with chave.open("x", encoding="utf-8") as arquivo:
            arquivo.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    app.secret_key = chave.read_text(encoding="utf-8").strip()
    app.config.update(ACESSO_BANCO=pasta / "acesso.sqlite3", SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE="Lax", PERMANENT_SESSION_LIFETIME=timedelta(hours=8))
    tentativas = {}

    def conectar():
        conexao = sqlite3.connect(app.config["ACESSO_BANCO"])
        conexao.execute("CREATE TABLE IF NOT EXISTS proprietario (id INTEGER PRIMARY KEY CHECK(id=1), usuario TEXT NOT NULL, senha_hash TEXT NOT NULL)")
        conexao.execute("CREATE TABLE IF NOT EXISTS contas (id INTEGER PRIMARY KEY, usuario TEXT NOT NULL UNIQUE, senha_hash TEXT NOT NULL)")
        with conexao:
            conexao.execute("INSERT OR IGNORE INTO contas SELECT id, usuario, senha_hash FROM proprietario")
        return conexao

    def buscar_conta(usuario):
        conexao = conectar()
        try:
            return conexao.execute("SELECT id, usuario, senha_hash FROM contas WHERE usuario = ?", (usuario,)).fetchone()
        finally:
            conexao.close()

    def csrf():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(32)
        return session["csrf"]

    app.jinja_env.globals["csrf_token"] = csrf

    @app.before_request
    def proteger():
        if request.endpoint == "static":
            return
        publico = request.endpoint in ("entrar", "primeiro_acesso")
        if not publico and not session.get("conta_id"):
            if request.path.startswith("/api/") or request.path == "/chat":
                return jsonify(resposta="Sua sessão terminou. Entre novamente."), 401
            return redirect(url_for("entrar"))
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            recebido = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
            if not session.get("csrf") or not hmac.compare_digest(session["csrf"].encode("utf-8"), recebido.encode("utf-8")):
                return jsonify(resposta="Atualize a página e tente novamente."), 400

    @app.after_request
    def privacidade(resposta):
        if request.endpoint != "static":
            resposta.headers["Cache-Control"] = "no-store"
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        return resposta

    @app.route("/primeiro-acesso", methods=["GET", "POST"])
    @app.route("/cadastro", methods=["GET", "POST"])
    def primeiro_acesso():
        if request.remote_addr not in ("127.0.0.1", "::1"):
            abort(403)
        if session.get("conta_id"):
            return redirect(url_for("index"))
        erro = None
        if request.method == "POST":
            usuario = request.form.get("usuario", "").strip()
            senha = request.form.get("senha", "")
            if not 3 <= len(usuario) <= 60 or not 10 <= len(senha) <= 128:
                erro = "Use um usuário de 3 a 60 caracteres e uma senha de 10 a 128 caracteres."
            elif senha != request.form.get("confirmacao"):
                erro = "As senhas não coincidem."
            else:
                conexao = conectar()
                try:
                    with conexao:
                        conta_id = conexao.execute(
                            "INSERT INTO contas (usuario, senha_hash) VALUES (?, ?)",
                            (usuario, generate_password_hash(senha)),
                        ).lastrowid
                except sqlite3.IntegrityError:
                    erro = "Este usuário já existe. Escolha outro nome ou entre na sua conta."
                else:
                    autenticar(conta_id, usuario)
                    return redirect(url_for("index"))
                finally:
                    conexao.close()
        return render_template("login.html", criar=True, erro=erro)

    @app.route("/entrar", methods=["GET", "POST"])
    def entrar():
        if session.get("usuario"):
            return redirect(url_for("index"))
        erro = None
        if request.method == "POST":
            endereco = request.remote_addr
            agora = time.monotonic()
            falhas = [t for t in tentativas.get(endereco, []) if agora - t < 300]
            tentativas[endereco] = falhas
            if len(falhas) >= 5:
                return render_template("login.html", criar=False, erro="Muitas tentativas. Aguarde cinco minutos."), 429
            senha = request.form.get("senha", "")
            conta = buscar_conta(request.form.get("usuario", "").strip())
            if conta and len(senha) <= 128 and check_password_hash(conta[2], senha):
                tentativas.pop(endereco, None)
                autenticar(conta[0], conta[1])
                return redirect(url_for("index"))
            falhas.append(agora)
            erro = "Usuário ou senha incorretos."
        return render_template("login.html", criar=False, erro=erro)

    def autenticar(conta_id, usuario):
        session.clear()
        session["conta_id"] = conta_id
        session["usuario"] = usuario
        session.permanent = True
        csrf()

    @app.post("/sair")
    def sair():
        session.clear()
        return redirect(url_for("entrar"))
