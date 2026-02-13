import re
import logging
from typing import Literal

logger = logging.getLogger(__name__)

MessageType = Literal['saudacao', 'agradecimento', 'pergunta', 'cancelamento', 'dados']


class MessageClassifier:
    """
    Classifica mensagens para roteamento sem usar IA.

    Decide se a mensagem e saudacao, agradecimento, pergunta pura,
    cancelamento ou contem dados para extracao.

    Regra: se a mensagem contem numeros, provavelmente tem dados
    (CNPJ, valor) e deve ir para extracao mesmo que tenha pergunta.
    """

    SAUDACOES = {
        'oi', 'ola', 'olá', 'bom dia', 'boa tarde', 'boa noite',
        'hey', 'eae', 'e ai', 'fala', 'salve', 'opa',
    }

    AGRADECIMENTOS = {
        'obrigado', 'obrigada', 'valeu', 'vlw', 'thanks',
        'brigado', 'brigada', 'grato', 'grata', 'agradeco',
    }

    CANCELAMENTOS = {
        'cancelar', 'cancela', 'desisto', 'para', 'parar',
        'nao quero', 'deixa pra la', 'esquece',
    }

    INDICADORES_PERGUNTA = {
        'como', 'qual', 'que', 'quem', 'onde', 'quando',
        'por que', 'porque', 'quanto', 'quantos',
        'o que', 'pra que', 'precisa', 'posso', 'pode',
        'funciona', 'faz', 'aceita', 'serve',
    }

    @classmethod
    def classify(cls, mensagem: str) -> MessageType:
        """
        Classifica a mensagem do usuario.

        Args:
            mensagem: Texto da mensagem

        Returns:
            Tipo da mensagem: 'saudacao', 'agradecimento', 'pergunta',
                              'cancelamento' ou 'dados'
        """
        msg = mensagem.strip().lower()
        msg_clean = re.sub(r'[^\w\s]', '', msg)
        words = msg_clean.split()
        tem_numeros = bool(re.search(r'\d{2,}', msg))

        # Se tem numeros, provavelmente contem dados (CNPJ, valor)
        # Vai direto para extracao, mesmo que tenha pergunta junto
        if tem_numeros:
            logger.debug(f"Classificado como 'dados' (contem numeros): {msg[:50]}")
            return 'dados'

        # Cancelamento
        if msg_clean in cls.CANCELAMENTOS or msg in cls.CANCELAMENTOS:
            logger.debug(f"Classificado como 'cancelamento': {msg[:50]}")
            return 'cancelamento'

        # Saudacao pura (sem dados misturados)
        if cls._is_saudacao(msg_clean, words):
            logger.debug(f"Classificado como 'saudacao': {msg[:50]}")
            return 'saudacao'

        # Agradecimento
        if cls._is_agradecimento(words):
            logger.debug(f"Classificado como 'agradecimento': {msg[:50]}")
            return 'agradecimento'

        # Pergunta pura (sem dados)
        if cls._is_pergunta(msg, words):
            logger.debug(f"Classificado como 'pergunta': {msg[:50]}")
            return 'pergunta'

        # Default: assume que contem dados para extracao
        logger.debug(f"Classificado como 'dados' (default): {msg[:50]}")
        return 'dados'

    @classmethod
    def _is_saudacao(cls, msg_clean: str, words: list) -> bool:
        """Verifica se e saudacao pura."""
        # Mensagem curta que e so saudacao
        if msg_clean in cls.SAUDACOES:
            return True

        # "oi tudo bem", "bom dia pessoal"
        if len(words) <= 4 and words[0] in cls.SAUDACOES:
            return True

        # "bom dia" / "boa tarde" (duas palavras)
        if len(words) >= 2:
            duas = f"{words[0]} {words[1]}"
            if duas in cls.SAUDACOES and len(words) <= 5:
                return True

        return False

    @classmethod
    def _is_agradecimento(cls, words: list) -> bool:
        """Verifica se e agradecimento."""
        return any(word in cls.AGRADECIMENTOS for word in words)

    @classmethod
    def _is_pergunta(cls, msg: str, words: list) -> bool:
        """Verifica se e pergunta pura (sem dados)."""
        if '?' in msg:
            return True

        # Comeca com indicador de pergunta
        for indicador in cls.INDICADORES_PERGUNTA:
            if msg.startswith(indicador + ' ') or msg.startswith(indicador + ','):
                return True

        # "o que e", "pra que serve"
        if len(words) >= 2:
            duas = f"{words[0]} {words[1]}"
            if duas in {'o que', 'pra que', 'por que', 'como que'}:
                return True

        return False
