import random
import logging
from typing import Optional

from apps.core.models import DadosNFSe, Session
from apps.core.reponse_builder import ResponseBuilder

logger = logging.getLogger(__name__)


class SmartResponseBuilder(ResponseBuilder):
    """
    Gera respostas humanizadas baseadas nos dados validados.

    Usa templates com variacao contextual para parecer natural
    sem precisar de chamada de IA. Herda de ResponseBuilder
    para manter metodos existentes (build_espelho, build_cancelado, etc).
    """

    # --- Saudacoes ---

    def build_saudacao(self, session: Optional[Session] = None) -> str:
        """Resposta para saudacoes, com contexto da sessao."""
        if session and session.invoice_data:
            dados = session.invoice_data
            faltantes = dados.missing_fields
            erros = dados.invalid_fields

            # Tem dados parciais - lembra o usuario
            if faltantes and not erros:
                campos = self._formatar_campos(faltantes)
                return random.choice([
                    f"Oi! Ainda estamos naquela nota. Falta {campos}.",
                    f"Ola! Continuando de onde paramos, preciso de {campos}.",
                    f"E ai! Lembra da nota? So falta {campos}.",
                ])

            # Tem erros pendentes
            if erros:
                return random.choice([
                    "Oi! Ainda temos uma nota em andamento. Preciso que corrija alguns dados.",
                    "Ola! Continuando a nota, tem uns dados que precisam de correcao.",
                ])

        # Sessao nova ou sem dados
        return random.choice([
            "Oi! Para emitir sua nota, me passa o CNPJ do cliente, valor e descricao do servico.",
            "Ola! Me manda os dados da nota: CNPJ, valor e descricao do servico.",
            "Oi! Pra emitir a nota preciso do CNPJ, valor e descricao. Pode mandar!",
            "E ai! Quer emitir uma nota? Me passa CNPJ do cliente, valor e descricao.",
        ])

    # --- Agradecimentos ---

    def build_agradecimento(self) -> str:
        """Resposta para agradecimentos."""
        return random.choice([
            "Por nada! Qualquer coisa e so chamar.",
            "Disponha! Se precisar de outra nota, e so mandar.",
            "De nada! Estou aqui se precisar.",
            "Tranquilo! Quando precisar, e so chamar.",
        ])

    # --- Resposta principal baseada nos dados validados ---

    def build_smart_response(self, dados: DadosNFSe) -> str:
        """
        Gera resposta contextual baseada nos dados validados pelo Pydantic.

        Prioridade:
        1. Erros de validacao -> informar o erro
        2. Dados completos -> espelho da nota
        3. Dados parciais -> pedir o que falta
        """
        # Prioridade 1: Erros
        if dados.invalid_fields:
            return self._build_error_response(dados)

        # Prioridade 2: Completo
        if dados.data_complete:
            return self.build_espelho(dados.to_dict())

        # Prioridade 3: Parcial
        return self._build_partial_response(dados)

    # --- Respostas de erro ---

    def _build_error_response(self, dados: DadosNFSe) -> str:
        """Resposta para erros de validacao."""
        erros = []
        confirmados = []
        faltantes = []

        # Analisa CNPJ
        if dados.cnpj.status == 'error':
            erros.append(self._cnpj_error_msg(dados.cnpj))
        elif dados.cnpj.status == 'validated':
            confirmados.append('CNPJ')
        else:
            faltantes.append('CNPJ')

        # Analisa Valor
        if dados.valor.status == 'error':
            erros.append(self._valor_error_msg(dados.valor))
        elif dados.valor.status == 'validated':
            confirmados.append('valor')
        else:
            faltantes.append('valor')

        # Analisa Descricao
        if dados.descricao.status == 'error':
            erros.append(self._descricao_error_msg(dados.descricao))
        elif dados.descricao.status == 'validated':
            confirmados.append('descricao')
        else:
            faltantes.append('descricao')

        # Montar resposta
        parts = []

        # Erros primeiro
        parts.append(" ".join(erros))

        # Confirmados
        if confirmados:
            conf_str = " e ".join(confirmados)
            parts.append(f"{conf_str} confirmado{'s' if len(confirmados) > 1 else ''}.")

        # Faltantes
        if faltantes:
            campos = self._formatar_campos(faltantes)
            parts.append(f"Tambem preciso de {campos}.")

        return " ".join(parts)

    def _cnpj_error_msg(self, cnpj) -> str:
        if cnpj.error_type == 'DIGITO_VERIFICADOR_INVALIDO':
            return random.choice([
                "Esse CNPJ parece ter os digitos incorretos, pode conferir?",
                "O CNPJ informado nao bate, pode verificar os numeros?",
            ])
        if cnpj.error_type == 'FORMATO_INVALIDO':
            return random.choice([
                "Esse CNPJ nao parece valido. Precisa ter 14 digitos.",
                "O CNPJ precisa ter 14 digitos, pode conferir?",
            ])
        return "O CNPJ informado parece incorreto, pode verificar?"

    def _valor_error_msg(self, valor) -> str:
        if valor.error_type == 'VALOR_INVALIDO':
            return random.choice([
                "O valor precisa ser maior que zero.",
                "O valor informado precisa ser positivo.",
            ])
        return "O valor informado nao parece correto, pode verificar?"

    def _descricao_error_msg(self, descricao) -> str:
        if descricao.error_type == 'DESCRICAO_INVALIDA' or descricao.error_type == 'MUITO_CURTA':
            return random.choice([
                "A descricao ficou muito curta. Pode detalhar melhor o servico?",
                "Preciso de uma descricao mais detalhada do servico prestado.",
            ])
        if descricao.error_type == 'MUITO_LONGA':
            return "A descricao ficou muito longa. Tenta resumir em ate 500 caracteres."
        return "A descricao precisa de ajuste, pode reformular?"

    # --- Respostas para dados parciais ---

    def _build_partial_response(self, dados: DadosNFSe) -> str:
        """Resposta para dados parciais (sem erro, incompleto)."""
        confirmados = []
        faltantes = []

        for campo, label in [('cnpj', 'CNPJ'), ('valor', 'valor'), ('descricao', 'descricao')]:
            obj = getattr(dados, campo)
            if obj.status == 'validated':
                confirmados.append(label)
            elif obj.status == 'null':
                faltantes.append(label)

        # Nenhum campo confirmado (primeira mensagem, ex: "quero emitir nota")
        if len(confirmados) == 0:
            return random.choice([
                "Para emitir a nota, preciso do CNPJ do cliente, valor e descricao do servico.",
                "Me passa o CNPJ do cliente, o valor e a descricao do servico.",
                "Pra comecar, preciso de tres informacoes: CNPJ, valor e descricao.",
            ])

        # Falta 1 campo
        if len(faltantes) == 1:
            campo = faltantes[0]
            conf_str = " e ".join(confirmados)
            artigo = "a " if campo == "descricao" else "o "
            return random.choice([
                f"{conf_str} confirmado{'s' if len(confirmados) > 1 else ''}! So falta {artigo}{campo}.",
                f"Recebi {conf_str}. Agora preciso d{artigo}{campo}.",
                f"Otimo! Ja tenho {conf_str}. Falta {artigo}{campo}.",
            ])

        # Faltam 2 campos
        if len(faltantes) == 2:
            confirmado = confirmados[0]
            falt_str = " e ".join(faltantes)
            return random.choice([
                f"{confirmado} confirmado! Agora me passa {falt_str}.",
                f"Recebi o {confirmado}. Ainda preciso de {falt_str}.",
            ])

        # Fallback
        return "Para emitir a nota, preciso do CNPJ, valor e descricao do servico."

    # --- Repetir nota ---

    def build_repetir_nota(self, dados: dict, data_original, razao_social_tomador: str) -> str:
        """
        Espelho para nota repetida, com header indicando a origem.

        Args:
            dados: DadosNFSe.to_dict()
            data_original: datetime da nota original
            razao_social_tomador: Nome do tomador da nota original
        """
        if data_original:
            data_str = data_original.strftime('%d/%m/%Y')
            header = f"*Repetindo nota de {data_str} para {razao_social_tomador}*\n\n"
        else:
            header = f"*Repetindo nota para {razao_social_tomador}*\n\n"

        espelho = self.build_espelho(dados)
        return header + espelho

    # --- Sugestao de descricao ---

    def build_sugestao_descricao(self, dados: 'DadosNFSe', sugestao: str) -> str:
        """
        Mostra dados confirmados + sugestao de descricao do historico.

        Args:
            dados: DadosNFSe com dados parciais
            sugestao: Descricao sugerida do historico
        """
        parts = []

        # Mostrar dados confirmados
        if dados.cnpj.status == 'validated':
            razao = dados.cnpj.razao_social or dados.cnpj.cnpj
            parts.append(f"CNPJ: {razao}")
        if dados.valor.status == 'validated':
            parts.append(f"Valor: {dados.valor.valor_formatted}")

        confirmados = "\n".join(f"- {p}" for p in parts)

        # Truncar sugestao se muito longa
        sugestao_display = sugestao if len(sugestao) <= 100 else sugestao[:97] + "..."

        return (
            f"{confirmados}\n\n"
            f"Da ultima vez para esse cliente voce usou:\n"
            f"_{sugestao_display}_\n\n"
            f"Quer usar a mesma descricao? (*sim* ou informe uma nova)"
        )

    # --- Helpers ---

    def _formatar_campos(self, campos: list) -> str:
        """Formata lista de campos para texto natural."""
        if len(campos) == 1:
            return campos[0]
        if len(campos) == 2:
            return f"{campos[0]} e {campos[1]}"
        return f"{', '.join(campos[:-1])} e {campos[-1]}"
