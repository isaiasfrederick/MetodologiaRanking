from RepositorioCentralConceitos import CasadorConceitos
from pywsd.utils import lemmatize, porter, lemmatize_sentence
from Utilitarios import Util
from pywsd.cosine import cosine_similarity as cos_sim
from pywsd.lesk_isaias import cosine_lesk
from nltk.corpus import stopwords, wordnet
from nltk import pos_tag, word_tokenize
from nltk.corpus import wordnet
from itertools import chain

import inspect
import re
import os


class DesambiguadorOxford(object):
    def __init__(self, configs, base_ox):
        self.configs = configs
        self.base_ox = base_ox
        self.rep_conceitos = CasadorConceitos(self.configs, self.base_ox)

        self.usar_cache = True
        self.dir_cache = configs['oxford']['cache']['desambiguador']


    """ Gera a assinatura a partir de um significado Oxford a partir dos parametros """
    def assinatura_significado_aux(self, lema, pos, definicao, lista_exemplos, extrair_relacao_semantica=False):
        retornar_valida = Util.retornar_valida_pra_indexar

        assinatura = retornar_valida(definicao.replace('.', '')).lower()
        assinatura = [p for p in word_tokenize(assinatura) if not p in [',', ';', '.']]

        if lista_exemplos:
            assinatura += list(chain(*[retornar_valida(ex).split() for ex in lista_exemplos]))

        if extrair_relacao_semantica:
            nova_definicao = definicao.replace(lema, '')
            substantivos = self.rep_conceitos.extrair_substantivos(nova_definicao)

            hiperonimos_extraidos = self.rep_conceitos.extrair_hiperonimos_detectados(lema, pos, definicao)
            for h in hiperonimos_extraidos:
                dist_cosseno = Util.cosseno(definicao, wordnet.synset(h).definition())
                print('\t- ' + str(h) + '  -  ' + str(dist_cosseno) + ' - ' + str(hiperonimos_extraidos[h]))
                for h2 in wordnet.synsets(h.split('.')[0]):
                    if h2.name() != h:
                        dist_cosseno = Util.cosseno(definicao, h2.definition())
                        print('\t\t- ' + h2.name() + '  -  ' + str(dist_cosseno))

        assinatura += lema
        assinatura = [p for p in assinatura if len(p) > 1]

        return assinatura

    """ Metodo Cosseno feito para o dicionario de Oxford """
    def cosine_lesk(self, ctx, ambigua, pos, nbest=True, lematizar=True, stem=True, stop=True, usar_ontologia=False, usar_exemplos=False, busca_ampla=False):
        if self.usar_cache:
            vars_locais = dict(locals())

            del vars_locais['self']
            del vars_locais['ambigua']

            vars_locais = [",".join((str(k),str(v))) for k, v in vars_locais.iteritems()]
            chave_vars_locais = "::".join(vars_locais)

            dir_completo_obj = self.dir_cache+"/"+ ambigua+".json"

            if ambigua+'.json' in os.listdir(self.dir_cache):
                obj_cache = Util.abrir_json(dir_completo_obj)
            else:
                obj_cache = Util.abrir_json(dir_completo_obj, criar=True)

            if chave_vars_locais in obj_cache:
                return obj_cache[chave_vars_locais]

        if len(pos) == 1:
            pos = Util.conversor_pos_wn_oxford(pos)

        assinaturas = self.assinatura_significado(ambigua, usar_exemplos=usar_exemplos)
        assinaturas = [a for a in assinaturas if pos == a[0].split('.')[1]]

        # Tirando palavras de tamanho 1
        ctx = [p for p in word_tokenize(ctx.lower()) if len(p) > 1]
        ctx = Util.processar_ctx(ctx, stop=stop, lematizar=lematizar, stem=stem)

        pontuacao = [ ]

        for a in assinaturas:
            ass_definicao = Util.processar_ctx(a[3], stop=stop, lematizar=lematizar, stem=stem)
            registro_definicao = a[:3]
            pontuacao.append((cos_sim(" ".join(ctx), " ".join(ass_definicao)), registro_definicao))

        res_des = [(s, p) for p, s in sorted(pontuacao, reverse=True)]

        if self.usar_cache:
            obj_cache[chave_vars_locais] = res_des
            Util.salvar_json(dir_completo_obj, obj_cache)

        return res_des

    """ Gera uma assinatura de um significado Oxford para aplicar Cosseno """
    def assinatura_significado(self, lema, lematizar=True, stem=False, stop=True, extrair_relacao_semantica=False, usar_exemplos=False):
        resultado = self.base_ox.obter_obj_unificado(lema)

        if not resultado:
            resultado = {}

        lema = lemmatize(lema)

        assinaturas_significados = [ ]  #(nome, definicao, exemplos)

        for pos in resultado.keys():
            significados = resultado[pos].keys()

            indice = 1
            for s in significados:
                nome_sig = "%s.%s.%d" % (lema, pos, indice)
                indice += 1

                if usar_exemplos:
                    exemplos = resultado[pos][s]['exemplos']
                else:
                    exemplos = [ ]

                # nome, definicao, exemplos, assinatura
                definicao_corrente = [nome_sig, s, exemplos, [ ]]
                assinaturas_significados.append(definicao_corrente)

                # Colocando exemplos na assinatura
                definicao_corrente[len(definicao_corrente)-1] += self.assinatura_significado_aux(lema, pos, s, exemplos)
        
                sig_secundarios = resultado[pos][s]['def_secs']

                for ss in sig_secundarios:
                    nome_sig_sec = "%s.%s.%d" % (lema, pos, indice)

                    if usar_exemplos:
                        exemplos_secundarios = resultado[pos][s]['def_secs'][ss]['exemplos']
                    else:
                        exemplos_secundarios = [ ]

                    definicao_corrente_sec = [nome_sig_sec, ss, exemplos_secundarios, [ ]]
                    assinaturas_significados.append(definicao_corrente_sec)

                    definicao_corrente_sec[len(definicao_corrente)-1] += self.assinatura_significado_aux(lema, pos, ss, exemplos_secundarios)

                    indice += 1

        for s in assinaturas_significados:
            s[3] = Util.processar_ctx(s[3], stop=True, lematizar=True, stem=True)

        return [tuple(a) for a in assinaturas_significados]

    def retornar_valida(self, frase):
        return Util.retornar_valida(frase)

    def metodos_baseline(self, frase, palavra, pos=None, limite=None, usar_exemplos=False):
        limite = 10000 if limite == None else limite

        if pos.__len__() == 1:
            pos = Util.conversor_pos_wn_oxford(pos)

        resultado = self.base_ox.obter_obj_unificado(palavra)

        if not resultado:
            return [ ]

        definicoes_selecionadas = [ ]
        sinonimos_selecionados = set()

        for definicao in resultado[pos].keys()[:limite]:            
            definicoes_selecionadas.append(definicao)
        for definicao in resultado[pos]:
            for def_sec in resultado[pos][definicao]['def_secs']:
                if definicao.__len__() < limite:
                    definicoes_selecionadas.append(def_sec)

        for definicao in definicoes_selecionadas:
            obj_unificado = self.base_ox.obter_obj_unificado(palavra)            
            sinonimos = self.base_ox.obter_sinonimos_fonte_obj_unificado(pos, definicao, obj_unificado)

            if not sinonimos:
                print('Definicao pra tirar sinonimos: ' + str(definicao))
                sinonimos = self.base_ox.extrair_sinonimos_candidatos_definicao(definicao, pos)
                print('Sinonimos retirados: ' + str(sinonimos) + '\n\n')

                if not palavra in BaseUnificadaObjetosOxford.sinonimos_extraidos_definicao:
                    BaseUnificadaObjetosOxford.sinonimos_extraidos_definicao[palavra] = {}       

                BaseUnificadaObjetosOxford.sinonimos_extraidos_definicao[palavra][definicao] = sinonimos

            for sin in sinonimos:
                if Util.multipalavra(sin) == False:
                    sinonimos_selecionados.add(sin)

        sinonimos_selecionados = list(sinonimos_selecionados)

        return sinonimos_selecionados


    def extrair_sinonimos(self, ctx, palavra, pos=None, usar_exemplos=False, busca_ampla=False, repetir=False, coletar_todos=True):
        max_sinonimos = 10

        obter_objeto_unificado_oxford = self.base_ox.obter_obj_unificado
        obter_sinonimos_oxford = self.base_ox.obter_sinonimos_fonte_obj_unificado

        try:
            resultado = self.cosine_lesk(ctx, palavra, pos, usar_exemplos=usar_exemplos, busca_ampla=busca_ampla)
        except Exception, e:
            resultado = [ ]

        sinonimos = [ ]

        try:
            if resultado[0][1] == 0:
                resultado = [resultado[0]]
                repetir = False
            else:
                resultado = [item for item in resultado if item[1] > 0]
        except:
            resultado = [ ]

        continuar = bool(resultado)

        while len(sinonimos) < max_sinonimos and continuar:
            len_sinonimos = len(sinonimos)

            for item in resultado:
                definicao, pontuacao = item[0][1], item[1]

                if len(sinonimos) < max_sinonimos:
                    try:                        
                        obj_unificado = obter_objeto_unificado_oxford(palavra)

                        sinonimos_tmp = obter_sinonimos_oxford(pos, definicao, obj_unificado)
                        sinonimos_tmp = [s for s in sinonimos_tmp if not Util.e_multipalavra(s)]
                        sinonimos_tmp = list(set(sinonimos_tmp) - set(sinonimos))

                        if coletar_todos: sinonimos += sinonimos_tmp
                        elif sinonimos_tmp: sinonimos += [sinonimos_tmp[0]]

                    except: pass
                else:
                    continuar = False

            if repetir == False: continuar = False
            elif len_sinonimos == len(sinonimos): continuar = False

        return sinonimos[:max_sinonimos]


    def __del__(self):
        pass