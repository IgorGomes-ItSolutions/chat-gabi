from pathlib import Path

from flask import current_app, has_request_context, session


def arquivo_da_conta(nome, padrao):
    if not has_request_context():
        return Path(padrao)
    conta_id = session.get("conta_id")
    if type(conta_id) is not int:
        raise RuntimeError("Conta autenticada necessária")
    pasta = Path(current_app.instance_path) / "contas" / str(conta_id)
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / nome
