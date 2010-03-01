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
    if len(context['areas'])==31:
        u_perminssion=False
    else:
        u_perminssion=True
    try:
        tmp_del=[]
        time=None
        for i,dim in enumerate(dimension):
            if dim['default_dim']['value']:
                tmp_del.append(i)
        tmp_del.reverse()
        for j in tmp_del:
            dimension.pop(j)
        for x,date_time in enumerate(dimension):
            if date_time['name']['value'] == "date":
                global MAX_DISPLAY_DIMENSION
                time = date_time
                dimension.pop(x)
                MAX_DISPLAY_DIMENSION=3
    except:
        pass
    if len(dimension) <= MAX_DISPLAY_DIMENSION:
        return {'main_di': dimension,'u_p': u_perminssion,'time':time}
    else:
        return {'main_di': dimension[:MAX_DISPLAY_DIMENSION], 'all_di': dimension[MAX_DISPLAY_DIMENSION:],'u_p': u_perminssion,'time':time}

@stringfilter
@register.filter
def cut(value):
    if len(value)>6:
        value=value[:5]+"..."
    return value

@stringfilter
@register.filter
def perm(value):
    if value == "provname":
            return "disabled='disabled'"
    return ""
