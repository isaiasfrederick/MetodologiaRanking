#! coding: utf-8
from ModuloOxfordAPI.ModuloClienteOxfordAPI import ClienteOxfordAPI
from ModuloUtilitarios.Utilitarios import Utilitarios

# importando desambiguadores
from ModuloDesambiguacao.DesambiguadorOxford import DesambiguadorOxford
from ModuloDesambiguacao.DesambiguadorWordnet import DesambiguadorWordnet
from ModuloDesambiguacao.DesambiguadorUnificado import DesambiguadorUnificado

import itertools

from nltk.corpus import wordnet as wn
import traceback

# Esta classe é front-end para cada método por mim gerado pra gerar o ranking de sinônimos
class InterfaceAbordagens(object):
    def __init__(self, configs, cli_oxford, cli_babelnet, dir_contadores, base_unificada_oxford):
        self.configs = configs
        
        self.desambiguador_wordnet = None
        self.desambiguador_oxford = None
        self.desambiguador_unificado = None

        self.desambiguador_oxford = DesambiguadorOxford(configs, base_unificada_oxford)
        self.desambiguador_unificado = DesambiguadorUnificado(configs, base_unificada_oxford)
        self.desambiguador_wordnet = DesambiguadorWordnet(configs)

        self.cli_oxford_api = cli_oxford
        self.cli_babelnet_api = cli_babelnet

        self.contadores = Utilitarios.carregar_json(dir_contadores)

    def buscar_sinonimos(self, palavra, pos, metodo, fontes = ['wordnet'], multiword=False, contexto=None, ordenar=True):
        topk = 2

        flag_wordnet = True
        flag_oxford = True
        flag_unificado = True

        pos_wn = Utilitarios.conversor_pos_semeval_wn(pos)
        pos_ox = pos

        if metodo == 'simples_wordnet' and flag_wordnet:
            return self.buscar_sinonimos_simples_wordnet(palavra, pos_wn, fontes, False)
        elif metodo == 'baseline_wordnet' and flag_wordnet:
            return self.buscar_sinonimos_baseline_semeval_wordnet(palavra, pos_wn, fontes, multiword=False)
        elif metodo == 'topk_wordnet' and flag_wordnet:
            return self.buscar_topk_wordnet(palavra, pos_wn, fontes, multiword, topk)
        elif metodo == 'todos_wordnet' and flag_wordnet:
            return self.buscar_todos_significados_wordnet(palavra, pos_wn, fontes, multiword, 10000)
        elif metodo == 'buscar_sinonimos_principal_synset_wordnet' and flag_wordnet:
            return self.buscar_sinonimos_principal_synset_wordnet(palavra, pos_wn, fontes, multiword=False)
        elif metodo == 'desambiguador_wordnet_ontologia' and flag_wordnet:
            return self.desambiguador_wordnet.extrair_sinonimos(contexto, palavra, pos=pos_wn)
        # METODOS DO DICIONARIO DE OXFORD
        if metodo == 'simples_oxford' and flag_oxford:
            return self.desambiguador_oxford.metodos_baseline(contexto, palavra, pos=pos, limite=10000, usar_exemplos=False)
        elif metodo == 'topk_oxford' and flag_oxford:
            return self.desambiguador_oxford.metodos_baseline(contexto, palavra, pos=pos, limite=topk, usar_exemplos=False)
        elif metodo == 'todos_oxford' and flag_oxford:
            return self.desambiguador_oxford.metodos_baseline(contexto, palavra, pos=pos, limite=10000, usar_exemplos=False)
        elif metodo == 'buscar_sinonimos_principal_significado_oxford' and flag_oxford:
            return self.desambiguador_oxford.metodos_baseline(contexto, palavra, pos=pos, limite=1, usar_exemplos=False)
        elif metodo == 'desambiguador_oxford' and flag_oxford:
            return self.desambiguador_oxford.extrair_sinonimos(contexto, palavra, pos=pos, usar_exemplos=False)
        elif metodo == 'desambiguador_oxford_exemplos' and flag_oxford:
            return self.desambiguador_oxford.extrair_sinonimos(contexto, palavra, pos=pos, usar_exemplos=True)
        # METODOS DE DADOS UNIFICADOS
        elif metodo == 'desambiguador_unificado' and flag_unificado:
            return self.desambiguador_unificado.extrair_sinonimos(contexto, palavra, pos=pos, usar_exemplos=False)
        elif metodo == 'desambiguador_unificado_exemplos' and flag_unificado:
            return self.desambiguador_unificado.extrair_sinonimos(contexto, palavra, pos=pos, usar_exemplos=True)
        else: pass

        return []

    # obtem todos sinonimos de todos synsets da Wordnet
    def buscar_sinonimos_simples_wordnet(self, palavra, pos, fontes, multiword):
        sinonimos = []

        for s in wn.synsets(unicode(palavra), pos):
            for l in s.lemma_names():
                sinonimos.append(l)

        saida_sinonimos = []
        for s in set(sinonimos):
            if (not Utilitarios.multipalavra(s) and not multiword) or multiword:
                saida_sinonimos.append(s)

        return saida_sinonimos

    def buscar_todos_significados_wordnet(self, palavra, pos, fontes, multiword, topk):
        resultado = self.buscar_topk_wordnet(palavra, pos, fontes, multiword, 10000)

        if len(resultado) == 0:
            print((palavra, pos))
            raw_input('Resultado: ' + str(resultado))

        return resultado

    def buscar_sinonimos_desambiguacao(self, palavra, pos, ctxt, fontes, multiword):
        sinonimos = []
        synsets = wn.synsets(palavra, pos)

        significados = self.desambiguador_unificado.desambiguar(ctxt, palavra)
        significados = [res[0] for res in significados if res[1]]

        for s in significados:
            for l in s.lemma_names():
                if not l in sinonimos:
                    sinonimos.append(l)
                        
        return [s for s in sinonimos if (not Utilitarios.multipalavra(s) and not multiword) or multiword]

    def buscar_topk_wordnet(self, palavra, pos, fontes, multiword, topk):
        try:
            meu_set = set()
            for s in wn.synsets(palavra, pos)[:topk]:
                for l in s.lemma_names():
                    meu_set.add(l)
            return list(meu_set)
        except:
            traceback.print_stack()
            return []

    def buscar_sinonimos_principal_synset_wordnet(self, palavra, pos, fontes, multiword):
        resultado = wn.synsets(palavra, pos)[0].lemma_names()

        return Utilitarios.remover_multipalavras(resultado)

    def buscar_sinonimos_baseline_semeval_wordnet(self, palavra, pos, fontes, multiword):
        sinonimos_nivel1 = set()
        sinonimos_nivel2 = set()
        sinonimos_nivel3 = set()
        sinonimos_nivel4 = set()
        # Similar TOS
        sinonimos_nivel5 = set()
        # Todos os Lemas de todos Synsets
        sinonimos_nivel6 = set()

        palavra = unicode(palavra)

        synset = wn.synsets(palavra)[0]
        sinonimos_nivel1.update(synset.lemma_names())

        if synset.pos() in ['n', 'v'] or True:
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

        if synset.pos() in ['n', 'v'] or True:
            if wn.synsets(palavra).__len__() > 1:
                for s in wn.synsets(palavra[1:]):
                    for h in s.hypernyms(): sinonimos_nivel4.update(s.lemma_names())
        else:
            if wn.synsets(palavra).__len__() > 1:
                for s in wn.synsets(palavra[1:]):
                    for p in synset.part_meronyms():
                        for h in p.hypernyms():
                            sinonimos_nivel4.update(h.lemma_names())
                    for p in synset.part_holonyms():
                        for h in p.hypernyms():
                            sinonimos_nivel4.update(h.lemma_names())
                    for m in synset.member_meronyms():
                        for m in p.hypernyms():
                            sinonimos_nivel4.update(m.lemma_names())
                    for m in synset.member_holonyms():
                        for m in p.hypernyms():
                            sinonimos_nivel4.update(m.lemma_names())
                    
        for todos_synsets in wn.synsets(palavra, pos):
            for similar in todos_synsets.similar_tos():
                sinonimos_nivel5.update(similar.lemma_names())

        sinonimos_nivel2 = Utilitarios.remover_multipalavras(list(sinonimos_nivel2))
        sinonimos_nivel3 = Utilitarios.remover_multipalavras(list(sinonimos_nivel3))
        sinonimos_nivel4 = Utilitarios.remover_multipalavras(list(sinonimos_nivel4))
        sinonimos_nivel5 = Utilitarios.remover_multipalavras(list(sinonimos_nivel5))

        todos_resultados = [sinonimos_nivel2, sinonimos_nivel3, sinonimos_nivel4, sinonimos_nivel5]
        todos_resultados = list(itertools.chain(*todos_resultados))

        if todos_resultados.__len__() == 0:
            for synset in wn.synsets(palavra, pos):
                sinonimos_nivel6.update(synset.lemma_names())
            todos_resultados.append(Utilitarios.remover_multipalavras(list(sinonimos_nivel6)))
            todos_resultados = list(itertools.chain(*todos_resultados))

        resultado_final = []

        if todos_resultados.__len__() == 0:
            for synset in wn.synsets(palavra, pos):
                    sinonimos_nivel6.update(synset.lemma_names())

        for e in todos_resultados:
            if not e in resultado_final:
                resultado_final.append(e)

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