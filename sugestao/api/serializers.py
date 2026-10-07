from rest_framework import serializers

from sugestao.models import Sugestao, VersaoArtigo

# --- 1. Serializers de Entrada (Input / Requisições) ---

class CriarSugestaoSerializer(serializers.Serializer):
    """
    Valida o payload de entrada para criação de uma nova sugestão.
    POST /api/trechos/<id>/sugestoes/
    """
    texto = serializers.CharField(
        allow_blank=True,
        trim_whitespace=True,
        required=True,
        help_text="Texto proposto para a sugestão (pode ser vazio)."
    )


class DecidirSugestaoSerializer(serializers.Serializer):
    """
    Valida a ação de decisão sobre uma sugestão.
    POST /api/sugestoes/<id>/decisao/
    """
    acao = serializers.CharField(
        required=True,
        help_text="Ação a ser executada: 'aceitar' ou 'rejeitar'."
    )

    def validate_acao(self, value: str) -> str:
        value_normalizado = value.strip().lower()
        if value_normalizado not in ("aceitar", "rejeitar"):
            raise serializers.ValidationError(
                f"Ação inválida '{value}'. Os valores permitidos são 'aceitar' ou 'rejeitar'."
            )
        return value_normalizado


# --- 2. Serializers de Saída (Output / Respostas JSON) ---

class SugestaoOutputSerializer(serializers.ModelSerializer):
    """
    Formatador de saída para objetos do modelo Sugestao.
    """
    class Meta:
        model = Sugestao
        fields = (
            "id",
            "trecho_id",
            "texto",
            "status",
            "criada_em",
            "decidida_em",
        )
        read_only_fields = fields


class HistoricoTrechoOutputSerializer(serializers.Serializer):
    """Texto original do trecho e todas as sugestões associadas."""
    trecho_id = serializers.IntegerField()
    texto_original = serializers.CharField(allow_blank=True)
    sugestoes = SugestaoOutputSerializer(many=True)


class ArtigoHTMLOutputSerializer(serializers.Serializer):
    """
    Formatador para o HTML compilado do artigo.
    GET /api/artigos/<id>/
    """
    artigo_id = serializers.IntegerField()
    conteudo_html = serializers.CharField()


class VersaoArtigoOutputSerializer(serializers.ModelSerializer):
    """
    Formatador para historico de versoes/snapshots do artigo.
    GET /api/artigos/<id>/versoes/
    """
    class Meta:
        model = VersaoArtigo
        fields = (
            "id",
            "artigo_id",
            "conteudo",
            "criada_em",
        )
        read_only_fields = fields
