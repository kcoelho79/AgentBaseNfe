"""
Comando para expirar sessões antigas automaticamente.

Uso:
    python manage.py expire_sessions
    
Pode ser executado via cron job para limpeza periódica.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.db_models import SessionSnapshot
from apps.core.states import SessionState
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Expira sessões que ultrapassaram o TTL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas mostra quais sessões seriam expiradas sem modificá-las',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Buscar sessões não-terminais que podem estar expiradas
        sessoes_ativas = SessionSnapshot.objects.exclude(
            estado__in=SessionState.terminal_states()
        )
        
        expiradas = 0
        verificadas = 0
        
        for snapshot in sessoes_ativas:
            verificadas += 1
            
            if snapshot.is_expired():
                expiradas += 1
                
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'[DRY-RUN] Sessão {snapshot.sessao_id} '
                            f'(telefone: {snapshot.telefone}, estado: {snapshot.estado}) '
                            f'seria expirada'
                        )
                    )
                else:
                    # Atualizar estado para expirado
                    snapshot.estado = SessionState.EXPIRADO.value
                    snapshot.snapshot_reason = 'expired'
                    snapshot.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Sessão {snapshot.sessao_id} '
                            f'(telefone: {snapshot.telefone}) expirada'
                        )
                    )
                    
                    logger.info(
                        f'Sessão expirada automaticamente: {snapshot.sessao_id}',
                        extra={
                            'telefone': snapshot.telefone,
                            'estado_anterior': snapshot.estado
                        }
                    )
        
        # Resumo
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Sessões verificadas: {verificadas}'))
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'Sessões que seriam expiradas: {expiradas}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Sessões expiradas: {expiradas}')
            )
