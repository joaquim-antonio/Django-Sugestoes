from django.db import IntegrityError, transaction
from django.utils import timezone

from sugestao.models import Sugestao, Trecho

from .exceptions import Conflito, ErroDeValidacao, NaoEncontrado

ACOES = ("aceitar", "rejeitar")
STATUS_DO_HISTORICO = ("substituida", "rejeitada")


def criar_sugestao(trecho_id, texto):
    """Cadastra uma sugestão pendente para o trecho (simula a resposta da LLM)."""
    texto = _normalizar_texto(texto)
    if not Trecho.objects.filter(pk=trecho_id).exists():
        raise NaoEncontrado("Trecho não encontrado.")
    try:
        with transaction.atomic():
            return Sugestao.objects.create(trecho_id=trecho_id, texto=texto)
    except IntegrityError as erro:
        if "uma_pendente_por_trecho" in str(erro):
            raise Conflito("O trecho já tem uma sugestão pendente.") from erro
        raise


@transaction.atomic
def decidir(sugestao_id, acao):
    """Aceita ou rejeita uma sugestão pendente com proteção contra concorrência."""
    if acao not in ACOES:
        raise ErroDeValidacao(f"Ação inválida. Use uma de: {', '.join(ACOES)}.")

    sugestao = Sugestao.objects.select_for_update().filter(pk=sugestao_id).first()
    if sugestao is None:
        raise NaoEncontrado("Sugestão não encontrada.")
    if sugestao.status != "pendente":
        raise Conflito(f"A sugestão já foi decidida (status: {sugestao.status}).")

    if acao == "aceitar":
        Sugestao.objects.filter(trecho_id=sugestao.trecho_id, status="aceita").update(
            status="substituida"
        )
        sugestao.status = "aceita"
    else:
        sugestao.status = "rejeitada"
    sugestao.decidida_em = timezone.now()
    sugestao.save(update_fields=["status", "decidida_em"])
    return sugestao


def obter_pendente(trecho_id):
    return _obter_por_status(trecho_id, "pendente")


def obter_aceita(trecho_id):
    return _obter_por_status(trecho_id, "aceita")


def listar_historico(trecho_id, status=None):
    """Lista sugestões substituídas/rejeitadas da mais recente para a mais antiga."""
    if status is not None and status not in STATUS_DO_HISTORICO:
        raise ErroDeValidacao(f"Status inválido. Use um de: {', '.join(STATUS_DO_HISTORICO)}.")
    if not Trecho.objects.filter(pk=trecho_id).exists():
        raise NaoEncontrado("Trecho não encontrado.")
    filtro = [status] if status else STATUS_DO_HISTORICO
    return list(
        Sugestao.objects.filter(trecho_id=trecho_id, status__in=filtro).order_by(
            "-decidida_em", "-id"
        )
    )


def _normalizar_texto(texto):
    """Texto vazio é permitido; texto contendo apenas espaços vira string vazia."""
    if not isinstance(texto, str):
        raise ErroDeValidacao("O texto é obrigatório (pode ser uma string vazia).")
    return texto if texto.strip() else ""


def _obter_por_status(trecho_id, status):
    sugestao = Sugestao.objects.filter(trecho_id=trecho_id, status=status).first()
    if sugestao is not None:
        return sugestao
    if not Trecho.objects.filter(pk=trecho_id).exists():
        raise NaoEncontrado("Trecho não encontrado.")
    raise NaoEncontrado(f"O trecho não tem sugestão {status}.")
