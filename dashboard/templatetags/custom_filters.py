from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()

@register.filter(name='json_script')
def json_script(value, element_id):
    return mark_safe(
        f'<script id="{element_id}" type="application/json">{json.dumps(value, indent=2)}</script>'
    )