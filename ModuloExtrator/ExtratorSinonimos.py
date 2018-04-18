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

    def buscar_sinonimos(self, palavra, pos, metodo, fontes = ['wordnet'], multiword=False, contexto=None, ordenar=True):
        if metodo == 'simples':
            return self.buscar_sinonimos_simples(palavra, pos, fontes, False)
        elif metodo == 'desambiguador':
            return self.buscar_sinonimos_desambiguacao(palavra, pos, contexto, fontes, False)
        elif metodo == 'baseline':
            return self.buscar_sinonimos_baseline_semeval(palavra, pos, fontes, multiword=False)
        elif metodo == 'topk':
            return self.buscar_top_k(palavra, pos, fontes, multiword, 2)
        elif metodo == 'todos':
            return self.buscar_todos_significados(palavra, pos, fontes, multiword, 10000)
        elif metodo == 'minha_abordagem':
            return self.buscar_sinonimos_minha_abordagem(palavra, pos, fontes, multiword=False)

        return []

    # obtem todos sinonimos de todos synsets da Wordnet
    def buscar_sinonimos_simples(self, palavra, pos, fontes, multiword):
        sinonimos = []

        for s in wn.synsets(unicode(palavra), pos):
            for l in s.lemma_names():
                sinonimos.append(l)

        saida_sinonimos = []
        for s in set(sinonimos):
            if (not Utilitarios.multipalavra(s) and not multiword) or multiword:
                saida_sinonimos.append(s)

        return saida_sinonimos

    def buscar_todos_significados(self, palavra, pos, fontes, multiword, topk):
        return self.buscar_top_k(palavra, pos, fontes, multiword, 10000)

    def buscar_sinonimos_desambiguacao(self, palavra, pos, ctxt, fontes, multiword):
        sinonimos = []
        synsets = wn.synsets(palavra, pos)

        significados = self.desambiguador.desambiguar(ctxt, palavra)
        significados = [res[0] for res in significados if res[1]]

        for s in significados:
            for l in s.lemma_names():
                if not l in sinonimos:
                    sinonimos.append(l)
                        
        return [s for s in sinonimos if (not Utilitarios.multipalavra(s) and not multiword) or multiword]

    def buscar_top_k(self, palavra, pos, fontes, multiword, topk):
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

    def buscar_sinonimos_minha_abordagem(self, palavra, pos, fontes, multiword):
        resultado = wn.synsets(palavra, pos)[0].lemma_names()
        return Utilitarios.remover_multipalavras(resultado)

    def buscar_sinonimos_baseline_semeval(self, palavra, pos, fontes, multiword):
        sinonimos_nivel1 = set()
        sinonimos_nivel2 = set()
        sinonimos_nivel3 = set()
        sinonimos_nivel4 = set()

        palavra = unicode(palavra)

        synset = wn.synsets(palavra)[0]
        sinonimos_nivel1.update(synset.lemma_names())

        if synset.pos() in ['n', 'v']:
            for h in synset.hypernyms():
                sinonimos_nivel2.update(h.lemma_names())
        else:
            for s in synset.part_meronyms(): sinonimos_nivel2.update(s.lemma_names())
            for s in synset.part_holonyms(): sinonimos_nivel2.update(s.lemma_names())
            for s in synset.member_meronyms(): sinonimos_nivel2.update(s.lemma_names())
            for s in synset.member_holonyms(): sinonimos_nivel2.update(s.lemma_names())

        if wn.synsets(palavra).__len__() > 1:
            for s in wn.synsets(palavra[1:]):
                sinonimos_nivel3.update(s.lemma_names())

        if synset.pos() in ['n', 'v']:
            if wn.synsets(palavra).__len__() > 1:
                for s in wn.synsets(palavra[1:]):
                    for h in s.hypernyms(): sinonimos_nivel4.update(s.lemma_names())
        else:
            if wn.synsets(palavra).__len__() > 1:
                for s in wn.synsets(palavra[1:]):
                    for p in synset.part_meronyms():
                        for h in p.hypernyms():
                            sinonimos_nivel4.add(h.lemma_names())
                    for p in synset.part_holonyms():
                        for h in p.hypernyms():
                            sinonimos_nivel4.add(h.lemma_names())
                    for m in synset.member_meronyms():
                        for m in p.hypernyms():
                            sinonimos_nivel4.add(m.lemma_names())
                    for m in synset.member_holonyms():
                        for m in p.hypernyms():
                            sinonimos_nivel4.add(m.lemma_names())
                    
        sinonimos_nivel2 = Utilitarios.remover_multipalavras(list(sinonimos_nivel2))
        sinonimos_nivel3 = Utilitarios.remover_multipalavras(list(sinonimos_nivel3))
        sinonimos_nivel4 = Utilitarios.remover_multipalavras(list(sinonimos_nivel4))

        resolverdor_duplicatas = set(sinonimos_nivel2)
        resolutor_colisoes_list = list(resolverdor_duplicatas)

        todos_resultados = [sinonimos_nivel2, sinonimos_nivel3, sinonimos_nivel4]

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

    def ordenar_por_frequencia(self, todas_palavras):
        contadores = self.contadores

        palavras_indexadas = dict()
        palavras_ordenadas = []
        
        for palavra in todas_palavras:
            try:
                if not contadores[palavra] in palavras_indexadas:
                    palavras_indexadas[contadores[palavra]] = []
            except:
                palavras_indexadas[0] = []

            try:
                palavras_indexadas[contadores[palavra]].append(palavra)
            except:
                palavras_indexadas[0].append(palavra)

        chaves = palavras_indexadas.keys()
        chaves.sort(reverse=True)

        for chave in chaves:
            palavras_ordenadas += list(set(palavras_indexadas[chave]))

        return palavras_ordenadas