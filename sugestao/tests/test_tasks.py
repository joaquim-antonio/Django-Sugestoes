from django.test import TestCase

from sugestao.models import Artigo, Secao, Trecho, VersaoArtigo
from sugestao.services import criar_sugestao, decidir
from sugestao.tasks import gerar_versao


class GerarVersaoTaskTestCase(TestCase):

    def setUp(self):
        self.artigo = Artigo.objects.create(titulo="Artigo Celery")
        self.secao = Secao.objects.create(artigo=self.artigo, nome="Seção 1", posicao=1)
        self.trecho = Trecho.objects.create(secao=self.secao, posicao=1, texto="Texto base")

    def test_gerar_versao_com_sucesso(self):
        resultado = gerar_versao.apply(args=[self.artigo.id]).get()

        self.assertEqual(resultado["status"], "criado")
        self.assertEqual(VersaoArtigo.objects.filter(artigo=self.artigo).count(), 1)

        versao = VersaoArtigo.objects.get(id=resultado["versao_id"])
        self.assertIn("<h1>Artigo Celery</h1>", versao.conteudo)
        self.assertIn("<p>Texto base</p>", versao.conteudo)

    def test_gerar_versao_idempotencia_sem_alteracoes(self):
        res1 = gerar_versao.apply(args=[self.artigo.id]).get()
        self.assertEqual(res1["status"], "criado")

        res2 = gerar_versao.apply(args=[self.artigo.id]).get()
        self.assertEqual(res2["status"], "ignorado")
        self.assertEqual(res2["motivo"], "conteudo_identico")
        self.assertEqual(VersaoArtigo.objects.filter(artigo=self.artigo).count(), 1)

    def test_gerar_nova_versao_apos_aceitar_sugestao(self):
        gerar_versao.apply(args=[self.artigo.id]).get()

        sugestao = criar_sugestao(self.trecho.id, "Texto alterado pela sugestão")
        decidir(sugestao.id, "aceitar")

        res2 = gerar_versao.apply(args=[self.artigo.id]).get()
        self.assertEqual(res2["status"], "criado")
        self.assertEqual(VersaoArtigo.objects.filter(artigo=self.artigo).count(), 2)

    def test_gerar_versao_artigo_inexistente_retorna_erro(self):
        resultado = gerar_versao.apply(args=[99999]).get()
        self.assertEqual(resultado["status"], "erro")
        self.assertEqual(VersaoArtigo.objects.count(), 0)