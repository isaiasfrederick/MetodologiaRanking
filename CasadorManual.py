# coding: utf-8

from Utilitarios import Utilitarios
from ModuloBasesLexicas.ModuloClienteOxfordAPI import BaseUnificadaObjetosOxford
from nltk.corpus import wordnet

wn = wordnet

# Realiza o casamento manual com os termos de Oxford e Wordnet
class CasadorManual(object):
    def __init__(self, configs):
        self.configs = configs
        # self.configs['dir_base_casada_manualmente']
        self.diretorio_base_casada_manualmente = self.configs['dir_base_casada_manualmente']
        self.base_casada_manualmente = Utilitarios.carregar_json(self.diretorio_base_casada_manualmente)
        self.base_unificada_oxford = BaseUnificadaObjetosOxford(self.configs)

        if self.base_casada_manualmente == None:
            self.base_casada_manualmente = {}

    def ler_inteiros(self, msg):
        try:
            valores = raw_input(msg)
            valores = valores.replace(',', ' ')

            return [int(v) for v in valores.split(' ')]
        except:
            return []

    # Base casada manualmente possuira tres vetores:
    # Um do casamento - Dicionario
    # Um da Wordnet - Uma lista
    # Um do dicionário de Oxford -  
    def iniciar_casamento(self, termo, pos, corrigir=False):
        if corrigir:
            del self.base_casada_manualmente[termo]

        if not termo in self.base_casada_manualmente:
            self.base_casada_manualmente[termo] = {}

        if not wn.synsets(unicode(termo), pos)[0].name() in self.base_casada_manualmente[termo]:
            obj_oxford = self.base_unificada_oxford.obter_obj_unificado(termo)       
            pos_oxford = Utilitarios.conversor_pos_wn_oxford(pos)

            try:
                obj_oxford = obj_oxford[pos_oxford]
            except TypeError:
                print('A POS %s para o termo %s nao foi encontrada!' % (pos_oxford, termo))
                return 

            for synset in wn.synsets(unicode(termo), pos):
                self.base_casada_manualmente[termo][synset.name()] = []

                print('\n\n')
                print('\t' + str((str(termo), str(pos))))
                print('\t' + synset.definition().upper() + '\n')
                
                indice = 1
                definicoes_indexadas = []
                for definicao in obj_oxford:
                    definicoes_indexadas.append(definicao)
                    print('\n\t\t' + str(indice) + ' - ' + repr(definicao) + '\n')
                    indice += 1
                    for def_sec_iter in obj_oxford[definicao]['def_secs']:
                        def_sec = def_sec_iter.encode('utf8')
                        definicoes_indexadas.append(def_sec)
                        print('\t\t' + str(indice) + ' - ' + repr(def_sec))
                        indice += 1

                valores = self.ler_inteiros('\n\tINDICES: ')
                print('\tAnotacao > ' + str(valores))
                print('\n\n')

                for v in valores:
                    try:
                        self.base_casada_manualmente[termo][synset.name()].append(definicoes_indexadas[v-1])
                    except IndexError: pass

            dir_saida = self.diretorio_base_casada_manualmente
            Utilitarios.salvar_json(dir_saida, self.base_casada_manualmente)

    def recuperar_exemplos(self, nome_synset=""):
        termo = wn.synset(nome_synset).lemma_names()[0]
        pos_oxford = wn.synset(nome_synset).pos()
        pos_oxford = Utilitarios.conversor_pos_wn_oxford(pos_oxford)

        try:
            obj_unificado = self.base_unificada_oxford.obter_obj_unificado(termo)[pos_oxford]            
        except:
            print('Excecao: ' + str((termo, pos_oxford)))
            obj_unificado = None
        
        try:
            definicoes_oxford = self.base_casada_manualmente[termo][nome_synset]
        except:
            print('Excecao! Nao foram encontradas definicoes para o (%s, %s) na base casada manualmente!' % (termo, nome_synset))
            definicoes_oxford = None

        if definicoes_oxford:
            lista_definicoes = []

            for def_principal in obj_unificado:
                reg = ("", def_principal, obj_unificado[def_principal]['exemplos'])
                lista_definicoes.append(reg)
                for def_sec in obj_unificado[def_principal]['def_secs']:                        
                    reg = ("", def_sec, obj_unificado[def_principal]['def_secs'][def_sec]['exemplos'])
                    lista_definicoes.append(reg)
           
            for nome_def, definicao, exemplos in lista_definicoes:
                if definicao in definicoes_oxford:
                    return exemplos

        return []