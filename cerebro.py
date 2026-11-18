import json

from config import NOME_ASSISTENTE

from ia import perguntar_ia
from memoria import salvar_informacao, obter_memoria


def analisar_mensagem(mensagem):
    """
    Usa a inteligência artificial para analisar
    a mensagem do usuário e identificar informações
    que podem ser importantes para a memória.
    """

    memoria_atual = obter_memoria()

    memoria_texto = json.dumps(
        memoria_atual,
        ensure_ascii=False,
        indent=2
    )

    contexto = f"""
Você é o módulo de memória de {NOME_ASSISTENTE}.

Sua função é analisar a mensagem do usuário e decidir
se existe alguma informação pessoal ou relevante que
deva ser armazenada na memória permanente.

MEMÓRIA ATUAL:

{memoria_texto}

MENSAGEM DO USUÁRIO:

{mensagem}

Analise a mensagem e responda SOMENTE em JSON válido.

Use exatamente este formato:

{{
    "deve_salvar": true,
    "tipo": "nome",
    "valor": "Igor"
}}

ou, se não houver nada importante para guardar:

{{
    "deve_salvar": false,
    "tipo": null,
    "valor": null
}}

Tipos permitidos inicialmente:

- nome
- cidade
- profissao
- preferencia
- projeto
- nota

Não invente informações.
Só registre algo que realmente esteja presente
na mensagem do usuário.
"""

    try:
        resposta = perguntar_ia(
            mensagem,
            contexto
        )

        resposta = resposta.strip()

        if resposta.startswith("```"):
            resposta = resposta.replace("```json", "")
            resposta = resposta.replace("```", "")
            resposta = resposta.strip()

        resultado = json.loads(resposta)

        if resultado.get("deve_salvar") is True:
            tipo = resultado.get("tipo")
            valor = resultado.get("valor")

            if tipo and valor:
                salvar_informacao(tipo, valor)

        return resultado

    except Exception as erro:
        print("ERRO AO ANALISAR MEMÓRIA:")
        print(erro)

        return {
            "deve_salvar": False,
            "tipo": None,
            "valor": None
        }


def consultar_memoria(tipo):
    """
    Consulta uma informação específica da memória.
    """

    memoria = obter_memoria()

    if tipo in memoria.get("perfil", {}):
        return memoria["perfil"][tipo]

    for nota in memoria.get("notas", []):
        if nota.get("tipo") == tipo:
            return nota.get("valor")

    return None


def salvar_memoria(tipo, valor):
    """
    Salva uma informação na memória permanente.
    """

    salvar_informacao(tipo, valor)

    return {
        "memoria": tipo,
        "valor": valor
    }