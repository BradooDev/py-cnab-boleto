# -*- encoding: utf8 -*-

import codecs
import importlib
from datetime import datetime
from cnab240 import errors


class Evento(object):

    def __init__(self, banco, codigo_evento):
        self._segmentos = []
        self.banco = banco
        self.codigo_evento = codigo_evento
        self._codigo_lote = None

    def adicionar_segmento(self, segmento):
        self._segmentos.append(segmento)
        for segmento in self._segmentos:
            segmento.servico_codigo_movimento = self.codigo_evento

    @property
    def segmentos(self):
        return self._segmentos

    def __getattribute__(self, name):
        for segmento in object.__getattribute__(self, '_segmentos'):
            if hasattr(segmento, name):
                return getattr(segmento, name)
        return object.__getattribute__(self, name)

    def __unicode__(self):
        return u'\r\n'.join(unicode(seg) for seg in self._segmentos)

    def __len__(self):
        return len(self._segmentos)

    @property
    def codigo_lote(self):
        return self._codigo_lote

    @codigo_lote.setter
    def codigo_lote(self, valor):
        self._codigo_lote = valor
        for segmento in self._segmentos:
            segmento.controle_lote = valor

    def atualizar_codigo_registros(self, last_id):
        current_id = last_id
        for segmento in self._segmentos:
            if segmento.servico_segmento in ('A','J'):
                # Atualizado o código para que a linha do segmento j52 não aumente o valor
                # Extender para verificar o Segmento Anf
                if "J52" in str(type(segmento)):
                    segmento.servico_numero_registro = current_id
                else:
                    current_id += 1
                    segmento.servico_numero_registro = current_id
            else:
                segmento.servico_numero_registro = current_id
        return current_id


class Lote(object):

    def __init__(self, banco, header=None, trailer=None):
        self.banco = banco
        self.header = header
        self.trailer = trailer
        self._codigo = None
        if self.trailer != None:
            self.trailer.quantidade_registros = 2
        self._eventos = []

    @property
    def codigo(self):
        return self._codigo

    @codigo.setter
    def codigo(self, valor):
        self._codigo = valor
        if self.header != None:
            self.header.controle_lote = valor
        if self.trailer != None:
            self.trailer.controle_lote = valor
        self.atualizar_codigo_eventos()

    def atualizar_codigo_eventos(self):
        for evento in self._eventos:
            evento.codigo_lote = self._codigo

    def atualizar_codigo_registros(self):
        last_id = 0
        for evento in self._eventos:
            last_id = evento.atualizar_codigo_registros(last_id)

    @property
    def eventos(self):
        return self._eventos

    def adicionar_evento(self, evento):
        if not isinstance(evento, Evento):
            raise TypeError

        self._eventos.append(evento)
        if self.trailer != None and hasattr(self.trailer, 'quantidade_registros'):
            self.trailer.quantidade_registros += len(evento)
        self.atualizar_codigo_registros()

        if self._codigo:
            self.atualizar_codigo_eventos()

    # Breakpoint
    def __unicode__(self):
        if not self._eventos:
            raise errors.NenhumEventoError()

        result = []
        if self.header != None:
            result.append(unicode(self.header))
        result.extend(unicode(evento) for evento in self._eventos)
        if self.trailer != None:
            result.append(unicode(self.trailer))
        return '\r\n'.join(result)

    def __len__(self):
        if self.trailer != None and hasattr(self.trailer, 'quantidade_registros'):
            return self.trailer.quantidade_registros
        else:
            return len(self._eventos)


class Arquivo(object):

    def __init__(self, banco, **kwargs):
        """Arquivo Cnab240."""

        self._lotes = []
        self.banco = banco
        arquivo = kwargs.get('arquivo')
        if isinstance(arquivo, (file, codecs.StreamReaderWriter)):
            return self.carregar_retorno(arquivo)

        self.header = self.banco.registros.HeaderArquivo(**kwargs)
        # NEW: Adicionado para voltar o Numero do Lote no Trailer do Arquivo
        kwargs.update({'codigo_lote': 9999})
        self.trailer = self.banco.registros.TrailerArquivo(**kwargs)
        self.trailer.totais_quantidade_lotes = 0
        self.trailer.totais_quantidade_registros = 2

        if "arquivo_data_de_geracao" in dir(self.header) and \
           self.header.arquivo_data_de_geracao is None:
            now = datetime.now()
            self.header.arquivo_data_de_geracao = int(now.strftime("%d%m%Y"))

        if "arquivo_hora_de_geracao" in dir(self.header) and \
           self.header.arquivo_hora_de_geracao is None:
            if now is None:
                now = datetime.now()
            self.header.arquivo_hora_de_geracao = int(now.strftime("%H%M%S"))

    def carregar_retorno(self, arquivo):

        lote_aberto = None
        evento_aberto = None

        for linha in arquivo:
            tipo_registro = linha[7]

            if tipo_registro == '0':
                self.header = self.banco.registros.HeaderArquivo()
                self.header.carregar(linha)

            elif tipo_registro == '1':
                codigo_servico = linha[9:11]

                if codigo_servico == '01':
                    header_lote = self.banco.registros.HeaderLoteCobranca()
                    header_lote.carregar(linha)
                    trailer_lote = self.banco.registros.TrailerLoteCobranca()
                    lote_aberto = Lote(self.banco, header_lote, trailer_lote)
                    self._lotes.append(lote_aberto)
                elif codigo_servico == '04':
                    header_lote = self.banco.registros.HeaderLoteExtrato()
                    header_lote.carregar(linha)
                    trailer_lote = self.banco.registros.TrailerLoteExtrato()
                    lote_aberto = Lote(self.banco, header_lote, trailer_lote)
                    self._lotes.append(lote_aberto)

            elif tipo_registro == '3':
                tipo_segmento = linha[13]
                codigo_evento = linha[15:17]

                if tipo_segmento == 'T':
                    seg_t = self.banco.registros.SegmentoT()
                    seg_t.carregar(linha)

                    evento_aberto = Evento(self.banco, int(codigo_evento))
                    lote_aberto._eventos.append(evento_aberto)
                    evento_aberto._segmentos.append(seg_t)

                elif tipo_segmento == 'U':
                    seg_u = self.banco.registros.SegmentoU()
                    seg_u.carregar(linha)
                    evento_aberto._segmentos.append(seg_u)
                    evento_aberto = None

                elif tipo_segmento == 'E':
                    seg_e = self.banco.registros.SegmentoE()
                    seg_e.carregar(linha)
                    if codigo_evento == '  ':
                        codigo_evento = 0
                    evento_aberto = Evento(self.banco, int(codigo_evento))
                    lote_aberto._eventos.append(evento_aberto)
                    evento_aberto._segmentos.append(seg_e)

            elif tipo_registro == '5':
                if trailer_lote is not None:
                    lote_aberto.trailer.carregar(linha)
                else:
                    raise Exception

            elif tipo_registro == '9':
                self.trailer = self.banco.registros.TrailerArquivo()
                self.trailer.carregar(linha)

    @property
    def lotes(self):
        return self._lotes

    def incluir_cobranca(self, header, **kwargs):
        # 1 eh o codigo de cobranca
        codigo_evento = 1
        evento = Evento(self.banco, codigo_evento)

        seg_p = self.banco.registros.SegmentoP(**kwargs)
        evento.adicionar_segmento(seg_p)

        seg_q = self.banco.registros.SegmentoQ(**kwargs)
        evento.adicionar_segmento(seg_q)

        seg_r = self.banco.registros.SegmentoR(**kwargs)
        if seg_r.necessario():
            evento.adicionar_segmento(seg_r)

        lote_cobranca = self.encontrar_lote(codigo_evento)

        if lote_cobranca is None:
            header = self.banco.registros.HeaderLoteCobranca(**header)
            trailer = self.banco.registros.TrailerLoteCobranca()
            lote_cobranca = Lote(self.banco, header, trailer)
            self.adicionar_lote(lote_cobranca)

            if "controlecob_numero" not in dir(header):
                header.controlecob_numero = int('{0}{1:02}'.format(
                    self.header.arquivo_sequencia,
                    lote_cobranca.codigo))

            if "controlecob_data_gravacao" not in dir(header):
                header.controlecob_data_gravacao = self.header.arquivo_data_de_geracao

        lote_cobranca.adicionar_evento(evento)
        # Incrementar numero de registros no trailer do arquivo
        self.trailer.totais_quantidade_registros += len(evento)

    def incluir_pagamento_itau(self, header, **kwargs):
        # 20 eh o codigo de pagamento
        codigo_evento = 20
        # codigo_evento = kwargs['servico_codigo_movimento']
        evento = Evento(self.banco, codigo_evento)

        if kwargs['num_nota_fiscal_cnpj']:
            seg_anf = self.banco.registros.SegmentoAnf(**kwargs)
            evento.adicionar_segmento(seg_anf)
            seg_anf.servico_segmento = 'A'
            # seg_b = self.banco.registros.SegmentoB(**kwargs)
            # evento.adicionar_segmento(seg_b)
            # seg_b.servico_segmento = 'B'
        # elif kwargs['valor_csll']:
        #     seg_c = self.banco.registros.SegmentoC(**kwargs)
        #     evento.adicionar_segmento(seg_c)
        #     codigo_evento = 20
        # elif kwargs['autenticacao']:
        #     seg_z = self.banco.registros.SegmentoZ(**kwargs)
        #     evento.adicionar_segmento(seg_z)
        #     codigo_evento = 20
        # elif kwargs['']
        elif header['forma_pagamento'] in (30,31):
            seg_j = self.banco.registros.SegmentoJ(**kwargs)
            seg_j.servico_segmento = 'J'
            evento.adicionar_segmento(seg_j)
            num_lote = kwargs.get('controle_lote')
            evento._codigo_lote = num_lote
            seg_j52 = self.banco.registros.SegmentoJ52(**kwargs)
            seg_j52.servico_segmento = 'J52'
            evento.adicionar_segmento(seg_j52)

        else:
            seg_a = self.banco.registros.SegmentoA(**kwargs)
            seg_a.servico_segmento = 'A'
            evento.adicionar_segmento(seg_a)
            # NEW: Adicionado nro do lote para o segmento
            num_lote = kwargs.get('controle_lote')
            evento._codigo_lote = num_lote
            # seg_b = self.banco.registros.SegmentoB(**kwargs)
            # evento.adicionar_segmento(seg_b)
            # seg_b.servico_segmento = 'B'

        #FIXME
        #A operacao abaixo tem que ser trata de forma diferente
        #Quando é um novo lote ela deve retornar None
        #Desta forma estara resolvido a questao da separacao de lote
        lote_cobranca = self.encontrar_lote_pag_itau(codigo_evento)

        if lote_cobranca is None:
            header = self.banco.registros.HeaderLoteSisPag2(**header)
            trailer = self.banco.registros.TrailerLotePagamento(**kwargs)
            lote_cobranca = Lote(self.banco, header, trailer)
            # NEW: Adicionada a validação para o caso de pagamento, onde o numero do lote
            # é enviado pelo segmento A

            if num_lote:
                self.adicionar_lote(lote_cobranca, num_lote)
            else:
                self.adicionar_lote(lote_cobranca)

        for eventos in evento._segmentos:
            eventos.servico_codigo_movimento = kwargs['servico_codigo_movimento']

        lote_cobranca.adicionar_evento(evento)
        # Incrementar numero de registros no trailer do arquivo
        self.trailer.totais_quantidade_registros += len(evento)

    def encontrar_lote(self, codigo_servico):
        for lote in self.lotes:
            if lote.header.servico_servico == codigo_servico:
                return lote

    # NEW: Adicionado um argumento na função para incluir nro de Lote
    def adicionar_lote(self, lote, cod_lote=None):
        if not isinstance(lote, Lote):
            raise TypeError('Objeto deve ser instancia de "Lote"')

        self._lotes.append(lote)
        if cod_lote == None:
            lote.codigo = len(self._lotes)
        else:
            lote.codigo = cod_lote

        if self.trailer is not None:
            if hasattr(self.trailer, 'totais_quantidade_lotes'):
                # Incrementar numero de lotes no trailer do arquivo
                self.trailer.totais_quantidade_lotes += 1

            if hasattr(self.trailer, 'totais_quantidade_registros'):
                # Incrementar numero de registros no trailer do arquivo
                self.trailer.totais_quantidade_registros += len(lote)

    def escrever(self, file_):
        file_.write(unicode(self).encode('ascii'))

    def __unicode__(self):
        if not self._lotes:
            raise errors.ArquivoVazioError()

        result = []
        result.append(unicode(self.header))
        result.extend(unicode(lote) for lote in self._lotes)
        result.append(unicode(self.trailer))
        # Adicionar elemento vazio para arquivo terminar com \r\n
        result.append(u'')
        return u'\r\n'.join(result)

    def encontrar_lote_pag(self, codigo_servico):
        for lote in self.lotes:
            # FIXME
            if codigo_servico == 20:
                return lote
            #
            if lote.header.servico_servico == codigo_servico:
                return lote

    def encontrar_lote_pag_itau(self, codigo_servico):
        for lote in self.lotes:
            # CORRIGIR AQUI
            #LAYOUTE_LOTE NAO É A VARIAVEL CORRETA A SER UTILIZADA
            if codigo_servico == 20:
                return lote
            if lote.header.layout_lote == codigo_servico:
                return lote

    # Implementação para Pag_For
    def incluir_pagamento(self, **kwargs):
        # 20: PAGTO FORNECEDORES
        codigo_evento = 20
        evento = Evento(self.banco, codigo_evento)

        t_pag_for = self.banco.registros.TransacaoPagFor(**kwargs)
        evento.adicionar_segmento(t_pag_for)

        lote_pag = self.encontrar_lote_pag(codigo_evento)

        if lote_pag is None:
            header = None
            trailer = None
            lote_pag = Lote(self.banco, header, trailer)
            self.adicionar_lote(lote_pag)

        lote_pag.adicionar_evento(evento)
        # Incrementar numero de registros no trailer do arquivo
        self.trailer.totais_quantidade_registros += len(evento)


class ArquivoCobranca400(object):

    def __init__(self, banco, **kwargs):
        """Arquivo Cnab400."""

        self._lotes = []
        self.banco = banco
        arquivo = kwargs.get('arquivo')
        if isinstance(arquivo, (file, codecs.StreamReaderWriter)):
            return self.carregar_retorno(arquivo)

        self.header = self.banco.registros.HeaderArquivo(**kwargs)
        self.trailer = self.banco.registros.TrailerArquivo(**kwargs)

        if self.header.arquivo_data_de_geracao is None:
            now = datetime.now()
            self.header.arquivo_data_de_geracao = int(now.strftime("%d%m%Y"))

    def carregar_retorno(self, arquivo):

        lote_aberto = None
        evento_aberto = None

        for linha in arquivo:
            tipo_registro = linha[0]

            if tipo_registro == '0':
                self.header = self.banco.registros.HeaderArquivo()
                self.header.carregar(linha)
                lote_aberto = Lote(self.banco)
                self._lotes.append(lote_aberto)

            elif tipo_registro == '1':
                tipo_segmento = linha[0]
                # codigo_evento = linha[15:17]

                if tipo_segmento == '1':
                    trans_tipo1 = self.banco.registros.TransacaoTipo1()
                    trans_tipo1.carregar(linha)

                    evento_aberto = Evento(self.banco, 1)
                    lote_aberto._eventos.append(evento_aberto)
                    evento_aberto._segmentos.append(trans_tipo1)

                    evento_aberto = None

            elif tipo_registro == '9':
                self.trailer = self.banco.registros.TrailerArquivo()
                self.trailer.carregar(linha)

    @property
    def lotes(self):
        return self._lotes

    def incluir_cobranca(self, **kwargs):
        # 1 eh o codigo de cobranca
        codigo_evento = 1
        evento = Evento(self.banco, codigo_evento)

        trans_tp1 = self.banco.registros.TransacaoTipo1(**kwargs)
        evento.adicionar_segmento(trans_tp1)

        lote_cobranca = self.encontrar_lote(codigo_evento)

        if lote_cobranca is None:
            header = None
            trailer = None
            lote_cobranca = Lote(self.banco, header, trailer)
            self.adicionar_lote(lote_cobranca)

        lote_cobranca.adicionar_evento(evento)

    def encontrar_lote(self, codigo_servico):
        for lote in self.lotes:
            # if lote.header.codigo_servico == codigo_servico:
            #     return lote
            return lote

    def adicionar_lote(self, lote):
        if not isinstance(lote, Lote):
            raise TypeError('Objeto deve ser instancia de "Lote"')

        self._lotes.append(lote)
        lote.codigo = len(self._lotes)

        if self.trailer != None:
            if hasattr(self.trailer, 'totais_quantidade_lotes'):
                # Incrementar numero de lotes no trailer do arquivo
                self.trailer.totais_quantidade_lotes += 1

            if hasattr(self.trailer, 'totais_quantidade_registros'):
                # Incrementar numero de registros no trailer do arquivo
                self.trailer.totais_quantidade_registros += len(lote)

    def escrever(self, file_):
        file_.write(unicode(self).encode('ascii'))

    def __unicode__(self):
        if not self._lotes:
            raise errors.ArquivoVazioError()

        result = []
        result.append(unicode(self.header))
        result.extend(unicode(lote) for lote in self._lotes)
        result.append(unicode(self.trailer))
        # Adicionar elemento vazio para arquivo terminar com \r\n
        result.append(u'')
        return u'\r\n'.join(result)
