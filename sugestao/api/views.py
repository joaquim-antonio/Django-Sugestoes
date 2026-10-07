from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from sugestao.api.serializers import (
    ArtigoHTMLOutputSerializer,
    CriarSugestaoSerializer,
    DecidirSugestaoSerializer,
    HistoricoTrechoOutputSerializer,
    SugestaoOutputSerializer,
    VersaoArtigoOutputSerializer,
)
from sugestao.models import VersaoArtigo
from sugestao.services import (
    Conflito,
    ErroDeValidacao,
    NaoEncontrado,
    criar_sugestao,
    decidir,
    listar_historico,
    montar_artigo_html,
    restaurar_original,
)
from sugestao.tasks import gerar_versao


class CriarListarSugestaoView(APIView):
    """
    POST /api/trechos/<id>/sugestoes/ -> Cria uma nova sugestão pendente.
    GET  /api/trechos/<id>/sugestoes/ -> Lista o texto original e todas as sugestões do trecho.
    """

    @extend_schema(
            summary="Criar Sugestão",
            description="Cria uma nova sugestão pendente para o trecho especificado.",
            request=CriarSugestaoSerializer,
            responses={
                201: SugestaoOutputSerializer,
                400: OpenApiResponse(description="Erro de validação nos dados enviados."),
                404: OpenApiResponse(description="Trecho não encontrado."),
                409: OpenApiResponse(description="Já existe uma sugestão pendente para este trecho."),
            },
        )
    def post(self, request, trecho_id: int):
        serializer = CriarSugestaoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            sugestao = criar_sugestao(
                trecho_id=trecho_id,
                texto=serializer.validated_data["texto"],
            )
            return Response(
                SugestaoOutputSerializer(sugestao).data,
                status=status.HTTP_201_CREATED,
            )
        except NaoEncontrado as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except Conflito as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ErroDeValidacao as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Listar Histórico de Sugestões",
        description="Recupera o texto original do trecho e todas as sugestões, da mais recente para a mais antiga.",
        responses={
            200: HistoricoTrechoOutputSerializer,
            404: OpenApiResponse(description="Trecho não encontrado."),
        },
    )
    def get(self, request, trecho_id: int):
        try:
            historico = listar_historico(trecho_id=trecho_id)
            return Response(
                HistoricoTrechoOutputSerializer(historico).data,
                status=status.HTTP_200_OK,
            )
        except NaoEncontrado as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)


class DecidirSugestaoView(APIView):
    """
    POST /api/sugestoes/<id>/decisao/ -> Aceita ou rejeita uma sugestão pendente.
    """
    
    @extend_schema(
        summary="Decidir Sugestão",
        description="Aceita ou rejeita uma sugestão pendente.",
        request=DecidirSugestaoSerializer,
        responses={
            200: SugestaoOutputSerializer,
            400: OpenApiResponse(description="Ação inválida (deve ser 'aceitar' ou 'rejeitar')."),
            404: OpenApiResponse(description="Sugestão não encontrada."),
            409: OpenApiResponse(description="Sugestão não está no status pendente."),
        },
    )
    def post(self, request, sugestao_id: int):
        serializer = DecidirSugestaoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            sugestao = decidir(
                sugestao_id=sugestao_id,
                acao=serializer.validated_data["acao"],
            )
            return Response(
                SugestaoOutputSerializer(sugestao).data,
                status=status.HTTP_200_OK,
            )
        except NaoEncontrado as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except Conflito as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ErroDeValidacao as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class RestaurarOriginalTrechoView(APIView):
    """POST /api/trechos/<id>/restaurar-original/ -> Restaura o texto original."""

    @extend_schema(
        summary="Restaurar Texto Original do Trecho",
        description=(
            "Marca como substituída a sugestão atualmente aceita. "
            "O artigo volta a usar o texto original do trecho."
        ),
        responses={
            200: SugestaoOutputSerializer,
            404: OpenApiResponse(description="Trecho não encontrado."),
            409: OpenApiResponse(description="O trecho já está usando o texto original."),
        },
    )
    def post(self, request, trecho_id: int):
        try:
            sugestao = restaurar_original(trecho_id)
            return Response(
                SugestaoOutputSerializer(sugestao).data,
                status=status.HTTP_200_OK,
            )
        except NaoEncontrado as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except Conflito as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)


class ObterArtigoMontadoView(APIView):
    """
    GET /api/artigos/<id>/ -> Retorna o HTML compilado do artigo em tempo real.
    """

    @extend_schema(
        summary="Obter Artigo Compilado em HTML",
        description="Gera o HTML do artigo em tempo real aplicando as sugestões aceitas.",
        responses={
            200: ArtigoHTMLOutputSerializer,
            404: OpenApiResponse(description="Artigo não encontrado."),
        },
    )
    def get(self, request, artigo_id: int):
        try:
            conteudo_html = montar_artigo_html(artigo_id)
            payload = {
                "artigo_id": artigo_id,
                "conteudo_html": conteudo_html,
            }
            return Response(
                ArtigoHTMLOutputSerializer(payload).data,
                status=status.HTTP_200_OK,
            )
        except NaoEncontrado as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)


class CriarListarVersaoArtigoView(APIView):
    """
    POST /api/artigos/<id>/versoes/ -> Agenda a geração de um snapshot via Celery (202 Accepted).
    GET  /api/artigos/<id>/versoes/ -> Lista todos os snapshots gerados do artigo.
    """

    @extend_schema(
        summary="Gerar Snapshot de Versão (Assíncrono)",
        description="Agenda a geração de um novo snapshot do artigo via Worker do Celery.",
        responses={
            202: OpenApiResponse(description="Geração de versão agendada com sucesso."),
            404: OpenApiResponse(description="Artigo não encontrado."),
        },
    )
    def post(self, request, artigo_id: int):
        try:
            # Valida existência básica antes de despachar a task
            montar_artigo_html(artigo_id)
            
            # Despacha a task assíncrona no Celery
            gerar_versao.delay(artigo_id)

            return Response(
                {"detail": "Agendamento de geração de versão realizado com sucesso."},
                status=status.HTTP_202_ACCEPTED,
            )
        except NaoEncontrado as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        summary="Listar Versões do Artigo",
        description="Recupera o histórico de snapshots gravados para o artigo.",
        responses={
            200: VersaoArtigoOutputSerializer(many=True),
            404: OpenApiResponse(description="Artigo não encontrado."),
        },
    )
    def get(self, request, artigo_id: int):
        try:
            # Valida se o artigo existe
            montar_artigo_html(artigo_id)

            versoes = VersaoArtigo.objects.filter(artigo_id=artigo_id).order_by("-criada_em")
            return Response(
                VersaoArtigoOutputSerializer(versoes, many=True).data,
                status=status.HTTP_200_OK,
            )
        except NaoEncontrado as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
