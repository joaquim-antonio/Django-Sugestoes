# Decisões de design

Este documento registra as decisões de produto discutidas para a API de sugestões e explica como elas aparecem na implementação. A seção final destaca comportamentos que existem no código, mas que ainda podem ser decisões a confirmar.

## Decisões confirmadas

### O texto original é preservado

O texto de referência de cada trecho fica em `Trecho.texto`. Aceitar sugestões não sobrescreve esse campo. Assim, o sistema preserva a origem e pode voltar a usá-la sem criar uma sugestão artificial.

### Uma sugestão aceita define o texto vigente

O artigo usa o texto da sugestão com status `aceita`, quando existe. Sem uma sugestão aceita, usa `Trecho.texto`. Sugestões pendentes, rejeitadas ou substituídas ficam no histórico, mas não alteram o artigo compilado.

O banco permite no máximo uma sugestão `aceita` e uma `pendente` por trecho. Essa regra também permite que um trecho tenha uma sugestão aceita e uma pendente ao mesmo tempo.

### Restaurar o original é uma operação explícita

`POST /api/trechos/<trecho_id>/restaurar-original/` marca a sugestão atualmente aceita como `substituida`. Sem sugestão aceita, o compilador volta automaticamente a usar o texto original do trecho. A operação não cria uma nova sugestão.

Se o trecho não existe, a API retorna `404`. Se já não há sugestão aceita, retorna `409`, pois o texto original já está vigente. Em caso de sucesso, retorna a sugestão alterada.

### O histórico do trecho mostra todas as sugestões

`GET /api/trechos/<trecho_id>/sugestoes/` retorna o texto original e todas as sugestões associadas ao trecho, sem filtro por status. As sugestões vêm da mais recente para a mais antiga; o ID desempata datas de criação iguais. O parâmetro `status`, se enviado, não altera a lista.

Exemplo de resposta:

```json
{
  "trecho_id": 42,
  "texto_original": "Texto original do trecho.",
  "sugestoes": [
    {
      "id": 9,
      "trecho_id": 42,
      "texto": "Texto proposto.",
      "status": "aceita",
      "criada_em": "2026-10-07T12:00:00Z",
      "decidida_em": "2026-10-07T12:05:00Z"
    }
  ]
}
```

### O HTML não inclui quebras de linha artificiais

O compilador concatena as tags com `"".join(partes)`. Não insere `\n` entre os elementos HTML. Título, seção e conteúdo do trecho são escapados antes de entrar no HTML.

Uma sugestão aceita com texto vazio representa a remoção do trecho: o parágrafo é omitido. A seção e seu título continuam no artigo.

### A decisão identifica a sugestão

`POST /api/sugestoes/<sugestao_id>/decisao/` recebe o ID da sugestão e a ação `aceitar` ou `rejeitar`. Assim, a operação decide a sugestão específica indicada pelo cliente. Uma sugestão que já não está pendente gera conflito (`409`).

## Snapshots de artigo

`GET /api/artigos/<artigo_id>/` monta o HTML com o estado atual dos dados. Ele não lê nem grava snapshots.

`POST /api/artigos/<artigo_id>/versoes/` agenda uma task Celery. O worker monta o HTML quando executa a task e grava uma cópia em `VersaoArtigo`. Portanto, o snapshot representa o estado encontrado na execução do worker, que pode ser posterior ao momento do POST.

Se o HTML recém-compilado for idêntico ao snapshot mais recente, a task não cria outro registro. A comparação é com a última versão, não com todas as versões antigas. Os snapshots são cópias históricas; não restauram nem alteram o estado vigente do artigo.

## Integridade e concorrência

As regras estruturais também são impostas pelo banco:

- Seções têm posições únicas dentro de um artigo.
- Trechos têm posições únicas dentro de uma seção.
- Um trecho tem no máximo uma sugestão aceita e uma pendente.
- Sugestões pendentes não têm `decidida_em`; sugestões decididas têm essa data.
- O status da sugestão deve pertencer ao conjunto conhecido pelo domínio.

As operações de aceitar/rejeitar e restaurar bloqueiam a linha do trecho dentro de uma transação. Esse trecho funciona como ponto comum de sincronização: aceitar uma sugestão e restaurar o original não devem alterar ao mesmo tempo o estado vigente do mesmo trecho. A linha da sugestão também é bloqueada antes de ser atualizada.

Erros de domínio são convertidos pela API em respostas HTTP: recurso ausente em `404`, conflito de estado em `409` e entrada inválida em `400`.

## Dados de demonstração e persistência local

O PostgreSQL do Docker Compose usa o volume nomeado `pgdata`, então reiniciar ou recriar o container do banco não apaga os dados por si só. Remover o volume, por exemplo com `docker compose down -v`, apaga esses dados.

O comando `python manage.py seed` limpa os registros existentes dos modelos do domínio antes de recriar os dados demonstrativos. Deve ser tratado como destrutivo e usado apenas quando essa substituição for desejada.

## Comportamentos a confirmar

Estes pontos são consequências do código atual; não foram definidos explicitamente como requisitos de produto:

- A data `decidida_em` da sugestão aceita é atualizada ao restaurar o original. Quando uma nova sugestão é aceita, a sugestão aceita anterior passa a `substituida`, mas sua data de decisão anterior é preservada. Convém decidir se `decidida_em` representa a decisão original ou a última mudança de estado.
- A restauração e a substituição por outra sugestão usam o mesmo status `substituida`. O histórico não distingue por que a sugestão deixou de estar vigente. Se essa distinção for necessária, será preciso registrar um motivo ou evento separado.
- Os endpoints de decisão e restauração não implementam autenticação ou autorização específica no código atual. Se houver múltiplos perfis de usuário, as permissões ainda precisam ser definidas.
- A rota de decisão usa `sugestao_id`, enquanto a restauração usa `trecho_id`: a primeira atua sobre uma proposta específica; a segunda atua sobre o estado vigente do trecho.
