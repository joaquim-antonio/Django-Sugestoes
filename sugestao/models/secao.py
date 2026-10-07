from django.db import models

from .artigo import Artigo


class Secao(models.Model):
    artigo = models.ForeignKey(
        Artigo, 
        on_delete=models.CASCADE, 
        related_name='secoes'
    )
    nome = models.CharField(max_length=255)
    posicao = models.PositiveIntegerField()

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=['artigo', 'posicao'], 
                name='uma_posicao_por_artigo',
            ),
        )

    def __str__(self):
        return f"{self.artigo.titulo} - {self.nome}"

