# analysis/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplie une valeur par un argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0