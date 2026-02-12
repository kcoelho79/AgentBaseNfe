"""
Template filters para formatação de tempo.
"""
from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def timesince_short(value):
    """
    Retorna tempo decorrido em formato curto.
    
    Exemplos:
        - "2h 15min"
        - "5min"
        - "3d 4h"
        - "agora"
    """
    if not value:
        return "—"
    
    now = timezone.now()
    diff = now - value
    
    total_seconds = int(diff.total_seconds())
    
    if total_seconds < 60:
        return "agora"
    
    minutes = total_seconds // 60
    hours = minutes // 60
    days = hours // 24
    
    if days > 0:
        remaining_hours = hours % 24
        if remaining_hours > 0:
            return f"{days}d {remaining_hours}h"
        return f"{days}d"
    
    if hours > 0:
        remaining_minutes = minutes % 60
        if remaining_minutes > 0:
            return f"{hours}h {remaining_minutes}min"
        return f"{hours}h"
    
    return f"{minutes}min"
