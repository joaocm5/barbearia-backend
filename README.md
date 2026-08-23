# Barbearia Vintage — Backend

API REST que gerencia clientes e agendamentos da Barbearia Vintage. Inclui
autenticação por sessão e integração com uma automação no n8n que envia
e-mail de confirmação ao cliente a cada novo agendamento.

Case da 2ª fase do processo seletivo da Insper Jr.

---

## Stack e decisões

| Camada | Escolha | Por quê |
|---|---|---|
| Backend | Flask | Framework mínimo: uma rota é uma função com um decorador. Sem camadas que eu não conseguisse explicar. |
| Banco | SQLite com SQL puro | Já vem no Python, guarda tudo em um arquivo e não exige instalação. Para uma barbearia de bairro, é dimensionamento adequado. |
| Autenticação | Sessão do Flask + hash de senha | Poucas linhas, cookie assinado, senha nunca armazenada em texto. |
| Automação | n8n (Webhook → Code → Send Email) | Tira do backend a responsabilidade de enviar e-mail. |

Optei conscientemente por SQL escrito à mão em vez de um ORM: o sistema tem
duas tabelas e cinco tipos de consulta, e o SQL direto deixa explícito o que
acontece no banco.

---

## Como rodar

```bash
pip install flask flask-cors requests

python database.py     # cria as tabelas e o usuário inicial
python app.py          # sobe a API em http://127.0.0.1:5000
```

Usuário criado por padrão:

```
admin@barbearia.com / 123456
```

O frontend está em outro repositório: [barbearia-frontend](https://github.com/joaocm5/barbearia-frontend)

---

## Estrutura

```
app.py            rotas da API e regras de negócio
database.py       conexão, criação das tabelas e usuário inicial
n8n/              workflow da automação, exportado em JSON
barbearia.db      banco (gerado ao rodar database.py, fora do versionamento)
```

---

## Modelo de dados

**usuarios** — `id`, `email`, `senha_hash`
**clientes** — `id`, `nome`, `email`, `observacoes`
**agendamentos** — `id`, `cliente_id`, `data`, `horario`, `servico`, `status`

O agendamento guarda o `cliente_id`, não o nome. Assim, corrigir o cadastro de
um cliente mantém todo o histórico dele correto.

Datas são gravadas como `AAAA-MM-DD` e horários como `HH:MM`. Nesse formato a
ordenação alfabética coincide com a cronológica, o que faz o `ORDER BY`
funcionar sem conversão. A exibição em formato brasileiro acontece na
interface e no e-mail.

---

## Rotas

Todas exigem sessão ativa, exceto `/login`.

| Método | Rota | Ação |
|---|---|---|
| POST | `/login` | Autentica e abre a sessão |
| POST | `/logout` | Encerra a sessão |
| GET | `/eu` | Informa se a sessão ainda é válida |
| GET | `/clientes` | Lista os clientes |
| POST | `/clientes` | Cadastra um cliente |
| PUT | `/clientes/<id>` | Edita um cliente |
| DELETE | `/clientes/<id>` | Remove um cliente |
| GET | `/agendamentos` | Lista a agenda, ordenada por data e horário |
| POST | `/agendamentos` | Cria um agendamento e aciona o n8n |
| PUT | `/agendamentos/<id>` | Edita um agendamento |
| PATCH | `/agendamentos/<id>/status` | Altera apenas o status |
| DELETE | `/agendamentos/<id>` | Remove um agendamento |

A listagem da agenda faz `JOIN` com clientes, devolvendo nome e e-mail já
resolvidos — a interface não precisa de uma segunda consulta para exibir a
tabela.

---

## Automação (n8n)

Ao criar um agendamento, o backend consulta o registro recém-gravado já com os
dados do cliente e envia esse pacote ao webhook do n8n. O fluxo tem três nós:

1. **Webhook** — recebe o POST
2. **Code** — formata a data para o padrão brasileiro e monta assunto e corpo
3. **Send Email** — envia via SMTP ao cliente

A chamada ao n8n está dentro de um `try/except` de propósito: o agendamento já
foi gravado quando ela acontece. Se a automação estiver fora do ar, o
compromisso continua salvo e o funcionário recebe confirmação normalmente — a
falha é registrada no log, não repassada como erro ao usuário.

Para rodar a automação:

```bash
npx n8n     # sobe o editor em http://localhost:5678
```

Importe o arquivo de `n8n/`, configure a credencial SMTP e publique o workflow.

---

## Segurança

- Senhas armazenadas apenas como hash (`werkzeug.security`)
- Consultas parametrizadas com `?`, prevenindo SQL injection
- Rotas protegidas por um decorador único, evitando esquecer a verificação
- CORS restrito à origem do frontend, não liberado com `*`
- Mensagem de erro genérica no login, sem revelar se o e-mail existe

---

## Limitações conhecidas

Decisões de escopo tomadas em função do prazo de 48 horas:

- `secret_key` e credenciais estão no código; em produção viriam de variáveis de ambiente
- Não há validação de conflito de horário — dois agendamentos podem ocupar o mesmo horário
- Não há paginação na listagem da agenda
- Cadastro de novos funcionários é feito diretamente no banco, sem tela própria