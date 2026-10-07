from django.db import models
from django.db.models import Q

from .trecho import Trecho


class Sugestao(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        ACEITA = 'aceita', 'Aceita'
        REJEITADA = 'rejeitada', 'Rejeitada'
        SUBSTITUIDA = 'substituida', 'Substituída'

    trecho = models.ForeignKey(
        Trecho, 
        on_delete=models.CASCADE, 
        related_name='sugestoes'
    )
    texto = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDENTE
    )
    criada_em = models.DateTimeField(auto_now_add=True)
    decidida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=['trecho'],
                condition=Q(status='aceita'),
                name='uma_aceita_por_trecho'
            ),
            models.UniqueConstraint(
                fields=['trecho'],
                condition=Q(status='pendente'),
                name='uma_pendente_por_trecho'
            ),
            models.CheckConstraint(
                condition=Q(status__in=['pendente', 'aceita', 'rejeitada', 'substituida']),
                name='status_valido'
            ),
            models.CheckConstraint(
                condition=Q(status='pendente', decidida_em__isnull=True) | 
                          Q(status__in=['aceita', 'rejeitada', 'substituida'], decidida_em__isnull=False),
                name='decisao_tem_data'
            ),
        )
    
    def __str__(self):
        return f"Sugestão #{self.id} ({self.status}) - Trecho {self.trecho_id}"