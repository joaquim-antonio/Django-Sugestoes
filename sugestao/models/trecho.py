from django.db import models

from .secao import Secao


class Trecho(models.Model):
    secao = models.ForeignKey(Secao, on_delete=models.CASCADE, related_name="trechos")
    posicao = models.PositiveIntegerField()
    texto = models.TextField()

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=["secao", "posicao"], name="uma_posicao_por_secao"
            ),
        )

    def __str__(self):
        return f"Trecho {self.posicao} da seção {self.secao.nome}"
