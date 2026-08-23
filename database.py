#poderia fazer listas no python mas quando desliga o programa, a lista some. e deve estar funcionando o tempo todo
#logo vou importar o SQLite, que é um banco de dados que cabe em um único arquivo no meu computador

#CREATE TABLE — cria a "planilha"
#INSERT — acrescenta uma linha
#SELECT — busca linhas
#UPDATE — altera uma linha
#DELETE — apaga uma linha


#sqlite3.connect("barbearia.db") — abre o arquivo de aço
#conexao.cursor() — o cursor é o funcionário que mexe nas gavetas.
#cursor.execute("...") — você entrega a ordem para o funcionário. O texto dentro dos parênteses é a ordem escrita em SQL. Nesse caso: "crie uma gaveta chamada clientes com essas divisórias".
#conexao.commit() (o do SQLite) — grava os dados no banco.

import sqlite3

def conectar():
    conexao = sqlite3.connect("barbearia.db")
    conexao.row_factory = sqlite3.Row
    return conexao

def criar_tabelas():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT,
            observacoes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            horario TEXT NOT NULL,
            servico TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'agendado',
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    """)

    conexao.commit()
    conexao.close()
    print("Tabelas criadas com sucesso")

if __name__ == "__main__":
    criar_tabelas()