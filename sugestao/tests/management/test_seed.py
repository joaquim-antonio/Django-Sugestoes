from io import StringIO

from django.core.management import call_command
from django.db.models import Count, Q
from django.test import TestCase

from sugestao.models import Artigo, Secao, Sugestao, Trecho

CONTAGEM_ESPERADA = {"pendente": 2, "aceita": 5, "rejeitada": 1, "substituida": 1}


class SeedTest(TestCase):
    def rodar_seed(self):
        call_command("seed", stdout=StringIO())

    def contagem_por_status(self):
        return dict(Sugestao.objects.values_list("status").annotate(total=Count("id")))

    def test_cria_um_artigo_com_tres_secoes(self):
        self.rodar_seed()
        self.assertEqual(Artigo.objects.count(), 1)
        self.assertEqual(Secao.objects.count(), 3)

    def test_contagem_de_sugestoes_por_status(self):
        self.rodar_seed()
        self.assertEqual(self.contagem_por_status(), CONTAGEM_ESPERADA)

    def test_e_repetivel(self):
        self.rodar_seed()
        self.rodar_seed()
        self.assertEqual(Artigo.objects.count(), 1)
        self.assertEqual(self.contagem_por_status(), CONTAGEM_ESPERADA)

    def test_apaga_os_artigos_que_ja_existiam(self):
        Artigo.objects.create(titulo="Criado à mão")
        self.rodar_seed()
        self.assertFalse(Artigo.objects.filter(titulo="Criado à mão").exists())

    def test_cenarios_previstos(self):
        self.rodar_seed()
        trechos = Trecho.objects.annotate(
            aceitas=Count("sugestoes", filter=Q(sugestoes__status="aceita")),
            pendentes=Count("sugestoes", filter=Q(sugestoes__status="pendente")),
            substituidas=Count("sugestoes", filter=Q(sugestoes__status="substituida")),
        )
        with self.subTest("trecho sem sugestão"):
            self.assertEqual(Trecho.objects.filter(sugestoes__isnull=True).count(), 1)
        with self.subTest("aceita e pendente no mesmo trecho"):
            self.assertEqual(trechos.filter(aceitas=1, pendentes=1).count(), 1)
        with self.subTest("histórico: substituída e aceita no mesmo trecho"):
            self.assertEqual(trechos.filter(aceitas=1, substituidas=1).count(), 1)
        with self.subTest("seção com todos os trechos apagados"):
            resultados = Secao.objects.get(nome="Resultados")
            apagados = Sugestao.objects.filter(trecho__secao=resultados, status="aceita", texto="")
            self.assertEqual(apagados.count(), resultados.trechos.count())

    def test_posicoes_se_repetem_entre_secoes(self):
        # Serve de base para testar a ordenação do artigo montado depois.
        self.rodar_seed()
        self.assertEqual(Trecho.objects.filter(posicao=1).count(), 3)