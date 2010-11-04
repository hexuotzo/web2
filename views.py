# -*- coding: utf-8 -*-
import syslog
import urllib
import time
import re
from pyExcelerator import *
from OpenFlashChart import *
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.views.decorators.cache import cache_page
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.contrib import auth
from django.contrib.auth.models import *
from django.contrib.auth.forms import PasswordChangeForm
from django.template import Context, loader, RequestContext
from django.core.urlresolvers import reverse
from danaweb.settings import WEB2_VERSION
from danaweb.models import View, Flashurl, TIME_NAME_MAPPING, VIEW_TYPE, City, UserDimension, DataSet,  UserAction, TIME_CHOICES, UserFav
from danaweb.utils import view_permission, bind_query_range, show_view_options, COLUMN_OPTION_MAPPING, format_table, bind_dimension_options, get_dimension, ViewObj, SQLGenerator, list2dict, merge_date, execute_sql,get_relation_query,multiple_array, get_next,showtable_500, get_user_dimension,get_default_date,format_date , NON_NUMBER_FIELD, BAR_FORMAT_FIELD, DATE_FORMAT_FIELD,country_session,query_session,HIGHEST_AUTHORITY,MAX_DATA
from danaweb.excel import *
import time

X_LABELS = {'bar': ('provname', 'cityname'),
            'line': ('begin_date', 'end_date'),
            }

CHART_COLOR = ('#D54648', '#ad8bcf', '#3a0e53', '#94480a', '#ef07ab', '#339b92', '#008E8F', '#FFF467', '#AFD8F6', '#8CBA02', '#A287BE','#D54648', '#ad8bcf', '#3a0e53', '#94480a', '#ef07ab', '#339b92', '#008E8F', '#FFF467', '#AFD8F6', '#8CBA02', '#A287BE','#D54648', '#ad8bcf', '#3a0e53', '#94480a', '#ef07ab', '#339b92', '#008E8F', '#FFF467', '#AFD8F6', '#8CBA02', '#A287BE','#D54648', '#ad8bcf', '#3a0e53', '#94480a', '#ef07ab', '#339b92', '#008E8F', '#FFF467', '#AFD8F6', '#8CBA02', '#A287BE')


def show_table(request):
    """
    execute sql and fetch results.
    """
    user_id = request.user.id
    data = request.POST.copy()
    data.pop('timestamp')
    provlist = len(data['provname'].split(",")) if data.has_key('provname') else 0
    try:
        view_id = data.get('view_id')
        data.pop('view_id')
        v = View.objects.get(id=view_id)
    except:
        raise Http404
    
    # get container div, sent it back to client and put table in that container.
    try:
        page = data['current_page']
        data.pop('current_page')
        page = int(page)
    except:
        page = 1
    container_id = data.get('container')
    data.pop('container')
    view_obj = ViewObj(v, request)
    t = loader.get_template('results.html')
    try:
        v_query = view_obj.get_query()
        v_query = query_session(v_query)
        u_d = get_user_dimension(user_id,view_id)
        #生成sql语句
        sql_sum =  SQLGenerator(data, view_obj, u_d,request).get_count().encode('utf-8')  #求总量的sql语句
        object_sql = SQLGenerator(data, view_obj, u_d,request)
        sql = object_sql.get_sql().encode('utf-8') #查询内容的sql语句
        sql_sum_column = object_sql.sum_column  #求和的字段
        sql_column_sum =  execute_sql(sql_sum)
        sum_data = dict(zip(sql_sum_column,sql_column_sum[0])) 
        d_count = execute_sql(sql,True) #取出记录条数,做分页
        paginator = Paginator(range(d_count), MAX_DATA)
        try:
            contacts = paginator.page(page)
        except (EmptyPage, InvalidPage):
            contacts = paginator.page(paginator.num_pages)
        #分页：例 第1页显示 0，30--limit 0,30   第2页显示 30，30 -- limit 30,30
        #所以公式为  （页数-1）*每页显示 ， 页数*每页显示
        sql = "%s limit %s,%s"%(sql,(page-1)*MAX_DATA,MAX_DATA)
        view_id = view_obj.obj['view_id']
        res = execute_sql(sql)
        u_dimension = u_d.split(",") if len(u_d)>0 else []
        res = format_table(res, view_obj,u_dimension,sum_data)
        head,res = (res[0],res[1:]) if res else ("",[])
        tips,u_session="",True
        if country_session(u_d) and provlist<HIGHEST_AUTHORITY and v_query:
            tips = "如果要看分省/市数据，请在维度设置中勾选省/市<p>如果查看全国数据，请将省条件全选"
            u_session = False
        html = t.render(Context({'view_id': view_id,
                                'res': res,
                                'contacts':contacts,
                                'd_count':d_count,
                                'u_session':u_session,
                                'tips':tips,
                                'head':head,
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
            UserAction(name=request.user,action="下载报表",data="%s-%s"%(v.cname,v.get_time_type_display())).save()
        except:
            raise Http404
        view_obj = ViewObj(v, request)
        u_d = get_user_dimension(user_id,view_id) 
        sql_sum =  SQLGenerator(data, view_obj, u_d,request).get_count().encode('utf-8')  #求总量的sql语句
        object_sql = SQLGenerator(data,view_obj,u_d,request)
        sql = object_sql.get_sql().encode('utf-8') #查询内容的sql语句
        sql_sum_column = object_sql.sum_column  #求和的字段
        sql_column_sum =  execute_sql(sql_sum)
        sum_data = dict(zip(sql_sum_column,sql_column_sum[0]))        
        res = execute_sql(sql)
        res = format_table(res, view_obj,u_d,sum_data)
        w = Workbook()
        ws = w.add_sheet('result')
        ws.write_merge(0, 0, 0, len(res[0])-1, '%s:%s  (%s ---- %s)'%(v.cname,v.get_time_type_display(),data['begin_date'],data['end_date']))
        if not res:
            response = HttpResponse("",mimetype='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename=result.xls'
            return response   
        #write to header
        for k,header in enumerate(res[0]):
            ws.write(1, k, header['cname']['value'])
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
                ws.write(i+2,j, new_cell)
        w_save = w.save_stream()      
        response = HttpResponse(w_save,mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=result.xls'
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
    user = request.user
    #superuser = request.user.is_superuser
    if request.method == 'GET':
        cname = request.GET.get('cname')
        view = View.objects.filter(cname=cname)
        try:
            fav_list = UserFav.objects.get(user=user)
            fav_list = [k.cname for k in fav_list.fav.all()]
        except:
            fav_list = []
        is_infav = True if cname in fav_list else False
        if not cname:
            f_views = {}
            if fav_list:
                for key in views:
                    f_views[key]=[]
                for k,v in views.items():
                    for name in v:
                        if name[0] in fav_list:
                            f_views[k].append(name[0])
            return render_to_response('view.html', {'version':WEB2_VERSION,
                                                    'views':views, 
                                                    'areas':areas,
                                                    'f_views':f_views,
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
            UserAction(name=request.user,action="查看报表报表",data=view[0].cname).save()
            link_list = get_relation_query(view[0])
            return render_to_response('view.html', {'version':WEB2_VERSION,
                                                    'json': data, 
                                                    'view':view,
                                                    'views':views, 
                                                    'areas':areas,
                                                    'cname':cname,
                                                    'help':help,
                                                    'time':date,
                                                    'is_infav':is_infav,
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
    #if request.get_host()=="new.report.umessage.com.cn":
    #    return render_to_response("autojump.html")
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
        user = auth.authenticate(username=request.POST.get('f_user'),
                        password=request.POST.get('f_psw'))       
        if user is not None:
            auth.login(request, user)
            set_session(request)
            UserAction(name=request.user,action="登录").save()
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
    UserAction(name=request.user,action="登出").save()
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
        province = request.POST.get('province')
        province = province.split(",")
        citys = City.objects.filter(pname__in=province)
        return render_to_response('city.html', {'citys':citys})
    return HttpResponse("ok")

def query(request):
    if request.POST:
        query = request.POST.get('query')
        fname = request.POST.get('fname')
        position = request.POST.get('posi')
        next_posi = request.POST.get('next_posi')
        query = query.split(",")
        next_list = get_next(fname,position,query,next_posi)
        multilist = multiple_array(next_list)
        return render_to_response('next.html',{'next_list':multilist})
    return HttpResponse("ok")

def val(request):
    if request.POST:
        query = request.POST.get('query')
        fname = request.POST.get('fname')
        position = request.POST.get('posi')
        next_posi = request.POST.get('next_posi')
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
        url_get = request.POST.get('url')
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
            indicator = request.POST.get('ind').encode("utf-8")
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
            if key:
                try:
                    data[key]=value.decode("utf-8")
                except:
                    data[key]=value
        u.delete()
        try:
            user_id = request.user.id
            view_id = data.get('view_id')
            data.pop('view_id')
            v = View.objects.get(id=view_id)
            UserAction(name=request.user,action="查看柱图线图",data="%s-%s"%(v.cname,v.get_time_type_display())).save()
        except:
            raise Http404
        type = data.get('type')
        # default chart type is bar
        if not type:
            type = "bar"
        indicator = data['indicator'].split(",")
        data.pop('indicator')
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
        if labels == ['\n']:labels=['全国\n'.decode("utf-8")]
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
                    graph.tip = '#key#<br>[#x_label#]:#val#'
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

def quickly_time(request):
    '''
    快捷选择日期,这个哄幼儿园小朋友的功能并不是我想加的...太2了
    '''
    if request.method == "POST":
        time_name = request.POST.get('type')
        today = datetime.date.today()
        days = datetime.timedelta(1)
        if time_name == "yesterday" :      #昨天
            begin_time = (today - days).strftime("%Y-%m-%d")
            end_time = (today - days).strftime("%Y-%m-%d")
        elif time_name == "b_week" :         #上上周四至上周三
            begin_time = (today - datetime.timedelta(days = today.isoweekday() + 10)).strftime("%Y-%m-%d")
            end_time = (today - datetime.timedelta(days = today.isoweekday() + 4)).strftime("%Y-%m-%d")
        elif time_name == "b_month" :        #上月全月
            month_first = datetime.date(today.year,today.month,1) - days
            begin_time = month_first.strftime("%Y-%m-01")
            end_time = month_first.strftime("%Y-%m-%d")
        elif time_name == "this_week" :      #上周四到本周三
            begin_time = (today - datetime.timedelta(days = today.isoweekday() + 3)).strftime("%Y-%m-%d")
            end_time = (today - datetime.timedelta(days = today.isoweekday() - 3)).strftime("%Y-%m-%d") 
        elif time_name == "this_month" :     #本月截止到昨天
            begin_time = today.strftime("%Y-%m-01")
            end_time = (today - days).strftime("%Y-%m-%d")
        elif time_name == "this_year" :      #今年1月1号至今
            begin_time = today.strftime("%Y-01-01")
            end_time = (today - days).strftime("%Y-%m-%d")
        elif time_name == "this_year" :      #今年1月1号至今
            begin_time = today.strftime("%Y-01-01")
            end_time = (today - days).strftime("%Y-%m-%d")
        else:
            raise Http404
        begin_and_end = "%s;%s"%(begin_time,end_time)
        return HttpResponse(begin_and_end)
    else:
        raise Http404
        
def help(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('../login/')
    views = request.session.get('view', {})
    areas = request.session.get('area', [])
    view_id = request.POST.get('view_id')
    v = View.objects.get(id=view_id)
    if request.method == 'GET':
        cname="帮助"
        return render_to_response('help/main.html', locals(), context_instance=RequestContext(request))
    else:
        raise Http404


def get_help(request,name):
    if request.method == 'GET':
        cname="帮助"
        page="help/%s.html"%name
        UserAction(name=request.user,action="查看帮助",data="%s.html"%name).save()
        return render_to_response(page, locals(), context_instance=RequestContext(request))
    else:
        raise Http404
        
def change_pwd(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('../login/')
    #superuser = request.user.is_superuser
    views = request.session.get('view', {})
    cname = "密码修改"
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            success = "密码修改完成"
            UserAction(name=request.user,action="修改密码").save()
            return render_to_response('change_pwd.html', {'success':success,
                                            'form': form,
                                            'cname':cname, 
                                            'views': views, 
                                            'version':WEB2_VERSION,
                                            },context_instance=RequestContext(request))
    else:
        form = PasswordChangeForm(request.user)
    return render_to_response('change_pwd.html', {'form': form,
                                            'cname': cname,
                                            'views': views, 
                                            'version':WEB2_VERSION,
                                            },context_instance=RequestContext(request))
                                            
def view_search(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('../login/')
    views = request.session.get('view', {})
    cname = "报表查询" 
    #superuser = request.user.is_superuser
    if request.method == 'POST':
        keyword = request.POST.get('search_key')
        s_views = {}
        for key in views:
            s_views[key]=[]
        for k,v in views.items():
            for name in v:
                if bool(re.search(keyword, name[0], re.IGNORECASE)): #忽略大小写
                    s_views[k].append(name[0])
        tmp_list = []
        view_value = s_views.values()
        map(tmp_list.extend,view_value)
        has_values = len(tmp_list)
        UserAction(name=request.user,action="搜索报表",data="关键词:'%s'"%keyword.encode("utf-8")).save()
        return render_to_response('view_search.html',{'views': views,
                                                      'viewname':s_views,
                                                      'cname': cname,
                                                      'has_values':has_values,
                                                      'version':WEB2_VERSION,
                                                      },context_instance=RequestContext(request))
    else:
        raise Http404
    
def user_fav(request):
    '''
    报表收藏功能
    拿到manytomany对应的报表list
    判断是否在session中，这一部原理同view_search
    '''
    if request.method == 'POST':
        user = request.user
        views = request.session.get('view', {})
        fav_key = request.POST.get('fav')
        fav_type = request.POST.get('fav_type')
        if fav_key != "":
            v = View.objects.filter(cname = fav_key)
            myfav,create = UserFav.objects.get_or_create(user=user)
            if fav_type == "addfav" :   #收藏
                for i in v:
                    myfav.fav.add(i)
            elif fav_type == "delfav" :   #取消收藏
                for i in v:
                    myfav.fav.remove(i) 
        return HttpResponse(fav_type)  
    elif request.method == 'GET' :
        user = user = request.user
        fav_key = request.GET.get('cname')
        myfav,create = UserFav.objects.get_or_create(user=user)
        v = View.objects.filter(cname = fav_key)
        for i in v:
            myfav.fav.remove(i) 
        return HttpResponseRedirect('/show_view/')
    raise Http404
    
    
def is_login(request):
    if not request.user.is_authenticated():
        return HttpResponse("is_logout")
    return HttpResponse("ok")
