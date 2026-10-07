from celery import shared_task
from django.db import DatabaseError, OperationalError, transaction

from sugestao.models import VersaoArtigo
from sugestao.services import NaoEncontrado, montar_artigo_html


@shared_task(
    bind=True,  
    max_retries=3,
    default_retry_delay=5,
)
def gerar_versao(self, artigo_id: int) -> dict:
    """
    Task assíncrona para compilar o HTML do artigo e salvar uma nova VersaoArtigo.
    Garante idempotência: se o conteúdo HTML for idêntico à última versão gravada,
    nenhum registro duplicado é criado.
    """
    try:
        # 1. Compila o HTML atual utilizando o serviço
        conteudo_html = montar_artigo_html(artigo_id)

        with transaction.atomic():
            # 2. Busca o último snapshot de versão deste artigo
            ultima_versao = (
                VersaoArtigo.objects.filter(artigo_id=artigo_id)
                .order_by("-criada_em")
                .first()
            )

            # 3. Check de Idempotência: se o HTML for idêntico ao último, ignora
            if ultima_versao and ultima_versao.conteudo == conteudo_html:
                return {
                    "status": "ignorado",
                    "motivo": "conteudo_identico",
                    "versao_id": ultima_versao.id,
                }

            # 4. Salva o novo snapshot no banco
            nova_versao = VersaoArtigo.objects.create(
                artigo_id=artigo_id,
                conteudo=conteudo_html,
            )

            return {
                "status": "criado",
                "versao_id": nova_versao.id,
            }

    except NaoEncontrado as exc:
        # Se o artigo não existir, encerra a execução sem tentar novamente (retry)
        return {"status": "erro", "motivo": str(exc)}
    except (OperationalError, DatabaseError) as exc:
        # Erros transitórios de infra/banco acionam retry automático
        raise self.retry(exc=exc)   