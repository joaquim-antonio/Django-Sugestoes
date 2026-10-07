from html import escape

from django.db.models import F, OuterRef, Subquery, TextField
from django.db.models.functions import Coalesce

from sugestao.models import Artigo, Sugestao

from .exceptions import NaoEncontrado


def montar_artigo_html(artigo_id):
    """Devolve o HTML do artigo com o texto vigente de cada trecho.

    O texto vigente é o da sugestão aceita, se houver, senão o original. Tudo
    vem de UMA consulta: uma instrução enxerga um estado só do banco, então uma
    decisão simultânea nunca produz um artigo misturado, e não há N+1.
    Trecho apagado (aceita com texto vazio) é omitido; a seção mantém o título.
    """
    aceita = Sugestao.objects.filter(
        trecho_id=OuterRef("secoes__trechos__id"), status="aceita"
    ).values("texto")[:1]
    linhas = list(
        Artigo.objects.filter(pk=artigo_id)
        .annotate(
            texto_vigente=Coalesce(
                Subquery(aceita, output_field=TextField()), F("secoes__trechos__texto")
            )
        )
        .order_by("secoes__posicao", "secoes__trechos__posicao")
        .values_list(
            "titulo",
            "secoes__id",
            "secoes__nome",
            "secoes__trechos__id",
            "texto_vigente",
        )
    )
    if not linhas:
        raise NaoEncontrado("Artigo não encontrado.")

    partes = [f"<h1>{escape(linhas[0][0])}</h1>"]
    secao_atual = None
    for _, secao_id, secao_nome, trecho_id, texto in linhas:
        if secao_id is None:  # artigo sem seções
            continue
        if secao_id != secao_atual:
            partes.append(f"<h2>{escape(secao_nome)}</h2>")
            secao_atual = secao_id
        if (
            trecho_id is None or not texto.strip()
        ):  # seção sem trechos ou trecho apagado
            continue
        partes.append(f"<p>{escape(texto)}</p>")
    return "".join(partes)
