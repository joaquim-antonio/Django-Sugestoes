class NaoEncontrado(Exception):
    """O recurso pedido não existe (a view responde 404)."""


class Conflito(Exception):
    """O estado atual não permite a operação (a view responde 409)."""


class ErroDeValidacao(Exception):
    """A entrada é inválida (a view responde 400)."""
