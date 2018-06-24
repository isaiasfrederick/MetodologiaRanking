# coding: utf-8

from ModuloUtilitarios.Utilitarios import Utilitarios
from pywsd.lesk import cosine_lesk
from nltk.corpus import wordnet
from pywsd.lesk import *

wn = wordnet

class Ponderador(object):
    def __init__(self, configs):
        self.configs = configs
        self.base_sinonimia = Utilitarios.carregar_json(self.configs['base_wander'])

    # Retorna uma lista de palavras correlatas
    def iniciar_processo(self, termo, pos, contexto):
        representa_multipalavra = Utilitarios.representa_multipalavra
        
        conjunto_solucao = []
        pontuacoes_agregadas = dict()

        resultado = self.processar_termo(termo, pos)

        # Cria o ranking a partir do desambiguador
        ponderacoes = cosine_lesk(contexto, termo, pos=pos, nbest=True)

        for significado_termo in self.base_sinonimia[termo]:
            for significado_sinonimo in self.base_sinonimia[termo][significado_termo]:
                for registro in self.base_sinonimia[termo][significado_termo][significado_sinonimo]:
                    nova_frase, synset_definicao, pontuacao = registro
                    chave_par = synset_definicao + '#' + significado_sinonimo
                    
                    if not chave_par in pontuacoes_agregadas:
                        pontuacoes_agregadas[chave_par] = {}

                    pontuacoes_agregadas[chave_par][nova_frase] = pontuacao
        casamentos_por_ordenacao = dict()

        for chave_par in pontuacoes_agregadas:
            todos_pesos = pontuacoes_agregadas[chave_par].values()
            pontuacao_media = sum(todos_pesos) / len(todos_pesos)

            if not pontuacao_media in casamentos_por_ordenacao:
                casamentos_por_ordenacao[pontuacao_media] = []

            casamentos_por_ordenacao[pontuacao_media].append(chave_par)

        pontuacoes_ordenadas = casamentos_por_ordenacao.keys()
        pontuacoes_ordenadas.sort(reverse=True)

        # Escolhe o synset mais bem avaliado. Caso score for ZERO, pegar o principal
        synset_desambiguado = None
        
        try:
            if bool(ponderacoes[0][1]):
                synset_desambiguado = ponderacoes[0][0]
            else:
                synset_desambiguado = wn.synsets(termo, pos)[0]
        except:
            return []

        if not pos in self.configs['pos_wander']:
            conjunto_solucao = [l for l in synset_desambiguado.lemma_names() if representa_multipalavra(l)]
            conjunto_solucao = self.coletar_lemas([s[0] for s in ponderacoes])

            if conjunto_solucao == [] and False:
                for s in wn.synsets(termo, pos):
                    for l in s.lemma_names():
                        if not l in conjunto_solucao and not representa_multipalavra(l):
                            conjunto_solucao.append(l)

                conjunto_solucao = conjunto_solucao[:10]

            return conjunto_solucao

        for pt in pontuacoes_ordenadas:
            # Se o nome do Synset escolhido faz parte do casamento
            if synset_desambiguado.name() in casamentos_por_ordenacao[pt][0].split('#')[0]:
                nome_synset = casamentos_por_ordenacao[pt][0].split('#')[1]
                conjunto_solucao.append(self.extrair_lema(nome_synset))

        return conjunto_solucao

    # Coleta os dez primeiros lemas dos synsets ponderados
    def coletar_lemas(self, synsets_ordenados):
        saida = []

        for s in synsets_ordenados:
            for l in s.lemma_names():
                if not Utilitarios.representa_multipalavra(l) and not l in saida:
                    saida.append(l)

        return saida[:10]

    def extrair_lema(self, nome_synset):
        todos_lemas = wn.synset(nome_synset).lemma_names()

        try:
            return [l for l in todos_lemas if not Utilitarios.representa_multipalavra(l)][0]
        except:
            return None

    def processar_termo(self, termo, pos):
        if not termo in self.base_sinonimia:
            self.base_sinonimia[termo] = {}

            for synset in wn.synsets(termo, pos):
                synsets_sinonimos = self.obter_synsets_sinonimos(synset, pos)
                resultado = self.comparar_termo(termo, pos, synsets_sinonimos)
                self.base_sinonimia[termo][synset.name()] = resultado

            Utilitarios.salvar_json(self.configs['base_wander'], self.base_sinonimia)            
            return self.base_sinonimia[termo]

        else:
            return self.base_sinonimia[termo]


    def comparar_termo(self, termo, pos, synsets_sinonimos):
        resultado = dict()

        for s in synsets_sinonimos:
            resultado[s.name()] = []

            sinonimo = s.name().split('.')[0]

            pontuacoes = []
            novos_exemplos = list(s.examples())

            for exemplo in novos_exemplos:
                ponderacoes = cosine_lesk(exemplo, termo, pos=pos, nbest=True)

                for registro in ponderacoes:
                    novo_registro = (exemplo, registro[0].name(), registro[1])
                    resultado[s.name()].append(novo_registro)

        return resultado

    # Obtem a lista de sinonimos mediante o critério do Wander
    def obter_lista_sinonimos(self, palavra):
        sinonimos = set()

        for s in wn.synsets(palavra):
            sinonimos.update([p for p in s.lemma_names() if not Utilitarios.representa_multipalavra(p)])

        return [p for p in list(sinonimos) if not p[0].isupper()]

    # Recebe um synset e retorna todos aqueles a partir de seu hiperonimo original
    def obter_synsets_sinonimos(self, synset_original, pos):
        try:
            lema_hiperonimo = synset_original.hypernyms()[0].lemma_names()[0]

            return [s for s in wn.synsets(lema_hiperonimo) if s.pos() == pos]
        except:
            #raw_input("Synset original: " + str(synset_original))
            return []

# Itera cada synset original S
# Salva cada Synset original
# Armazena synset S original
# Para cada synset, compara com seu hiperonimo S