# apps/core/states.py
"""
Definição de estados da máquina de estados para sessões de NFSe.

Este módulo centraliza todos os estados possíveis e suas transições válidas,
prevenindo bugs causados por strings mágicas espalhadas pelo código.
"""

from enum import Enum
from typing import Set


class SessionState(str, Enum):
    """
    Estados possíveis da sessão de emissão de NFSe.
    
    Fluxo normal:
        coleta → dados_incompletos → aguardando_confirmacao → 
        processando → aprovado
    
    Estados terminais:
        - processando: Enviado para Tecnospeed
        - aprovado: NFSe emitida com sucesso
        - rejeitado: Rejeitada pela prefeitura
        - erro: Erro técnico na emissão
        - cancelado_usuario: Usuário cancelou
        - expirado: Sessão expirou (TTL)
    """
    
    # Estados ativos (sessão em andamento)
    COLETA = 'coleta'
    DADOS_INCOMPLETOS = 'dados_incompletos'
    AGUARDANDO_CONFIRMACAO = 'aguardando_confirmacao'
    
    # Estados de processamento/finalização
    PROCESSANDO = 'processando'
    APROVADO = 'aprovado'
    REJEITADO = 'rejeitado'
    ERRO = 'erro'
    
    # Estados de cancelamento
    CANCELADO_USUARIO = 'cancelado_usuario'
    EXPIRADO = 'expirado'
    
    @classmethod
    def terminal_states(cls) -> Set[str]:
        """
        Retorna conjunto de estados terminais (sessão finalizada).
        
        Sessões nesses estados não devem ser retornadas como "ativas"
        e não permitem novas transições.
        
        Returns:
            Set com valores dos estados terminais
        """
        return {
            cls.PROCESSANDO.value,
            cls.APROVADO.value,
            cls.REJEITADO.value,
            cls.ERRO.value,
            cls.CANCELADO_USUARIO.value,
            cls.EXPIRADO.value,
        }
    
    @classmethod
    def active_states(cls) -> Set[str]:
        """
        Retorna conjunto de estados ativos (sessão em andamento).
        
        Sessões nesses estados aceitam novas mensagens do usuário.
        
        Returns:
            Set com valores dos estados ativos
        """
        return {
            cls.COLETA.value,
            cls.DADOS_INCOMPLETOS.value,
            cls.AGUARDANDO_CONFIRMACAO.value,
        }
    
    @classmethod
    def choices(cls):
        """
        Retorna choices para uso em Django models.
        
        Returns:
            Lista de tuplas (valor, label) para CharField choices
        """
        return [
            (cls.COLETA.value, 'Coletando Dados'),
            (cls.DADOS_INCOMPLETOS.value, 'Dados Incompletos'),
            (cls.AGUARDANDO_CONFIRMACAO.value, 'Aguardando Confirmação'),
            (cls.PROCESSANDO.value, 'Processando'),
            (cls.APROVADO.value, 'Aprovado'),
            (cls.REJEITADO.value, 'Rejeitado'),
            (cls.ERRO.value, 'Erro'),
            (cls.CANCELADO_USUARIO.value, 'Cancelado pelo Usuário'),
            (cls.EXPIRADO.value, 'Expirado'),
        ]


# Mapeamento de transições válidas
# Chave: estado atual | Valor: conjunto de estados permitidos
VALID_TRANSITIONS = {
    SessionState.COLETA: {
        SessionState.DADOS_INCOMPLETOS,
        SessionState.AGUARDANDO_CONFIRMACAO,
        SessionState.EXPIRADO,
    },
    SessionState.DADOS_INCOMPLETOS: {
        SessionState.DADOS_INCOMPLETOS,  # loop: ainda falta dados
        SessionState.AGUARDANDO_CONFIRMACAO,
        SessionState.CANCELADO_USUARIO,
        SessionState.EXPIRADO,
    },
    SessionState.AGUARDANDO_CONFIRMACAO: {
        SessionState.PROCESSANDO,
        SessionState.CANCELADO_USUARIO,
        SessionState.EXPIRADO,
    },
    SessionState.PROCESSANDO: {
        SessionState.APROVADO,
        SessionState.REJEITADO,
        SessionState.ERRO,
    },
    # Estados terminais não têm transições válidas
    SessionState.APROVADO: set(),
    SessionState.REJEITADO: set(),
    SessionState.ERRO: set(),
    SessionState.CANCELADO_USUARIO: set(),
    SessionState.EXPIRADO: set(),
}


def is_valid_transition(from_state: str, to_state: str) -> bool:
    """
    Verifica se uma transição de estado é válida.
    
    Args:
        from_state: Estado atual (string)
        to_state: Estado destino (string)
        
    Returns:
        True se a transição é permitida, False caso contrário
        
    Examples:
        >>> is_valid_transition('coleta', 'dados_incompletos')
        True
        >>> is_valid_transition('aprovado', 'processando')
        False
        >>> is_valid_transition('invalid_state', 'coleta')
        False
    """
    try:
        from_enum = SessionState(from_state)
        to_enum = SessionState(to_state)
        return to_enum in VALID_TRANSITIONS.get(from_enum, set())
    except ValueError:
        # Estado inválido
        return False


def get_valid_next_states(current_state: str) -> Set[str]:
    """
    Retorna estados válidos a partir do estado atual.
    
    Args:
        current_state: Estado atual (string)
        
    Returns:
        Set com valores dos estados válidos para transição
        
    Examples:
        >>> get_valid_next_states('coleta')
        {'dados_incompletos', 'aguardando_confirmacao', 'expirado'}
    """
    try:
        state_enum = SessionState(current_state)
        return {s.value for s in VALID_TRANSITIONS.get(state_enum, set())}
    except ValueError:
        return set()
