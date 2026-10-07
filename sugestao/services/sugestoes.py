from django.db import IntegrityError, transaction
from django.utils import timezone

from sugestao.models import Sugestao, Trecho

from .exceptions import Conflito, ErroDeValidacao, NaoEncontrado

ACOES = ("aceitar", "rejeitar")


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

    trecho_id = Sugestao.objects.filter(pk=sugestao_id).values_list("trecho_id", flat=True).first()
    if trecho_id is None:
        raise NaoEncontrado("Sugestão não encontrada.")
    Trecho.objects.select_for_update().get(pk=trecho_id)

    sugestao = Sugestao.objects.select_for_update().get(pk=sugestao_id)
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


@transaction.atomic
def restaurar_original(trecho_id):
    """Desfaz a sugestão aceita do trecho para que o artigo use o texto original."""
    trecho = Trecho.objects.select_for_update().filter(pk=trecho_id).first()
    if trecho is None:
        raise NaoEncontrado("Trecho não encontrado.")

    sugestao = (
        Sugestao.objects.select_for_update()
        .filter(trecho_id=trecho.id, status="aceita")
        .first()
    )
    if sugestao is None:
        raise Conflito("O trecho já está usando o texto original.")

    sugestao.status = "substituida"
    sugestao.decidida_em = timezone.now()
    sugestao.save(update_fields=["status", "decidida_em"])
    return sugestao


def obter_pendente(trecho_id):
    return _obter_por_status(trecho_id, "pendente")


def obter_aceita(trecho_id):
    return _obter_por_status(trecho_id, "aceita")


def listar_historico(trecho_id):
    """Retorna o texto original e todas as sugestões do trecho, da mais nova à mais antiga."""
    trecho = Trecho.objects.filter(pk=trecho_id).first()
    if trecho is None:
        raise NaoEncontrado("Trecho não encontrado.")
    sugestoes = Sugestao.objects.filter(trecho_id=trecho_id).order_by("-criada_em", "-id")
    return {"trecho_id": trecho.id, "texto_original": trecho.texto, "sugestoes": sugestoes}


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
