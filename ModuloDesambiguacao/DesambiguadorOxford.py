from CasadorDefinicoes.RepositorioCentralConceitos import CasadorConceitos
from pywsd.utils import lemmatize, porter, lemmatize_sentence
from ModuloUtilitarios.Utilitarios import Utilitarios
from pywsd.cosine import cosine_similarity as cos_sim
from pywsd.lesk_isaias import cosine_lesk
from ModuloOxfordAPI.ModuloClienteOxfordAPI import *
from nltk.corpus import stopwords, wordnet
from nltk import pos_tag, word_tokenize
from nltk.corpus import wordnet
from itertools import chain
import re


class DesambiguadorOxford(object):
    def __init__(self, configs, base_unificada_oxford):
        self.configs = configs
        self.base_unificada_oxford = base_unificada_oxford
        self.rep_conceitos = CasadorConceitos(self.configs, self.base_unificada_oxford)

    # Retira relacoes semanticas a partir da Wordnet
    def extrair_relacao_semantica(self, lemma, palavras_arg):
        palavras = list(palavras_arg)
        casamentos = dict()

        for p in palavras:
            casamentos[p] = dict()

        for synset in wordnet.synsets(lemma):
            pass

        return []

    """ Gera a assinatura a partir de um significado Oxford a partir dos parametros """
    def assinatura_significado_aux(self, lema, pos, definicao, lista_exemplos, extrair_relacao_semantica=False):
        retornar_valida = Utilitarios.retornar_valida_pra_indexar

        assinatura = retornar_valida(definicao.replace('.', '')).lower()
        assinatura = [p for p in word_tokenize(assinatura) if not p in [',', ';', '.']]

        if lista_exemplos:
            assinatura += list(chain(*[retornar_valida(ex).split() for ex in lista_exemplos]))

        if extrair_relacao_semantica:
            nova_definicao = definicao.replace(lema, '')
            substantivos = self.rep_conceitos.extrair_substantivos(nova_definicao)

            hiperonimos_extraidos = self.rep_conceitos.extrair_hiperonimos_detectados(lema, pos, definicao)
            for h in hiperonimos_extraidos:
                dist_cosseno = Utilitarios.cosseno(definicao, wordnet.synset(h).definition())
                print('\t- ' + str(h) + '  -  ' + str(dist_cosseno) + ' - ' + str(hiperonimos_extraidos[h]))
                for h2 in wordnet.synsets(h.split('.')[0]):
                    if h2.name() != h:
                        dist_cosseno = Utilitarios.cosseno(definicao, h2.definition())
                        print('\t\t- ' + h2.name() + '  -  ' + str(dist_cosseno))

        assinatura += lema
        assinatura = [p for p in assinatura if len(p) > 1]

        return assinatura

    """ Metodo Cosseno feito para o dicionario de Oxford """
    def adapted_cosine_lesk(self, frase, ambigua, pos, nbest=True,\
        lematizar=True, stem=True, stop=True, usar_ontologia=False, usar_exemplos=False):

        assinaturas = self.assinatura_significado(ambigua, usar_exemplos=usar_exemplos)
        assinaturas = [a for a in assinaturas if pos in a[0]]

        frase = [p for p in word_tokenize(frase.lower()) if not p in [',', ';', '.']]        

        if stem:
            frase = [i for i in frase if i not in stopwords.words('english')]
        if lematizar:
            frase = [lemmatize(i) for i in frase]
        if stem:
            frase = [porter.stem(i) for i in frase]

        pontuacao = []

        for a in assinaturas:
            ass_tmp = a[3]

            if stop:
                ass_tmp = [i for i in ass_tmp if i not in stopwords.words('english')]
            if lematizar:
                ass_tmp = [lemmatize(i) for i in ass_tmp]
            if stem:
                ass_tmp = [porter.stem(i) for i in ass_tmp]

            pontuacao.append((cos_sim(" ".join(frase), " ".join(ass_tmp)), a[0:3]))

        resultado = [(s, p) for p, s in sorted(pontuacao, reverse=True)]

        return resultado if nbest else [resultado[0]]

    """Gera uma assinatura de um significado Oxford para aplicar Cosseno"""
    def assinatura_significado(self, lema, lematizar=True, stem=False, stop=True, extrair_relacao_semantica=False, usar_exemplos=False):
        resultado = self.base_unificada_oxford.iniciar_consulta(lema)

        if not resultado:
            resultado = {}

        lema = lemmatize(lema)

        assinaturas_significados = []  #(nome, definicao, exemplos)

        for pos in resultado.keys():
            significados = resultado[pos].keys()

            indice = 1
            for s in significados:
                nome_sig = "%s.%s.%d" % (lema, pos, indice)
                indice += 1

                if usar_exemplos:
                    exemplos = resultado[pos][s]['exemplos']
                else:
                    exemplos = []

                # nome, definicao, exemplos, assinatura
                synset_corrente = [nome_sig, s, exemplos, []]
                assinaturas_significados.append(synset_corrente)

                # Colocando exemplos na assinatura
                synset_corrente[3] += self.assinatura_significado_aux(lema, pos, s, exemplos, extrair_relacao_semantica)

                sig_secundarios = resultado[pos][s]['def_secs']

                for ss in sig_secundarios:
                    nome_sig_sec = "%s.%s.%d" % (lema, pos, indice)

                    if usar_exemplos:
                        exemplos_secundarios = resultado[pos][s]['def_secs'][ss]['exemplos']
                    else:
                        exemplos_secundarios = []

                    synset_corrente_sec = [nome_sig_sec, ss, exemplos_secundarios, []]
                    assinaturas_significados.append(synset_corrente_sec)

                    synset_corrente_sec[3] += self.assinatura_significado_aux(lema, pos, ss, exemplos_secundarios, extrair_relacao_semantica)

                    indice += 1

        for s in assinaturas_significados:
            if stop == True:
                s[3] = [i for i in s[3] if i not in stopwords.words('english')]
            if lematizar == True:
                s[3] = [lemmatize(i) for i in s[3]]
            if stem == True:
                s[3] = [porter.stem(i) for i in s[3]]

        return [tuple(a) for a in assinaturas_significados]

    def retornar_valida(self, frase):
        return Utilitarios.retornar_valida(frase)

    def metodos_baseline(self, frase, palavra, pos=None, limite=None, usar_exemplos=False):
        limite = 10000 if limite == None else limite

        if pos.__len__() == 1:
            pos = Utilitarios.conversor_pos_wn_oxford(pos)

        resultado = self.base_unificada_oxford.iniciar_consulta(palavra)

        if not resultado:
            return []

        definicoes_selecionadas = [ ]
        sinonimos_selecionados = set()

        for definicao in resultado[pos].keys()[:limite]:            
            definicoes_selecionadas.append(definicao)
        for definicao in resultado[pos]:
            for def_sec in resultado[pos][definicao]['def_secs']:
                if definicao.__len__() < limite:
                    definicoes_selecionadas.append(def_sec)

        for definicao in definicoes_selecionadas:
            obj_unificado = self.base_unificada_oxford.obter_obj_unificado(palavra)
            sinonimos = self.base_unificada_oxford.obter_sinonimos_fonte_obj_unificado(pos, definicao, obj_unificado)

            if not sinonimos:
                print('Definicao pra tirar sinonimos: ' + str(definicao))
                sinonimos = self.base_unificada_oxford.extrair_sinonimos_candidatos_definicao(definicao, pos)
                print('Sinonimos retirados: ' + str(sinonimos) + '\n\n')

                if not palavra in BaseUnificadaObjetosOxford.sinonimos_extraidos_definicao:
                    BaseUnificadaObjetosOxford.sinonimos_extraidos_definicao[palavra] = {}                
                BaseUnificadaObjetosOxford.sinonimos_extraidos_definicao[palavra][definicao] = sinonimos

            for sin in sinonimos:
                if Utilitarios.multipalavra(sin) == False:
                    sinonimos_selecionados.add(sin)

        sinonimos_selecionados = list(sinonimos_selecionados)

        return sinonimos_selecionados

    def extrair_sinonimos(self, frase, palavra, pos=None, usar_exemplos=False):
        max_sinonimos = 10
        
        resultado = self.adapted_cosine_lesk(frase, palavra, pos, usar_exemplos=usar_exemplos)
        sinonimos = []

        for item in resultado:
            definicao, pontuacao = item[0][1], item[1]

            if sinonimos.__len__() < max_sinonimos:
                obj_unificado = self.base_unificada_oxford.obter_obj_unificado(palavra)

                sinonimos_tmp = self.base_unificada_oxford.obter_sinonimos_fonte_obj_unificado(pos, definicao, obj_unificado)

                if sinonimos_tmp == None:
                    sinonimos_tmp = []

                for s in [s for s in sinonimos_tmp if Utilitarios.multipalavra(s) == False]:
                    sinonimos.append(s)

        return sinonimos[:max_sinonimos]