from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from sugestao.models import Artigo, Secao, Sugestao, Trecho, VersaoArtigo


class SugestaoViewsAPITestCase(APITestCase):

    def setUp(self):
        self.artigo = Artigo.objects.create(titulo="Artigo Teste API")
        self.secao = Secao.objects.create(artigo=self.artigo, nome="Seção API", posicao=1)
        self.trecho = Trecho.objects.create(secao=self.secao, posicao=1, texto="Texto base do trecho")

    # --- 1. Testes de POST /api/trechos/<id>/sugestoes/ ---

    def test_criar_sugestao_com_sucesso_retorna_201(self):
        url = reverse("trecho-sugestoes", kwargs={"trecho_id": self.trecho.id})
        payload = {"texto": "Sugestão via API"}

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["texto"], "Sugestão via API")
        self.assertEqual(response.data["status"], Sugestao.Status.PENDENTE)
        self.assertEqual(Sugestao.objects.count(), 1)

    def test_criar_sugestao_trecho_inexistente_retorna_404(self):
        url = reverse("trecho-sugestoes", kwargs={"trecho_id": 99999})
        payload = {"texto": "Sugestão para trecho fantasma"}

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)

    def test_criar_segunda_sugestao_pendente_mesmo_trecho_retorna_409(self):
        url = reverse("trecho-sugestoes", kwargs={"trecho_id": self.trecho.id})
        payload = {"texto": "Primeira sugestão"}
        self.client.post(url, payload, format="json")

        # Tentativa de criar a segunda pendente
        payload_duplicado = {"texto": "Segunda sugestão"}
        response = self.client.post(url, payload_duplicado, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("detail", response.data)

    # --- 2. Testes de GET /api/trechos/<id>/sugestoes/ ---

    def test_listar_historico_sugestoes_retorna_200(self):
        antiga = Sugestao.objects.create(
            trecho=self.trecho,
            texto="S1",
            status=Sugestao.Status.REJEITADA,
            decidida_em=timezone.now() - timedelta(days=2),
        )
        recente = Sugestao.objects.create(
            trecho=self.trecho,
            texto="S2",
            status=Sugestao.Status.SUBSTITUIDA,
            decidida_em=timezone.now() - timedelta(days=1),
        )
        pendente = Sugestao.objects.create(trecho=self.trecho, texto="S3")

        url = reverse("trecho-sugestoes", kwargs={"trecho_id": self.trecho.id})
        response = self.client.get(f"{url}?status=rejeitada")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["trecho_id"], self.trecho.id)
        self.assertEqual(response.data["texto_original"], self.trecho.texto)
        self.assertEqual(
            [sugestao["id"] for sugestao in response.data["sugestoes"]],
            [pendente.id, recente.id, antiga.id],
        )

    def test_listar_historico_ignora_parametro_status(self):
        url = reverse("trecho-sugestoes", kwargs={"trecho_id": self.trecho.id})
        response = self.client.get(f"{url}?status=status_inexistente")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- 3. Testes de POST /api/sugestoes/<id>/decisao/ ---

    def test_decidir_sugestao_aceitar_retorna_200(self):
        sugestao = Sugestao.objects.create(trecho=self.trecho, texto="Novo texto aceito")
        url = reverse("sugestao-decisao", kwargs={"sugestao_id": sugestao.id})
        payload = {"acao": "aceitar"}

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Sugestao.Status.ACEITA)

    def test_decidir_sugestao_acao_invalida_retorna_400(self):
        sugestao = Sugestao.objects.create(trecho=self.trecho, texto="Texto")
        url = reverse("sugestao-decisao", kwargs={"sugestao_id": sugestao.id})
        payload = {"acao": "acao_invalida"}

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_decidir_sugestao_ja_decidida_retorna_409(self):
        sugestao = Sugestao.objects.create(
            trecho=self.trecho,
            texto="Texto",
            status=Sugestao.Status.REJEITADA,
            decidida_em=timezone.now(),
        )
        url = reverse("sugestao-decisao", kwargs={"sugestao_id": sugestao.id})
        payload = {"acao": "aceitar"}

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    # --- 4. Testes de GET /api/artigos/<id>/ ---

    def test_obter_artigo_montado_retorna_200_com_html(self):
        url = reverse("artigo-montado", kwargs={"artigo_id": self.artigo.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["artigo_id"], self.artigo.id)
        self.assertIn("<h1>Artigo Teste API</h1>", response.data["conteudo_html"])
        self.assertIn("<h2>Seção API</h2>", response.data["conteudo_html"])
        self.assertIn("<p>Texto base do trecho</p>", response.data["conteudo_html"])

    # --- 5. Testes de POST/GET /api/artigos/<id>/versoes/ ---

    @patch("sugestao.api.views.gerar_versao.delay")
    def test_agendar_geracao_versao_retorna_202_e_despacha_task(self, mock_task_delay):
        url = reverse("artigo-versoes", kwargs={"artigo_id": self.artigo.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_task_delay.assert_called_once_with(self.artigo.id)

    def test_listar_versoes_artigo_retorna_200(self):
        VersaoArtigo.objects.create(artigo=self.artigo, conteudo="<h1>Versão 1</h1>")
        url = reverse("artigo-versoes", kwargs={"artigo_id": self.artigo.id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["conteudo"], "<h1>Versão 1</h1>")
