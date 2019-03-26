# -*- coding: utf-8 -*-
import gc
import itertools
import json
import math
import os
import statistics
import sys
import traceback
from collections import Counter
from fractions import Fraction as F
from string import punctuation

import nltk
import textblob
from nltk.corpus import wordnet
from pywsd.lesk import cosine_lesk

import CasadorManual
from Arvore import Arvore, No
from CasadorManual import CasadorManual
from DesambiguadorWordnet import DesWordnet
from DesOx import DesOx
from ExtratorWikipedia import ExtratorWikipedia
from Indexador import Whoosh
from OxAPI import BaseOx
from RepresentacaoVetorial import RepVetorial
from Utilitarios import Util

wn = wordnet


class Alvaro(object):
    INSTANCE = None
    OBJETO_NGRAMS = {}

    PONDERACAO_DEFINICOES = None

    NGRAMS_COCA = {}
    NGRAMS_SIGNALMEDIA = {}
    NGRAMS_LEIPZIG = {}

    # Este objeto armazena quais palavras do
    # dicionario de Oxford teve seus exemplos indexados também
    PALAVRAS_EXEMPLOS_INDEXADOS = None

    # Frequencia palavras
    FREQUENCIA_PMI = {}

    # "nome#pos" : relacao
    RELACAO_SINONIMIA = {}

    # Wikipedia
    FRASES_WIKIPEDIA = None
    INDEXES_WIKIPEDIA = None

    def __init__(self, configs, base_ox, casador_manual, rep_vetorial):
        self.cfgs = configs
        self.base_ox = base_ox
        self.casador_manual = casador_manual
        self.rep_vetorial = rep_vetorial

    # Dada uma definicao para um determinado lema e definicao e deriva sinonimos p/ determinada definicao
    @staticmethod
    def gerar_palavras_relacionadas(lema, pos, definicao):
        tokens_tagueados = nltk.pos_tag(nltk.word_tokenize(definicao))
        tokens = [t for t, tag in tokens_tagueados if tag[0] in ["N", "J", "V"]]
        tokens += [lema]

        inst = RepVetorial.INSTANCE
        palavras_relacionadas = RepVetorial.obter_palavras_relacionadas
        palavras_derivadas = palavras_relacionadas(
            inst, positivos=tokens, pos=pos, topn=200)

        return palavras_derivadas

    @staticmethod
    def contexto_comum_definicao(lema, pos, definicao):
        tokens_tagueados = nltk.pos_tag(nltk.word_tokenize(definicao))
        tokens = [t for t, tag in tokens_tagueados if tag[0] in ["N", "J", "V"]]
        tokens += [lema]

        inst = RepVetorial.INSTANCE
        palavras_relacionadas = RepVetorial.obter_palavras_relacionadas

        try:
            interseccao_palavras = palavras_relacionadas(
                inst, positivos=[tokens[0]], pos=pos, topn=200)
            interseccao_palavras = [p for p, s in interseccao_palavras]
        except:
            return set()

        for t in tokens[1:]:
            try:
                palavras = palavras_relacionadas(
                    inst, positivos=[t], pos=pos, topn=200)
                palavras = [p for p, s in palavras]
                interseccao_palavras = set(
                    interseccao_palavras) & set(palavras)

                if not interseccao_palavras:
                    return interseccao_palavras

            except:
                return set()

        return interseccao_palavras

    def construir_arvores_definicoes(self, lema, pos, max_prof, cands):
        seps = ":::"
        arvores = []

        prof = 1

        for def_polissemia in BaseOx.obter_definicoes(self.base_ox, lema, pos):
            mxsdef = self.cfgs['alvaro']['mxspdef_wn']

            sins = BaseOx.obter_sins(
                self.base_ox, lema, def_polissemia, pos=pos)
            sins = [s for s in sins if not Util.e_mpalavra(s)][:mxsdef]

            if cands in [None, []]:
                flag_cand = True
                cands = []
            else:
                flag_cand = False

            if set(sins).intersection(set(cands)) or flag_cand:
                label = "%s%s%s" % (lema, seps, def_polissemia)
                nodo_nivel1 = self.adicionar_nivel_arvore(
                    label, No(None, label), pos, prof + 1, max_prof, cands)
                arvores.append(Arvore(nodo_nivel1))

        return arvores

    """
    Recebe uma arvore e gera todos caminhos que nao
    representam ciclo retornam conjunto de todos os caminhos possíveis
    """
    @staticmethod
    def construir_caminho_arvore(self, arvores, cands):
        caminhos_arvore = []

        for arvore_sinonimia in arvores:
            for caminho in arvore_sinonimia.percorrer():
                try:
                    cam_tmp = [tuple(reg.split(':::'))
                               for reg in caminho.split("/")]
                    cam_tmp = [
                        p for (p, def_p) in cam_tmp if p in cands or cands == []]
                    conts_corretos = [1 for i in range(
                        len(Counter(cam_tmp).values()))]
                    # Se todas palavras só ocorrem uma vez, entao nao existe ciclos
                    if Counter(cam_tmp).values() == conts_corretos:
                        if not caminho in caminhos_arvore:
                            caminhos_arvore.append(caminho)
                except ValueError, ve:
                    pass

        return caminhos_arvore

    def adicionar_nivel_arvore(self, label, nodo_pai, pos, prof, max_prof, cands):
        flag_cand = cands in [None, []]
        seps = ":::"

        # Se for menor que a profundidade maxima permitida
        if prof <= max_prof:
            lema, definicao = tuple(label.split(seps))
            for sin in BaseOx.obter_sins(self.base_ox, lema, definicao, pos=pos):
                if sin in cands or flag_cand:
                    for def_polissemia in BaseOx.obter_definicoes(self.base_ox, sin, pos=pos):
                        label = "%s%s%s" % (sin, seps, def_polissemia)
                        nodo_pai.add_filho(self.adicionar_nivel_arvore(label,
                                                                       No(nodo_pai, label), pos, prof+1, max_prof, cands))

        # Pai nao tera filhos, caso base
        return nodo_pai

    def construir_relacao_definicoes(self, palavra, pos, fontes='oxford', indice=1000):
        cfgs = self.cfgs

        resultado = {}

        dir_cache_rel_sinonimia = cfgs['caminho_bases'] + \
            '/'+cfgs['oxford']['cache']['sinonimia']

        kcache_relacao_sin = "%s-%s.json" % (palavra, pos)
        dir_obj = dir_cache_rel_sinonimia+'/'+kcache_relacao_sin

        if fontes == 'oxford':
            definicoes_palavra = BaseOx.obter_definicoes(
                BaseOx.INSTANCE, palavra, pos)
            for def_polis in definicoes_palavra[:indice]:
                resultado[def_polis] = {}
                for sin in BaseOx.obter_sins(BaseOx.INSTANCE, palavra, def_polis):
                    resultado[def_polis][sin] = BaseOx.obter_definicoes(
                        BaseOx.INSTANCE, sin, pos)
                    if resultado[def_polis][sin] == None:
                        resultado[d] = []
            return resultado
        else:
            raise Exception('Este tipo de fonte nao foi implementada!')

    def pontuar_relacaosinonimia_wmd(self, palavra, pos, todos_caminhos):
        if Alvaro.PONDERACAO_DEFINICOES == None:
            Alvaro.PONDERACAO_DEFINICOES = Alvaro.carregar_base_ponderacao_definicoes()

        caminhos_ponderados = {}

        for caminho_iter in todos_caminhos:
            caminho_tokenizado = caminho_iter.split("/")

            if not caminho_iter in caminhos_ponderados:
                caminhos_ponderados[caminho_iter] = []

            for aresta_iter in itertools.product(caminho_tokenizado, caminho_tokenizado):
                aresta = list(aresta_iter)
                aresta.sort()
                aresta = tuple(aresta)

                ini, fim = aresta

                def1 = ini.split(":::")[1]
                def2 = fim.split(":::")[1]
                pont_wmd = None

                if ini != fim and not str(aresta) in Alvaro.PONDERACAO_DEFINICOES:
                    pont_wmd = RepVetorial.word_move_distance(
                        RepVetorial.INSTANCE, def1, def2)
                    Alvaro.PONDERACAO_DEFINICOES[str(aresta)] = pont_wmd
                    caminhos_ponderados[caminho_iter].append(
                        (aresta, pont_wmd))

        return caminhos_ponderados

    def pontuar_relacaosinonimia_exemplos(self, palavra, pos, todos_caminhos):
        wmd = RepVetorial.word_move_distance

        for caminho_iter in todos_caminhos:
            caminho_tokenizado = caminho_iter.split("/")
            for aresta_iter in itertools.product(caminho_tokenizado, caminho_tokenizado):
                aresta = list(aresta_iter)
                aresta.sort()
                aresta = tuple(aresta)

                ini, fim = aresta

                lema1, def1 = ini.split(":::")
                lema2, def2 = fim.split(":::")

                chave = tuple(sorted((ini, fim), reverse=False))

                if not str(chave) in Alvaro.PONDERACAO_DEFINICOES:
                    if def1 != def2:
                        sins_lema1 = BaseOx.obter_sins(
                            BaseOx.INSTANCE, lema1, def1, pos=pos)
                        sins_lema2 = BaseOx.obter_sins(
                            BaseOx.INSTANCE, lema2, def2, pos=pos)

                        if lema1 in sins_lema1:
                            sins_lema1.remove(lema1)
                        if lema2 in sins_lema2:
                            sins_lema2.remove(lema2)

                        for sin_iter1 in sins_lema1:
                            for ex_iter in BaseOx.obter_atributo(BaseOx.INSTANCE, lema2, pos, def2, 'exemplos'):
                                if lema2 in ex_iter:
                                    ex_def2 = ex_iter.replace(lema2, sin_iter1)
                                    sc_wmd = wmd(
                                        RepVetorial.INSTANCE, ex_iter, ex_def2)
                                    # lema, def, pos, sin, lema, def, pos, ex
                                    padrao_cmd = "%s@@@@%s@@@@%s@@@@@%s@@@@%s@@@@%s@@@@%s@@@@%f"
                                    padrao_cmd = padrao_cmd % (
                                        lema1, def1, pos, sin_iter1, lema2, def2, ex_def2, sc_wmd)
                                    os.system(
                                        'echo \"%s\" >> ../Bases/linhas.txt' % padrao_cmd)

                        for sin_iter2 in sins_lema2:
                            for ex_iter in BaseOx.obter_atributo(BaseOx.INSTANCE, lema1, pos, def1, 'exemplos'):
                                if lema1 in ex_iter:
                                    ex_def1 = ex_iter.replace(lema1, sin_iter2)
                                    sc_wmd = wmd(
                                        RepVetorial.INSTANCE, ex_iter, ex_def1)
                                    # lema, def, pos, sin, lema, def, pos, ex
                                    padrao_cmd = "%s@@@@%s@@@@%s@@@@@%s@@@@%s@@@@%s@@@@%s@@@@%f"
                                    padrao_cmd = padrao_cmd % (
                                        lema2, def2, pos, sin_iter2, lema1, def1, ex_def1, sc_wmd)
                                    os.system(
                                        'echo \"%s\" >> ../Bases/linhas.txt' % padrao_cmd)

                        sc = None

                    Alvaro.PONDERACAO_DEFINICOES[str(chave)] = 1

        return None

    # Obtem a palavra mais usual para o significado mais usual para uma palavra
    def sugestao_contigencial(self, palavra,
                              pos, fontes_def='oxford',
                              metodo='definicao_usual',
                              ctx=None, med_sim='cosine'):

        if metodo == 'definicao_usual':
            if pos == 'r':
                sins = wn.synsets(palavra, pos)[0].lemma_names()
                try:
                    sins.remove(palavra)
                except:
                    pass
                return sins

            if fontes_def == 'wordnet':
                for syn in wn.synsets(palavra, pos):
                    for lema in syn.lemma_names():
                        if not Util.e_mpalavra(lema) and lema != palavra:
                            return [lema]
            elif fontes_def == 'oxford':
                try:
                    pos_ox = Util.cvsr_pos_semeval_ox(pos)
                    todas_definicoes = BaseOx.obter_definicoes(palavra, pos_ox)
                    def_prin = todas_definicoes[0]
                    sins = BaseOx.obter_sins(palavra, def_prin)
                    return sins
                except Exception, e:
                    print(e)
                    pass
        elif metodo == 'desambiguador':
            if fontes_def == 'wordnet':
                raise("\n\nFuncao nao implementada!\n\n")
            elif fontes_def == 'oxford':
                des_ox = DesOx(self.cfgs, self.base_ox,
                               rep_vetorial=self.rep_vetorial)
                try:
                    label, definicao, exemplos = DesOx.desambiguar(
                        des_ox, ctx, palavra, pos, nbest=True, med_sim=med_sim)[0][0]
                    sins_preditos = BaseOx.obter_sins(palavra, definicao, pos)
                    return sins_preditos
                except Exception, e:
                    pass
        else:
            raise("\nOpcao invalida para o metodo de SUGESTAO CONTIGENCIAL!\n")

        return [""]

    # Gabarito no formato [[palavra, voto], ...]
    def possui_moda(self, gabarito):
        todos_votos = sorted([v[1] for v in gabarito], reverse=True)

        try:
            return todos_votos[0] > todos_votos[1]
        except IndexError:
            return True

        return False

    """
    Recebe uma lista de pares <palavra, definicao> e
    retorna sinonimos para cada par. Vale lembrar: sinonimos
    compartilhados entre os pares nao sao permitidos no
    conjunto-resposta. O intuito é fazer da lista de sinônimos
    um importante fator discriminante entre "sinonimos de 1a ordem".
    """
    @staticmethod
    def obter_sinonimos_filtrados(lista_definicoes, pos, remover_sinonimos_replicados=True):
        conjunto_universo_sinonimos = {}

        # Estrutura com pares <(palavra, definicao>: sinonimo)>
        definicoes_sinonimos = {}

        for palavra, definicao in lista_definicoes:
            lista_sinonimos = BaseOx.obter_sins(
                BaseOx.INSTANCE, palavra, definicao, pos, remover_sinonimos_replicados=True)

            for s in lista_sinonimos:
                if not s in conjunto_universo_sinonimos:
                    conjunto_universo_sinonimos[s] = []
                conjunto_universo_sinonimos[s].append(
                    str((palavra, definicao)))
            definicoes_sinonimos[str((palavra, definicao))] = []

        for palavra, definicao in lista_definicoes:
            lista_sinonimos = BaseOx.obter_sins(
                BaseOx.INSTANCE, palavra, definicao, pos, remover_sinonimos_replicados=True)
            for s in lista_sinonimos:
                # Se Sinonimo esta vinculado a somente um par <palavra, definicao>
                if conjunto_universo_sinonimos[s].__len__() == 1:
                    definicoes_sinonimos[str((palavra, definicao))].append(s)

        return definicoes_sinonimos

    @staticmethod
    def gerar_ngrams_exemplos(candidato, pos):
        for def_iter in BaseOx.obter_definicoes(BaseOx.INSTANCE, candidato, pos=pos):
            for ex in BaseOx.obter_atributo(BaseOx.INSTANCE, candidato, pos, def_iter, 'exemplos'):
                ex_blob = textblob.TextBlob(ex)

                for ng in ex_blob.ngrams(n=Util.CONFIGS['ngram']['max']):
                    ng_str = " ".join(ng)
                    #ng_tags = str(nltk.pos_tag(nltk.word_tokenize(ng_str)))

                    chave_reg = "%s:::%s" % (candidato, def_iter)

                    if not chave_reg in Alvaro.INDEXES_REGID:
                        Alvaro.INDEXES_REGID[chave_reg] = len(
                            Alvaro.INDEXES_REGID)
                        Alvaro.INDEXES_IDREG[len(
                            Alvaro.INDEXES_REGID)-1] = chave_reg

                    if not ng_str in Alvaro.NGRAMS_EXOX_PLAIN:
                        Alvaro.NGRAMS_EXOX_PLAIN[ng_str] = set(
                            [Alvaro.INDEXES_REGID[chave_reg]])
                    else:
                        Alvaro.NGRAMS_EXOX_PLAIN[ng_str].add(
                            Alvaro.INDEXES_REGID[chave_reg])

                ex_blob = None

    @staticmethod
    def indexar_exemplos(cand_iter, pos, fonte='oxford'):
        from Indexador import Whoosh

        singleton = BaseOx.INSTANCE

        if not cand_iter in Alvaro.PALAVRAS_EXEMPLOS_INDEXADOS:
            documentos = []

            for def_iter in BaseOx.obter_definicoes(BaseOx.INSTANCE, cand_iter, pos):
                titulo = cand_iter + ":::" + def_iter
                dir_doc = "%s-%s.json" % (cand_iter, pos)

                exemplos = BaseOx.obter_atributo(
                    singleton, cand_iter, pos, def_iter, 'exemplos')
                exemplos = ":::".join(exemplos)

                documentos.append((titulo, dir_doc, exemplos))

            Whoosh.iniciar_indexacao_exemplos(documentos)
            Alvaro.PALAVRAS_EXEMPLOS_INDEXADOS.add(cand_iter)

    def selec_ngrams(self, palavra, frase, cands):
        cfgs = self.cfgs
        min_ngram = cfgs['ngram']['min']
        max_ngram = cfgs['ngram']['max']

        pont_ngram = dict([(p, 0.00) for p in cands])

        ngrams_coca = Alvaro.NGRAMS_COCA
        ngrams_signalmedia = Alvaro.NGRAMS_SIGNALMEDIA

        for cand_iter in cands:
            nova_frase = frase.replace(palavra, cand_iter)
            ngrams_derivados_frase = Alvaro.gerar_ngrams_tagueados(
                nova_frase, min_ngram,
                max_ngram, cand_iter)

            ngrams_leipzig = {}

            # Carregando N-grams de Leipzig e derivando N-grams para N = 2, 3, 4 e 5
            if True:
                if "leipzig" in self.cfgs['ngram']['fontes']:
                    ngrams_leipzig = Alvaro.carregar_ngrams_leipzig(
                        palavra, cand_iter)
                    # derivando demais n-grams
                    dir_ngrams_derivados = cfgs['ngram']['dir_derivado'] % cand_iter

                    if os.path.exists(dir_ngrams_derivados) == False:
                        min_ng, max_ng = cfgs['ngram']['min'], cfgs['ngram']['max']
                        ngrams_derivados_leipzig = Alvaro.derivar_ngrams(
                            ngrams_leipzig, min_ng, max_ng)
                        Util.salvar_json(dir_ngrams_derivados,
                                         ngrams_derivados_leipzig)
                    else:
                        ngrams_derivados_leipzig = Util.abrir_json(
                            dir_ngrams_derivados)

                    for ng_str in ngrams_derivados_leipzig:
                        ngrams_leipzig[ng_str] = ngrams_derivados_leipzig[ng_str]

                    ngrams_derivados_leipzig = None

            for __ng_iter__ in ngrams_derivados_frase:
                ng_iter = [(unicode(p), pt) for (p, pt) in __ng_iter__]
                ng_iter_sm = " ".join([p for (p, pt) in __ng_iter__])

                freq_ngram = 0
                nova_pont = 0

                corpus_ngrams = {
                    "coca": {"ngrams": ngrams_coca, "ng_chave": unicode(ng_iter)},
                    "leipzig": {"ngrams": ngrams_leipzig, "ng_chave": unicode(__ng_iter__)},
                    "signalmedia": {"ngrams": ngrams_signalmedia, "ng_chave": unicode(ng_iter_sm)}
                }

                for nome_corpus in set(corpus_ngrams.keys()) & set(self.cfgs['ngram']['fontes']):
                    ngrams = corpus_ngrams[nome_corpus]['ngrams']
                    ng_chave = corpus_ngrams[nome_corpus]['ng_chave']

                    if ng_chave in ngrams:
                        freq_ngram = int(ngrams[ng_chave])
                        nova_pont = Alvaro.pont_colocacao(
                            freq_ngram, len(__ng_iter__), max_ngram)
                        pont_ngram[cand_iter] += nova_pont

            ngrams_leipzig = None
            ngrams_derivados_frase = None

        top_ngrams = [(p, pont_ngram[p]) for p in cands]

        return top_ngrams

    @staticmethod
    def derivar_ngrams(ngrams, _min_, _max_):
        novos_ngrams = {}
        for ng_str in ngrams:
            try:
                ng = eval(ng_str)
                for n in range(_min_, _max_):
                    for i in range(_max_-n):
                        try:
                            novo_ng = str(ng[i:i+n])
                            if not novo_ng in novos_ngrams:
                                novos_ngrams[novo_ng] = ngrams[ng_str]
                            else:
                                novos_ngrams[novo_ng] += ngrams[ng_str]
                        except:
                            pass
            except Exception, e:
                print("\nErro para ngram: %s\n" % str(ng))
                print(e)
        return novos_ngrams

    @staticmethod
    def derivar_ngrams_string(ngrams, _min_, _max_):
        novos_ngrams = {}
        for ng_str in ngrams:
            try:
                ng = ng_str.split(" ")
                for n in range(_min_, _max_):
                    for i in range(_max_-n):
                        try:
                            novo_ng = " ".join(ng[i:i+n])
                            if not novo_ng in novos_ngrams:
                                novos_ngrams[novo_ng] = ngrams[ng_str]
                            else:
                                novos_ngrams[novo_ng] += ngrams[ng_str]
                        except:
                            pass
            except Exception, e:
                print("\nErro para ngram: %s\n" % str(ng))
                print(e)
        return novos_ngrams

    def selec_candidatos(self, palavra, pos, fontes=['wordnet'], indice_definicao=-1):
        maxpordef_wn = Util.CONFIGS['alvaro']['mxspdef_wn']
        maxpordef_ox = Util.CONFIGS['alvaro']['mxspdef_ox']

        candidatos_best = set()
        candidatos_oot = set()

        comprimento = None

        if fontes in [[], None]:
            raise Exception("Fontes nao foram informadas!")
        if indice_definicao != -1 and fontes != ['oxford']:
            msg = "\nVoce nao pode selecionar um unico indice para mais de duas fontes! "
            msg += "O casamento de definicoes nao existe implementado!\n"
            raise Exception(msg)

        if 'wordnet' in fontes:
            for s in wn.synsets(palavra, pos):
                for l in list(set(s.lemma_names()) - set(candidatos_oot))[:maxpordef_wn]:
                    candidatos_oot.update([l])
                    candidatos_best.update([l])

                try:
                    if pos in ['n']:
                        for h in s.hypernyms():
                            candidatos_oot.update(
                                h.lemma_names()[:maxpordef_wn])
                        for h in s.hyponyms():
                            candidatos_oot.update(
                                h.lemma_names()[:maxpordef_wn])
                    elif pos in ['a', 'r', 'v']:
                        for similar in s.similar_tos():
                            candidatos_oot.update(
                                similar.lemma_names()[:maxpordef_wn])
                except Exception, e:
                    pass

        if 'oxford' in fontes:
            todas_definicoes = BaseOx.obter_definicoes(
                BaseOx.INSTANCE, palavra, pos)
            for definicao in todas_definicoes:
                try:
                    cands_iter = []
                    todos_sinonimos = BaseOx.obter_sins(
                        BaseOx.INSTANCE, palavra, definicao, pos)

                    for c in todos_sinonimos:
                        if not c in cands_iter and len(cands_iter) < maxpordef_ox:
                            cands_iter.append(c)
                    candidatos_tmp = cands_iter
                    #candidatos_tmp = BaseOx.obter_sins(BaseOx.INSTANCE, palavra, definicao, pos)[:maxpordef_ox]
                except:
                    candidatos_tmp = []

                candidatos_best.update(
                    [] if candidatos_tmp == None else candidatos_tmp)
                candidatos_oot.update(
                    [] if candidatos_tmp == None else candidatos_tmp)

        comprimento = len(candidatos_oot)

        if set(['wordembbedings', 'embbedings']).intersection(set(fontes)):
            obter_palavras_relacionadas = self.rep_vetorial.obter_palavras_relacionadas
            ptmp = [p[0] for p in obter_palavras_relacionadas(positivos=[palavra],
                                                              pos=pos, topn=comprimento)]
            candidatos_oot.update(ptmp)

        if palavra in candidatos_oot:
            candidatos_oot.remove(palavra)

        cands = [p for p in list(candidatos_oot) if len(p) > 1]
        cands = [p for p in cands if p.istitle() == False]
        cands = [p for p in cands if not Util.e_mpalavra(p)]

        retorno = {}

        retorno['uniao'] = list(candidatos_best.union(candidatos_oot))
        retorno['best'] = candidatos_best
        retorno['oot'] = candidatos_oot

        return retorno

    # Retirado de https://stevenloria.com/tf-idf/

    @staticmethod
    def tf(word, text_blob):
        return float(text_blob.words.count(word))
        # return float(blob.words.count(word)) / float(len(blob.words))

    @staticmethod
    def n_containing(word, bloblist):
        return sum(1 for blob in bloblist if word in blob.words)

    @staticmethod
    def idf(word, bloblist):
        # return math.log(len(bloblist) / len((1 + self.n_containing(word, bloblist))))
        x = Alvaro.n_containing(word, bloblist)
        return math.log(len(bloblist) / (x if x else 1))

    @staticmethod
    def tfidf(word, blob, bloblist):
        return Alvaro.tf(word, blob) * Alvaro.idf(word, bloblist)

    # https://corpus.byu.edu/mutualInformation.asp
    # https://corpustools.readthedocs.io/en/latest/mutual_information.html
    # https://stackoverflow.com/questions/13488817/pointwise-mutual-information-on-text
    # https://medium.com/@nicharuch/collocations-identifying-phrases-that-act-like-individual-words-in-nlp-f58a93a2f84a
    @staticmethod
    def pontuar_pmi(freq_x, freq_y, freq_xy, indexes):
        searcher = Whoosh.searcher(Whoosh.DIR_INDEXES)

        total_sentencas = searcher.doc_count()

        px = float(freq_x) / total_sentencas
        py = float(freq_y) / total_sentencas
        pxy = float(freq_xy) / total_sentencas

        return math.log(pxy / (px * py), 2)

    @staticmethod
    def abrir_contadores_pmi():
        cfgs = Util.CONFIGS
        try:
            Alvaro.FREQUENCIA_PMI = Util.abrir_json(
                cfgs['metodo_pmi']['dir_contadores'], criarsenaoexiste=False)
            return Alvaro.FREQUENCIA_PMI != None
        except:
            return False

    @staticmethod
    def salvar_contadores_pmi():
        cfgs = Util.CONFIGS
        if Alvaro.FREQUENCIA_PMI != None:
            Util.salvar_json(cfgs['metodo_pmi']
                             ['usar_metodo'], Alvaro.FREQUENCIA_PMI)
            Alvaro.FREQUENCIA_PMI = None
            return True
        else:
            return False

    @staticmethod
    def gerar_ngrams_tagueados(sentenca, _min_, _max_, palavra_central=None):
        ngrams_dict = {}
        tokens_tagueados = nltk.pos_tag(nltk.word_tokenize(sentenca))

        for n in range(_min_, _max_+1):
            ngrams_dict[n] = []

        for n in range(_min_, _max_+1):
            for i in range(0, len(tokens_tagueados)-n):
                if i+n < len(tokens_tagueados):
                    novo_ngram = tokens_tagueados[i:i+n]

                    if palavra_central in [t for (t, pt) in novo_ngram] or palavra_central == None:
                        novo_ngram = [(t, pt) for (t, pt)
                                      in novo_ngram if not t in punctuation]
                        if palavra_central in [t for (t, pt) in novo_ngram] or palavra_central == None:
                            try:
                                if not novo_ngram in ngrams_dict[len(novo_ngram)]:
                                    ngrams_dict[len(novo_ngram)].append(
                                        novo_ngram)
                            except:
                                pass

        ngrams = []

        for n in sorted(ngrams_dict.keys(), reverse=True):
            ngrams += ngrams_dict[n]

        return ngrams

    @staticmethod
    def carregar_coca_ngrams(diretorio):
        min_ngram = Util.CONFIGS['ngram']['min']
        max_ngram = Util.CONFIGS['ngram']['max']

        arquivo_ngrams = open(diretorio, 'r')
        todas_linhas = arquivo_ngrams.readlines()
        arquivo_ngrams.close()

        todos_ngrams_tuplas = {}  # <ngram : count>

        for linha_iter in todas_linhas:
            colunas = str(linha_iter).lower().split("\t")
            freq, tokens = int(colunas[0]), "\t".join(colunas[1:])

            ngrams = Alvaro.gerar_ngrams_tagueados(
                tokens, min_ngram, max_ngram)

            for ng in ngrams:
                if not str(ng) in todos_ngrams_tuplas:
                    todos_ngrams_tuplas[str(ng)] = int(freq)
                else:
                    todos_ngrams_tuplas[str(ng)] += int(freq)

        return todos_ngrams_tuplas

    @staticmethod
    def pont_colocacao(freq, len_sintagma, max_sintagma):
        return freq * (len_sintagma ** 3)

    # https://stackoverflow.com/questions/24192979/
    @staticmethod
    def obter_antonimos(palavra, pos):
        if not pos in ['a', 's']:
            return []

        anto = []
        for s in wn.synsets(palavra, pos):
            for l in s.lemmas():
                for a in l.antonyms():
                    if not a.name() in anto:
                        anto.append(a.name())
        return anto

    @staticmethod
    def carregar_ngrams_leipzig(palavra, substituto):
        if substituto in Util.CONFIGS["ngram"]["blacklist"]:
            return {}

        dir_conts_ngrams_leipzig = Util.CONFIGS['ngram']['leipzig_conts'] % substituto

        if os.path.exists(dir_conts_ngrams_leipzig) == True:
            return Util.abrir_json(dir_conts_ngrams_leipzig)

        dict_freq_ngrams = {}

        print("\nExtraindo do corpus sentencas para '%s'" % substituto)
        try:
            obj = Alvaro.gerar_ngrams_leipzig([substituto])
        except:
            obj = []
        print("Sentencas extraidas!")

        print("Contabilizando n-grams!")

        for reg in obj:
            ng_str = str(nltk.pos_tag(nltk.word_tokenize(" ".join(reg))))
            if not ng_str in dict_freq_ngrams:
                dict_freq_ngrams[ng_str] = 1
            else:
                dict_freq_ngrams[ng_str] += 1

        print("n-grams contabilizados!")
        print("\n")

        obj = None
        arq = None

        Util.salvar_json(dir_conts_ngrams_leipzig, dict_freq_ngrams)

        return dict_freq_ngrams

    @staticmethod
    def gerar_ngrams_leipzig(lista_palavras, postags=False):
        if type(lista_palavras) != list:
            raise Exception("Tipo errado!")

        system = os.system

        file_ngrams_tmp = '../Bases/ngrams.tmp'
        diretorio_leipzig_txt = "~/Bases/Corpora/Leipzig/*"

        if os.path.exists(file_ngrams_tmp) == True:
            system('rm '+file_ngrams_tmp)

        filtro = "".join(' | grep "%s"' % p for p in lista_palavras)
        comando_filtro = 'cat %s %s >> %s' % (
            diretorio_leipzig_txt, filtro, file_ngrams_tmp)

        os.system(comando_filtro)
        print(comando_filtro)

        cont_linhas = 0
        with open(file_ngrams_tmp, 'r') as saida_grep:
            for linha_iter in saida_grep:
                cont_linhas += 1

        if cont_linhas > 30000:
            raise Exception("Arquivo de n-grams grande!")

        resultado = []

        with open(file_ngrams_tmp, 'r') as saida_grep:
            for linha_iter in saida_grep:
                saida_blob = textblob.TextBlob(
                    Util.completa_normalizacao(linha_iter))
                ngrams_linha = saida_blob.ngrams(
                    n=Util.CONFIGS['ngram']['max'])

                for ng in ngrams_linha:
                    if len(set(lista_palavras) & set(ng)) == len(lista_palavras):
                        if postags == False:
                            resultado.append(ng)
                        else:
                            resultado.append(nltk.pos_tag(ng))

                saida_blob = None
                ngrams_linha = None

        if os.path.exists(file_ngrams_tmp) == True:
            os.system('rm ' + file_ngrams_tmp)

        return resultado

    @staticmethod
    def carregar_base_ponderacao_definicoes():
        import json

        dir_arq = "../Bases/ponderacao_definicoes.json"
        if os.path.exists(dir_arq) == True:
            Alvaro.PONDERACAO_DEFINICOES = Util.abrir_json(dir_arq)
        else:
            Alvaro.PONDERACAO_DEFINICOES = {}

        return Alvaro.PONDERACAO_DEFINICOES

    @staticmethod
    def salvar_base_ponderacao_definicoes():
        dir_arq = "../Bases/ponderacao_definicoes.json"
        if Alvaro.PONDERACAO_DEFINICOES != None:
            Util.salvar_json(dir_arq, Alvaro.PONDERACAO_DEFINICOES)

    """
    Gera tokens de correlacao entre palavras da frase e sinonimos-candidatos
    """
    @staticmethod
    def gerar_pares_pmi(palavra, frase, cands):
        pos_uteis_frase = ['N', 'V']

        tokens_tagueados = nltk.pos_tag(nltk.word_tokenize(frase.lower()))
        tokens_frase = [r[0] for r in tokens_tagueados if r[1]
                        [0] in pos_uteis_frase and r[0] != palavra]

        if palavra in tokens_frase:
            tokens_frase.remove(palavra)

        for t in list(tokens_frase):
            if Util.singularize(t) != t:
                tokens_frase.append(Util.singularize(t))

        # Gerando pares de correlação
        pares = list(set(list(itertools.product(*[tokens_frase, cands]))))

        return [reg for reg in pares if len(reg[0]) > 1 and len(reg[1]) > 1]

    @staticmethod
    def pontuar_frase_correlacao_pmi(pares_frase, pos, palavra=None, frase=None):
        deletar_docs_duplicados = Util.CONFIGS['corpora']['deletar_docs_duplicados']
        verbose_pmi = Util.CONFIGS['metodo_pmi']['verbose']
        pontuacao_definicoes = {}

        for par in pares_frase:
            token_frase, cand_par = par
            indexes_ex = Whoosh.DIR_INDEXES_EXEMPLOS

            obter_docs = Whoosh.consultar_documentos

            if Util.singularize(token_frase) != Util.singularize(cand_par):
                # Pesquisa
                if not str(par) in Alvaro.FREQUENCIA_PMI:
                    docs_corpora = obter_docs(
                        list(par), operador="AND", dir_indexes=Whoosh.DIR_INDEXES)
                    Alvaro.FREQUENCIA_PMI[str(par)] = len(docs_corpora)
                    frequencia_par = len(docs_corpora)
                    docs_corpora = None
                else:
                    frequencia_par = Alvaro.FREQUENCIA_PMI[str(par)]

                # Se o par ocorre no minimo uma vez...
                if frequencia_par > 0:
                    token_frase, cand_par = par

                    if cand_par in Alvaro.FREQUENCIA_PMI:
                        if Alvaro.FREQUENCIA_PMI[cand_par] == 0:
                            del Alvaro.FREQUENCIA_PMI[cand_par]

                    if token_frase in Alvaro.FREQUENCIA_PMI:
                        if Alvaro.FREQUENCIA_PMI[token_frase] == 0:
                            del Alvaro.FREQUENCIA_PMI[token_frase]

                    if not token_frase in Alvaro.FREQUENCIA_PMI:
                        Alvaro.FREQUENCIA_PMI[token_frase] = Whoosh.count(
                            token_frase, Whoosh.DIR_INDEXES)

                    if not cand_par in Alvaro.FREQUENCIA_PMI:
                        Alvaro.FREQUENCIA_PMI[cand_par] = Whoosh.count(
                            cand_par, Whoosh.DIR_INDEXES)

                    try:
                        min_par = min(
                            Alvaro.FREQUENCIA_PMI[cand_par], Alvaro.FREQUENCIA_PMI[token_frase])
                        percentagem_par = float(frequencia_par)/float(min_par)
                    except:
                        percentagem_par = 0.00

                    if verbose_pmi:
                        print("\n")
                        print("Par: " + str(par))
                        print("Frequencia no corpus de '%s': %d" % (
                            token_frase, Alvaro.FREQUENCIA_PMI[token_frase]))
                        print("Frequencia no corpus de '%s': %d" % (
                            cand_par, Alvaro.FREQUENCIA_PMI[cand_par]))
                        print("Porcentagem: " + str(percentagem_par) + "%")
                        print("\n")

                    # Se a frequencia de cada um é maior que ZERO
                    if Alvaro.FREQUENCIA_PMI[token_frase] > 0 and Alvaro.FREQUENCIA_PMI[cand_par] > 0:
                        # Calculando PMI para palavras co-ocorrentes no Corpus
                        pmi = Alvaro.pontuar_pmi(
                            Alvaro.FREQUENCIA_PMI[token_frase],
                            Alvaro.FREQUENCIA_PMI[cand_par],
                            frequencia_par,
                            Whoosh.DIR_INDEXES)

                        if verbose_pmi or True:
                            print("PMI para '%s': %f" % (str(par), pmi))

                        #os.system('echo "%s" >> /mnt/ParticaoAlternat/pmi-log.txt'%frase)
                        #os.system('echo "%s" >> /mnt/ParticaoAlternat/pmi-log.txt'%str(par))
                        #os.system('echo "%s" >> /mnt/ParticaoAlternat/pmi-log.txt'%str(pmi))

                        # Filtrando do corpus do dicionario documentos
                        # referentes à definicao do candidato + POS tag
                        docs_exemplos_tmp = obter_docs(list(par),
                                                       dir_indexes=Whoosh.DIR_INDEXES_EXEMPLOS)

                        docs_exemplos = []

                        # Se os documentos
                        for doc in docs_exemplos_tmp:
                            # So selecionando exemplos pertencentes ao candidato
                            if cand_par in doc['title'] and cand_par + '-' + pos in doc['path']:
                                docs_exemplos.append(doc)

                        docs_exemplos_tmp = None
                    else:
                        docs_exemplos = []

                    if docs_exemplos:
                        for doc in docs_exemplos:
                            if cand_par in doc['title'] and cand_par + '-' + pos in doc['path']:
                                if verbose_pmi:
                                    print('\n')
                                    print((cand_par, token_frase))
                                    print(doc['title'])
                                    print(doc['path'])
                                    print('\n')

                                # Exemplo de uma dada definicao
                                exemplos_selecionados = doc['content']
                                blob_ex = textblob.TextBlob(
                                    exemplos_selecionados)

                                print("\n\n")
                                #print("PALAVRA: " + palavra)
                                #print("FRASE: " + frase)
                                print(doc['title'])
                                print("\n")
                                print("TF Exemplos:")
                                palavras_relevantes_exemplos_tmp = Alvaro.tf_exemplos(
                                    blob_ex, min_freq=2)
                                palavras_relevantes_exemplos = [
                                    p for p, freq in palavras_relevantes_exemplos_tmp]

                                for palavra in palavras_relevantes_exemplos:
                                    inst = RepVetorial.INSTANCE
                                    # obter_palavras_relacionadas(self, positivos=None, negativos=None, pos=None, topn=1):
                                    try:
                                        res = RepVetorial.obter_palavras_relacionadas(
                                            inst, positivos=[palavra], topn=200)
                                        print("\n\t%s: %s" %
                                              (palavra.upper(), str(res)))
                                    except:
                                        pass

                                print("\nPalavras relevantes exemplos:")
                                raw_input(palavras_relevantes_exemplos_tmp)
                                print("\n\n")

                                # Frequencia
                                ftoken_frase = Alvaro.tf(token_frase, blob_ex)

                                if verbose_pmi:
                                    fm_token_frase = Alvaro.tf(
                                        token_frase, blob_ex)/blob_ex.split(':::').__len__()
                                    print("FreqMedia '%s': %f" % (
                                        token_frase, fm_token_frase))
                                    print("Frequencia '%s': %f" % (
                                        token_frase, ftoken_frase))
                                    print("PMI x Frequencia: %f" %
                                          (ftoken_frase * pmi))

                                if not doc['title'] in pontuacao_definicoes:
                                    pontuacao_definicoes[doc['title']] = []

                                pontuacao_definicoes[doc['title']].append(
                                    ftoken_frase * pmi)
                    else:
                        if verbose_pmi:
                            print(
                                "Palavras %s nao sao relacionadas no dicionario!" % str(par))

                    docs_exemplos = None

                # Deletando arquivos duplicados
                if deletar_docs_duplicados == True:
                    # Usado para reconhecer documentos duplicados
                    # na indexacao e, posteriormente, deleta-los
                    set_docs_corpora = set()
                    paths_repetidos = set()
                    documentos_deletaveis = []

                    try:
                        for doc_iter in docs_corpora:
                            if len(doc_iter['content']) > Util.CONFIGS['max_text_length']:
                                md5_doc = Util.md5sum_string(
                                    doc_iter['content'])

                                if not md5_doc in set_docs_corpora:
                                    set_docs_corpora.add(md5_doc)
                                else:
                                    if not doc_iter['path'] in paths_repetidos:
                                        doc_tmp = Whoosh.buscar_docnum(
                                            doc_iter['path'])
                                        documentos_deletaveis.append(doc_tmp)
                                        paths_repetidos.add(doc_iter['path'])

                        if documentos_deletaveis:
                            Whoosh.remover_docs(documentos_deletaveis)

                    except Exception, e:
                        pass
                else:
                    docs_corpora = None

                    set_docs_corpora = None
                    paths_repetidos = None
                    documentos_deletaveis = None

        return pontuacao_definicoes

    @staticmethod
    def pmi(palavra1, palavra2):
        freq_x = Whoosh.count(palavra1, Whoosh.DIR_INDEXES)
        freq_y = Whoosh.count(palavra2, Whoosh.DIR_INDEXES)
        freq_xy = Whoosh.count([palavra1, palavra2], Whoosh.DIR_INDEXES)

        return Alvaro.pontuar_pmi(freq_x, freq_y, freq_xy, Whoosh.DIR_INDEXES)

    """
    A partir de um conjunto de exemplos, armazenados
    em um BlobText, gere o ranking de palavras mais frequentes
    """
    @staticmethod
    def tf_exemplos(blob_exemplos, min_freq=1):
        contadores = {}

        cfgs = Util.CONFIGS

        pro = [p.lower() for p in cfgs['pronomes']]
        prep = [p.lower() for p in cfgs['preposicoes']]
        artigos = [p.lower() for p in cfgs['artigos']]
        conj = [p.lower() for p in cfgs['conjuncoes']]
        verbos_lig = [p.lower() for p in cfgs['verbos_ligacao']]

        palavras_excluiveis = pro+prep+artigos+conj+verbos_lig

        for p in blob_exemplos.words:
            freq = Alvaro.tf(p, blob_exemplos)
            if freq >= min_freq:
                if not p.lower() in palavras_excluiveis:
                    contadores[p] = freq

        return sorted(contadores.items(), key=lambda x: x[1], reverse=True)

    """
    Obtem palavras similares (interseccao) comuns ao
    contexto das duas palavras passadas como parametros do metodo
    """
    @staticmethod
    def interseccao_palavras(p1, p2, pos):
        inst = RepVetorial.INSTANCE
        set_p1 = RepVetorial.obter_palavras_relacionadas(inst, positivos=[p1], pos=pos, topn=200)
        set_p2 = RepVetorial.obter_palavras_relacionadas(inst, positivos=[p2], pos=pos, topn=200)

        set_p1 = [p for p, s in set_p1]
        set_p2 = [p for p, s in set_p2]

        return list(set(set_p1)&set(set_p2))

    @staticmethod
    def palavras_similares(c, pos):
        dir_arq = "../Bases/PalavrasSimilaresEmbbedings/%s-%s.json" % (c, pos)

        if Util.arq_existe(None, dir_arq) == False:
            similares = RepVetorial.obter_palavras_relacionadas
            try:
                similares_embbedings = similares(
                    RepVetorial.INSTANCE, positivos=[c], topn=200, pos=pos)
                Util.salvar_json(dir_arq, similares_embbedings)
            except:
                return []
        else:
            similares_embbedings = Util.abrir_json(
                dir_arq, criarsenaoexiste=False)

        return similares_embbedings

    @staticmethod
    def aplicar_wmd_sinonimia(palavra_target, pos, candidatos):
        resultado = Alvaro.pontuar_definicoes_frases(palavra_target, pos)

        try:
            resultado = [p for p, s in resultado if p in candidatos]
            return resultado + list(set(candidatos)-set(resultado))
        except Exception, e:
            return []

    """
    Dado um conjunto de candidatos, gera uma malha cartesiana
    de sinonimia sobre todas definicoes de cada um dos candidatos
    atraves da medida WMD. Ao final, salva em disco o objeto obtido
    """
    @staticmethod
    def gerar_pares_candidatos(lexelt, candidatos, pos):
        cfgs = Util.CONFIGS

        cache_ox = cfgs['oxford']['cache']
        dir_arquivo = cfgs['caminho_bases']+'/' + \
            cache_ox['sinonimiaWMD']+'/'+lexelt+".json"

        if Util.arq_existe(None, dir_arquivo):
            return Util.abrir_json(dir_arquivo)

        definicoes = {}
        ponderacoes = {}

        for c in candidatos:
            definicoes[c] = BaseOx.obter_definicoes(BaseOx.INSTANCE, c, pos)

        todos_pares = itertools.combinations(candidatos, 2)

        for par in todos_pares:
            p1, p2 = par

            if p1 != p2:
                for d1 in definicoes[p1]:
                    for d2 in definicoes[p2]:
                        inst_repvet = RepVetorial.INSTANCE

                        if p1 < p2:
                            chave_par = "%s:::%s;;;%s:::%s" % (p1, d1, p2, d2)
                        else:
                            chave_par = "%s:::%s;;;%s:::%s" % (p2, d2, p1, d1)

                        if not chave_par in ponderacoes:
                            pontuacao = RepVetorial.word_move_distance(
                                inst_repvet, d1, d2)
                            ponderacoes[chave_par] = pontuacao

        Util.salvar_json(dir_arquivo, ponderacoes)
        definicoes = None

        return ponderacoes

    """
    Recebe um inventario de sentido na forma lista de lema:::definicao
    e gera um score baseado na medida de word_move_distance
    Retorna: uma lista ordenada de pares <lema:::definicao, score_wmd>
    """
    @staticmethod
    def des_inventario_estendido_wmd(lexelt, frase, lista_inventario):
        cache = Util.CONFIGS['oxford']['cache']['desambiguador_wmd']
        dir_arquivo = cache + '/' + lexelt + ".des.json"

        if Util.arq_existe(None, dir_arquivo) == False:
            resultado = []

            for reg in lista_inventario:
                lema, deflema = reg.split(":::")

                inst = RepVetorial.INSTANCE
                pontuacao = RepVetorial.word_move_distance(
                    inst, deflema, frase)
                resultado.append((reg, pontuacao))

            saida_ordenda = Util.sort(resultado, col=1, reverse=False)
            Util.salvar_json(dir_arquivo, saida_ordenda)

            return saida_ordenda

        else:
            return Util.abrir_json(dir_arquivo, criarsenaoexiste=False)

    @staticmethod
    def salvar_documento_wikipedia(verbete, url):
        inst = ExtratorWikipedia.INSTANCE
        texto, refs = ExtratorWikipedia.obter_texto(
            inst, url, obter_referencias=True)
        texto = Util.completa_normalizacao(texto)

        dir_arquivo = "../Bases/Cache/Wikipedia/%s.json" % verbete
        obj_pagina = Util.abrir_json(dir_arquivo, criarsenaoexiste=True)

        if not verbete in obj_pagina:
            obj_pagina[verbete] = {}

        obj_pagina[verbete][url] = texto

        try:
            return Util.salvar_json(dir_arquivo, obj_pagina)
        except:
            return False

    """
    Recebe um conjunto de frases e, entao, calcula as definicoes cujas frases associadas
    estejam em uma distancia num espaco vetorial menor que as frases das demais definicoes

    metodo_ordem = 'menos_dispares'
    metodo_ordem = 'frase_mais_proxima'
    """
    @staticmethod
    def calc_distancia_ex(lexelt, todos_ex, instancia_entrada, melhor_predicao=[]):
        frase_entrada, palavra_entrada = instancia_entrada
        todos_scores = []

        exs_separados = {}
        contador_frases_ruins = {}

        for lema, frase, lema, definicao, ex, pontuacao in todos_ex:
            chave = lema + ":::" + definicao
            if pontuacao != float('inf'):
                todos_scores.append(pontuacao)
                if not chave in exs_separados:
                    exs_separados[chave] = []
                exs_separados[chave].append((ex, pontuacao))

        media = Util.media(todos_scores)

        if media == float('inf'):
            print("\nUma frase de exemplo possui distancia infinita!\n")

        desvio_padrao = statistics.pstdev(todos_scores)

        for lema, frase, lema, definicao, ex, pontuacao in todos_ex:
            # Se o score é maior que (média + desvio padrao), a definicao é ruim
            if pontuacao > media + desvio_padrao:
                chave = lema + ":::" + definicao
                if not chave in contador_frases_ruins:
                    contador_frases_ruins[chave] = 0
                contador_frases_ruins[chave] += 1

        res_ordenado = set()
        qtde_exemplos_definicao = []

        for lema, frase, lema, definicao, ex, pontuacao in todos_ex:
            chave = lema + ":::" + definicao

            try:
                qtde_exemplos_dispares = contador_frases_ruins[chave]
            except:
                qtde_exemplos_dispares = 0

            qtde_exemplos = len(exs_separados[chave])
            qtde_exemplos_definicao.append(qtde_exemplos)

            proporcao = float(qtde_exemplos_dispares) / float(qtde_exemplos)

            reg = (chave, proporcao, qtde_exemplos)
            res_ordenado.add(reg)

        res_ordenado = Util.sort(list(res_ordenado), col=1, reverse=False)

        res_ordenado_valido = []
        res = []

        contador_reg = 0

        flag = False
        indices_validos = []

        print("\n")

        for chave, proporcao, qtde_exemplos in res_ordenado:
            reg = (chave, proporcao, qtde_exemplos)
            media_qtde_ex = Util.media(qtde_exemplos_definicao)
            desvpad_qtde_ex = statistics.pstdev(qtde_exemplos_definicao)

            # Se quantidade de exemplos é maior que (média - desvio padrão)
            if qtde_exemplos >= media_qtde_ex - desvpad_qtde_ex:
                res_ordenado_valido.append(reg)
                res.append(reg[0].split(":::")[0])
                if reg[0].split(":::")[0] in melhor_predicao:
                    indices_validos.append(contador_reg)
                    print(str(str(contador_reg) + ' - ' + str(reg) + "\n").upper())
                    flag = True
                contador_reg += 1
            else:
                pass

        if flag == True:
            arq_saida = "/mnt/ParticaoAlternat/Bases/ResultadosAnotadosDesambiguador/%s.json" % lexelt
            arq_saida = arq_saida.replace(' ', '-')

            if Util.arq_existe(None, arq_saida):
                return list(set(res))

            while True:
                try:
                    indice = int(raw_input("\nDigite o indice valido: "))
                    if int(indice) in indices_validos or indice < 0:
                        break
                except:
                    pass

            print(res_ordenado_valido[indice])
            print(res_ordenado_valido[-1])

            valor_max = res_ordenado_valido[-1][1]
            valor_min = res_ordenado_valido[0][1]

            percentile = valor_max / 10.0
            proporcao_melhor = res_ordenado_valido[indice][1]
            percentile_achado = int(math.ceil(proporcao_melhor / percentile))

            if indice > 0:
                obj = {}
                obj['percentil'] = percentile_achado
                obj['proporcao_melhor'] = proporcao_melhor
                obj['ranking'] = res_ordenado_valido

                Util.salvar_json(arq_saida, obj)

        return list(set(res))

    """
    Retorna os sinomos cuja as definições associadas tem suas frases de
    exemplo com baixa distancia semantica após a aplicação do método da substituição
    """
    @staticmethod
    def pontuar_definicoes_frases(palavra_target, pos, max_frases=100000000000):
        pontuacoes = {}

        sinonimos_usados = set()

        # obter_atributo(self, palavra, pos, definicao, atributo):
        for def_target in BaseOx.obter_definicoes(BaseOx.INSTANCE, palavra_target, pos):
            sinonimos = BaseOx.obter_sins(
                BaseOx.INSTANCE, palavra_target, def_target, pos)
            melhor_sinonimo = None

            for s in sinonimos:
                if s != palavra_target and not s in sinonimos_usados:
                    sinonimos_usados.add(s)
                    melhor_sinonimo = s
                    break

            if melhor_sinonimo:
                for def_siter in BaseOx.obter_definicoes(BaseOx.INSTANCE, melhor_sinonimo, pos):
                    melhor_sinonimo_sing = Util.singularize(melhor_sinonimo)

                    chave = melhor_sinonimo_sing+'@@@@'+def_siter

                    pontuacoes[chave] = []
                    todos_exemplos = BaseOx.obter_atributo(BaseOx.INSTANCE,
                                                           melhor_sinonimo, pos, def_siter, 'exemplos')[:max_frases]

                    for ex_ in todos_exemplos:
                        ex = ex_.lower()
                        novo_ex = ex.replace(
                            melhor_sinonimo_sing, palavra_target)

                        if novo_ex == ex:
                            novo_ex = ex.replace(
                                melhor_sinonimo, palavra_target)

                        try:
                            if novo_ex == ex:
                                t = (melhor_sinonimo, melhor_sinonimo_sing)
                                raise Exception(
                                    "\nNova frase deu errado! P: %s\n" % str(t))
                            else:
                                wmd = RepVetorial.word_move_distance(
                                    RepVetorial.INSTANCE, ex, novo_ex)
                                pontuacoes[chave].append(wmd)
                        except:
                            pass

                    if pontuacoes[chave].__len__():
                        media = Util.media(pontuacoes[chave])
                        pontuacoes[chave] = media
                    else:
                        del pontuacoes[chave]

        psaida = [(s, pontuacoes[s]) for s in pontuacoes]

        return Util.sort(psaida, col=1, reverse=False)
