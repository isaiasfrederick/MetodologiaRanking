from ModuloOxfordAPI.ModuloClienteOxfordAPI import ClienteOxfordAPI
from Desambiguacao.Desambiguador import Desambiguador
from nltk.corpus import wordnet as wn
from Utilitarios import Utilitarios
import traceback

class ExtratorSinonimos(object):
    def __init__(self, configs, cli_oxford, cli_babelnet):
        self.configs = configs
        
        self.desambiguador = Desambiguador()
        self.cli_oxford_api = cli_oxford
        self.cli_babelnet_api = cli_babelnet

        self.contadores = Utilitarios.carregar_json(self.configs['leipzig']['dir_contadores'])

    def busca_sinonimos(self, palavra, pos, algoritmo, multiword=False, contexto=None, ordenar=True):
        if algoritmo == 'simples':
            return self.busca_sinonimos_simples(palavra, pos, contexto, False)
        elif algoritmo == 'desambiguador':
            return self.busca_sinonimos_desambiguacao(palavra, pos, contexto, False)
        elif algoritmo == 'baseline':
            return self.buscar_sinonimos_baseline_semeval(synset, multiword=False)
        elif algoritmo == 'wander':
            pass
        elif algoritmo == 'estatistica':
            pass
        else:
            pass

        return None

    # obtem todos sinonimos de todos synsets da Wordnet
    def busca_sinonimos_simples(self, palavra, pos, contexto, multiword):
        sinonimos = []

        for s in wn.synsets(unicode(palavra), pos):
            for l in s.lemma_names():
                sinonimos.append(l)

        sinonimos_final = []

        for e in list(set(sinonimos)):
            if not (Utilitarios.multipalavra(e) and multiword == False):
                sinonimos_final.append(e.lower())

        return [s for s in sinonimos_final if (not Utilitarios.multipalavra(s) and not multiword) or multiword]

    def busca_sinonimos_desambiguacao(self, palavra, pos, contexto, multiword):
        sinonimos = []
        synsets = wn.synsets(palavra, pos)

        significados = self.desambiguador.desambiguar(contexto, palavra)
        significados = [res[0] for res in significados if res[1]]

        for s in significados:
            for l in s.lemma_names():
                if not l in sinonimos:
                    sinonimos.append(l)
                        
        return [s for s in sinonimos if (not Utilitarios.multipalavra(s) and not multiword) or multiword]

    def ordenar_por_frequencia(self, palavras):
        contadores = self.contadores
        palavras_indexadas = dict()
        palavras_ordenadas = []
        
        for p in palavras:
            try:
                if not contadores[p] in palavras_indexadas:
                    palavras_indexadas[contadores[p]] = []
            except:
                palavras_indexadas[0] = []

            try:
                palavras_indexadas[contadores[p]].append(p)
            except:
                palavras_indexadas[0].append(p)

        chaves = palavras_indexadas.keys()
        #chaves.sort(reverse=True)

        for chave in chaves:
            palavras_ordenadas += list(set(palavras_indexadas[chave]))

        return palavras_ordenadas

    def buscar_sinonimos_baseline_semeval(self, synset, multiword):
        sinonimos_nivel1 = set()
        sinonimos_nivel2 = set()
        sinonimos_nivel3 = set()
        sinonimos_nivel4 = set()

        for s in synset.lemma_names(): sinonimos_nivel1.add(s)

        for h in synset.hypernyms():
            for sh in h.lemma_names():
                sinonimos_nivel2.add(sh)

        if synset.pos() == 'r': pos = 'Adverb'
        elif synset.pos() in ['a', 's']: pos = 'Adjective'
        elif synset.pos() == 'n': pos = 'Noun'
        elif synset.pos() == 'v': pos = 'Verb'
        else: pos = ''

        for lemma in synset.lemma_names():
            if lemma in synset.name():
                try:
                    obj_sinonimos = self.cli_oxford_api.obter_sinonimos(lemma)
                    obj_definicoes = self.cli_oxford_api.obter_definicoes(lemma)

                    obj_final = self.cli_oxford_api.mesclar_significados_sinonimos(obj_definicoes,obj_sinonimos)
                    obj_final = obj_final[pos]

                    for registro in obj_final:
                        try:
                            for syn in registro['synonyms']:
                                sinonimos_nivel3.add(syn)
                        except KeyError, ke: pass
                        try:
                            for subsense in registro['subsenses']:
                                for syn in subsense['synonyms']:
                                    sinonimos_nivel3.add(syn)
                        except KeyError, ke: pass
                except AttributeError, ae:
                    traceback.print_exc()

        conjunto = list()
        for l in synset.lemma_names():
            for s in wn.synsets(l):
                if s != synset:
                    for n in s.lemma_names():
                        sinonimos_nivel4.add(n)

        sinonimos_nivel1 = Utilitarios.remover_multipalavras(list(sinonimos_nivel1))
        sinonimos_nivel2 = Utilitarios.remover_multipalavras(list(sinonimos_nivel2))
        sinonimos_nivel3 = Utilitarios.remover_multipalavras(list(sinonimos_nivel3))
        sinonimos_nivel4 = Utilitarios.remover_multipalavras(list(sinonimos_nivel4))

        resolverdor_duplicatas = set(sinonimos_nivel1)
        resolutor_colisoes_list = list(resolverdor_duplicatas)

        todos_resultados = [sinonimos_nivel1, sinonimos_nivel2, sinonimos_nivel3, sinonimos_nivel4]

        for i in range(1, len(todos_resultados)):
            for syn in todos_resultados[i]:
                if syn not in resolverdor_duplicatas:
                    resolutor_colisoes_list.append(syn)
                    resolverdor_duplicatas.add(syn)

        return [s for s in sinonimos_final if (not Utilitarios.multipalavra(s) and not multiword) or multiword]

