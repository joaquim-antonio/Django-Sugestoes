import threading

from django.db import connection
from django.test import TransactionTestCase

from sugestao.models import Artigo, Secao, Sugestao, Trecho
from sugestao.services import Conflito, criar_sugestao, decidir


class ConcorrenciaServicesTestCase(TransactionTestCase):

    def setUp(self):
        self.artigo = Artigo.objects.create(titulo="Artigo Concorrência")
        self.secao = Secao.objects.create(artigo=self.artigo, nome="Seção 1", posicao=1)
        self.trecho = Trecho.objects.create(secao=self.secao, posicao=1, texto="Texto original")

    def test_decisoes_concorrentes_mesma_sugestao_uma_vence_outra_recebe_conflito(self):
        """Duas threads tentam decidir a mesma sugestão pendente ao mesmo tempo."""
        sugestao = criar_sugestao(self.trecho.id, "Sugestão para decidir")
        barrier = threading.Barrier(2)
        resultados = []

        def worker(acao):
            try:
                barrier.wait()  # Sincroniza o disparo exato
                res = decidir(sugestao.id, acao)
                resultados.append(("sucesso", res.status))
            except Conflito as exc:
                resultados.append(("conflito", str(exc)))
            finally:
                connection.close()

        t1 = threading.Thread(target=worker, args=("aceitar",))
        t2 = threading.Thread(target=worker, args=("rejeitar",))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Validações: exatamente uma thread deve ter sucesso e a outra deve falhar com Conflito
        sucessos = [r for r in resultados if r[0] == "sucesso"]
        conflitos = [r for r in resultados if r[0] == "conflito"]

        self.assertEqual(len(sucessos), 1)
        self.assertEqual(len(conflitos), 1)

        # O estado no banco deve refletir o resultado da thread vencedora
        sugestao.refresh_from_db()
        self.assertIn(sugestao.status, [Sugestao.Status.ACEITA, Sugestao.Status.REJEITADA])

    def test_criacoes_concorrentes_mesmo_trecho_uma_cria_outra_recebe_conflito(self):
        """Duas threads tentam criar sugestão pendente para o mesmo trecho simultaneamente."""
        barrier = threading.Barrier(2)
        resultados = []

        def worker(texto):
            try:
                barrier.wait()
                res = criar_sugestao(self.trecho.id, texto)
                resultados.append(("sucesso", res.id))
            except Conflito as exc:
                resultados.append(("conflito", str(exc)))
            finally:
                connection.close()

        t1 = threading.Thread(target=worker, args=("Sugestão Thread 1",))
        t2 = threading.Thread(target=worker, args=("Sugestão Thread 2",))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        sucessos = [r for r in resultados if r[0] == "sucesso"]
        conflitos = [r for r in resultados if r[0] == "conflito"]

        self.assertEqual(len(sucessos), 1)
        self.assertEqual(len(conflitos), 1)

        # Garante que ficou apenas UMA sugestão pendente gravada no banco
        self.assertEqual(Sugestao.objects.filter(trecho=self.trecho, status=Sugestao.Status.PENDENTE).count(), 1)