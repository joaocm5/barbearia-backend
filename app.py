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

if __name__ == "__main__":
    app.run(debug=True)             # liga o servidor; debug recarrega sozinho ao salvar