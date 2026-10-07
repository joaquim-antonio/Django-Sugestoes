from django.db import models

from .artigo import Artigo


class VersaoArtigo(models.Model):
    artigo = models.ForeignKey(
        Artigo, 
        on_delete=models.CASCADE, 
        related_name='versoes'
    )
    conteudo = models.TextField()
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = (
            models.Index(fields=['artigo', '-criada_em'], name='idx_artigo_versoes_recentes'),
        )

    def __str__(self):
        return f"Versão de {self.artigo.titulo} em {self.criada_em:%d/%m/%Y %H:%M}"
        