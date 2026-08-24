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
import os
from dotenv import load_dotenv

load_dotenv()
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

    #id INTEGER PRIMARY KEY AUTOINCREMENT — toda linha ganha um número único, gerado sozinho. É como cada registro é identificado. Cliente 1, cliente 2, e assim por diante.
    #cliente_id + FOREIGN KEY — essa é a parte mais importante. O agendamento não guarda o nome do cliente; guarda o número dele.

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT,
            observacoes TEXT
        )
    """)

    #NOT NULL — campo obrigatório. Não dá para gravar um agendamento sem data.
    #DEFAULT 'agendado' — todo agendamento novo já nasce com esse status, sem você precisar informar. Depois o Marcelo muda para concluído, cancelado ou não compareceu.
    #IF NOT EXISTS — pode rodar esse arquivo dez vezes que ele não apaga nada nem dá erro.

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

# ferramenta do Flask que transforma a senha em hash
from werkzeug.security import generate_password_hash


# CRIA O USUARIO INICIAL - o funcionario que vai acessar o sistema
def criar_usuario_inicial():
    # email e senha do funcionario inicial vem do .env
    email = os.getenv("ADMIN_EMAIL")
    senha = os.getenv("ADMIN_SENHA")
    conexao = conectar()


    # verifica se ja existe, para nao duplicar ao rodar de novo
    existente = conexao.execute(
        "SELECT id FROM usuarios WHERE email = ?", (email,)
    ).fetchone()

    if existente is None:
        conexao.execute(
            "INSERT INTO usuarios (email, senha_hash) VALUES (?, ?)",
            # NUNCA guardamos a senha em texto puro, so o hash dela
            (email, generate_password_hash(senha))
        )
        conexao.commit()
        print(f"Usuario criado: {email} / senha: {senha}")
    else:
        print("Usuario ja existe")

    conexao.close()


if __name__ == "__main__":
    criar_tabelas()
    criar_usuario_inicial()
