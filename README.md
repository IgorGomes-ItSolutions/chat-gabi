# Chat Gabi

Assistente de chat feito com Flask. Comecei com uma única conversa e depois passei a salvar cada chat separadamente. Na versão atual, cada conta tem sua própria lista de conversas e pode voltar a um assunto sem misturar o histórico com o de outro usuário.

O backend usa Python, SQLite e a API da OpenAI. A interface usa Jinja, CSS e JavaScript. Há também comandos locais para cadastrar e consultar contas recorrentes.

## Rodar no Windows

Com Python instalado, execute no PowerShell, dentro da pasta do projeto.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Preencha `OPENAI_API_KEY` no arquivo `.env` para usar o chat. Depois, inicie o Flask:

```powershell
.\.venv\Scripts\python.exe -m flask --app app run
```

Abra [localhost:5000](http://127.0.0.1:5000) e clique em **Criar conta**. Use **Novo chat** para começar outro assunto. Os dados da aplicação ficam em `instance/`.

## Testes

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -v
```

Os testes usam dados temporários e simulam a API da OpenAI. O projeto está em fase de teste local e beta privado.
