from django.urls import path

from sugestao.api.views import (
    CriarListarSugestaoView,
    CriarListarVersaoArtigoView,
    DecidirSugestaoView,
    ObterArtigoMontadoView,
    RestaurarOriginalTrechoView,
)

urlpatterns = [
    # Rotas de Sugestões
    path(
        "trechos/<int:trecho_id>/sugestoes/",
        CriarListarSugestaoView.as_view(),
        name="trecho-sugestoes",
    ),
    path(
        "sugestoes/<int:sugestao_id>/decisao/",
        DecidirSugestaoView.as_view(),
        name="sugestao-decisao",
    ),
    path(
        "trechos/<int:trecho_id>/restaurar-original/",
        RestaurarOriginalTrechoView.as_view(),
        name="trecho-restaurar-original",
    ),
    # Rotas de Artigos e Versões
    path(
        "artigos/<int:artigo_id>/",
        ObterArtigoMontadoView.as_view(),
        name="artigo-montado",
    ),
    path(
        "artigos/<int:artigo_id>/versoes/",
        CriarListarVersaoArtigoView.as_view(),
        name="artigo-versoes",
    ),
]
