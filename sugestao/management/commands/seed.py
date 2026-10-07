from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from sugestao.models import Artigo, Secao, Sugestao, Trecho, VersaoArtigo


class Command(BaseCommand):
    help = "Popula o banco de dados com artigos longos e realistas cobrindo 100% dos cenários de borda do domínio."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Limpando dados antigos do banco..."))

        with transaction.atomic():
            # 1. Limpeza do banco na ordem reversa de chaves estrangeiras
            VersaoArtigo.objects.all().delete()
            Sugestao.objects.all().delete()
            Trecho.objects.all().delete()
            Secao.objects.all().delete()
            Artigo.objects.all().delete()

            now = timezone.now()

            # ARTIGO 1: Arquitetura de Microserviços e Resiliência
            # (Cenários: Sugestão Pendente, Substituída, Rejeitada, Remoção e Múltiplos Snapshots)
            self.stdout.write(
                "Gerando Artigo 1: Padrões de Resiliência em Sistemas Distribuídos..."
            )

            artigo_1 = Artigo.objects.create(
                titulo="Padrões Avançados de Resiliência e Tolerância a Falhas em Sistemas Distribuídos"
            )

            # Seção 1.1
            sec_1_1 = Secao.objects.create(
                artigo=artigo_1,
                nome="1. Introdução e Desafios da Concorrência Distribuída",
                posicao=1,
            )

            # Trecho 1.1.1: CASO - Sugestão Pendente regular + Histórico de SUBSTITUIDA
            t_1_1_1 = Trecho.objects.create(
                secao=sec_1_1,
                posicao=1,
                texto="A transição de arquiteturas monolíticas para microserviços altera fundamentalmente as garantias de consistência do sistema. Em um ambiente distribuído, a latência de rede deixa de ser negligenciável e as falhas parciais passam a ser um evento esperado, exigindo estratégias explícitas de mitigação.",
            )
            Sugestao.objects.create(
                trecho=t_1_1_1,
                texto="A migração de monólitos para microserviços elimina a consistência ACID tradicional em favor de modelos eventualmente consistentes.",
                status=Sugestao.Status.SUBSTITUIDA,
                decidida_em=now - timedelta(days=3),
            )
            Sugestao.objects.create(
                trecho=t_1_1_1,
                texto="A transição de arquiteturas monolíticas para microserviços altera fundamentalmente as garantias de consistência do sistema, introduzindo desafios complexos de particionamento de dados e latência.",
                status=Sugestao.Status.PENDENTE,
            )

            # Trecho 1.1.2: Trecho Estável
            Trecho.objects.create(
                secao=sec_1_1,
                posicao=2,
                texto="Diferente das transações ACID locais garantidas por bancos de dados relacionais únicos, os sistemas distribuídos frequentemente recorrem ao Teorema CAP e ao modelo BASE (Basically Available, Soft-state, Eventual consistency) para alcançar escalabilidade horizontal.",
            )

            # Seção 1.2
            sec_1_2 = Secao.objects.create(
                artigo=artigo_1,
                nome="2. Padrões de Isolamento e Isolação de Impacto",
                posicao=2,
            )

            # Trecho 1.2.1: CASO - Sugestão REJEITADA no histórico
            t_1_2_1 = Trecho.objects.create(
                secao=sec_1_2,
                posicao=1,
                texto="O padrão Circuit Breaker atua como um disjuntor elétrico: ao detectar uma taxa elevada de erros ao comunicar-se com um serviço externo, ele 'abre' o circuito imediatamente, evitando o esgotamento de threads no serviço chamador e permitindo que o sistema remoto se recupere.",
            )
            Sugestao.objects.create(
                trecho=t_1_2_1,
                texto="O Circuit Breaker deve ser implementado usando blocos simples de try/catch no código do controlador.",
                status=Sugestao.Status.REJEITADA,
                decidida_em=now - timedelta(days=1),
            )

            # Trecho 1.2.2: CASO - Sugestão PENDENTE de REMOÇÃO (Texto Vazio)
            t_1_2_2 = Trecho.objects.create(
                secao=sec_1_2,
                posicao=2,
                texto="Complementarmente, a técnica de Bulkhead divide os recursos de computação (como pools de conexões e threads) em partições isoladas. Dessa forma, uma sobrecarga em um módulo secundário não consome a capacidade necessária para processar requisições críticas.",
            )
            Sugestao.objects.create(
                trecho=t_1_2_2,
                texto="",  # Proposta de remoção do trecho
                status=Sugestao.Status.PENDENTE,
            )

            # Snapshots/Versões Históricas do Artigo 1
            VersaoArtigo.objects.create(
                artigo=artigo_1,
                conteudo=(
                    "<h1>Padrões Avançados de Resiliência em Sistemas Distribuídos</h1>"
                    "<h2>1. Introdução</h2>"
                    "<p>A transição para microserviços altera as garantias do sistema.</p>"
                ),
                criada_em=now - timedelta(days=5),
            )
            VersaoArtigo.objects.create(
                artigo=artigo_1,
                conteudo=(
                    "<h1>Padrões Avançados de Resiliência e Tolerância a Falhas em Sistemas Distribuídos</h1>"
                    "<h2>1. Introdução e Desafios da Concorrência Distribuída</h2>"
                    "<p>A transição de arquiteturas monolíticas para microserviços altera fundamentalmente as garantias de consistência do sistema. Em um ambiente distribuído, a latência de rede deixa de ser negligenciável e as falhas parciais passam a ser um evento esperado, exigindo estratégias explícitas de mitigação.</p>"
                    "<p>Diferente das transações ACID locais garantidas por bancos de dados relacionais únicos, os sistemas distribuídos frequentemente recorrem ao Teorema CAP e ao modelo BASE (Basically Available, Soft-state, Eventual consistency) para alcançar escalabilidade horizontal.</p>"
                    "<h2>2. Padrões de Isolamento e Isolação de Impacto</h2>"
                    "<p>O padrão Circuit Breaker atua como um disjuntor elétrico: ao detectar uma taxa elevada de erros ao comunicar-se com um serviço externo, ele 'abre' o circuito imediatamente, evitando o esgotamento de threads no serviço chamador e permitindo que o sistema remoto se recupere.</p>"
                    "<p>Complementarmente, a técnica de Bulkhead divide os recursos de computação (como pools de conexões e threads) em partições isoladas. Dessa forma, uma sobrecarga em um módulo secundário não consome a capacidade necessária para processar requisições críticas.</p>"
                ),
                criada_em=now - timedelta(hours=2),
            )

            # ARTIGO 2: Engenharia de Prompt e Modelos de Linguagem
            # (Cenários: Trecho 100% Limpo sem sugestões e Artigo com ZERO Snapshots)
            self.stdout.write("Gerando Artigo 2: Engenharia de Prompt em LLMs...")

            artigo_2 = Artigo.objects.create(
                titulo="Engenharia de Prompt e Injeção de Contexto em Modelos de Linguagem de Larga Escala"
            )

            # Seção 2.1
            sec_2_1 = Secao.objects.create(
                artigo=artigo_2,
                nome="1. Arquitetura de Prompts e RAG (Retrieval-Augmented Generation)",
                posicao=1,
            )

            # Trecho 2.1.1: CASO - Sugestão Pendente Regular
            t_2_1_1 = Trecho.objects.create(
                secao=sec_2_1,
                posicao=1,
                texto="A técnica de RAG (Retrieval-Augmented Generation) combina a capacidade generativa de Modelos de Linguagem (LLMs) com bases de conhecimento externas em tempo de execução, reduzindo alucinações e permitindo o acesso a dados privados sem a necessidade de re-treinamento.",
            )
            Sugestao.objects.create(
                trecho=t_2_1_1,
                texto="O padrão RAG (Retrieval-Augmented Generation) enriquece a janela de contexto de modelos generativos consultando bancos vetoriais em tempo real, mitigando drasticamente alucinações e reduzindo custos operacionais.",
                status=Sugestao.Status.PENDENTE,
            )

            # Trecho 2.1.2: CASO - Trecho 100% LIMPO (sem histórico e sem sugestões)
            Trecho.objects.create(
                secao=sec_2_1,
                posicao=2,
                texto="Para garantir respostas precisas, o pipeline de recuperação extrai embeddings do texto de consulta e realiza a busca por similaridade de cosseno em um banco de dados vetorial especializado, injetando os documentos mais relevantes diretamente no prompt do sistema.",
            )

            # Seção 2.2
            sec_2_2 = Secao.objects.create(
                artigo=artigo_2,
                nome="2. Estratégias de CoT (Chain-of-Thought) e System Prompts",
                posicao=2,
            )

            # Trecho 2.2.1: Trecho Estável
            Trecho.objects.create(
                secao=sec_2_2,
                posicao=1,
                texto="O encadeamento de raciocínio (Chain-of-Thought) instrui o modelo a explicitar as etapas intermediárias de lógica antes de produzir a resposta final. Essa abordagem melhora significativamente o desempenho em tarefas complexas de matemática, código e análise lógica.",
            )

            # O artigo_2 NÃO recebe registros em VersaoArtigo (Testa GET /api/artigos/2/versoes/ -> [])

        self.stdout.write(
            self.style.SUCCESS(
                "Banco de dados populado com sucesso com 2 artigos técnicos realistas!"
            )
        )
