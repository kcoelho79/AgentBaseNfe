#!/usr/bin/env python
"""
Script para executar testes de IA vs IA.

Uma IA simula um usuário conversando com o sistema de emissão de NFSe.

Uso:
    python manage.py shell < apps/core/tests/run_ai_tests.py

    Ou diretamente:
    python apps/core/tests/run_ai_tests.py [cenario]

Exemplos:
    python apps/core/tests/run_ai_tests.py                    # Todos os cenários
    python apps/core/tests/run_ai_tests.py happy_path         # Cenário específico
    python apps/core/tests/run_ai_tests.py --list             # Lista cenários
    python apps/core/tests/run_ai_tests.py --interactive      # Modo interativo
"""

import os
import sys
import argparse
from datetime import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.core.tests.ai_test_client import (
    AITestClient,
    TestResult,
    TestExecution,
    SCENARIOS,
    list_scenarios,
    get_scenario
)


class Colors:
    """Cores para output no terminal."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header():
    """Imprime cabeçalho."""
    print(f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════════╗
║                    🤖 AI vs AI - Teste de NFSe                       ║
║                                                                       ║
║   Uma IA simula usuário conversando com o sistema de emissão         ║
╚══════════════════════════════════════════════════════════════════════╝
{Colors.RESET}
""")


def print_scenario_header(scenario_name: str, description: str):
    """Imprime cabeçalho do cenário."""
    print(f"""
{Colors.BLUE}{'═' * 70}
{Colors.BOLD}📋 Cenário: {scenario_name}{Colors.RESET}
{Colors.BLUE}{description}
{'═' * 70}{Colors.RESET}
""")


def print_conversation(execution: TestExecution, verbose: bool = True):
    """Imprime a conversa."""
    if not verbose:
        return

    print(f"\n{Colors.MAGENTA}💬 Conversa:{Colors.RESET}\n")

    for turn in execution.conversation:
        print(f"  {Colors.CYAN}[Turn {turn.turn_number}]{Colors.RESET}")
        print(f"  {Colors.GREEN}👤 Usuário:{Colors.RESET} {turn.user_message}")

        # Trunca resposta longa do bot
        bot_response = turn.bot_response
        if len(bot_response) > 200:
            bot_response = bot_response[:200] + "..."
        print(f"  {Colors.BLUE}🤖 Bot:{Colors.RESET} {bot_response}")
        print()


def print_result(execution: TestExecution):
    """Imprime resultado do teste."""
    result_colors = {
        TestResult.SUCCESS: Colors.GREEN,
        TestResult.FAILED: Colors.RED,
        TestResult.TIMEOUT: Colors.YELLOW,
        TestResult.ERROR: Colors.RED,
    }

    result_icons = {
        TestResult.SUCCESS: "✅",
        TestResult.FAILED: "❌",
        TestResult.TIMEOUT: "⏱️",
        TestResult.ERROR: "💥",
    }

    color = result_colors.get(execution.result, Colors.RESET)
    icon = result_icons.get(execution.result, "?")

    print(f"""
{Colors.BOLD}📊 Resultado:{Colors.RESET}
  {icon} {color}{execution.result.value.upper()}{Colors.RESET}
  📈 Turnos: {execution.total_turns}
  🔄 Estado final: {execution.final_state or 'N/A'}
""")

    if execution.error_message:
        print(f"  {Colors.RED}⚠️ Erro: {execution.error_message}{Colors.RESET}")


def run_scenario(client: AITestClient, scenario_name: str, verbose: bool = True) -> TestExecution:
    """Executa um cenário."""
    scenario = get_scenario(scenario_name)
    if not scenario:
        print(f"{Colors.RED}❌ Cenário '{scenario_name}' não encontrado{Colors.RESET}")
        return None

    print_scenario_header(scenario.name, scenario.description)

    # Telefone único para cada cenário (evita conflitos)
    telefone = f"55000000{hash(scenario_name) % 10000:04d}"

    print(f"  📱 Telefone teste: {telefone}")
    print(f"  🎯 Resultado esperado: {scenario.expected_result.value}")
    print(f"  🔄 Max turnos: {scenario.max_turns}")

    execution = client.run_scenario(scenario, telefone)

    print_conversation(execution, verbose)
    print_result(execution)

    # Verifica se passou
    passed = execution.result == scenario.expected_result
    if passed:
        print(f"  {Colors.GREEN}✅ PASSOU{Colors.RESET}")
    else:
        print(f"  {Colors.RED}❌ FALHOU (esperado: {scenario.expected_result.value}){Colors.RESET}")

    return execution


def run_all_scenarios(client: AITestClient, verbose: bool = False) -> dict:
    """Executa todos os cenários."""
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "executions": []
    }

    for scenario_name in list_scenarios():
        execution = run_scenario(client, scenario_name, verbose)
        if execution:
            results["total"] += 1
            results["executions"].append(execution)

            if execution.result == execution.scenario.expected_result:
                results["passed"] += 1
            else:
                results["failed"] += 1

        print("\n" + "─" * 70 + "\n")

    return results


def print_summary(results: dict):
    """Imprime resumo dos testes."""
    print(f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════════╗
║                         📊 RESUMO DOS TESTES                         ║
╚══════════════════════════════════════════════════════════════════════╝
{Colors.RESET}
  Total de testes: {results['total']}
  {Colors.GREEN}✅ Passou: {results['passed']}{Colors.RESET}
  {Colors.RED}❌ Falhou: {results['failed']}{Colors.RESET}

  Taxa de sucesso: {results['passed'] / results['total'] * 100:.1f}%
""")

    # Detalhes dos que falharam
    failed = [e for e in results['executions'] if e.result != e.scenario.expected_result]
    if failed:
        print(f"\n{Colors.RED}Testes que falharam:{Colors.RESET}")
        for e in failed:
            print(f"  - {e.scenario.name}: {e.result.value} (esperado: {e.scenario.expected_result.value})")


def interactive_mode(client: AITestClient):
    """Modo interativo para rodar testes."""
    while True:
        print(f"\n{Colors.CYAN}Cenários disponíveis:{Colors.RESET}")
        for i, name in enumerate(list_scenarios(), 1):
            scenario = get_scenario(name)
            print(f"  {i}. {name} - {scenario.description}")

        print(f"\n  {len(list_scenarios()) + 1}. Rodar TODOS")
        print(f"  0. Sair")

        try:
            choice = input(f"\n{Colors.BOLD}Escolha: {Colors.RESET}").strip()

            if choice == "0":
                break
            elif choice == str(len(list_scenarios()) + 1):
                results = run_all_scenarios(client, verbose=True)
                print_summary(results)
            elif choice.isdigit() and 1 <= int(choice) <= len(list_scenarios()):
                scenario_name = list_scenarios()[int(choice) - 1]
                run_scenario(client, scenario_name, verbose=True)
            else:
                # Tenta como nome de cenário
                if choice in list_scenarios():
                    run_scenario(client, choice, verbose=True)
                else:
                    print(f"{Colors.RED}Opção inválida{Colors.RESET}")

        except KeyboardInterrupt:
            break

    print(f"\n{Colors.CYAN}Até logo! 👋{Colors.RESET}\n")


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Testes AI vs AI para sistema de NFSe",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python run_ai_tests.py                    # Todos os cenários
  python run_ai_tests.py happy_path         # Cenário específico
  python run_ai_tests.py --list             # Lista cenários
  python run_ai_tests.py --interactive      # Modo interativo
  python run_ai_tests.py --verbose          # Com detalhes da conversa
        """
    )

    parser.add_argument(
        "scenario",
        nargs="?",
        help="Nome do cenário a executar (opcional)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Lista cenários disponíveis"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Modo interativo"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostra conversa completa"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="URL base do servidor (default: http://localhost:8000)"
    )

    args = parser.parse_args()

    print_header()

    # Lista cenários
    if args.list:
        print(f"{Colors.CYAN}Cenários disponíveis:{Colors.RESET}\n")
        for name in list_scenarios():
            scenario = get_scenario(name)
            print(f"  {Colors.BOLD}{name}{Colors.RESET}")
            print(f"    {scenario.description}")
            print(f"    Dados: {scenario.dados_nota}")
            print()
        return

    # Verifica se servidor está rodando
    import httpx
    try:
        response = httpx.get(f"{args.url}/health/", timeout=5)
    except Exception:
        print(f"{Colors.RED}❌ Servidor não está respondendo em {args.url}{Colors.RESET}")
        print(f"   Inicie o servidor com: python manage.py runserver")
        return

    # Cria cliente
    client = AITestClient(base_url=args.url)

    try:
        # Modo interativo
        if args.interactive:
            interactive_mode(client)
            return

        # Cenário específico
        if args.scenario:
            run_scenario(client, args.scenario, verbose=True)
            return

        # Todos os cenários
        print(f"{Colors.YELLOW}Executando todos os cenários...{Colors.RESET}\n")
        results = run_all_scenarios(client, verbose=args.verbose)
        print_summary(results)

    finally:
        client.close()


if __name__ == "__main__":
    main()
