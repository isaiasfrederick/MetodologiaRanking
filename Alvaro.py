# -*- coding: UTF-8 -*-
from DesOx import DesOx
from DesambiguadorWordnet import DesWordnet
from CasadorManual import CasadorManual
from Utilitarios import Util
from Arvore import Arvore, No
from nltk.corpus import wordnet
from RepresentacaoVetorial import RepVetorial
from string import punctuation
import CasadorManual
import gc
import traceback
import math
import sys
import os
import nltk
import itertools
import textblob
import json

from OxAPI import BaseOx
from pywsd.lesk import cosine_lesk

wn = wordnet


class Alvaro(object):
    INSTANCE = None
    OBJETO_NGRAMS = { }

    PONDERACAO_DEFINICOES = { }
    NGRAMS_COCA = { }

    # "nome#pos" : relacao
    RELACAO_SINONIMIA = { }

    def __init__(self, configs, base_ox, casador_manual, rep_vetorial):
        self.cfgs = configs
        self.base_ox = base_ox
        self.casador_manual = casador_manual
        self.rep_vetorial = rep_vetorial

    def construir_arvore_definicoes(self, lema, pos, max_prof, cands):
        seps = ":::"
        arvores = [ ]

        prof = 1

        for def_polissemia in BaseOx.obter_definicoes(self.base_ox, lema, pos):
            mxsdef = self.cfgs['alvaro']['mxspdef']

            sins = BaseOx.obter_sins(self.base_ox, lema, def_polissemia, pos=pos)
            sins = [s for s in sins if not Util.e_mpalavra(s)][:mxsdef]

            if cands in [None, [ ]]:
                flag_cand = True
                cands = [ ]
            else:
                flag_cand = False

            if set(sins).intersection(set(cands)) or flag_cand:
                label = "%s%s%s"%(lema, seps, def_polissemia)
                nodo_nivel1 = self.adicionar_nivel_arvore(label, No(None, label), pos, prof + 1, max_prof, cands)
                arvores.append(Arvore(nodo_nivel1))

        return arvores

    def adicionar_nivel_arvore(self, label, nodo_pai, pos, prof, max_prof, cands):
        flag_cand = cands in [None, [ ]]
        seps = ":::"

        # Se for menor que a profundidade maxima permitida
        if prof <= max_prof:
            lema, definicao = tuple(label.split(seps))
            for sin in BaseOx.obter_sins(self.base_ox, lema, definicao, pos=pos):
                if sin in cands or flag_cand:
                    for def_polissemia in BaseOx.obter_definicoes(self.base_ox, sin, pos=pos):
                        label = "%s%s%s"%(sin, seps, def_polissemia)
                        nodo_pai.add_filho(self.adicionar_nivel_arvore(label,
                                        No(nodo_pai, label), pos, prof+1, max_prof, cands))

        # Pai nao tera filhos, caso base
        return nodo_pai

    def construir_relacao_definicoes(self, palavra, pos, fontes='oxford', indice=1000):
        cfgs = self.cfgs

        resultado = { }

        dir_cache_rel_sinonimia = cfgs['caminho_bases']+'/'+cfgs['oxford']['cache']['sinonimia']

        kcache_relacao_sin = "%s-%s.json"%(palavra, pos)
        dir_obj = dir_cache_rel_sinonimia+'/'+kcache_relacao_sin

        if fontes == 'oxford':
            definicoes_palavra = BaseOx.obter_definicoes(BaseOx.INSTANCE, palavra, pos)
            for def_polis in definicoes_palavra[:indice]:
                resultado[def_polis] = { }
                for sin in BaseOx.obter_sins(BaseOx.INSTANCE, palavra, def_polis):
                    resultado[def_polis][sin] = BaseOx.obter_definicoes(BaseOx.INSTANCE, sin, pos)
                    if resultado[def_polis][sin] == None: resultado[d] = [ ]
            return resultado
        else:
            raise Exception('Este tipo de fonte nao foi implementada!')

    def pontuar_relsin_wmd(self, palavra, pos, todos_caminhos):
        if Alvaro.PONDERACAO_DEFINICOES in [{ }, None]:
            Alvaro.PONDERACAO_DEFINICOES = Alvaro.carregar_base_ponderacao_definicoes()

        caminhos_ponderados = {  }

        for caminho_iter in todos_caminhos:
            caminho_tokenizado = caminho_iter.split("/")
            
            if not caminho_iter in caminhos_ponderados:
                caminhos_ponderados[caminho_iter] = [ ]

            for aresta_iter in itertools.product(caminho_tokenizado, caminho_tokenizado):
                aresta = list(aresta_iter)
                aresta.sort()
                aresta = tuple(aresta)

                ini, fim = aresta

                def1 = ini.split(":::")[1]
                def2 = fim.split(":::")[1]
                pont_wmd = None

                if ini != fim and not str(aresta) in Alvaro.PONDERACAO_DEFINICOES:
                    pont_wmd = RepVetorial.word_move_distance(RepVetorial.INSTANCE, def1, def2)
                    Alvaro.PONDERACAO_DEFINICOES[str(aresta)] = pont_wmd
                    caminhos_ponderados[caminho_iter].append((aresta, pont_wmd))

        return caminhos_ponderados

    def pontuar_relsin_exemplos(self, palavra, pos, todos_caminhos):
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
                        sins_lema1 = BaseOx.obter_sins(BaseOx.INSTANCE, lema1, def1, pos=pos)
                        sins_lema2 = BaseOx.obter_sins(BaseOx.INSTANCE, lema2, def2, pos=pos)

                        if lema1 in sins_lema1:
                            sins_lema1.remove(lema1)
                        if lema2 in sins_lema2:
                            sins_lema2.remove(lema2)

                        for sin_iter1 in sins_lema1:
                            for ex_iter in BaseOx.obter_atributo(BaseOx.INSTANCE, lema2, pos, def2, 'exemplos'):
                                if lema2 in ex_iter:
                                    ex_def2 = ex_iter.replace(lema2, sin_iter1)
                                    sc_wmd = wmd(RepVetorial.INSTANCE, ex_iter, ex_def2)
                                    # lema, def, pos, sin, lema, def, pos, ex
                                    padrao_cmd = "%s@@@@%s@@@@%s@@@@@%s@@@@%s@@@@%s@@@@%s@@@@%f"
                                    padrao_cmd = padrao_cmd%(lema1, def1, pos, sin_iter1, lema2, def2, ex_def2, sc_wmd)
                                    os.system('echo \"%s\" >> ../Bases/linhas.txt'%padrao_cmd)

                        for sin_iter2 in sins_lema2:
                            for ex_iter in BaseOx.obter_atributo(BaseOx.INSTANCE, lema1, pos, def1, 'exemplos'):
                                if lema1 in ex_iter:
                                    ex_def1 = ex_iter.replace(lema1, sin_iter2)
                                    sc_wmd = wmd(RepVetorial.INSTANCE, ex_iter, ex_def1)
                                    # lema, def, pos, sin, lema, def, pos, ex
                                    padrao_cmd = "%s@@@@%s@@@@%s@@@@@%s@@@@%s@@@@%s@@@@%s@@@@%f"
                                    padrao_cmd = padrao_cmd%(lema2, def2, pos, sin_iter2, lema1, def1, ex_def1, sc_wmd)
                                    os.system('echo \"%s\" >> ../Bases/linhas.txt'%padrao_cmd)

                        sc = None

                    Alvaro.PONDERACAO_DEFINICOES[str(chave)] = 1

        return None

    def pontuar_relsin_subst(self, palavra, pos, todos_caminhos):
        wmd = RepVetorial.word_move_distance
        max_ex = 4

        caminho_scores = { }

        for caminho in todos_caminhos:
            if not caminho in caminho_scores: caminho_scores[caminho] = [ ]
            for aresta in caminho.split("/"):
                lema, definicao = aresta.split(":::")
                if lema != palavra:
                    exemplos = BaseOx.obter_atributo(BaseOx.INSTANCE, lema, pos, definicao, 'exemplos')[:max_ex]
                    for ex_iter in exemplos:
                        ex = ex_iter.replace(lema, palavra)
                        if ex != ex_iter:
                            sc = wmd(RepVetorial.INSTANCE, ex, ex_iter)
                            caminho_scores[caminho].append(sc)

        return caminho_scores

    # Obtem a palavra mais usual para o significado mais usual para uma palavra
    def sugestao_contigencial(self, palavra,\
                        pos, fontes_def='oxford',\
                        metodo='definicao_usual',\
                        ctx=None, med_sim='cosine'):

        if metodo == 'definicao_usual':
            if pos == 'r':
                sins = wn.synsets(palavra, pos)[0].lemma_names()
                try:
                    sins.remove(palavra)
                except: pass
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
                des_ox = DesOx(self.cfgs, self.base_ox, rep_vetorial=self.rep_vetorial)
                try:
                    label, definicao, exemplos = DesOx.desambiguar(des_ox, ctx, palavra, pos, nbest=True, med_sim=med_sim)[0][0]
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
        return todos_votos.count(todos_votos[0])!=1

    def selec_ngrams(self, palavra, frase, cands):
        cfgs = self.cfgs
        min_ngram = cfgs['ngram']['min']
        max_ngram = cfgs['ngram']['max']

        pont_ngram = dict([(p, 0.00) for p in cands])

        ngrams_coca = Alvaro.NGRAMS_COCA

        for cand_iter in cands:
            nova_frase = frase.replace(palavra, cand_iter)

            ngrams_leipzig = Alvaro.carregar_ngrams_leipzig(palavra, cand_iter)
            ngrams_derivados_frase = Alvaro.gerar_ngrams_tagueados(nova_frase, min_ngram, max_ngram, cand_iter)

            # derivando demais n-grams
            dir_ngrams_derivados = cfgs['ngram']['dir_derivado'] % cand_iter
            if os.path.exists(dir_ngrams_derivados) == False:
                novos_ngrams = Alvaro.derivar_ngrams(ngrams_leipzig, cfgs['ngram']['min'], cfgs['ngram']['max'])
                Util.salvar_json(dir_ngrams_derivados, novos_ngrams)
            else:
                novos_ngrams = Util.abrir_json(dir_ngrams_derivados)

            for ng_str in novos_ngrams: ngrams_leipzig[ng_str] = novos_ngrams[ng_str]
            novos_ngrams = None

            for __ng_iter__ in ngrams_derivados_frase:
                ng_iter = [(unicode(p), pt) for (p, pt) in __ng_iter__]

                freq_ngram_iter = 0
                nova_pont = 0

                # COCA Corpus
                if unicode(ng_iter) in ngrams_coca:
                    freq_ngram_iter = int(ngrams_coca[unicode(ng_iter)])
                    nova_pont = Alvaro.pont_colocacao(freq_ngram_iter, len(ng_iter), max_ngram)
                    pont_ngram[cand_iter] += nova_pont
                # Leipzig Corpus
                if unicode(__ng_iter__) in ngrams_leipzig:
                    freq_ngram_iter += int(ngrams_leipzig[unicode(__ng_iter__)])
                    nova_pont += Alvaro.pont_colocacao(freq_ngram_iter, len(ng_iter), max_ngram)
                    pont_ngram[cand_iter] += nova_pont

            ngrams_leipzig = None
            ngrams_derivados_frase = None

        top_ngrams = [(p, pont_ngram[p]) for p in cands]
        return top_ngrams

    @staticmethod
    def derivar_ngrams(ngrams, _min_, _max_):
        novos_ngrams = { }
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
                        except: pass
            except Exception, e:                
                print("\nErro para ngram: %s\n"%str(ng))
                print(e)
        return novos_ngrams

    # Seletor candidatos desconsiderando a questao da polissemia sob este aspecto
    # este metodo seleciona todos os candidatos 
    def selec_candidatos(self, palavra, pos, fontes=['wordnet'], maxpordef=4, indice_definicao=-1):
        maxpordef_ox = 1

        candidatos = set()
        comprimento = None

        if fontes in [[ ], None]:
            raise Exception("Fontes nao foram informadas!")
        if indice_definicao != -1 and fontes!=['oxford']:
            msg = "\nVoce nao pode selecionar um unico indice para mais de duas fontes! "
            msg += "O casamento de definicoes nao existe implementado!\n" 
            raise Exception(msg)

        if 'wordnet' in fontes:
            for s in wn.synsets(palavra, pos):
                candidatos.update(s.lemma_names()[:maxpordef])
                if pos in ['n']:
                    for h in s.hypernyms():
                        candidatos.update(h.lemma_names()[:maxpordef])
                    for h in s.hyponyms():
                        candidatos.update(h.lemma_names()[:maxpordef])
                elif pos in ['a', 'r', 'v']:
                    for similar in s.similar_tos():
                        candidatos.update(similar.lemma_names()[:maxpordef])

        if 'oxford' in fontes:
            todas_definicoes = BaseOx.obter_definicoes(BaseOx.INSTANCE, palavra, pos)            
            for definicao in todas_definicoes:
                try:                
                    candidatos_tmp = BaseOx.obter_sins(BaseOx.INSTANCE, palavra, definicao, pos)[:maxpordef_ox]
                except:
                    candidatos_tmp = [ ]
                candidatos.update([ ] if candidatos_tmp == None else candidatos_tmp)

        comprimento = len(candidatos)

        if set(['wordembbedings', 'embbedings']).intersection(set(fontes)):
            obter_palavras_relacionadas = self.rep_vetorial.obter_palavras_relacionadas
            ptmp = [p[0] for p in obter_palavras_relacionadas(positivos=[palavra],\
                                                        pos=pos, topn=comprimento)]
            candidatos.update(ptmp)

        if palavra in candidatos:
            candidatos.remove(palavra)

        return [p for p in list(candidatos) if len(p) > 1]

    # Retirado de https://stevenloria.com/tf-idf/
    def tf(self, word, blob):
        return float(blob.words.count(word))
        #return float(blob.words.count(word)) / float(len(blob.words))

    def n_containing(self, word, bloblist):
        return sum(1 for blob in bloblist if word in blob.words)

    def idf(self, word, bloblist):
        return math.log(len(bloblist) / len((1 + self.n_containing(word, bloblist))))

    def tfidf(self, word, blob, bloblist):
        return self.tf(word, blob) * self.idf(word, bloblist)

    @staticmethod
    def gerar_ngrams_tagueados(sentenca, _min_, _max_, palavra_central=None):
        ngrams_dict = { }
        tokens_tagueados = nltk.pos_tag(nltk.word_tokenize(sentenca))

        for n in range(_min_, _max_+1):
            ngrams_dict[n] = [ ]

        for n in range(_min_, _max_+1):
            for i in range(0, len(tokens_tagueados)-n):
                if i+n < len(tokens_tagueados):
                    novo_ngram = tokens_tagueados[i:i+n]
                
                    if palavra_central in [t for (t, pt) in novo_ngram] or palavra_central == None:
                        novo_ngram = [(t, pt) for (t, pt) in novo_ngram if not t in punctuation]
                        if palavra_central in [t for (t, pt) in novo_ngram] or palavra_central == None:
                            try:
                                if not novo_ngram in ngrams_dict[len(novo_ngram)]:
                                    ngrams_dict[len(novo_ngram)].append(novo_ngram)
                            except: pass

        ngrams = [ ]

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

        todos_ngrams_tuplas = { } # <ngram : count>

        for linha_iter in todas_linhas:
            colunas = str(linha_iter).lower().split("\t")
            freq, tokens = int(colunas[0]), "\t".join(colunas[1:])

            ngrams = Alvaro.gerar_ngrams_tagueados(tokens, min_ngram, max_ngram)

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
            return [ ]
            
        anto = [ ]
        for s in wn.synsets(palavra, pos):
            for l in s.lemmas():
                for a in l.antonyms():
                    if not a.name() in anto:
                        anto.append(a.name())
        return anto

    @staticmethod
    def carregar_ngrams_leipzig(palavra, substituto):
        if substituto in Util.CONFIGS["ngram"]["blacklist"]:
            return { }

        dir_ngrams_lpzg = '../Bases/Corpora/Leipzig-ngrams'
        dir_conts_ngrams = dir_ngrams_lpzg+'/%s.conts.json'%(substituto)

        if os.path.exists(dir_conts_ngrams) == True:
            return Util.abrir_json(dir_conts_ngrams)

        dict_freq_ngrams = { }

        print("\nExtraindo do corpus sentencas para '%s'"% substituto)
        try:
            obj = Alvaro.gerar_ngrams_leipzig([substituto])
        except:
            print("\n@@@ Erro na geração de n-grams do Leipzig Corpus para a palavra '%s'!\n"%substituto)
            obj = [ ]
        print("Sentencas extraidas!")

        max_ngram = Util.CONFIGS['ngram']['max']

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

        Util.salvar_json(dir_conts_ngrams, dict_freq_ngrams)

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
        comando_filtro = 'cat %s %s >> %s'%(diretorio_leipzig_txt, filtro, file_ngrams_tmp)

        os.system(comando_filtro)
        print(comando_filtro)

        cont_linhas = 0
        with open(file_ngrams_tmp, 'r') as saida_grep:
            for linha_iter in saida_grep:
                cont_linhas += 1

        if cont_linhas > 30000:
            raise Exception("Arquivo de n-grams grande!")

        resultado = [ ]

        with open(file_ngrams_tmp, 'r') as saida_grep:
            for linha_iter in saida_grep:
                saida_blob = textblob.TextBlob(Util.completa_normalizacao(linha_iter))
                ngrams_linha = saida_blob.ngrams(n=Util.CONFIGS['ngram']['max'])

                for ng in ngrams_linha:
                    if len(set(lista_palavras)&set(ng)) == len(lista_palavras):
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
            Alvaro.PONDERACAO_DEFINICOES = {  }

        return Alvaro.PONDERACAO_DEFINICOES

    @staticmethod
    def salvar_base_ponderacao_definicoes():
        dir_arq = "../Bases/ponderacao_definicoes.json"
        if Alvaro.PONDERACAO_DEFINICOES != None:
            Util.salvar_json(dir_arq, Alvaro.PONDERACAO_DEFINICOES)