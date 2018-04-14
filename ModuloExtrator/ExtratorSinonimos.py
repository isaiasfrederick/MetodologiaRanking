from ModuloOxfordAPI.ModuloClienteOxfordAPI import ClienteOxfordAPI
from ModuloUtilitarios.Utilitarios import Utilitarios
from ModuloDesambiguacao.Desambiguador import Desambiguador
from nltk.corpus import wordnet as wn
import traceback

class ExtratorSinonimos(object):
    def __init__(self, configs, cli_oxford, cli_babelnet, dir_contadores):
        self.configs = configs
        
        self.desambiguador = Desambiguador()
        self.cli_oxford_api = cli_oxford
        self.cli_babelnet_api = cli_babelnet

        self.contadores = Utilitarios.carregar_json(dir_contadores)

    def buscar_sinonimos(self, palavra, pos, algoritmo, multiword=False, contexto=None, ordenar=True):
        if algoritmo == 'simples':
            return self.buscar_sinonimos_simples(palavra, pos, contexto, False)
        elif algoritmo == 'desambiguador':
            return self.buscar_sinonimos_desambiguacao(palavra, pos, contexto, False)
        elif algoritmo == 'baseline':
            return self.buscar_sinonimos_baseline_semeval(palavra, multiword=False)
        elif algoritmo == 'topk':
            return self.buscar_topk(palavra, pos, multiword, 2)
        elif algoritmo == 'todos':
            return self.buscar_todos_significados(palavra, pos, multiword, 10000)
        else:
            pass

        return None

    # obtem todos sinonimos de todos synsets da Wordnet
    def buscar_sinonimos_simples(self, palavra, pos, contexto, multiword):
        sinonimos = []

        for s in wn.synsets(unicode(palavra), pos):
            for l in s.lemma_names():
                sinonimos.append(l)

        saida_sinonimos = []
        for s in set(sinonimos):
            if (not Utilitarios.multipalavra(s) and not multiword) or multiword:
                saida_sinonimos.append(s)

        return saida_sinonimos

    def buscar_todos_significados(self, palavra, pos, multiword, topk):
        return self.buscar_topk(palavra, pos, multiword, 10000)

    def buscar_sinonimos_desambiguacao(self, palavra, pos, contexto, multiword):
        sinonimos = []
        synsets = wn.synsets(palavra, pos)

        significados = self.desambiguador.desambiguar(contexto, palavra)
        significados = [res[0] for res in significados if res[1]]

        for s in significados:
            for l in s.lemma_names():
                if not l in sinonimos:
                    sinonimos.append(l)
                        
        return [s for s in sinonimos if (not Utilitarios.multipalavra(s) and not multiword) or multiword]

    def buscar_topk(self, palavra, pos, multiword, topk):
        try:
            meu_set = set()
            for s in wn.synsets(palavra, pos)[:topk]:
                for l in s.lemma_names():
                    meu_set.add(l)
            return list(meu_set)
        except:
            traceback.print_exc()
            raw_input('<enter>')
            return []

    def buscar_sinonimos_baseline_semeval(self, palavra, multiword):
        sinonimos_nivel1 = set()
        sinonimos_nivel2 = set()
        sinonimos_nivel3 = set()
        sinonimos_nivel4 = set()

        palavra = unicode(palavra)

        try:
            synset =  [res[0] for res in self.desambiguador.desambiguar(contexto, palavra) if res[1]][0]
        except:
            # Synset mais usual
            synset = wn.synsets(palavra)[0]

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
                    
                    if obj_sinonimos:
                        obj_definicoes = self.cli_oxford_api.obter_definicoes(lemma)

                        obj_final = self.cli_oxford_api.mesclar_significados_sinonimos(obj_definicoes,obj_sinonimos)
                        try:
                            obj_final = obj_final[pos]
                            for registro in obj_final:
                                try:
                                    for sin in registro['synonyms']:
                                        sinonimos_nivel3.add(sin)
                                except KeyError, ke: pass
                                try:
                                    for subsense in registro['subsenses']:
                                        for sin in subsense['synonyms']:
                                            sinonimos_nivel3.add(sin)
                                except KeyError, ke: pass
                        except: pass
                except AttributeError, ae: pass

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
            for sin in todos_resultados[i]:
                if sin not in resolverdor_duplicatas:
                    resolutor_colisoes_list.append(sin)
                    resolverdor_duplicatas.add(sin)

        resultado_final = []

        for s in resolverdor_duplicatas:
            if (not Utilitarios.multipalavra(s) and not multiword) or multiword:
                resultado_final.append(s)

        return resultado_final

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
        chaves.sort(reverse=True)

        for chave in chaves:
            palavras_ordenadas += list(set(palavras_indexadas[chave]))

        return palavras_ordenadas