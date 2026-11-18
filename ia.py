import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


def criar_cliente():
    """
    Cria o cliente da OpenAI usando a chave
    armazenada no arquivo .env.
    """

    chave_api = os.getenv("OPENAI_API_KEY")

    if not chave_api:
        raise ValueError(
            "A chave OPENAI_API_KEY não foi encontrada no arquivo .env."
        )

    return OpenAI(api_key=chave_api)


def perguntar_ia(mensagem, contexto=""):
    """
    Envia uma mensagem para a inteligência artificial
    e retorna a resposta.
    """

    cliente = criar_cliente()

    prompt = mensagem

    if contexto:
        prompt = f"""
Contexto da conversa:

{contexto}

Mensagem do usuário:

{mensagem}
"""

    resposta = cliente.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    return resposta.output_text