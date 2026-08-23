# importa o Flask e as ferramentas para ler dados e devolver JSON
from flask import Flask, request, jsonify

# importa a função de conexão que criamos no database.py
from database import conectar

# cria o aplicativo
app = Flask(__name__)


# rota inicial, só para conferir se o servidor está de pé
@app.route("/")
def ola():
    return "Barbearia Vintage no ar"


# LISTAR CLIENTES - devolve todos os clientes cadastrados
@app.route("/clientes", methods=["GET"])
def listar_clientes():
    conexao = conectar()                                            # abre o banco
    linhas = conexao.execute("SELECT * FROM clientes").fetchall()   # busca todas as linhas
    conexao.close()                                                 # fecha o banco
    return jsonify([dict(linha) for linha in linhas])               # converte para JSON e devolve


# CADASTRAR CLIENTE - recebe os dados e grava um cliente novo
@app.route("/clientes", methods=["POST"])
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
def remover_cliente(cliente_id):
    conexao = conectar()
    conexao.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    conexao.commit()
    conexao.close()
    return jsonify({"mensagem": "cliente removido"})


# LISTAR AGENDAMENTOS - a agenda organizada por data e horario
@app.route("/agendamentos", methods=["GET"])
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
@app.route("/agendamentos", methods=["POST"])
def criar_agendamento():
    dados = request.get_json()          # le o JSON enviado pelo frontend
    conexao = conectar()

    cursor = conexao.execute(
        "INSERT INTO agendamentos (cliente_id, data, horario, servico, status) VALUES (?, ?, ?, ?, ?)",
        # se o status nao vier, assume "agendado" como padrao
        (dados["cliente_id"], dados["data"], dados["horario"],
         dados["servico"], dados.get("status", "agendado"))
    )

    conexao.commit()                    # grava de verdade no banco
    novo_id = cursor.lastrowid          # id gerado pelo banco
    conexao.close()

    return jsonify({"id": novo_id, "mensagem": "agendamento criado"}), 201


# EDITAR AGENDAMENTO - altera todos os campos de um agendamento existente
@app.route("/agendamentos/<int:agendamento_id>", methods=["PUT"])
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
def remover_agendamento(agendamento_id):
    conexao = conectar()
    # a virgula em (agendamento_id,) e obrigatoria: sem ela nao e uma tupla
    conexao.execute("DELETE FROM agendamentos WHERE id = ?", (agendamento_id,))
    conexao.commit()
    conexao.close()
    return jsonify({"mensagem": "agendamento removido"})


if __name__ == "__main__":
    app.run(debug=True)             # liga o servidor; debug recarrega sozinho ao salvar