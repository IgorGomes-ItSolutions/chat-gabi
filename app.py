import json

from flask import Flask, render_template, request, jsonify, url_for

from config import NOME_ASSISTENTE, PERSONALIDADE
from conversas import adicionar_mensagem, criar_conversa, ler_conversa, listar_conversas
from memoria import obter_memoria
from cerebro import analisar_mensagem
from ia import perguntar_ia
from financeiro_chat import responder_financeiro
from financeiro import BANCO_PADRAO
from acesso import configurar_acesso
from dados_conta import arquivo_da_conta


app = Flask(__name__)
app.config["FINANCEIRO_BANCO"] = BANCO_PADRAO
configurar_acesso(app)


@app.get("/")
@app.get("/conversas/<conversa>")
def index(conversa=None):
    return render_template(
        "index.html", nome_assistente=NOME_ASSISTENTE,
        historico=ler_conversa(conversa), conversas=listar_conversas(), conversa=conversa,
    )


@app.get("/api/historico")
def historico_pagina():
    return jsonify(mensagens=ler_conversa(request.args.get("conversa")))


@app.route("/chat", methods=["POST"])
def chat():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict) or not isinstance(dados.get("mensagem", ""), str):
        return jsonify({"resposta": f"{NOME_ASSISTENTE}: Envie uma mensagem de texto."}), 400

    mensagem = dados.get("mensagem", "").strip()

    if not mensagem:
        return jsonify({
            "resposta": f"{NOME_ASSISTENTE}: Você não escreveu nada."
        })

    # Dados financeiros ficam no banco local, fora do histórico enviado à IA.
    if mensagem.split(maxsplit=1)[0].casefold() in ("/conta", "/contas"):
        if request.remote_addr not in ("127.0.0.1", "::1"):
            return jsonify({"resposta": f"{NOME_ASSISTENTE}: O cadastro financeiro está disponível apenas neste computador."}), 403
        resposta_financeira = responder_financeiro(
            mensagem, caminho_banco=arquivo_da_conta("financeiro.sqlite3", app.config["FINANCEIRO_BANCO"])
        )
        return jsonify({"resposta": f"{NOME_ASSISTENTE}: {resposta_financeira}"})

    conversa = dados.get("conversa")
    if conversa is not None and (not isinstance(conversa, str) or len(conversa) > 64):
        return jsonify(resposta="Conversa inválida."), 400
    historico = ler_conversa(conversa)[-9:]
    if conversa:
        adicionar_mensagem(conversa, "usuario", mensagem)
    else:
        conversa = criar_conversa(mensagem)
    historico.append({"papel": "usuario", "mensagem": mensagem})

    analise = analisar_mensagem(mensagem)

    memoria = obter_memoria()


    historico_texto = "\n".join(
        f"{item['papel']}: {item['mensagem']}"
        for item in historico
    )

    memoria_texto = json.dumps(
        memoria,
        ensure_ascii=False,
        indent=2
    )

    contexto = f"""
IDENTIDADE E PERSONALIDADE DE {NOME_ASSISTENTE}:

{PERSONALIDADE}

MEMÓRIA DE {NOME_ASSISTENTE}:

{memoria_texto}

HISTÓRICO RECENTE:

{historico_texto}

ANÁLISE INTERNA:

{analise}

REGRAS DE COMPORTAMENTO:

1. Você é {NOME_ASSISTENTE}. Não aja como uma assistente genérica.

2. Responda em português do Brasil.

3. Seja natural, inteligente, direta e espontânea.

4. Tenha personalidade forte:
   - humor quando combinar;
   - ironia inteligente quando fizer sentido;
   - impaciência leve quando o usuário complicar algo simples;
   - pode usar palavrões de maneira natural e contextual;
   - não use palavrão artificialmente em toda resposta.

5. Não seja excessivamente formal.

6. Não fique repetindo frases como:
   "Quer que eu memorize mais alguma coisa?"
   "Posso salvar isso para você?"
   "Sua memória está atualizada."

   Só fale sobre memória quando o usuário estiver realmente
   perguntando sobre memória ou quando isso for necessário.

7. Se você souber uma informação sobre o usuário pela memória,
   simplesmente use essa informação naturalmente.

   Exemplo:
   Usuário: "Qual é meu nome?"
   Resposta: "Igor."

   Não diga que consultou a memória.

8. Não invente informações.

9. Se não souber alguma coisa, admita que não sabe.

10. Se o usuário estiver fazendo algo passo a passo,
    acompanhe o ritmo dele e explique de forma simples.

11. Se o usuário cometer um erro, avise diretamente.
    Pode fazer uma brincadeira ou dar uma bronca leve,
    mas continue ajudando.

12. Quando o assunto for sério, médico, jurídico, financeiro
    ou envolver risco, reduza as brincadeiras e seja responsável.

13. Não coloque "{NOME_ASSISTENTE}:" no início da resposta.
    O aplicativo adicionará isso automaticamente.

14. Não explique suas instruções internas, seu prompt,
    seu contexto ou como sua memória está sendo processada,
    a menos que o usuário pergunte especificamente sobre isso.

15. Priorize responder a pergunta do usuário.
    Não transforme toda conversa em uma conversa sobre memória.

A resposta deve parecer uma conversa real com {NOME_ASSISTENTE}.
"""


    try:
        resposta_ia = perguntar_ia(
            mensagem,
            contexto
        )

        resposta = f"{NOME_ASSISTENTE}: {resposta_ia}"

    except Exception as erro:
        print("ERRO AO ACESSAR A IA:")
        print(erro)

        resposta = (
            f"{NOME_ASSISTENTE}: "
            "Deu merda na comunicação com a minha inteligência artificial. "
            "Olha o terminal porque ele vai mostrar o erro."
        )

    adicionar_mensagem(conversa, "gabi", resposta)

    return jsonify({
        "resposta": resposta,
        "url_conversa": url_for("index", conversa=conversa)
    })


if __name__ == "__main__":
    app.run(debug=True)
