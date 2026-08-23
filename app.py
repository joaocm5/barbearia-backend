from flask import Flask

app = Flask(__name__) #cria o aplicativo

@app.route("/") #devo copiar no link fornecido no terminal o que esta depois do /
def ola():
    return "Barbearia Vintage no ar" #é o que aparece na tela do navegador

if __name__ == "__main__":
    app.run(debug=True)   # Liga o servidor quando eu rodo o arquivo. O debug=True faz duas coisas úteis: reinicia o servidor sozinho toda vez que eu salvo o arquivo