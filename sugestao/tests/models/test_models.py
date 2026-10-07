from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from sugestao.models import Artigo, Secao, Sugestao, Trecho, VersaoArtigo


class ConstraintsDeSugestaoTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        artigo = Artigo.objects.create(titulo="Artigo")
        secao = Secao.objects.create(artigo=artigo, nome="Introdução", posicao=1)
        cls.trecho = Trecho.objects.create(secao=secao, posicao=1, texto="original")
        cls.outro_trecho = Trecho.objects.create(secao=secao, posicao=2, texto="outro")

    def criar(self, status, trecho=None, texto="texto", **campos):
        # Por padrão, só a pendente fica sem data de decisão.
        campos.setdefault("decidida_em", None if status == "pendente" else timezone.now())
        return Sugestao.objects.create(trecho=trecho or self.trecho, status=status, texto=texto, **campos)

    def viola(self, constraint, status, **campos):
        """Espera que criar a sugestão viole a constraint com esse nome.

        O atomic interno isola o erro: no Postgres, depois de um erro a transação
        do teste ficaria abortada e qualquer comando seguinte falharia.
        """
        with self.assertRaisesMessage(IntegrityError, constraint):
            with transaction.atomic():
                self.criar(status, **campos)

    def test_duas_aceitas_no_mesmo_trecho_violam(self):
        self.criar("aceita")
        self.viola("uma_aceita_por_trecho", "aceita")

    def test_duas_pendentes_no_mesmo_trecho_violam(self):
        self.criar("pendente")
        self.viola("uma_pendente_por_trecho", "pendente")

    def test_aceita_e_pendente_no_mesmo_trecho_sao_permitidas(self):
        self.criar("aceita")
        self.criar("pendente")
        self.assertEqual(self.trecho.sugestoes.count(), 2)

    def test_aceitas_em_trechos_diferentes_sao_permitidas(self):
        self.criar("aceita")
        self.criar("aceita", trecho=self.outro_trecho)
        self.assertEqual(Sugestao.objects.filter(status="aceita").count(), 2)

    def test_varias_rejeitadas_e_substituidas_sao_permitidas(self):
        for _ in range(3):
            self.criar("rejeitada")
            self.criar("substituida")
        self.assertEqual(self.trecho.sugestoes.count(), 6)

    def test_status_invalido_viola(self):
        # A decisao_tem_data também recusa status desconhecido, então o erro
        # pode apontar para qualquer uma das duas constraints.
        with self.assertRaisesRegex(IntegrityError, "status_valido|decisao_tem_data"):
            with transaction.atomic():
                self.criar("inexistente")

    def test_aceita_sem_data_de_decisao_viola(self):
        self.viola("decisao_tem_data", "aceita", decidida_em=None)

    def test_pendente_com_data_de_decisao_viola(self):
        self.viola("decisao_tem_data", "pendente", decidida_em=timezone.now())

    def test_texto_vazio_e_permitido(self):
        sugestao = self.criar("aceita", texto="")
        sugestao.refresh_from_db()
        self.assertEqual(sugestao.texto, "")


class ConstraintsDePosicaoTest(TestCase):
    def test_posicao_repetida_na_mesma_secao_de_um_artigo_viola(self):
        artigo = Artigo.objects.create(titulo="A")
        Secao.objects.create(artigo=artigo, nome="Intro", posicao=1)
        with self.assertRaisesMessage(IntegrityError, "uma_posicao_por_artigo"):
            with transaction.atomic():
                Secao.objects.create(artigo=artigo, nome="Outra", posicao=1)

    def test_mesma_posicao_de_secao_em_artigos_diferentes_e_permitida(self):
        Secao.objects.create(artigo=Artigo.objects.create(titulo="A"), nome="Intro", posicao=1)
        Secao.objects.create(artigo=Artigo.objects.create(titulo="B"), nome="Intro", posicao=1)
        self.assertEqual(Secao.objects.filter(posicao=1).count(), 2)

    def test_posicao_repetida_de_trecho_na_mesma_secao_viola(self):
        secao = Secao.objects.create(artigo=Artigo.objects.create(titulo="A"), nome="Intro", posicao=1)
        Trecho.objects.create(secao=secao, posicao=1, texto="a")
        with self.assertRaisesMessage(IntegrityError, "uma_posicao_por_secao"):
            with transaction.atomic():
                Trecho.objects.create(secao=secao, posicao=1, texto="b")

    def test_mesma_posicao_de_trecho_em_secoes_diferentes_e_permitida(self):
        artigo = Artigo.objects.create(titulo="A")
        for posicao in (1, 2):
            secao = Secao.objects.create(artigo=artigo, nome=f"S{posicao}", posicao=posicao)
            Trecho.objects.create(secao=secao, posicao=1, texto="a")
        self.assertEqual(Trecho.objects.filter(posicao=1).count(), 2)


class ApagarArtigoTest(TestCase):
    def test_apagar_o_artigo_apaga_tudo_que_depende_dele(self):
        artigo = Artigo.objects.create(titulo="A")
        secao = Secao.objects.create(artigo=artigo, nome="Intro", posicao=1)
        trecho = Trecho.objects.create(secao=secao, posicao=1, texto="a")
        Sugestao.objects.create(trecho=trecho, texto="b")
        VersaoArtigo.objects.create(artigo=artigo, conteudo="<h1>A</h1>")

        artigo.delete()

        for modelo in (Artigo, Secao, Trecho, Sugestao, VersaoArtigo):
            with self.subTest(modelo=modelo.__name__):
                self.assertEqual(modelo.objects.count(), 0)