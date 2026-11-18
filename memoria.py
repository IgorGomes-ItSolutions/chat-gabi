import json
from dados_conta import arquivo_da_conta


ARQUIVO_MEMORIA = "memoria.json"


MEMORIA_PADRAO = {
    "perfil": {},
    "preferencias": {},
    "projetos": [],
    "notas": []
}


def carregar_memoria():
    caminho = arquivo_da_conta("memoria.json", ARQUIVO_MEMORIA)
    if not caminho.exists():
        return MEMORIA_PADRAO.copy()

    with open(caminho, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    # Se o arquivo ainda estiver no formato antigo,
    # não vamos tentar usá-lo como memória estruturada.
    if isinstance(dados, list):
        return MEMORIA_PADRAO.copy()

    return dados


def salvar_memoria(memoria):
    caminho = arquivo_da_conta("memoria.json", ARQUIVO_MEMORIA)
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(
            memoria,
            arquivo,
            ensure_ascii=False,
            indent=4
        )


def salvar_informacao(tipo, valor):
    memoria = carregar_memoria()

    if tipo in ["nome", "cidade", "profissao"]:
        memoria["perfil"][tipo] = valor

    else:
        memoria["notas"].append({
            "tipo": tipo,
            "valor": valor
        })

    salvar_memoria(memoria)


def buscar_informacao(tipo):
    memoria = carregar_memoria()

    if tipo in memoria.get("perfil", {}):
        return memoria["perfil"][tipo]

    for nota in memoria.get("notas", []):
        if nota.get("tipo") == tipo:
            return nota.get("valor")

    return None


def obter_memoria():
    return carregar_memoria()