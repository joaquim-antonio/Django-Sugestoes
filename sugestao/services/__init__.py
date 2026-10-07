"""Serviços de domínio para sugestões e artigos.

Os reexports preservam os imports públicos anteriores de ``sugestao.services``.
"""

from .artigos import montar_artigo_html
from .exceptions import Conflito, ErroDeValidacao, NaoEncontrado
from .sugestoes import (
    ACOES,
    criar_sugestao,
    decidir,
    listar_historico,
    obter_aceita,
    obter_pendente,
    restaurar_original,
)

__all__ = [
    "ACOES",
    "Conflito",
    "ErroDeValidacao",
    "NaoEncontrado",
    "criar_sugestao",
    "decidir",
    "listar_historico",
    "montar_artigo_html",
    "obter_aceita",
    "obter_pendente",
    "restaurar_original",
]
