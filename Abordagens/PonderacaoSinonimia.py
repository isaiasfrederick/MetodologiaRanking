# coding: utf-8

from Utilitarios import Util
from CasadorManual import CasadorManual
from pywsd.lesk import cosine_lesk
from nltk.corpus import wordnet
from pywsd.lesk import *

wn = wordnet

class Ponderador(object):
    def __init__(self, configs):
        dir_base_sinonimia = self.solicitar_diretorio_base_sinonimia()

        self.configs = configs
        self.base_sinonimia = Util.abrir_json(dir_base_sinonimia)
        self.casador_manual = CasadorManual(self.configs)

    def solicitar_diretorio_base_sinonimia(self):
        cont = 0
        bases = Util.list_arqs("/media/isaias/ParticaoAlternat/Bases/")
        
        print('\n\n\tLISTAR BASES\n')
        for l in bases:
            print('\t%d\t%s' % (cont, l))
            cont += 1
        
        print('\n\n')
        return bases[int(raw_input('\tINDICE >>> '))]

    # Retorna uma lista de palavras correlatas
    def iniciar_processo(self, termo, pos, contexto, usar_fontes_secundarias=False, anotar_exemplos=False):
        representa_multipalavra = Util.e_multipalavra
        
        conjunto_solucao = [ ]
        pontuacoes_agregadas = dict()

        resultado = self.processar_termo(termo, pos, usar_fontes_secundarias=usar_fontes_secundarias, anotar_exemplos=anotar_exemplos)

        # Cria o ranking a partir do desambiguador
        # Desambiguador utilizado pelo Wander
        ponderacoes = cosine_lesk(contexto, termo, nbest=True)
        # FILTRAR PONDERACOES POR POS TAGS DE SEMEVAL
        ponderacoes = Util.filtrar_ponderacoes(pos, ponderacoes)

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
                casamentos_por_ordenacao[pontuacao_media] = [ ]

            casamentos_por_ordenacao[pontuacao_media].append(chave_par)

        pontuacoes_ordenadas = casamentos_por_ordenacao.keys()
        pontuacoes_ordenadas.sort(reverse=True)

        # Escolhe o synset mais bem avaliado. Caso score for ZERO, pegar o principal
        synset_desambiguado = None

        try:
            # SYNSET MAIS BEM PONTUADO
            if bool(ponderacoes[0][1]):
                synset_desambiguado = ponderacoes[0][0]
            else:
            # SYNSET MAIS USUAL
                synset_desambiguado = wn.synsets(termo, pos)[0]
        except:
            print('\n' + termo)
            print('Excecao na selecao do SYNSET mais bem pontuado.')
            return [ ]

        # SE NAO FOR POR QUE A ABORDAGEM DO WANDER TRATA, PEGAR OS LEMAS DO SENTIDO MAIS USUAL
        if not pos in self.configs['pos_wander']:
            conjunto_solucao = [l for l in synset_desambiguado.lemma_names() if representa_multipalavra(l)]
            conjunto_solucao = self.coletar_lemas([s[0] for s in ponderacoes])

            if conjunto_solucao == [termo] or not conjunto_solucao:
                def_tmp = synset_desambiguado.definition()
                conjunto_solucao = Util.extrair_sinonimos_candidatos_definicao(def_tmp, pos)

            return conjunto_solucao
        else:
            for pt in pontuacoes_ordenadas:
                # Se o nome do Synset escolhido faz parte do casamento
                if synset_desambiguado.name() in casamentos_por_ordenacao[pt][0].split('#')[0]:
                    nome_synset = casamentos_por_ordenacao[pt][0].split('#')[1]
                    if self.extrair_lema(nome_synset):
                        conjunto_solucao.append(self.extrair_lema(nome_synset))

            # SE CONJUNTO SOLUCAO E VAZIO OU COM TERMO ORIGINAL
            if conjunto_solucao == [termo] or not conjunto_solucao:
                definicao_principal = ponderacoes[0][0].definition()
                conjunto_solucao = Util.extrair_sinonimos_candidatos_definicao(definicao_principal, pos)
                
            return conjunto_solucao

    # Coleta os dez primeiros lemas dos synsets Ordenados
    def coletar_lemas(self, synsets_ordenados):
        saida = [ ]

        for s in synsets_ordenados:
            for l in s.lemma_names():
                if not Util.e_multipalavra(l) and not l in saida:
                    saida.append(l)

        return saida[:10]

    def extrair_lema(self, nome_synset):
        todos_lemas = wn.synset(nome_synset).lemma_names()

        try:
            return [l for l in todos_lemas if not Util.e_multipalavra(l)][0]
        except:
            return None

    # Este metodo, em especifico, realiza o metodo da substituicao 
    def processar_termo(self, termo, pos, usar_fontes_secundarias=False, anotar_exemplos=False):
        if not termo in self.base_sinonimia:
            self.base_sinonimia[termo] = {}

            # Percorre todas as definicoes do termo
            for synset in wn.synsets(termo, pos):
                # Recupera os synsets hiperonimos atraves do método do Wander
                synsets_sinonimos = self.obter_synsets_sinonimos(synset, pos)
                # Metodo da substituicao do Wander
                resultado = self.comparar_termo(termo, pos, synsets_sinonimos, usar_fontes_secundarias=usar_fontes_secundarias, anotar_exemplos=anotar_exemplos)
                self.base_sinonimia[termo][synset.name()] = resultado

            Util.salvar_json(self.configs['base_wander'], self.base_sinonimia)            
            return self.base_sinonimia[termo]

        else:
            return self.base_sinonimia[termo]

    def comparar_termo(self, termo, pos, todos_synsets_sinonimos, usar_fontes_secundarias=False, anotar_exemplos=False):
        resultado = dict()

        for synset_sinonimo in todos_synsets_sinonimos:
            resultado[synset_sinonimo.name()] = [ ]

            sinonimo = synset_sinonimo.name().split('.')[0]

            pontuacoes = [ ]
            novos_exemplos = list(synset_sinonimo.examples())

            if anotar_exemplos == True:
                # Solicita a anotacao dos termos para casar as definicoes, caso nao existam
                nome_synset_sinonimo = synset_sinonimo.lemma_names()[0]
                self.casador_manual.iniciar_casamento(nome_synset_sinonimo, synset_sinonimo.pos(), corrigir=False)

            try:
                if usar_fontes_secundarias == True:
                    novos_exemplos += self.casador_manual.recuperar_exemplos(synset_sinonimo.name())
                    print('Novos exemplos adicionados: ' + str(len(novos_exemplos)))
                    print('Termo: ' + termo)
                    print('Definicao: ' + synset_sinonimo.definition())
                    print('\n')
            except:
                print('Nao foram encontrados exemplos para ' + synset_sinonimo.name())

            for exemplo in novos_exemplos:
                ponderacoes = cosine_lesk(exemplo, termo, pos=pos, nbest=True)

                for registro in ponderacoes:
                    novo_registro = (exemplo, registro[0].name(), registro[1])
                    resultado[synset_sinonimo.name()].append(novo_registro)

        return resultado

    # Obtem a lista de sinonimos mediante o critério do Wander
    def obter_lista_sinonimos(self, palavra):
        sinonimos = set()

        for s in wn.synsets(palavra):
            sinonimos.update([p for p in s.lemma_names() if not Util.e_multipalavra(p)])

        return [p for p in list(sinonimos) if not p[0].isupper()]

    # Recebe um synset e retorna todos aqueles a partir de seu hiperonimo original
    def obter_synsets_sinonimos(self, synset_original, pos):
        try:
            lema_hiperonimo = synset_original.hypernyms()[0].lemma_names()[0]
            return [s for s in wn.synsets(lema_hiperonimo) if s.pos() == pos]
        except:
            return [ ]

# Itera cada synset original S
# Salva cada Synset original
# Armazena synset S original
# Para cada synset, compara com seu hiperonimo S