"""Comandos financeiros locais e explícitos, sem chamadas à IA."""

import sqlite3

from financeiro import cadastrar_conta, listar_contas


AJUDA = "Para cadastrar uma conta mensal, use: /conta Internet; 120,00; 10. Para listar, use /contas. Nenhum pagamento será realizado."


def _reais(centavos):
    return f"R$ {centavos // 100},{centavos % 100:02d}"


def responder_financeiro(mensagem, *, caminho_banco):
    comando, *resto = mensagem.strip().split(maxsplit=1)
    try:
        if comando.casefold() == "/contas":
            if resto:
                return AJUDA
            contas = listar_contas(caminho_banco=caminho_banco)
            if not contas:
                return "Você ainda não cadastrou contas mensais. " + AJUDA
            linhas = [
                f"#{c['id']} — {c['nome']}: {_reais(c['valor_centavos'])}, todo dia {c['dia_vencimento']}."
                for c in contas
            ]
            return "Contas mensais cadastradas:\n" + "\n".join(linhas) + "\nNos meses mais curtos, os dias inexistentes correspondem ao último dia do mês. Nenhum pagamento é realizado."
        if comando.casefold() != "/conta" or not resto:
            return AJUDA
        campos = [campo.strip() for campo in resto[0].split(";")]
        if len(campos) != 3:
            return AJUDA
        nome, valor, dia = campos
        if not dia.isascii() or not dia.isdigit() or len(dia) > 2:
            return "Informe o dia de vencimento de 1 a 31. " + AJUDA
        identificador = cadastrar_conta(nome, valor, int(dia), caminho_banco=caminho_banco)
        return f"Conta mensal #{identificador} cadastrada: {nome}, todo dia {int(dia)}. Nenhum pagamento foi realizado. Use /contas para conferir o valor."
    except ValueError as erro:
        return str(erro) + " " + AJUDA
    except (sqlite3.Error, OSError):
        return "Não consegui acessar o cadastro local. Confira a pasta do banco e tente novamente; use /contas para verificar se a conta foi salva."
