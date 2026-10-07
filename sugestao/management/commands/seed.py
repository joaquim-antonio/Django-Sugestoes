from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from sugestao.models import Artigo, Secao, Sugestao, Trecho


class Command(BaseCommand):
    help = "Apaga todos os artigos existentes e recria os dados de demonstração."

    @transaction.atomic
    def handle(self, *args, **options):
        Artigo.objects.all().delete()
        artigo = Artigo.objects.create(titulo="Revisão assistida de artigos científicos")

        # Seção 1: trecho sem sugestão, com pendente e com aceita.
        # O texto do primeiro trecho tem "&" e "<" para exercitar o escape do HTML.
        introducao = Secao.objects.create(artigo=artigo, nome="Introdução", posicao=1)
        self._trecho(introducao, 1, "Os modelos A & B foram comparados com significância p < 0,05.")
        t = self._trecho(introducao, 2, "Este trabalho investiga métodos de revisão assistida por inteligência artificial.")
        self._sugestao(t, "Este trabalho investiga métodos de revisão de textos assistida por inteligência artificial.", "pendente")
        t = self._trecho(introducao, 3, "Estudos anteriores mostram resultados promissores, mas inconsistentes.")
        self._sugestao(t, "Estudos anteriores apresentam resultados promissores, porém inconsistentes.", "aceita")

        # Seção 2: rejeitada, aceita com pendente, e histórico com substituída.
        metodos = Secao.objects.create(artigo=artigo, nome="Métodos", posicao=2)
        t = self._trecho(metodos, 1, "Os dados foram coletados em tres etapas.")
        self._sugestao(t, "Os dados foram coletados em três etapas.", "rejeitada")
        t = self._trecho(metodos, 2, "A amostra incluiu 120 artigos de diferentes áreas.")
        self._sugestao(t, "A amostra incluiu 120 artigos de diversas áreas do conhecimento.", "aceita")
        self._sugestao(t, "A amostra foi composta por 120 artigos de áreas distintas.", "pendente")
        t = self._trecho(metodos, 3, "Cada artigo foi dividido em trechos de ate cinco parágrafos.")
        self._sugestao(t, "Cada artigo foi dividido em trechos de até cinco parágrafos.", "substituida", dias_atras=2)
        self._sugestao(t, "Cada artigo foi segmentado em trechos de, no máximo, cinco parágrafos.", "aceita", dias_atras=1)

        # Seção 3: todos os trechos apagados (aceita com texto vazio).
        resultados = Secao.objects.create(artigo=artigo, nome="Resultados", posicao=3)
        for posicao, texto in enumerate(["Esta frase será removida do artigo final.", "Esta também será removida."], start=1):
            t = self._trecho(resultados, posicao, texto)
            self._sugestao(t, "", "aceita")

        self.stdout.write(self.style.SUCCESS(f"Seed concluído. Artigo criado com id={artigo.id}."))

    def _trecho(self, secao, posicao, texto):
        return Trecho.objects.create(secao=secao, posicao=posicao, texto=texto)

    def _sugestao(self, trecho, texto, status, dias_atras=0):
        decidida_em = None
        if status != "pendente":
            decidida_em = timezone.now() - timedelta(days=dias_atras)
        return Sugestao.objects.create(trecho=trecho, texto=texto, status=status, decidida_em=decidida_em)