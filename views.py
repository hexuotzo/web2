# -*- coding: utf-8 -*-
import syslog
from pyExcelerator import *
from OpenFlashChart import Chart
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.contrib import auth
from django.contrib.auth.models import *
from django.template import Context, loader, RequestContext
from django.core.urlresolvers import reverse
from web2.models import View, TIME_NAME_MAPPING, VIEW_TYPE, City, UserDimension,DataSet
from web2.utils import view_permission, bind_query_range, show_view_options, COLUMN_OPTION_MAPPING, format_table, bind_dimension_options, get_dimension, ViewObj, SQLGenerator, list2dict, merge_date, execute_sql, get_user_dimension, format_date ,NON_NUMBER_FIELD,get_res
from web2.excel import *
import time

X_LABELS = {'bar': ('provname', 'cityname', 'begin_date', 'end_date'),
            'line': ('provname', 'cityname', 'begin_date', 'end_date'),
            }

CHART_COLOR = ('#D54648', '#008E8F', '#FFF467', '#AFD8F6', '#8CBA02', '#A287BE')

def show_table(request):
    """
    execute sql and fetch results.
    """
    if request.method == 'GET':
        user_id = request.user.id
        data = request.GET.copy()
        try:
            view_id = data.get('view_id')
            data.pop('view_id')
            v = View.objects.get(id=view_id)
        except:
            raise Http404
        # get container div, sent it back to client and put table in that container.
        container_id = data.get('container')
        data.pop('container')
        view_obj = ViewObj(v, request)
        u_d = get_user_dimension(user_id,view_id)
        sql = SQLGenerator(data, view_obj, u_d,request).get_sql().encode('utf-8')
        view_id=view_obj.obj['view_id']
        res = execute_sql(sql)
        t = loader.get_template('results.html')
        if len(u_d)>0:
            u_dimension=u_d.split(",")
        else:
            u_dimension=[]
        res = format_table(res, view_obj,u_dimension)
        head,body = get_res(res)
        html = t.render(Context({'res': res,
                                'head':head,
                                'body':body,
                                'ud':u_dimension,
                                'headers': view_obj.get_headers(),
                                'table_name': view_obj.get_body()['dataset'].cname
                                }))
        json_text = simplejson.dumps({'container':container_id,'content':html})
        return HttpResponse(json_text)
    else:
        raise Http404

def down_excel(request):
    """
    download excel file.
    """
    if request.method == 'GET':
        user_id=request.user.id
        data = request.GET.copy()
        try:
            view_id = data.get('view_id')
            data.pop('view_id')
            v = View.objects.get(id=view_id)
        except:
            raise Http404

        view_obj = ViewObj(v, request)
        u_d = get_user_dimension(user_id,view_id)        
        sql = SQLGenerator(data,view_obj,u_d,request).get_sql().encode('utf-8')
        res = execute_sql(sql)

        res = format_table(res, view_obj,u_d)                
        w = Workbook()
        ws = w.add_sheet('result')

        if not res:
            response = HttpResponse("",mimetype='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename=result.xls'
            return response
            
        #write to header
        for k,header in enumerate(res[0]):
            ws.write(0, k, header['cname']['value'])

        res.pop(0)
        
        #write to data
        for i, line in enumerate(res):
            for j,cell in enumerate(line):
                if isinstance(cell['value'],str):
                    new_cell = unicode(cell['value'],'utf8')
                else:
                    new_cell = str(cell['value'])
                ws.write(i+1,j, new_cell)
     
        response = HttpResponse(w.save_stream(),mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=result.xls'
        return response
    else:
        raise Http404

def show_view(request):
    """
    display the corresponding views.
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('../login/')
    
    views = request.session.get('view', {})
    areas = request.session.get('area', [])
    if request.method == 'GET':
        cname = request.GET.get('cname')
        view = View.objects.filter(cname=cname)
        if not cname:
            key = views.iterkeys()

            try:
                key = key.next()
                cname = views[key][0][0]
            except:
                raise Http404
        has_permission = view_permission(views, cname)

        if cname and has_permission:
            try:
                data = get_view_obj(cname,request)
                help = view[0].dataset.name
                return render_to_response('view.html', {'json': data, 
                                                        'views':views, 
                                                        'areas':areas,
                                                        'cname':cname,
                                                        'help':help
                                                        }, context_instance=RequestContext(request))                
            except:
                help=""
            return render_to_response('view.html', {'views':views, 
                                                    'areas':areas,
                                                    'help':help
                                                    }, context_instance=RequestContext(request))
        else:
            raise Http404
    else:
        return Http404

def get_view_obj(cname, request, time_type=None):
    """
        return a list of objects representing view structure
    """
    data = []
    try:
        if time_type:
            views = View.objects.filter(cname=cname, time_type=time_type)
        else:
            views = View.objects.filter(cname=cname).order_by('time_type')
        for v in views:
            body = simplejson.loads(v.body)
            body_dict = list2dict(body)
            body_dict['view_id'] = v.id
            body_dict['time_type'] = TIME_NAME_MAPPING.get(str(v.time_type))
            body_dict['table'] = v.dataset.name
            bind_query_range(body_dict, request)
            dimension = body_dict.get('dimension', {}).get('values', [])
            bind_dimension_options(dimension, request.user.id, v.id)        
            data.append(body_dict)
    except:
        pass
    
    return data

def index(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/login/')

    views = request.session.get('view', {})
    key = views.iterkeys()
    try:
        key = key.next()
        cname = views[key][0][0]
    except:
        return render_to_response('welcome.html', locals())

    url = reverse("show_view")

    return HttpResponseRedirect(url)


def login(request):
    if request.user.is_authenticated():
        set_session(request)
        return HttpResponseRedirect('../')
    error_info = ""
    if request.POST:
        user = auth.authenticate(username=request.POST['f_user'],
                        password=request.POST['f_psw'])
        if user is not None:
            auth.login(request, user)
            set_session(request)
            #这个地方指定登陆成功后跳转的页面
            return HttpResponseRedirect('../login/')
        else:
            error_info=('用户名或密码错误')
    return render_to_response('index.html', {'error_info': error_info})

def logout(request):
    auth.logout(request)
    return HttpResponseRedirect('../login/')

def set_session(request):
    try:
        group_id = request.user.groups.all()[0].id
        if group_id:
            groups = Group.objects.get(id=group_id)
            area = []
            view_dict = {}
            view_sub = {}
            types = dict(VIEW_TYPE)
            for i in groups.area.all():
                area.append(i.pname)
            for j in groups.view.all():
                view = View.objects.get(id=j.id)
                view_list = view_dict.setdefault(types[view.view_type], [])
                cnames = [i[0] for i in view_list]
                if view.cname in cnames:
                    index = cnames.index(view.cname)
                    view_list[index].append(view.id)
                else:
                    view_list.append([view.cname, view.id])

            request.session['area'] = area
            request.session['view'] = view_dict
    except:
        print 'set session error'

    return request

def area(request):
    if request.POST:
        province = request.POST['province']
        citys = City.objects.filter(pname__in=province.split(','))
        return render_to_response('city.html', {'citys':citys})
    return HttpResponse("ok")

def show_option(request):
    if request.method == 'POST':
        dataset_id = request.POST.get('dataset')
        view_id = request.POST.get('view_id')        
        options = show_view_options(dataset_id, view_id)
        options = merge_date(options)
        return render_to_response('options.html', {'options': options,
                                                   'option_mapping': COLUMN_OPTION_MAPPING,
                                                   })
    else:
        raise Http404


def draw_graph(request):
    """
    execute sql and draw flash.
    """
    if request.method == 'GET':
        uid=request.user.id
        data = request.GET.copy()
        try:
            view_id = data.get('view_id')
            data.pop('view_id')
            v = View.objects.get(id=view_id)
        except:
            raise Http404

        type = data.get('type')
        data.pop('type')
        view_obj = ViewObj(v, request)
        u_d = get_user_dimension(uid,view_id)
        sql = SQLGenerator(data, view_obj, u_d,request).get_sql().encode('utf-8')
        res = execute_sql(sql)        

        # default chart type is bar
        if not type:
            type = "bar"

        chart = Chart()
        chart.title.text = v.cname
        headers = view_obj.get_headers()
        header_name = [ i['name']['value'] for i in headers]
        header_cname = [ i['cname']['value'] for i in headers]
       
        # generate x labels
        indexes = []
        label_keys = X_LABELS.get(type, {})
        for name in label_keys:
            try:
                index = header_name.index(name)
            except:
                index = -1
            indexes.append(index)
        is_day_report = True if view_obj.get_body()['time_type']['name'] == 'day' else False
        
        labels = []
        for line in res:
            label = []
            for i, line_index in enumerate(indexes):
                if line_index >= 0:
                    value = line[line_index]
                    try:
                        value = value.decode("utf-8")
                    except:
                        value = str(value)
                else:
                    value = ''
                    
                label.append(value)
                
                if i == len(indexes) - 1:
                    if is_day_report:
                        label.pop()
                        label[-1] = format_date(label[-1])
                    else:
                        end_date = label.pop()
                        begin_date = label.pop()
                        date_list = []
                        if begin_date:
                            date_list.append(format_date(begin_date))
                        if end_date:
                            date_list.append(format_date(end_date))
                        label.append("~".join(date_list))
            labels.append("\n".join(label))
        chart.x_axis = {'labels': {"labels": labels}}

        graph_els = filter(lambda x:x not in NON_NUMBER_FIELD, header_name)        

        els = []
        max_values = []

        # add chart elements one by one.
        if res:
            for i, el in enumerate(graph_els):
                index = header_name.index(el)
                values = [int(line[index]) for line in res]
                max_values.append(max(values))
                graph = Chart()
                graph.type = type
                graph.values = values
                graph.text = header_cname[index]
                graph.alpha = 0.5
                graph.fontsize = 12
                graph.tip = '%s<br>#val#' % header_cname[index]
                graph.colour = CHART_COLOR[i]
                els.append(graph)

        chart.elements = els

        if res:
            max_value = max(max_values)
            step = max_value/10
            chart.y_axis = {'max': max_value, 'min': 0, 'steps': step}
        return HttpResponse(chart.create())

def change_dimension(request):
    """
    change user dimensions
    """
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        view_id = request.POST.get('view_id')
        dimension = request.POST.get('dimension', '')

        # hack, replace date with begin_date and end_date
        dimension = dimension.replace('date', 'begin_date,end_date')
        try:
            user = User.objects.get(pk=user_id)
            view = View.objects.get(pk=view_id)
        except:
            raise Http404
        u_d, created = UserDimension.objects.get_or_create(user=user,view=view)
        u_d.dimension = dimension
        u_d.save()
        return HttpResponse("")
    else:
        raise Http404

def help(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('../login/')
    views = request.session.get('view', {})
    areas = request.session.get('area', [])
    
    if request.method == 'GET':
        cname = request.GET.get('cname')
    
        if not cname:
            key = views.iterkeys()
    
            try:
                key = key.next()
                cname = views[key][0][0]
            except:
                raise Http404
    
        has_permission = view_permission(views, cname)
    
        if cname and has_permission:
            data = get_view_obj(cname,request)
            cname="帮助"
            return render_to_response('help/main.html', locals(), context_instance=RequestContext(request))
        else:
            raise Http404
    else:
        return Http404

def get_help(request,name):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('../login/')
    views = request.session.get('view', {})
    areas = request.session.get('area', [])
    
    if request.method == 'GET':
        cname = request.GET.get('cname')
    
        if not cname:
            key = views.iterkeys()
    
            try:
                key = key.next()
                cname = views[key][0][0]
            except:
                raise Http404
    
        has_permission = view_permission(views, cname)
    
        if cname and has_permission:
            data = get_view_obj(cname,request)
            cname="帮助"
            page="help/%s.html"%name
            return render_to_response(page, locals(), context_instance=RequestContext(request))
        else:
            raise Http404
    else:
        return Http404
    
def test(request):
    abc=[]
    c={'a':'123','b':'324'}
    return render_to_response('test.html',locals())
