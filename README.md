# API de sugestões de artigos

Backend Django REST Framework para gerenciar artigos, seções, trechos e sugestões de revisão. Sugestões podem ser aceitas ou rejeitadas; o artigo pode ser montado em HTML e snapshots são gerados em segundo plano com Celery.

## Tecnologias

- Python 3.12 e Django 6.1
- Django REST Framework e drf-spectacular (OpenAPI, Swagger UI e Redoc)
- PostgreSQL 16
- Celery com Redis 7 como broker
- Docker Compose para executar banco, broker, aplicação e worker

## Configuração local

Copie `.env.example` para `.env` para executar com Docker Compose. Não use a chave de exemplo em produção. Se executar Django fora do Compose, ajuste `DATABASE_URL` para apontar para `localhost` e `CELERY_BROKER_URL` para `redis://localhost:6379/0`.

Crie e ative um ambiente virtual e instale as dependências:

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

## Execução com Docker Compose

O Compose inicia banco, Redis, servidor Django e worker:

```bash
docker compose up --build
```

O serviço `web` aplica as migrações ao iniciar. Para criar dados demonstrativos:

```bash
docker compose exec web python manage.py seed
```

## API e documentação

- API: `http://localhost:8000/api/`
- Schema OpenAPI: `http://localhost:8000/api/schema/`
- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`
- Redoc: `http://localhost:8000/api/schema/redoc/`

Rotas principais:

- `POST` e `GET /api/trechos/<trecho_id>/sugestoes/`
- `POST /api/sugestoes/<sugestao_id>/decisao/`
- `GET /api/artigos/<artigo_id>/`
- `POST` e `GET /api/artigos/<artigo_id>/versoes/`

## Testes e verificações

Execute os testes com:

```bash
python manage.py test
```

Verifique configuração e consistência das migrações com:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
```

## Dependências

`requirements.txt` contém as dependências de runtime e desenvolvimento, incluindo versões transitivas fixadas para tornar as instalações mais reproduzíveis. Ao atualizar pacotes, atualize esse arquivo e valide a instalação, os testes e o funcionamento da aplicação.
