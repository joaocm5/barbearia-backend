# ==========================================================
# IMPORTS
# ==========================================================
# requests permite que o backend faca chamadas HTTP para outros servicos
import requests
# Flask   = cria o servidor web
# request = le os dados que chegam do frontend
# jsonify = converte a resposta para JSON
# session = "caixinha" onde o Flask guarda quem esta logado.
#           Os dados ficam num cookie no navegador do usuario e
#           voltam a cada requisicao, e assim o servidor sabe quem e
#           a pessoa sem precisar pedir a senha de novo toda hora.
from flask import Flask, request, jsonify, session

# check_password_hash compara a senha digitada com o hash guardado no banco.
# O sistema nunca sabe qual e a senha - ele so consegue reconhecer
# quando a senha certa e digitada, porque o hash gerado bate com o salvo.
from werkzeug.security import check_password_hash

# wraps preserva o nome da funcao original quando ela e embrulhada
# por um decorador. Sem ele, o Flask acharia que todas as rotas
# protegidas se chamam "verificar" e daria erro de nome duplicado.
from functools import wraps

# funcao de conexao com o banco, definida no database.py
from database import conectar


# cria o aplicativo
app = Flask(__name__)


# ==========================================================
# CHAVE SECRETA
# ==========================================================

# O Flask ASSINA o cookie de sessao usando esta chave.
# Assinar nao e o mesmo que esconder: o conteudo do cookie e legivel,
# mas vem com uma "impressao digital" gerada a partir da chave.
#
# Se alguem editar o cookie a mao para dizer "sou o usuario 1",
# a impressao digital nao bate e o Flask descarta a sessao inteira.
# Como so o servidor conhece a chave, ninguem consegue forjar um cookie valido.
#
# Em um sistema real esta chave viria de uma variavel de ambiente,
# nunca escrita no codigo que vai para o GitHub.
app.secret_key = "chave-secreta-da-barbearia-vintage"

# endereco do webhook do n8n que dispara o email de confirmacao
# durante o desenvolvimento usamos a URL de teste (webhook-test)
URL_N8N = "http://localhost:5678/webhook-test/novo-agendamento"

# ----------------------------------------------------------
# PROTECAO DAS ROTAS
# ----------------------------------------------------------

# decorador: roda esta verificacao ANTES de qualquer rota protegida
def login_obrigatorio(funcao):
    @wraps(funcao)
    def verificar(*args, **kwargs):
        # se nao existe usuario na sessao, bloqueia
        if "usuario_id" not in session:
            return jsonify({"erro": "nao autenticado"}), 401   # 401 = nao autorizado
        # se existe, deixa a rota original rodar normalmente
        return funcao(*args, **kwargs)
    return verificar


# LOGIN - confere email e senha e abre a sessao
@app.route("/login", methods=["POST"])
def login():
    dados = request.get_json()
    conexao = conectar()

    # busca o usuario pelo email
    usuario = conexao.execute(
        "SELECT * FROM usuarios WHERE email = ?", (dados["email"],)
    ).fetchone()
    conexao.close()

    # se nao achou o email OU a senha nao bate, recusa
    # a mensagem e generica de proposito: nao revela qual dos dois errou
    if usuario is None or not check_password_hash(usuario["senha_hash"], dados["senha"]):
        return jsonify({"erro": "email ou senha invalidos"}), 401

    # guarda o usuario na sessao - e isso que mantem ele logado
    session["usuario_id"] = usuario["id"]
    session["usuario_email"] = usuario["email"]

    return jsonify({"mensagem": "login realizado", "email": usuario["email"]})


# LOGOUT - limpa a sessao
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"mensagem": "logout realizado"})


# QUEM SOU EU - o frontend usa para saber se ainda esta logado
@app.route("/eu", methods=["GET"])
def eu():
    if "usuario_id" not in session:
        return jsonify({"autenticado": False}), 401
    return jsonify({"autenticado": True, "email": session["usuario_email"]})

# rota inicial, só para conferir se o servidor está de pé
@app.route("/")
def ola():
    return "Barbearia Vintage no ar"


# LISTAR CLIENTES - devolve todos os clientes cadastrados
@app.route("/clientes", methods=["GET"])
@login_obrigatorio
def listar_clientes():
    conexao = conectar()                                            # abre o banco
    linhas = conexao.execute("SELECT * FROM clientes").fetchall()   # busca todas as linhas
    conexao.close()                                                 # fecha o banco
    return jsonify([dict(linha) for linha in linhas])               # converte para JSON e devolve


# CADASTRAR CLIENTE - recebe os dados e grava um cliente novo
@app.route("/clientes", methods=["POST"])
@login_obrigatorio
def criar_cliente():
    dados = request.get_json()      # lê o JSON enviado pelo frontend
    conexao = conectar()

    # os ? evitam SQL injection: os valores entram separados, nunca como comando
    cursor = conexao.execute(
        "INSERT INTO clientes (nome, email, observacoes) VALUES (?, ?, ?)",
        (dados["nome"], dados.get("email"), dados.get("observacoes"))
    )

    conexao.commit()                # confirma a gravação no banco
    novo_id = cursor.lastrowid      # pega o id que o banco gerou
    conexao.close()

    return jsonify({"id": novo_id, "mensagem": "cliente criado"}), 201   # 201 = criado

# EDITAR CLIENTE - altera os dados de um cliente existente
@app.route("/clientes/<int:cliente_id>", methods=["PUT"])
@login_obrigatorio
def editar_cliente(cliente_id):
    dados = request.get_json()
    conexao = conectar()
    conexao.execute(
        "UPDATE clientes SET nome = ?, email = ?, observacoes = ? WHERE id = ?",
        (dados["nome"], dados.get("email"), dados.get("observacoes"), cliente_id)
    )
    conexao.commit()
    conexao.close()
    return jsonify({"mensagem": "cliente atualizado"})


# REMOVER CLIENTE - apaga um cliente pelo id
@app.route("/clientes/<int:cliente_id>", methods=["DELETE"])
@login_obrigatorio
def remover_cliente(cliente_id):
    conexao = conectar()
    conexao.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    conexao.commit()
    conexao.close()
    return jsonify({"mensagem": "cliente removido"})


# LISTAR AGENDAMENTOS - a agenda organizada por data e horario
@app.route("/agendamentos", methods=["GET"])
@login_obrigatorio
def listar_agendamentos():
    conexao = conectar()
    linhas = conexao.execute("""
        SELECT
            agendamentos.id,
            agendamentos.data,
            agendamentos.horario,
            agendamentos.servico,
            agendamentos.status,
            agendamentos.cliente_id,
            clientes.nome AS cliente_nome,      -- AS cria um apelido para a coluna
            clientes.email AS cliente_email     -- email do cliente, usado depois pelo n8n
        FROM agendamentos
        -- JOIN junta as duas tabelas: pega o cliente_id do agendamento
        -- e busca a linha correspondente na tabela de clientes
        JOIN clientes ON clientes.id = agendamentos.cliente_id
        -- ordena por data e, dentro da mesma data, por horario
        ORDER BY agendamentos.data, agendamentos.horario
    """).fetchall()
    conexao.close()
    return jsonify([dict(linha) for linha in linhas])


# CRIAR AGENDAMENTO - vincula um cliente a uma data, horario e servico
# CRIAR AGENDAMENTO - grava no banco e avisa o n8n para enviar o email
@app.route("/agendamentos", methods=["POST"])
@login_obrigatorio
def criar_agendamento():
    dados = request.get_json()
    conexao = conectar()

    cursor = conexao.execute(
        "INSERT INTO agendamentos (cliente_id, data, horario, servico, status) VALUES (?, ?, ?, ?, ?)",
        (dados["cliente_id"], dados["data"], dados["horario"],
         dados["servico"], dados.get("status", "agendado"))
    )
    conexao.commit()
    novo_id = cursor.lastrowid

    # busca o agendamento recem-criado ja com nome e email do cliente,
    # porque o frontend so enviou o cliente_id e o n8n precisa dos dados completos
    agendamento = conexao.execute("""
        SELECT
            agendamentos.id,
            agendamentos.data,
            agendamentos.horario,
            agendamentos.servico,
            agendamentos.status,
            clientes.nome AS cliente_nome,
            clientes.email AS cliente_email
        FROM agendamentos
        JOIN clientes ON clientes.id = agendamentos.cliente_id
        WHERE agendamentos.id = ?
    """, (novo_id,)).fetchone()
    conexao.close()

    # avisa o n8n, que cuida de montar e enviar o email ao cliente
    # o try/except garante que uma falha no n8n NAO impeca o agendamento:
    # o compromisso ja esta salvo no banco, o email e consequencia
    try:
        requests.post(URL_N8N, json=dict(agendamento), timeout=5)
    except Exception as erro:
        print(f"Nao foi possivel avisar o n8n: {erro}")

    return jsonify({"id": novo_id, "mensagem": "agendamento criado"}), 201


# EDITAR AGENDAMENTO - altera todos os campos de um agendamento existente
@app.route("/agendamentos/<int:agendamento_id>", methods=["PUT"])
@login_obrigatorio
def editar_agendamento(agendamento_id):     # o id vem do endereco: /agendamentos/3
    dados = request.get_json()
    conexao = conectar()

    conexao.execute(
        """UPDATE agendamentos
           SET cliente_id = ?, data = ?, horario = ?, servico = ?, status = ?
           WHERE id = ?""",                 # WHERE limita a alteracao a uma linha so
        (dados["cliente_id"], dados["data"], dados["horario"],
         dados["servico"], dados["status"], agendamento_id)
    )

    conexao.commit()
    conexao.close()
    return jsonify({"mensagem": "agendamento atualizado"})


# ATUALIZAR SO O STATUS - PATCH altera um pedaco, diferente do PUT que troca tudo
@app.route("/agendamentos/<int:agendamento_id>/status", methods=["PATCH"])
@login_obrigatorio
def atualizar_status(agendamento_id):
    dados = request.get_json()
    novo_status = dados["status"]

    # regra de negocio: so aceita os quatro status previstos no case
    status_validos = ["agendado", "concluido", "cancelado", "nao_compareceu"]
    if novo_status not in status_validos:
        return jsonify({"erro": "status invalido"}), 400    # 400 = requisicao invalida

    conexao = conectar()
    conexao.execute(
        "UPDATE agendamentos SET status = ? WHERE id = ?",
        (novo_status, agendamento_id)
    )
    conexao.commit()
    conexao.close()

    return jsonify({"mensagem": "status atualizado"})


# REMOVER AGENDAMENTO - apaga pelo id
@app.route("/agendamentos/<int:agendamento_id>", methods=["DELETE"])
@login_obrigatorio
def remover_agendamento(agendamento_id):
    conexao = conectar()
    # a virgula em (agendamento_id,) e obrigatoria: sem ela nao e uma tupla
    conexao.execute("DELETE FROM agendamentos WHERE id = ?", (agendamento_id,))
    conexao.commit()
    conexao.close()
    return jsonify({"mensagem": "agendamento removido"})


if __name__ == "__main__":
    app.run(debug=True)             # liga o servidor; debug recarrega sozinho ao salvar