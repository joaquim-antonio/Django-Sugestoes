# API de sugestões de artigos

Backend Django REST Framework para gerenciar artigos, seções, trechos e sugestões de revisão. Sugestões podem ser aceitas ou rejeitadas; o artigo pode ser montado em HTML e snapshots são gerados em segundo plano com Celery. As decisões estão registradas em [Decisões.md](./docs/Decisoes.md)

## Configuração local

Copie `.env.example` para `.env` para executar com Docker Compose. Não use a chave de exemplo em produção. Se executar Django fora do Compose, ajuste `DATABASE_URL` para apontar para `localhost` e `CELERY_BROKER_URL` para `redis://localhost:6379/0`.

### Execução sem Docker Compose

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Inicie PostgreSQL e Redis:

```bash
docker compose up -d db redis
```

Aplique as migrações e carregue dados demonstrativos:

```bash
python manage.py migrate
python manage.py seed
```

Execute o servidor e, em outro terminal, o worker Celery:

```bash
python manage.py runserver
celery -A config worker --loglevel=info
```

### Execução com Docker Compose

O Compose inicia banco, Redis, servidor Django e worker:

```bash
docker compose up --build
```

O serviço `web` aplica as migrações ao iniciar. Para criar dados demonstrativos:

```bash
docker compose exec web python manage.py seed
```

### Testar a API pelo Swagger
Com a aplicação em execução via Docker Compose ou `runserver`, abra o [Swagger UI](http://localhost:8000/api/schema/swagger-ui/). Expanda uma rota, clique em **Try it out**, informe os parâmetros ou o corpo JSON e clique em **Execute** para enviar a requisição e ver a resposta.

### Testes e verificações
Execute os testes e gere o relatório de cobertura do código da aplicação (excluindo testes e migrações):

```bash
coverage run --source=sugestao --omit='*/tests/*,*/migrations/*' manage.py test
coverage report
```

A última medição local registrou **88% de cobertura de linhas** no código da aplicação. Essa execução usou SQLite temporário porque o PostgreSQL não estava disponível e a suíte não passou nesse backend (19 falhas e 3 erros em 71 testes); portanto, considere o percentual provisório e rode a medição com PostgreSQL para obter um resultado validado.

Verifique configuração e consistência das migrações com:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
```
