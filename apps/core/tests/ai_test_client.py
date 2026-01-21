"""
AI Test Client - IA que simula usuário conversando com o sistema de NFSe.

Usa OpenAI para gerar mensagens realistas de um usuário querendo emitir nota fiscal,
permitindo testes automatizados de conversação.
"""

import json
import logging
import httpx
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)


class TestResult(Enum):
    """Resultado do teste."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class TestScenario:
    """Define um cenário de teste."""
    name: str
    description: str
    persona_prompt: str
    dados_nota: Dict[str, Any]
    max_turns: int = 10
    expected_result: TestResult = TestResult.SUCCESS
    expected_final_state: str = "aguardando_confirmacao"
    should_confirm: bool = True  # Se deve confirmar a nota no final


@dataclass
class ConversationTurn:
    """Uma rodada de conversa."""
    turn_number: int
    user_message: str
    bot_response: str


@dataclass
class TestExecution:
    """Resultado da execução de um teste."""
    scenario: TestScenario
    result: TestResult
    conversation: List[ConversationTurn] = field(default_factory=list)
    final_state: Optional[str] = None
    error_message: Optional[str] = None
    total_turns: int = 0


class AITestClient:
    """
    Cliente de teste que usa IA para simular um usuário.

    A IA recebe um cenário (persona + dados da nota) e conversa naturalmente
    com o sistema até completar o objetivo ou atingir limite de turnos.
    """

    SYSTEM_PROMPT = """Você é um usuário simulado testando um sistema de emissão de notas fiscais via WhatsApp.

CONTEXTO:
Você quer emitir uma nota fiscal e vai conversar com um bot para fornecer os dados necessários.

SEU OBJETIVO:
Fornecer os seguintes dados de forma natural, como um usuário real faria:
{dados_nota}

REGRAS DE COMPORTAMENTO:
1. Converse de forma NATURAL, como alguém digitando no WhatsApp
2. Você pode fornecer todos os dados de uma vez OU aos poucos (mais realista)
3. Se o bot pedir algum dado, forneça-o
4. Se o bot mostrar um "espelho" da nota pedindo confirmação, responda "sim" para confirmar
5. Se cometer erro (CNPJ errado), corrija quando o bot apontar
6. NÃO invente dados além dos fornecidos acima
7. Seja breve e direto, como no WhatsApp

PERSONA:
{persona}

IMPORTANTE:
- Responda APENAS com a mensagem do usuário, sem explicações
- Uma mensagem por vez
- Mantenha o tom informal de WhatsApp
"""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        """
        Inicializa o cliente de teste.

        Args:
            base_url: URL base do servidor
            api_key: Chave da API OpenAI (usa settings se não fornecida)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key)
        self.http_client = httpx.Client(timeout=30.0)

    def _build_system_prompt(self, scenario: TestScenario) -> str:
        """Constrói o prompt do sistema para o cenário."""
        dados_str = json.dumps(scenario.dados_nota, indent=2, ensure_ascii=False)
        return self.SYSTEM_PROMPT.format(
            dados_nota=dados_str,
            persona=scenario.persona_prompt
        )

    def _generate_user_message(
        self,
        scenario: TestScenario,
        conversation_history: List[Dict[str, str]],
        last_bot_response: Optional[str] = None
    ) -> str:
        """
        Gera próxima mensagem do usuário usando IA.

        Args:
            scenario: Cenário de teste
            conversation_history: Histórico da conversa
            last_bot_response: Última resposta do bot

        Returns:
            Mensagem gerada pelo usuário simulado
        """
        messages = [
            {"role": "system", "content": self._build_system_prompt(scenario)}
        ]

        # Adiciona histórico
        for turn in conversation_history:
            messages.append({"role": "assistant", "content": f"[BOT]: {turn['bot']}"})
            messages.append({"role": "user", "content": turn['user']})

        # Adiciona última resposta do bot se houver
        if last_bot_response:
            messages.append({"role": "assistant", "content": f"[BOT]: {last_bot_response}"})
            messages.append({"role": "user", "content": "Agora responda como o usuário:"})
        else:
            messages.append({"role": "user", "content": "Inicie a conversa pedindo para emitir a nota:"})

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=200,
            temperature=0.7
        )

        return response.choices[0].message.content.strip()

    def _send_message(self, telefone: str, mensagem: str) -> Dict[str, Any]:
        """
        Envia mensagem para o sistema.

        Args:
            telefone: Número de telefone do teste
            mensagem: Mensagem a enviar

        Returns:
            Resposta do servidor
        """
        response = self.http_client.post(
            f"{self.base_url}/send/",
            json={"telefone": telefone, "mensagem": mensagem},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()

    def _clear_session(self, telefone: str) -> None:
        """Limpa sessão antes do teste."""
        try:
            self.http_client.post(f"{self.base_url}/clear/{telefone}/")
        except Exception:
            pass  # Ignora erros ao limpar

    def _check_confirmation_request(self, response: str) -> bool:
        """Verifica se o bot está pedindo confirmação."""
        confirmation_keywords = [
            "confirma a emissão",
            "digite *sim*",
            "digite sim",
            "confirmar",
            "espelho da nota"
        ]
        response_lower = response.lower()
        return any(kw in response_lower for kw in confirmation_keywords)

    def _check_processing(self, response: str) -> bool:
        """Verifica se a nota está sendo processada."""
        processing_keywords = [
            "processamento",
            "processando",
            "em processamento",
            "protocolo"
        ]
        response_lower = response.lower()
        return any(kw in response_lower for kw in processing_keywords)

    def run_scenario(self, scenario: TestScenario, telefone: str = "5500000000001") -> TestExecution:
        """
        Executa um cenário de teste.

        Args:
            scenario: Cenário a executar
            telefone: Número de telefone para o teste

        Returns:
            Resultado da execução
        """
        execution = TestExecution(scenario=scenario, result=TestResult.ERROR)
        conversation_history = []

        logger.info(f"Iniciando teste: {scenario.name}")

        try:
            # Limpa sessão anterior
            self._clear_session(telefone)

            last_bot_response = None

            for turn in range(scenario.max_turns):
                # Gera mensagem do usuário
                user_message = self._generate_user_message(
                    scenario,
                    conversation_history,
                    last_bot_response
                )

                logger.debug(f"Turn {turn + 1} - User: {user_message}")

                # Envia para o sistema
                response = self._send_message(telefone, user_message)
                bot_response = response.get("resposta", "")

                logger.debug(f"Turn {turn + 1} - Bot: {bot_response[:100]}...")

                # Registra turno
                execution.conversation.append(ConversationTurn(
                    turn_number=turn + 1,
                    user_message=user_message,
                    bot_response=bot_response
                ))
                execution.total_turns = turn + 1

                # Guarda histórico para próxima iteração
                conversation_history.append({
                    "user": user_message,
                    "bot": bot_response
                })
                last_bot_response = bot_response

                # Verifica se chegou na confirmação
                if self._check_confirmation_request(bot_response):
                    execution.final_state = "aguardando_confirmacao"

                    if scenario.should_confirm:
                        # Confirma a nota
                        confirm_response = self._send_message(telefone, "sim")
                        execution.conversation.append(ConversationTurn(
                            turn_number=turn + 2,
                            user_message="sim",
                            bot_response=confirm_response.get("resposta", "")
                        ))
                        execution.total_turns += 1

                        if self._check_processing(confirm_response.get("resposta", "")):
                            execution.final_state = "processando"
                            execution.result = TestResult.SUCCESS
                        else:
                            execution.result = TestResult.FAILED
                            execution.error_message = "Confirmação não gerou processamento"
                    else:
                        execution.result = TestResult.SUCCESS

                    break

                # Verifica se já está processando (caso tenha confirmado automaticamente)
                if self._check_processing(bot_response):
                    execution.final_state = "processando"
                    execution.result = TestResult.SUCCESS
                    break

            else:
                # Atingiu limite de turnos
                execution.result = TestResult.TIMEOUT
                execution.error_message = f"Atingiu limite de {scenario.max_turns} turnos"

        except Exception as e:
            execution.result = TestResult.ERROR
            execution.error_message = str(e)
            logger.exception(f"Erro no teste {scenario.name}")

        finally:
            # Limpa sessão após teste
            self._clear_session(telefone)

        return execution

    def close(self):
        """Fecha conexões."""
        self.http_client.close()


# ==================== CENÁRIOS DE TESTE PRÉ-DEFINIDOS ====================

SCENARIOS = {
    "happy_path": TestScenario(
        name="Happy Path - Todos dados de uma vez",
        description="Usuário fornece todos os dados corretos de uma vez",
        persona_prompt="Você é um empresário experiente, direto e objetivo. Fornece todos os dados de uma vez.",
        dados_nota={
            "cnpj": "11222333000181",
            "valor": "1500.00",
            "descricao": "Serviços de consultoria empresarial"
        },
        max_turns=5,
        expected_result=TestResult.SUCCESS
    ),

    "incremental": TestScenario(
        name="Incremental - Dados aos poucos",
        description="Usuário fornece dados incrementalmente",
        persona_prompt="Você é um usuário novo, um pouco inseguro. Prefere fornecer um dado por vez.",
        dados_nota={
            "cnpj": "11222333000181",
            "valor": "2500.00",
            "descricao": "Desenvolvimento de software sob demanda"
        },
        max_turns=8,
        expected_result=TestResult.SUCCESS
    ),

    "cnpj_invalido_corrigido": TestScenario(
        name="CNPJ Inválido -> Corrigido",
        description="Usuário envia CNPJ inválido e depois corrige",
        persona_prompt="""Você é um usuário que vai cometer um erro no CNPJ primeiro.
Na primeira mensagem, envie o CNPJ errado: 12345678000199
Quando o bot disser que está errado, corrija para o CNPJ correto.""",
        dados_nota={
            "cnpj": "11222333000181",  # CNPJ correto para usar após erro
            "valor": "800.00",
            "descricao": "Manutenção de equipamentos"
        },
        max_turns=10,
        expected_result=TestResult.SUCCESS
    ),

    "descricao_curta": TestScenario(
        name="Descrição curta -> Detalhada",
        description="Usuário envia descrição muito curta e depois detalha",
        persona_prompt="""Você é um usuário apressado.
Primeiro, envie uma descrição muito curta (menos de 10 caracteres): "TI"
Quando o bot pedir mais detalhes, forneça a descrição completa.""",
        dados_nota={
            "cnpj": "11222333000181",
            "valor": "3000.00",
            "descricao": "Consultoria em tecnologia da informação e suporte técnico"
        },
        max_turns=10,
        expected_result=TestResult.SUCCESS
    ),

    "usuario_confuso": TestScenario(
        name="Usuário Confuso",
        description="Usuário que não sabe bem o que fazer",
        persona_prompt="""Você é um usuário confuso que nunca usou o sistema.
Comece perguntando "como faço pra emitir nota?" antes de fornecer os dados.
Siga as instruções do bot.""",
        dados_nota={
            "cnpj": "11222333000181",
            "valor": "500.00",
            "descricao": "Serviços de assessoria contábil"
        },
        max_turns=12,
        expected_result=TestResult.SUCCESS
    ),

    "cancelamento": TestScenario(
        name="Cancelamento",
        description="Usuário cancela a emissão no final",
        persona_prompt="Você é um usuário que muda de ideia. Quando pedir confirmação, responda 'não'.",
        dados_nota={
            "cnpj": "11222333000181",
            "valor": "1000.00",
            "descricao": "Serviços diversos"
        },
        max_turns=8,
        should_confirm=False,  # Não confirmar automaticamente
        expected_result=TestResult.SUCCESS,
        expected_final_state="aguardando_confirmacao"
    ),
}


def get_scenario(name: str) -> Optional[TestScenario]:
    """Retorna cenário pelo nome."""
    return SCENARIOS.get(name)


def list_scenarios() -> List[str]:
    """Lista nomes dos cenários disponíveis."""
    return list(SCENARIOS.keys())
