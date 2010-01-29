from django import template
from django.template.defaultfilters import stringfilter

MAX_DISPLAY_DIMENSION = 4

register = template.Library()

@register.inclusion_tag('none.txt', takes_context=True)
def get_value(context, obj, key):
    value = obj.get(key)
    context['custom_value'] = value
    return {}
    

@register.inclusion_tag('cms_view_widget.html', takes_context=True)
def cms_view_type(context, name, value, mapping):
    options = mapping.get(name)

    if not options:
        type = 'text'
    else:
        try:
            dict(options)
            type = 'select'
        except:
            type = 'checkbox'

    return {'type': type, 
            'value': value, 
            'options': options, 
            'name': name
            }
    
@stringfilter
@register.filter
def truncateletters(value, num):

    try:
        num = int(num)
        if len(value) > num:
            value = "%s..." % value[:num-1]
    except:
        value = ''

    return value
    
@register.inclusion_tag('di_setting.html', takes_context=True)
def dimension_setting(context, dimension):
    try:
        tmp_del=[]
        for i,dim in enumerate(dimension):
            if dim['default_dim']['value']:
                tmp_del.append(i)
        tmp_del.reverse()
        for j in tmp_del:
            dimension.pop(j)
    except:
        pass
    return {'main_di': dimension}
#@register.filter
#def get_d(value,ud):
#    if value in ud:
#        return True
#    return False