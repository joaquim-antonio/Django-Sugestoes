from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from sugestao import services
from sugestao.models import Artigo, Secao, Sugestao, Trecho
from sugestao.services import Conflito, ErroDeValidacao, NaoEncontrado


def criar_trecho(secao=None, posicao=1, texto="original"):
    if secao is None:
        artigo = Artigo.objects.create(titulo="Artigo")
        secao = Secao.objects.create(artigo=artigo, nome="Introdução", posicao=1)
    return Trecho.objects.create(secao=secao, posicao=posicao, texto=texto)


def criar_sugestao(trecho, status="pendente", texto="sugestão", dias_atras=0):
    decidida_em = None
    if status != "pendente":
        decidida_em = timezone.now() - timedelta(days=dias_atras)
    return Sugestao.objects.create(trecho=trecho, texto=texto, status=status, decidida_em=decidida_em)


class CriarSugestaoTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.trecho = criar_trecho()

    def test_cria_uma_sugestao_pendente_sem_data_de_decisao(self):
        sugestao = services.criar_sugestao(self.trecho.id, "novo texto")
        self.assertEqual(sugestao.status, "pendente")
        self.assertEqual(sugestao.texto, "novo texto")
        self.assertIsNone(sugestao.decidida_em)
        self.assertEqual(sugestao.trecho_id, self.trecho.id)

    def test_trecho_inexistente(self):
        with self.assertRaises(NaoEncontrado):
            services.criar_sugestao(self.trecho.id + 1000, "x")

    def test_segunda_pendente_no_mesmo_trecho_e_conflito(self):
        services.criar_sugestao(self.trecho.id, "primeira")
        with self.assertRaises(Conflito):
            services.criar_sugestao(self.trecho.id, "segunda")
        self.assertEqual(self.trecho.sugestoes.count(), 1)

    def test_pode_criar_nova_depois_que_a_anterior_foi_decidida(self):
        for status in ("aceita", "rejeitada"):
            with self.subTest(status_anterior=status):
                trecho = criar_trecho(posicao=10 + len(status))
                criar_sugestao(trecho, status)
                nova = services.criar_sugestao(trecho.id, "outra")
                self.assertEqual(nova.status, "pendente")

    def test_texto_vazio_e_valido(self):
        self.assertEqual(services.criar_sugestao(self.trecho.id, "").texto, "")

    def test_texto_so_com_espacos_vira_vazio(self):
        self.assertEqual(services.criar_sugestao(self.trecho.id, "  \n\t ").texto, "")

    def test_texto_com_espacos_nas_pontas_nao_e_alterado(self):
        sugestao = services.criar_sugestao(self.trecho.id, " frase ")
        self.assertEqual(sugestao.texto, " frase ")

    def test_texto_que_nao_e_string_e_erro_de_validacao(self):
        for invalido in (None, 123, ["a"]):
            with self.subTest(texto=invalido):
                with self.assertRaises(ErroDeValidacao):
                    services.criar_sugestao(self.trecho.id, invalido)


class DecidirTest(TestCase):
    def setUp(self):
        self.trecho = criar_trecho()

    def test_aceitar_marca_aceita_e_registra_a_data(self):
        pendente = criar_sugestao(self.trecho)
        resultado = services.decidir(pendente.id, "aceitar")
        pendente.refresh_from_db()
        self.assertEqual(resultado.pk, pendente.pk)
        self.assertEqual(pendente.status, "aceita")
        self.assertIsNotNone(pendente.decidida_em)

    def test_rejeitar_marca_rejeitada_e_registra_a_data(self):
        pendente = criar_sugestao(self.trecho)
        services.decidir(pendente.id, "rejeitar")
        pendente.refresh_from_db()
        self.assertEqual(pendente.status, "rejeitada")
        self.assertIsNotNone(pendente.decidida_em)

    def test_aceitar_substitui_a_aceita_anterior_e_preserva_a_data_dela(self):
        antiga = criar_sugestao(self.trecho, "aceita", dias_atras=3)
        data_da_aceitacao = antiga.decidida_em
        nova = criar_sugestao(self.trecho)

        services.decidir(nova.id, "aceitar")

        antiga.refresh_from_db()
        nova.refresh_from_db()
        self.assertEqual(antiga.status, "substituida")
        self.assertEqual(antiga.decidida_em, data_da_aceitacao)
        self.assertEqual(nova.status, "aceita")
        self.assertEqual(self.trecho.sugestoes.filter(status="aceita").count(), 1)

    def test_rejeitar_nao_mexe_na_aceita_atual(self):
        aceita = criar_sugestao(self.trecho, "aceita")
        pendente = criar_sugestao(self.trecho)
        services.decidir(pendente.id, "rejeitar")
        aceita.refresh_from_db()
        self.assertEqual(aceita.status, "aceita")

    def test_decidir_o_que_nao_esta_pendente_e_conflito_e_nao_altera_nada(self):
        casos = [(s, a) for s in ("aceita", "rejeitada", "substituida") for a in services.ACOES]
        for posicao, (status, acao) in enumerate(casos, start=2):
            with self.subTest(status=status, acao=acao):
                sugestao = criar_sugestao(criar_trecho(self.trecho.secao, posicao), status)
                antes = (sugestao.status, sugestao.decidida_em)
                with self.assertRaises(Conflito):
                    services.decidir(sugestao.id, acao)
                sugestao.refresh_from_db()
                self.assertEqual((sugestao.status, sugestao.decidida_em), antes)

    def test_decidir_duas_vezes_a_mesma_pendente(self):
        pendente = criar_sugestao(self.trecho)
        services.decidir(pendente.id, "aceitar")
        with self.assertRaises(Conflito):
            services.decidir(pendente.id, "aceitar")

    def test_acao_invalida_e_erro_de_validacao_e_nao_altera_nada(self):
        pendente = criar_sugestao(self.trecho)
        with self.assertRaises(ErroDeValidacao):
            services.decidir(pendente.id, "talvez")
        pendente.refresh_from_db()
        self.assertEqual(pendente.status, "pendente")

    def test_sugestao_inexistente(self):
        with self.assertRaises(NaoEncontrado):
            services.decidir(999999, "aceitar")

    def test_ciclo_completo_cria_aceita_cria_outra_aceita(self):
        primeira = services.criar_sugestao(self.trecho.id, "primeira")
        services.decidir(primeira.id, "aceitar")
        segunda = services.criar_sugestao(self.trecho.id, "segunda")
        services.decidir(segunda.id, "aceitar")

        status = dict(self.trecho.sugestoes.values_list("texto", "status"))
        self.assertEqual(status, {"primeira": "substituida", "segunda": "aceita"})


class LeiturasTest(TestCase):
    def setUp(self):
        self.trecho = criar_trecho()

    def test_obter_pendente(self):
        pendente = criar_sugestao(self.trecho)
        criar_sugestao(self.trecho, "aceita")
        self.assertEqual(services.obter_pendente(self.trecho.id).pk, pendente.pk)

    def test_obter_aceita(self):
        aceita = criar_sugestao(self.trecho, "aceita")
        criar_sugestao(self.trecho)
        self.assertEqual(services.obter_aceita(self.trecho.id).pk, aceita.pk)

    def test_trecho_sem_pendente_ou_sem_aceita(self):
        with self.assertRaisesMessage(NaoEncontrado, "pendente"):
            services.obter_pendente(self.trecho.id)
        with self.assertRaisesMessage(NaoEncontrado, "aceita"):
            services.obter_aceita(self.trecho.id)

    def test_trecho_inexistente_nas_duas_leituras(self):
        for leitura in (services.obter_pendente, services.obter_aceita):
            with self.subTest(leitura=leitura.__name__):
                with self.assertRaisesMessage(NaoEncontrado, "Trecho não encontrado"):
                    leitura(self.trecho.id + 1000)

    def test_historico_traz_todas_as_sugestoes_da_mais_recente_para_a_mais_antiga(self):
        antiga = criar_sugestao(self.trecho, "substituida", dias_atras=5)
        recente = criar_sugestao(self.trecho, "rejeitada", dias_atras=1)
        meio = criar_sugestao(self.trecho, "rejeitada", dias_atras=3)
        aceita = criar_sugestao(self.trecho, "aceita")
        pendente = criar_sugestao(self.trecho, "pendente")

        historico = services.listar_historico(self.trecho.id)

        self.assertEqual(historico["texto_original"], self.trecho.texto)
        self.assertEqual(
            [s.pk for s in historico["sugestoes"]],
            [pendente.pk, aceita.pk, meio.pk, recente.pk, antiga.pk],
        )

    def test_historico_nao_mistura_trechos(self):
        outro = criar_trecho(self.trecho.secao, posicao=2)
        criar_sugestao(outro, "rejeitada")
        self.assertEqual(services.listar_historico(self.trecho.id)["sugestoes"], [])

    def test_historico_de_trecho_inexistente(self):
        with self.assertRaises(NaoEncontrado):
            services.listar_historico(self.trecho.id + 1000)


class MontarArtigoHtmlTest(TestCase):
    def novo_artigo(self, titulo="Título"):
        return Artigo.objects.create(titulo=titulo)

    def test_estrutura_com_titulo_secoes_e_paragrafos(self):
        artigo = self.novo_artigo("Meu artigo")
        secao = Secao.objects.create(artigo=artigo, nome="Introdução", posicao=1)
        criar_trecho(secao, 1, "Primeiro.")
        criar_trecho(secao, 2, "Segundo.")

        self.assertEqual(
            services.montar_artigo_html(artigo.id),
            "<h1>Meu artigo</h1>\n<h2>Introdução</h2>\n<p>Primeiro.</p>\n<p>Segundo.</p>",
        )

    def test_ordena_por_posicao_da_secao_e_depois_do_trecho(self):
        artigo = self.novo_artigo("A")
        # Criado de propósito fora de ordem, com posições repetidas entre seções.
        metodos = Secao.objects.create(artigo=artigo, nome="Métodos", posicao=2)
        criar_trecho(metodos, 2, "M2")
        criar_trecho(metodos, 1, "M1")
        intro = Secao.objects.create(artigo=artigo, nome="Intro", posicao=1)
        criar_trecho(intro, 2, "I2")
        criar_trecho(intro, 1, "I1")

        self.assertEqual(
            services.montar_artigo_html(artigo.id),
            "<h1>A</h1>\n<h2>Intro</h2>\n<p>I1</p>\n<p>I2</p>\n<h2>Métodos</h2>\n<p>M1</p>\n<p>M2</p>",
        )

    def test_usa_o_texto_da_aceita_e_ignora_as_demais(self):
        artigo = self.novo_artigo("A")
        secao = Secao.objects.create(artigo=artigo, nome="S", posicao=1)
        com_aceita = criar_trecho(secao, 1, "original 1")
        criar_sugestao(com_aceita, "aceita", "aceito 1")
        criar_sugestao(com_aceita, "pendente", "pendente 1")
        criar_sugestao(com_aceita, "substituida", "substituído 1")
        criar_sugestao(criar_trecho(secao, 2, "original 2"), "rejeitada", "rejeitado 2")
        criar_sugestao(criar_trecho(secao, 3, "original 3"), "pendente", "pendente 3")

        self.assertEqual(
            services.montar_artigo_html(artigo.id),
            "<h1>A</h1>\n<h2>S</h2>\n<p>aceito 1</p>\n<p>original 2</p>\n<p>original 3</p>",
        )

    def test_trecho_apagado_e_omitido_e_a_secao_mantem_o_titulo(self):
        artigo = self.novo_artigo("A")
        secao = Secao.objects.create(artigo=artigo, nome="Resultados", posicao=1)
        for posicao in (1, 2):
            criar_sugestao(criar_trecho(secao, posicao, "vai sumir"), "aceita", "")

        self.assertEqual(services.montar_artigo_html(artigo.id), "<h1>A</h1>\n<h2>Resultados</h2>")

    def test_secao_sem_trechos_mantem_o_titulo(self):
        artigo = self.novo_artigo("A")
        Secao.objects.create(artigo=artigo, nome="Vazia", posicao=1)
        self.assertEqual(services.montar_artigo_html(artigo.id), "<h1>A</h1>\n<h2>Vazia</h2>")

    def test_artigo_sem_secoes_so_tem_o_titulo(self):
        artigo = self.novo_artigo("Só título")
        self.assertEqual(services.montar_artigo_html(artigo.id), "<h1>Só título</h1>")

    def test_escapa_html_no_titulo_na_secao_e_no_texto(self):
        artigo = self.novo_artigo("A & B")
        secao = Secao.objects.create(artigo=artigo, nome="<i>S</i>", posicao=1)
        criar_trecho(secao, 1, "p < 0,05 & <script>alert(1)</script>")
        criar_sugestao(criar_trecho(secao, 2, "x"), "aceita", "<b>negrito</b>")

        html = services.montar_artigo_html(artigo.id)

        self.assertNotIn("<script>", html)
        self.assertNotIn("<b>", html)
        self.assertEqual(
            html,
            "<h1>A &amp; B</h1>\n<h2>&lt;i&gt;S&lt;/i&gt;</h2>\n"
            "<p>p &lt; 0,05 &amp; &lt;script&gt;alert(1)&lt;/script&gt;</p>\n"
            "<p>&lt;b&gt;negrito&lt;/b&gt;</p>",
        )

    def test_artigo_inexistente(self):
        with self.assertRaises(NaoEncontrado):
            services.montar_artigo_html(999999)

    def test_nao_mistura_artigos(self):
        a = self.novo_artigo("A")
        b = self.novo_artigo("B")
        criar_trecho(Secao.objects.create(artigo=a, nome="SA", posicao=1), 1, "texto de A")
        criar_trecho(Secao.objects.create(artigo=b, nome="SB", posicao=1), 1, "texto de B")
        self.assertNotIn("texto de B", services.montar_artigo_html(a.id))

    def test_usa_uma_unica_consulta_mesmo_com_muitos_trechos(self):
        artigo = self.novo_artigo("A")
        for numero in range(1, 4):
            secao = Secao.objects.create(artigo=artigo, nome=f"S{numero}", posicao=numero)
            for posicao in range(1, 6):
                trecho = criar_trecho(secao, posicao, f"t{numero}{posicao}")
                criar_sugestao(trecho, "aceita", f"a{numero}{posicao}")
        with self.assertNumQueries(1):
            services.montar_artigo_html(artigo.id)
