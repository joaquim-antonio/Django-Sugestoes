# Decisões de design

Este documento registra as decições tomadas a partir das presuposições adotadas na hora de desenvolver este teste técnico

## Principais presuposições
 - A lógica de processar o artigo, dividí-lo em seções e trechos não é responsabilidade do app desenvolvido neste teste. Os dados foram mockados com um seeder para representar alguns artigos processados em um momento anterior
 - As sugestões não são geradas por este app, visto que a comunicação com a API da LLM externa e o armazenamento de sugestões devem ser responsabilidade de outro môdulo. Essa "geração" de sugestões é simulada pela rota de criar uma nova sugestão, que atrela um sugestão a algum trecho

### O que este môdulo faz?
O môdulo implementado tem a responsabilidade exclusiva de lidar com a decisão em relação a uma sugestão. Ele rastreia as sugestões que pertencem a um trecho e, dependendo do que o usuario decide, o status da sugestão muda. Uma sugestão pode ser "PENDENTE", "ACEITA", "REJEITADA" e "SUBSTITUIDA". Só pode haver uma pendente e aceita por trecho. As sugestões com o status "ACEITA" são tratadas como o texto verdadeiros, o texto do trecho original é ignorado enquanto houver sugestões aceitas

### O texto original é preservado
O texto de referência de cada trecho fica em `Trecho.texto`. Aceitar sugestões não sobrescreve esse campo. Assim, o sistema preserva a origem e pode voltar a usá-la futuramente caso o usuario queira voltar na árvore de sugestões para o texto original.Atualmente, `POST /api/trechos/<trecho_id>/restaurar-original/` marca a sugestão aceita como `substituida`. Sem sugestão aceita, o compilador volta automaticamente a usar o texto original do trecho. A operação não cria uma nova sugestão.

### Uma sugestão aceita define o texto vigente
O artigo usa o texto da sugestão com status `aceita`, quando existe. Sem uma sugestão aceita, usa `Trecho.texto`. Sugestões pendentes, rejeitadas ou substituídas ficam no histórico, mas não alteram o artigo gerado.

O banco permite no máximo uma sugestão `aceita` e uma `pendente` por trecho. Essa regra também permite que um trecho tenha uma sugestão aceita e uma pendente ao mesmo tempo.

### O histórico do trecho mostra todas as sugestões
`GET /api/trechos/<trecho_id>/sugestoes/` retorna o texto original e todas as sugestões associadas ao trecho, sem filtro por status. As sugestões vêm da mais recente para a mais antiga; o ID desempata datas de criação iguais. O parâmetro `status`, se enviado, não altera a lista.

### Versões de artigo
`GET /api/artigos/<artigo_id>/` monta o HTML com o estado atual dos dados. Ele não lê nem grava versões.

`POST /api/artigos/<artigo_id>/versoes/` agenda uma task Celery. O worker monta o HTML quando executa a task e grava uma cópia em `VersaoArtigo`. Portanto, o versão representa o estado encontrado na execução do worker, que pode ser posterior ao momento do POST.

Se o HTML recém-compilado for idêntico ao versão mais recente, a task não cria outro registro. A comparação é com a última versão, não com todas as versões antigas. Os versãos são cópias históricas; não restauram nem alteram o estado vigente do artigo.

### Integridade e concorrência
As regras estruturais também são impostas pelo banco:

- Seções têm posições únicas dentro de um artigo.
- Trechos têm posições únicas dentro de uma seção.
- Um trecho tem no máximo uma sugestão aceita e uma pendente.
- Sugestões pendentes não têm `decidida_em`; sugestões decididas têm essa data.
- O status da sugestão deve pertencer ao conjunto conhecido pelo domínio.

As operações de aceitar/rejeitar e restaurar bloqueiam a linha do trecho dentro de uma transação. Esse trecho funciona como ponto comum de sincronização: aceitar uma sugestão e restaurar o original não devem alterar ao mesmo tempo o estado vigente do mesmo trecho. A linha da sugestão também é bloqueada antes de ser atualizada.

Erros de domínio são convertidos pela API em respostas HTTP: recurso ausente em `404`, conflito de estado em `409` e entrada inválida em `400`.
