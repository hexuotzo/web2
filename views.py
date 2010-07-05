# -*- coding: utf-8 -*-
import syslog
import urllib
import time
from pyExcelerator import *
from OpenFlashChart import Chart
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.views.decorators.cache import cache_page
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.contrib import auth
from django.contrib.auth.models import *
from django.contrib.auth.forms import PasswordChangeForm
from django.template import Context, loader, RequestContext
from django.core.urlresolvers import reverse
from web2.settings import WEB2_VERSION
from web2.models import View, Flashurl, TIME_NAME_MAPPING, VIEW_TYPE, City, UserDimension,DataSet,TIME_CHOICES
from web2.utils import view_permission, bind_query_range, show_view_options, COLUMN_OPTION_MAPPING, format_table, bind_dimension_options, get_dimension, ViewObj, SQLGenerator, list2dict, merge_date, execute_sql,get_relation_query,multiple_array, get_next,showtable_500, get_user_dimension,get_default_date,format_date , NON_NUMBER_FIELD, BAR_FORMAT_FIELD, DATE_FORMAT_FIELD, get_res,country_session,query_session,HIGHEST_AUTHORITY,MAX_DATA
from web2.excel import *
import time

X_LABELS = {'bar': ('provname', 'cityname'),
            'line': ('begin_date', 'end_date'),
            }

CHART_COLOR = ('#D54648', '#ad8bcf', '#3a0e53', '#94480a', '#ef07ab', '#339b92', '#008E8F', '#FFF467', '#AFD8F6', '#8CBA02', '#A287BE','#D54648', '#ad8bcf', '#3a0e53', '#94480a', '#ef07ab', '#339b92', '#008E8F', '#FFF467', '#AFD8F6', '#8CBA02', '#A287BE','#D54648', '#ad8bcf', '#3a0e53', '#94480a', '#ef07ab', '#339b92', '#008E8F', '#FFF467', '#AFD8F6', '#8CBA02', '#A287BE','#D54648', '#ad8bcf', '#3a0e53', '#94480a', '#ef07ab', '#339b92', '#008E8F', '#FFF467', '#AFD8F6', '#8CBA02', '#A287BE')


def show_table(request):
    """
    execute sql and fetch results.
    """
    if request.method == 'POST':
        user_id = request.user.id
        data = request.POST.copy()
        data.pop('timestamp')
        try:
            provlist=data['provname'].split(",")
        except:
            provlist=[]
        provlist=len(provlist)
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
        t = loader.get_template('results.html')
        try:
            v_query = view_obj.get_query()
            v_query = query_session(v_query)
            u_d = get_user_dimension(user_id,view_id)
            sql = SQLGenerator(data, view_obj, u_d,request).get_sql().encode('utf-8')
            sql = "%s limit %s"%(sql,MAX_DATA+10)
            view_id = view_obj.obj['view_id']
            res = execute_sql(sql)
            if len(u_d)>0:
                u_dimension=u_d.split(",")
            else:
                u_dimension=[]
            res = format_table(res, view_obj,u_dimension)
            head,body,counts,d_count = get_res(res)
            tips,u_session="",True
            #在分省市的报表中，没有选省市维度，也没全选省条件，弹出提示
            if country_session(u_d) and provlist<HIGHEST_AUTHORITY and v_query:
                tips = "如果要看分省数据，请在维度设置中勾选省份<p>如果查看全国数据，请将省条件全选"
                u_session = False
            elif d_count>=MAX_DATA:  #页面最大展示条数，大于这个数，提示用户下载全量EXCEL
                counts = ""  #超过范围，不显示合计
                tips = "<div id='down_excel' class='down_excel'><b>注意</b>：数据量过大，当前页面只显示前%s条，查全量请<a href='#' title='Excel下载'><font color='blue'><u>点此下载</u></font></a></div><br>"%MAX_DATA
            html = t.render(Context({'res': res,
                                    'd_count':d_count,
                                    'u_session':u_session,
                                    'tips':tips,
                                    'head':head,
                                    'body':body,
                                    'counts':counts,
                                    'ud':u_dimension,
                                    'container_id':container_id,
                                    'headers': view_obj.get_headers(),
                                    'table_name': view_obj.get_body()['dataset'].cname,
                                    }))
            json_text = simplejson.dumps({'container':container_id,'content':html})
            return HttpResponse(json_text)
        except:
            json_text = showtable_500(t,container_id,view_obj)
            return HttpResponse(json_text)
    else:
        raise Http404

def down_excel(request):
    """
    download excel file.
    """
    if request.method == 'POST': 
        user_id=request.user.id
        data = request.POST.copy()
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
                try:
                    cell['value'] = cell['value'].encode("utf-8")
                except:
                    pass
                if isinstance(cell['value'],str):
                    new_cell = unicode(cell['value'],'utf8')
                else:
                    new_cell = str(cell['value'])
                new_cell=new_cell.replace(",","")
                try:
                    new_cell=int(new_cell)
                except:
                    pass
                ws.write(i+1,j, new_cell)
        time_choices = dict(TIME_CHOICES)
        time_type = v.time_type.encode("utf-8")
        time_type = time_choices[time_type]
        cname = v.cname.encode("utf-8")
        excel_name = "%s_%s_%s"%(datetime.date.today().strftime("%Y%m%d"),cname,time_type)
        w_save = w.save_stream()      
        response = HttpResponse(w_save,mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s.xls'%excel_name
        return response
    else:
        raise Http404
        
def show_view(request):
    """
    display the corresponding views.
    """
    if not request.user.is_authenticated():
        try:
            cname = request.GET.get('cname')
            url_cname = urllib.quote(cname.encode('utf-8'))
            url = '../login/?next=%s'%url_cname
            return HttpResponseRedirect(url)
        except:
            return HttpResponseRedirect('../login/')
    views = request.session.get('view', {})
    areas = request.session.get('area', [])
    superuser = request.user.is_superuser
    if request.method == 'GET':
        cname = request.GET.get('cname')
        view = View.objects.filter(cname=cname)
        if not cname:
            return render_to_response('view.html', {'version':WEB2_VERSION,
                                                    'super':superuser,
                                                    'views':views, 
                                                    'areas':areas,
                                                    'help':"",
                                                    }, context_instance=RequestContext(request))                      
        has_permission = view_permission(views, cname)
        if cname and has_permission:
            try:
                help = view[0].dataset.name
                help = help.split("_")[:-2]
                help = "_".join(help)      
            except:
                help = ""
            data = get_view_obj(cname,request)
            date = get_default_date(view)
            view_id = view[0].id
            link_list = get_relation_query(view[0])
            return render_to_response('view.html', {'version':WEB2_VERSION,
                                                    'super':superuser,
                                                    'json': data, 
                                                    'views':views, 
                                                    'areas':areas,
                                                    'cname':cname,
                                                    'help':help,
                                                    'time':date,
                                                    'link_list':link_list,
                                                    }, context_instance=RequestContext(request))
    raise Http404


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
    #return render_to_response('frame.html',locals())
    return HttpResponseRedirect(url)


def login(request):
    next = request.GET.get('next','')
    if request.user.is_authenticated():
        set_session(request)
        return HttpResponseRedirect('../')
    error_info = ""
    if request.POST:
        next = request.POST.get('next')
        user = auth.authenticate(username=request.POST['f_user'],
                        password=request.POST['f_psw'])       
        if user is not None:
            auth.login(request, user)
            set_session(request)
            #这个地方指定登陆成功后跳转的页面
            if next:
                url_next = urllib.quote(next.encode('utf-8'))
                url = '../show_view/?cname=%s'%url_next
                return HttpResponseRedirect(url)
            else:
                return HttpResponseRedirect('../login/')
        else:
            error_info=('用户名或密码错误')
    return render_to_response('index.html', {'error_info': error_info,
                                             'next':next})

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
        province = province.split(",")
        citys = City.objects.filter(pname__in=province)
        return render_to_response('city.html', {'citys':citys})
    return HttpResponse("ok")

def query(request):
    if request.POST:
        query = request.POST['query']
        fname = request.POST['fname']
        position = request.POST['posi']
        next_posi = request.POST['next_posi']
        query = query.split(",")
        next_list = get_next(fname,position,query,next_posi)
        multilist = multiple_array(next_list)
        return render_to_response('next.html',{'next_list':multilist})
    return HttpResponse("ok")

def val(request):
    if request.POST:
        query = request.POST['query']
        fname = request.POST['fname']
        position = request.POST['posi']
        next_posi = request.POST['next_posi']
        query = query.split(",")
        next_list = get_next(fname,position,query,next_posi)
        val = ",".join(next_list)
        return HttpResponse(val)
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

def url_save(request):
    '''
    柱图线图的条件过长，先用POST存起来，再用GET方法给swfobject
    '''
    if request.method=='POST':
        url_get = request.POST['url']
        url_get = url_get.encode("utf-8")
        url_get = urllib.unquote(url_get)
        url_get = urllib.unquote(url_get)
        url_submit = dict(eval("{%s}"%url_get.replace("=",":")).items())
        view_id = url_submit["view_id"]
        user_id = request.user.id
        u_d = get_user_dimension(user_id,view_id)
        if country_session(u_d):tips="false"
        elif url_submit.has_key("provname") and len(url_submit["provname"].split(",")) > 10:tips="true"
        elif url_submit.has_key("cityname") and len(url_submit["cityname"].split(",")) > 10:tips="true"
        else:tips="false"
        if request.POST.has_key("ind"):
            indicator = request.POST['ind'].encode("utf-8")
            p = Flashurl(url = "{%s,'indicator':'%s'}"%(url_get.replace("=",":"),indicator))
        else:
            p = Flashurl(url = "{%s}"%url_get.replace("=",":"))
        p.save()
        time.sleep(2)
        result = "?tid=%s|%s"%(p.id,tips)
    return HttpResponse(result)
    
def draw_graph(request):
    """
    execute sql and draw flash.
    """
    if request.method == 'GET':
        t = request.GET.copy()
        tid = int(t['tid'])
        u = Flashurl.objects.get(id=tid)
        url = eval(u.url)
        data={}
        for key,value in url.items():
            try:
                data[key]=value.decode("utf-8")
            except:
                data[key]=value
        try:
            u.delete()
            data.pop("")
        except:
            pass
        try:
            user_id = request.user.id
            view_id = data.get('view_id')
            data.pop('view_id')
            v = View.objects.get(id=view_id)
        except:
            raise Http404
        type = data.get('type')
        # default chart type is bar
        if not type:
            type = "bar"
        if type == "bar":
            indicator = data['indicator'].split(",")
            data.pop('indicator')
        else:indicator = []
        x_axis = BAR_FORMAT_FIELD if type == "bar" else DATE_FORMAT_FIELD
        data.pop('type')
        view_obj = ViewObj(v, request)
        u_d = get_user_dimension(user_id,view_id)
        u_dimension = u_d.split(",") + NON_NUMBER_FIELD
        sql = SQLGenerator(data, view_obj, u_d, request,x_axis).get_sql().encode('utf-8')
        res = execute_sql(sql)
        chart = Chart()
        chart.title.text = v.cname
        chart.title.style = "{font-size: 17px; font-family: Verdana; text-align: center;}"
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
#                    try:
#                        value = value.encode("utf-8")
#                    except EOFError:
#                        value = str(value)
#                    except:pass
                else:
                    value = ''
                    
                label.append(value)
                
                if i == len(indexes) - 1 and type != "bar":
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
        if labels == ['\n']:labels=['全国\n']
        chart.x_axis = {'labels': {"labels": labels,"size":12}}
        graph_els = filter(lambda x:x not in u_dimension, header_name)
        els = []
        max_values = []
        # add chart elements one by one.
        if res:
            for i, el in enumerate(graph_els):
                if el not in indicator:
                    index = header_name.index(el)
                    try:
                        values = [int(line[index]) for line in res]
                        max_values.append(max(values))
                    except:
                        values = [line[index] for line in res]
                    graph = Chart()
                    graph.type = type
                    graph.values = values
                    graph.text = header_cname[index]
                    graph.alpha = 0.5
                    graph.fontsize = 13
                    graph.tip = '%s<br>#val#' % header_cname[index]
                    graph.colour = CHART_COLOR[i]
                    els.append(graph)
        chart.elements = els
        if res:
            max_value = max(max_values)
            step = max_value/10
            chart.y_axis = {'max': max_value, 'min': 0, 'steps': step,'labels': {"size":11}}
        chart_c=chart.create()
        return HttpResponse(chart_c)

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
        cname="帮助"
        return render_to_response('help/main.html', locals(), context_instance=RequestContext(request))
    else:
        raise Http404


def get_help(request,name):
    if request.method == 'GET':
        cname="帮助"
        page="help/%s.html"%name
        return render_to_response(page, locals(), context_instance=RequestContext(request))
    else:
        raise Http404
        
def change_pwd(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('../login/')
    views = request.session.get('view', {})
    areas = request.session.get('area', [])
    cname = "密码修改"
    view = View.objects.filter(cname=cname)
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            success = "密码修改完成"
            return render_to_response('change_pwd.html', {'success':success,
                                            'form': form,
                                            'cname':cname,
                                            'views':views, 
                                            'areas':areas,
                                            },context_instance=RequestContext(request))
    else:
        form = PasswordChangeForm(request.user)
    return render_to_response('change_pwd.html', {'form': form,
                                            'cname':cname,
                                            'views':views, 
                                            'areas':areas,
                                            },context_instance=RequestContext(request))
                             
def is_login(request):
    if not request.user.is_authenticated():
        return HttpResponse("is_logout")
    return HttpResponse("ok")
