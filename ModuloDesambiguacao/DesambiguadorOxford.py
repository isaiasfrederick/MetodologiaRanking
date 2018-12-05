from RepositorioCentralConceitos import CasadorConceitos
from pywsd.utils import lemmatize, porter, lemmatize_sentence
from Utilitarios import Util
from textblob import TextBlob
from pywsd.cosine import cosine_similarity as cos_sim
#from pywsd.lesk_isaias import cosine_lesk
from nltk.corpus import stopwords, wordnet
from nltk import pos_tag, word_tokenize
import itertools
import sys
import inspect
import re

import os


class DesOx(object):
    cache_objs_json = { }

    def __init__(self, configs, base_ox, rep_vetorial=None):
        self.cfgs = configs
        self.base_ox = base_ox
        self.rep_conceitos = CasadorConceitos(self.cfgs, self.base_ox)

        self.rep_vetorial = rep_vetorial

        self.usar_cache = True
        self.dir_cache = configs['oxford']['cache']['desambiguador']
        self.tam_max_ngram = 4

    """ Gera a assinatura a partir de um significado Oxford a partir dos parametros """

    def assinatura_significado_aux(self, lema, pos, definicao, lista_exemplos,
                                   extrair_relacao_semantica=False):

        retornar_valida = Util.retornar_valida_pra_indexar

        assinatura = retornar_valida(definicao.replace('.', '')).lower()
        assinatura = [p for p in word_tokenize(
            assinatura) if not p in [',', ';', '.']]

        if lista_exemplos:
            assinatura += list(itertools.chain(*[retornar_valida(ex).split() for ex in lista_exemplos]))

        if extrair_relacao_semantica:
            nova_definicao = definicao.replace(lema, '')
            substantivos = self.rep_conceitos.extrair_substantivos(
                nova_definicao)

            hiperonimos_extraidos = self.rep_conceitos.extrair_hiperonimos_detectados(
                lema, pos, definicao)
            for h in hiperonimos_extraidos:
                dist_cosseno = Util.cosseno(
                    definicao, wordnet.synset(h).definition())
                print('\t- ' + str(h) + '  -  ' + str(dist_cosseno) +
                      ' - ' + str(hiperonimos_extraidos[h]))
                for h2 in wordnet.synsets(h.split('.')[0]):
                    if h2.name() != h:
                        dist_cosseno = Util.cosseno(definicao, h2.definition())
                        print('\t\t- ' + h2.name() +
                              '  -  ' + str(dist_cosseno))

        assinatura += lema
        assinatura = [p for p in assinatura if len(p) > 1]

        return assinatura

    # "lematizar,True::nbest,True::stop,True::ctx,frase.::pos,r::usar_ontologia,False::stem,True::usar_exemplos,True::busca_ampla,False"
    def gerar_chave_cache(self, vars_locais):
        vars_locais = [",".join((str(k), str(v)))
                       for k, v in vars_locais.iteritems()]
        return "::".join(vars_locais)

    # Metodo Cosseno feito para o dicionario de Oxford
    # Retorna dados ordenados de forma decrescente
    def desambiguar(self, ctx, ambigua, pos, nbest=True,\
                    lematizar=True, stem=True, stop=True,\
                    usar_ontologia=False, usr_ex=False,\
                    busca_ampla=False, med_sim='cosine'):

        dir_cache_tmp = None
        dir_bases = self.cfgs['caminho_raiz_bases']

        self.usar_cache = False

        if self.usar_cache:
            obj_dir_cache_des = self.cfgs['oxford']['cache']['desambiguador']

            try:
                dir_cache_tmp = dir_bases+'/'+(obj_dir_cache_des[med_sim])
            except:
                raise Exception("Esta medida de similaridade inexiste!")

            vars_locais = dict(locals())

            del vars_locais['self']
            del vars_locais['ambigua']

            chave_vars = self.gerar_chave_cache(vars_locais)
            dir_completo_obj = "%s/%s.json" % (dir_cache_tmp, ambigua)

            if ambigua+'.json' in os.listdir(dir_cache_tmp):
                obj_cache = Util.abrir_json(dir_completo_obj)
            else:
                obj_cache = Util.abrir_json(dir_completo_obj, criar=True)

            if chave_vars in obj_cache:
                return obj_cache[chave_vars]

        if len(pos) == 1:
            pos = Util.cvrsr_pos_wn_oxford(pos)

        if med_sim == 'cosine':
            lem, st = True, True
        else:
            lem, st = False, False

        try:
            todas_assinaturas = self.ass_sig(ambigua, usar_exemplos=usr_ex, lematizar=lem, stem=st)
            todas_assinaturas = [a for a in todas_assinaturas if pos == a[0].split('.')[1]]

            # Tirando palavras de tamanho 1
            ctx = [p for p in word_tokenize(ctx.lower()) if len(p) > 1]

            ctx = Util.processar_ctx(ctx, stop=stop, lematizar=lem, stem=st)
        except KeyboardInterrupt, ke:
            pass

        pontuacao = []

        for a in todas_assinaturas:
            ass_definicao = Util.processar_ctx(a[3], stop=stop, lematizar=lematizar, stem=stem)

            label_def, desc_def, frase_def, ass_def = a
            reg_def = (label_def, desc_def, frase_def)

            if med_sim == 'cosine':
                func_sim = cos_sim
            elif med_sim == 'word_move_distance':
                func_sim = self.rep_vetorial.word_move_distance

            dist_simi = func_sim(" ".join(ctx), " ".join(ass_definicao))

            # Colocando valor infinito
            if dist_simi == float('inf'):
                dist_simi = float(1000)

            pontuacao.append((dist_simi, reg_def))            

        # Ordenacao da saida do desambiguador (cosine=decrescente, wmd=crescente)
        ordem_crescente = (med_sim == 'cosine')
        res_des = [(s, p) for p, s in sorted(pontuacao, reverse=ordem_crescente)]

        if self.usar_cache:
            obj_cache[chave_vars] = res_des
            Util.salvar_json(dir_completo_obj, obj_cache)

        return res_des

    def adapted_lesk(self, ctx, ambigua, pos, nbest=True,
                     lematizar=True, stem=True, stop=True,
                     usr_ex=False, janela=2):

        if len(pos) == 1:
            pos = Util.cvrsr_pos_wn_oxford(pos)

        limiar_polissemia = 10

        # Casamentos cartesianos das diferentes definicoes
        solucoes_candidatas = []

        # Todas definicoes da palavra ambigua
        definicoes = [
            def_ox for def_ox in self.base_ox.obter_definicoes(ambigua, pos)]

        ctx_blob = TextBlob(ctx)

        tags_validas = self.cfgs['pos_tags_treebank']
        tokens_validos = [(token, tag) for (token, tag)
                          in ctx_blob.tags if tag in tags_validas]

        tokens_validos_tmp = []

        # [('The', 'DT'), ('titular', 'JJ'), ('threat', 'NN'), ('of', 'IN'), ...]
        for token, tag in tokens_validos:
            pos_ox = Util.cvrsr_pos_wn_oxford(tag[0].lower())

            defs_token = self.base_ox.obter_definicoes(token, pos_ox)
            if not defs_token in [[], None]:
                tokens_validos_tmp.append((token, tag))
                solucoes_candidatas.append(defs_token)

        tokens_validos = tokens_validos_tmp
        tokens_validos_tmp = None

        indices_tokens_validos = []

        if len(tokens_validos) != len(solucoes_candidatas):
            raise Exception("\nTAMANHOS DIFERENTES!\n")

        i = 0
        for tk, tag in list(tokens_validos):
            if tk == ambigua:
                cont = 0
                for e in sorted(range(0, i), reverse=True):
                    if len(solucoes_candidatas[e]) < limiar_polissemia:
                        indices_tokens_validos.append(e)
                        cont += 1
                    if cont == janela:
                        break

                indices_tokens_validos.append(i)

                cont = 0
                for d in range(i+1, len(tokens_validos)):
                    if len(solucoes_candidatas[d]) < limiar_polissemia:
                        indices_tokens_validos.append(d)
                        cont += 1
                    if cont == janela:
                        break
                    print("Direita: Entrei aqui")

            i += 1

        tokens_validos = [tokens_validos[i] for i in indices_tokens_validos]

        print("\n")
        print("AMBIGUA: '%s'" % ambigua)
        print("CONTEXTO: '%s'\n" % ctx)
        print("TOKENS VALIDOS: "+str([(token, tag) for (token, tag) in tokens_validos]))
        prod = 1
        print("\n\n")
        print([len(solucoes_candidatas[i]) for i in indices_tokens_validos])
        for e in [solucoes_candidatas[i] for i in indices_tokens_validos]:
            prod *= len(e)
        print("Produtorio: "+str(prod))
        raw_input("\n")

        for dtmp in definicoes:
            d = str(dtmp).lower()

            todos_tamanhos_ngram = sorted(range(1, self.tam_max_ngram+1), reverse=True)

            for n in todos_tamanhos_ngram:
                ctx_blob = TextBlob(ctx.lower())
                todos_ngrams = ctx_blob.ngrams(n=n)

                for ngram in todos_ngrams:
                    ngram_str = " ".join(ngram)
                    freq = d.count(ngram_str)
                    pontuacao = freq*(n**2)

                    if freq:
                        d = d.replace(ngram_str, '')

        return 0.00

    """ Gera uma assinatura de um significado Oxford para aplicar Cosseno """
    def ass_sig(self, lema, lematizar=True,\
                            stem=False, stop=True,\
                            extrair_relacao_semantica=False,\
                            usar_exemplos=False):

        resultado = self.base_ox.obter_obj_unificado(lema)

        if not resultado:
            resultado = {}

        lema = lemmatize(lema)

        assinaturas_significados = []  # (nome, definicao, exemplos)

        for pos in resultado.keys():
            todos_significados = resultado[pos].keys()

            indice = 1
            for sig in todos_significados:
                nome_sig = "%s.%s.%d" % (lema, pos, indice)
                indice += 1

                if usar_exemplos:
                    exemplos = resultado[pos][sig]['exemplos']
                else:
                    exemplos = []

                # nome, definicao, exemplos, assinatura
                definicao_corrente = [nome_sig, sig, exemplos, []]
                assinaturas_significados.append(definicao_corrente)

                # Colocando exemplos na assinatura
                definicao_corrente[len(
                    definicao_corrente)-1] += self.assinatura_significado_aux(lema, pos, sig, exemplos)

                sig_secundarios = resultado[pos][sig]['def_secs']

                for ss in sig_secundarios:
                    nome_sig_sec = "%s.%s.%d" % (lema, pos, indice)

                    if usar_exemplos:
                        exemplos_secundarios = resultado[pos][sig]['def_secs'][ss]['exemplos']
                    else:
                        exemplos_secundarios = []

                    definicao_corrente_sec = [
                        nome_sig_sec, ss, exemplos_secundarios, []]
                    assinaturas_significados.append(definicao_corrente_sec)

                    definicao_corrente_sec[len(
                        definicao_corrente)-1] += self.assinatura_significado_aux(lema, pos, ss, exemplos_secundarios)

                    indice += 1

        for sig in assinaturas_significados:
            sig[3] = Util.processar_ctx(
                sig[3], stop=True, lematizar=True, stem=True)

        return [tuple(a) for a in assinaturas_significados]

    def retornar_valida(self, frase):
        return Util.retornar_valida(frase)

    def extrair_sinonimos(self, ctx, palavra, pos=None,
                          usar_exemplos=False, busca_ampla=False,
                          repetir=False, coletar_todos=True):

        max_sinonimos = 10

        obter_objeto_unificado_oxford = self.base_ox.obter_obj_unificado
        obter_sinonimos_oxford = self.base_ox.obter_sinonimos_fonte_obj_unificado

        try:
            resultado = self.desambiguar(ctx, palavra, pos, usr_ex=usar_exemplos, busca_ampla=busca_ampla)
        except Exception, e:
            resultado = []

        sinonimos = []

        try:
            if resultado[0][1] == 0:
                resultado = [resultado[0]]
                repetir = False
            else:
                resultado = [item for item in resultado if item[1] > 0]
        except:
            resultado = []

        continuar = bool(resultado)

        while len(sinonimos) < max_sinonimos and continuar:
            len_sinonimos = len(sinonimos)

            for item in resultado:
                definicao, pontuacao = item[0][1], item[1]

                if len(sinonimos) < max_sinonimos:
                    try:
                        obj_unificado = obter_objeto_unificado_oxford(palavra)

                        sinonimos_tmp = obter_sinonimos_oxford(
                            pos, definicao, obj_unificado)
                        sinonimos_tmp = [
                            s for s in sinonimos_tmp if not Util.e_multipalavra(s)]
                        sinonimos_tmp = list(
                            set(sinonimos_tmp) - set(sinonimos))

                        if coletar_todos:
                            sinonimos += sinonimos_tmp
                        elif sinonimos_tmp:
                            sinonimos += [sinonimos_tmp[0]]

                    except:
                        pass
                else:
                    continuar = False

            if repetir == False:
                continuar = False
            elif len_sinonimos == len(sinonimos):
                continuar = False

        return sinonimos[:max_sinonimos]
