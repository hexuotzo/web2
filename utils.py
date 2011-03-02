# -*- coding: utf-8 -*-
import syslog
import sys
import os
import os.path
from copy import deepcopy
import MySQLdb
from django.conf import settings
from django.utils import simplejson
from django.template.defaultfilters import floatformat
from django.template.loader import render_to_string
from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils.datastructures import SortedDict
#from django.shortcuts import render_to_response
from danaweb.models import TIME_NAME_MAPPING, View, DataSet, UserDimension, City
from django.template import Context, loader, RequestContext
from danaweb.dict import prov_dict,city_dict
from danaweb.settings import DICT_DIR, DANAWEB_LOG_PATH
import datetime
import random
import re
import threading
#LOG_FILENAME = '/tmp/log.out'
#logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG,)

HIGHEST_AUTHORITY = 33
MAX_DATA=50
DATE_RANGE_TABLE_WEEK="dict_report_week"
DATE_RANGE_TABLE_MONTH="dict_report_month"

VIEW_BODY_STRUCTURE = [{'query': {'cname': '条件'}}, 
                       {'dimension': {'cname': '维度'}},
                       {'indicator': {'cname': '指标'}}]


DEFAULT_LAYOUT_ORDER = ['name', 'cname', 'type', 'align', 'initcomma', 'decimal', 'checked','ind','count_sum','sort','link']


DEFAULT_COLUMN_VALUE = {'query': 
                        {'name': {'value': '', 'cname': '字段名'},
                         'cname': {'cname': '中文名', 'value': ''},
                         'type': {'cname': '类型', 'value':'0'},
                         'link':{'cname':'关联','value': ''},
                         'checked': False,
                         },
                        'indicator': 
                        {'name': {'value': '', 'cname': '字段名'},
                         'cname': {'cname': '中文名', 'value': ''},
                         'initcomma':{'cname': '千分位', 'value': False},
                         'align': {'cname': '对齐', 'value': '1'},
                         'decimal': {'cname': '小数位', 'value':0},
                         'count_sum':{'cname':'求和','value':False},
                         'sort':{'cname':'排序','value':0},
                         'checked': False,
                         },
                        'dimension': 
                        {'name': {'value': '', 'cname': '字段名'},
                         'cname': {'cname': '中文名', 'value': ''},
                         'default_dim':{'cname':'必选维度','value':False},
                         'main_dim':{'cname':'默认选中','value':False},
                         'checked': False,}
                        }

QUERY_TYPE = (('0', '单选框'), ('1', '多选框'), ('2', '日历'), ('3', '文本输入框'))

ALIGN_TYPE = (('0', '左对齐'), ('1', '右对齐'), ('2', '居中'))

ALIGN_VALUE = {'0': 'align=left',
               '1': 'align=right',
               '2': 'align=center'
               }

DECIMAL_TYPE = (('0', 0), ('1', 1), ('2', 2), ('3', 3))

COLUMN_OPTION_MAPPING = {
                         'align': ALIGN_TYPE,
                         'decimal': DECIMAL_TYPE, 
                         'type': QUERY_TYPE,
                         'main_dim':True,
                         'default_dim':True,
                         'count_sum':True,
                         'initcomma': True,
                        }
#线图柱图的X轴                  
NON_NUMBER_FIELD = ['begin_date', 'end_date', 'provname','cityname']
BAR_FORMAT_FIELD = ['provname','cityname']
DATE_FORMAT_FIELD = ['begin_date', 'end_date']


def view_permission(view_session, cname):
    """
    check whether the user has permission to see the view.
    """
    view_list = []
    for views in view_session.values():
        cname_list = [v[0] for v in views]
        if cname in cname_list:
            return True
    return False

def get_patch_connection():
    """
        manually create a connection for the patch database using MySQLdb.
    """
    conn = MySQLdb.connect(host = settings.PATCH_HOST, 
                            user = settings.PATCH_USER,
                            passwd = settings.PATCH_PASSWORD,
                            db = settings.PATCH_DATABASE,
                            charset="utf8")
    #conn.set_character_set('utf8')
    cursor = conn.cursor()
    #cursor.execute('SET NAMES utf8;')
    #cursor.execute('SET CHARACTER SET utf8;')
    #cursor.execute('SET character_set_connection=utf8;')

    return (conn, cursor)

def execute_sql(sql):
    """
    execute sql and log errors
    """
    #try:
    connection, cursor = get_patch_connection()
    cursor.execute(sql)
    res = [line for line in cursor.fetchall()]
    
    cursor.close()
    connection.close()
    #except Exception:
    #    syslog.openlog("dana_report", syslog.LOG_PID)
    #    syslog.syslog(syslog.LOG_ERR, str(Exception))
    #    res = []
        
    return res
    

def bind_query_range(body, request):
    """
    get query ranges from view.
    """
    queries = body.get('query', {}).get('values', [])
    for query in queries:
        name = query.get('name', {}).get('value')
        type = query.get('type', {}).get('value')
        # if it's a select, calculate its value range.
        if type in ('0', '1'):
            range = get_range(body, name, request)
            if range:
                #city name behaves different with other query, need to return a html of select body.
                if name == 'cityname':
                    body.get('query', {})['cityname'] = render_to_string('city.html', {'citys':range}).replace("\n", "")
                else:
                    query['range'] = range
    return True
    
    
def sort_u(value):
    '''
    排序去重复
    '''
    result = list(set(value))
    result.sort()
    return result
    
def file_to_str(name,position):
    filename = os.path.join(DICT_DIR,name)
    try:
        position = int(position)-1    #配置字段从1开始，python数组从0开始，所以-1
        f=open(filename,'r')
        result=[]
        for i in f:
            i=i.strip().decode('utf-8')
            v = i.split("|")[position]
            result.append(v)
        result = sort_u(result)
        return result
    except:
        return ["没有这个字典文件"]

def get_next(name,position,query,next):
    filename = "%s/%s"%(DICT_DIR,name)
    position = int(position)-1    #配置字段从1开始，python数组从0开始，所以-1
    next = int(next)-1
    result=[]
    try:
        f=open(filename,'r')
        for i in f:
            i=i.strip().decode('utf-8')
            prev = i.split("|")[position]
            if (prev in query) or prev=="":
                v = i.split("|")[next]
                result.append(v)
        result = sort_u(result)
    except:
        return ["没有这个字典文件"]
    finally:
        f.close()
        return result
def get_range(body, name, request):
    """
    calculate given column's value range
    """
    table = body['table']
    time_type = body['time_type']['name']
    # special cases for weekly and monthly date.
    if name in ('begin_date', 'end_date') and time_type in ('week', 'month', 'sweek' ,'smonth'):
        date = get_date_range(table, name ,time_type)
        return date
    
    if name == 'provname':
        areas = request.session.get('area', [])
        return areas

    if name == 'cityname':
        provnames = request.session.get('area', [])
        citys = City.objects.filter(pname__in=provnames).order_by('id')
        return citys

    try:
        for i in body['query']['values']:
            if name== i['name']['value']:
                link = i['link']['value']
        link = link.split("|")
        if len(link)>=2:
            filename = link[0]
            position = link[1]  #后台配置字段从1开始，python数组中是从0开始，所以-1
            res = file_to_str(filename,position)
            return res
    except:
        return []



def get_date_range(table, name, time_type):
    '''
    在有danacfg 没有数据时，返回空时间
    '''
    try:
        connection, cursor = get_patch_connection()
        sql = "select distinct(begin_date), end_date from %s order by begin_date desc" % table
        cursor.execute(sql)
        if time_type == "week" or time_type == "sweek":
            res = ["%s ~ %s" % line for line in cursor.fetchall()]
        else:
            res = ["%s" % line[0].strftime("%Y-%m") for line in cursor.fetchall()]
    except:
        res=[]
    return res

def get_default_date(view):
    '''
    日期条件，初始日期
    '''
    today = datetime.date.today()
    try:
        date = view[0].select_date
        days = datetime.timedelta(days=int(date))
    except:
        days = datetime.timedelta(days=1)
    default_day = str(today - days)
    return default_day
     

def show_view_options(dataset_id, view_id=None, body=None):

    """
    merge view and dataset to produce column information.
    """

    try:
        dataset = DataSet.objects.get(pk=dataset_id)
    except Exception, e:
        return []

    columns = dataset.datasetcolumn_set.all()
    all_column_name = columns.values('column_name', 'column_cname')
    all_column_name = [(c['column_name'], c['column_cname']) for c in all_column_name]
    column_name_mapping = dict(all_column_name)

    try:
        if view_id:
            view = View.objects.get(pk=view_id)
            body = simplejson.loads(view.body)
        else:
            body = simplejson.loads(body)
    except:
        return get_default_body(all_column_name)

    if body:
        for item in body:
            for k, v in item.items():
                values = v.get('values')
                if not values:
                    # get default values and continue to next loop
                    v['values'] = get_default_item(k, all_column_name)
                    continue
                view_column_name = []
                for def_k,def_v in DEFAULT_COLUMN_VALUE.get(k).items():
                    for i in values:
                        if not i.has_key(def_k):
                            i[def_k]=def_v
                # collect column names and set checked status to True
                for i, value in enumerate(values):
                    view_column_name.append(value['name']['value'])
                    value['checked'] = True
                    # use SortJsonDict to sort attributes orders
                    values[i] = SortJsonDict(value)
                    
                diff_name = set([names[0] for names in all_column_name]).difference(set(view_column_name))
                diff_name = list(diff_name)

                for name in diff_name:
                    view_column = deepcopy(values[0])
                    default_column = deepcopy(DEFAULT_COLUMN_VALUE.get(k))
                    default_column['name']['value'] = name
                    default_column['cname']['value'] = column_name_mapping.get(name)
                    view_column.update(default_column)
                    values.append(view_column)

        return body
    
    return get_default_body(all_column_name)

    
def merge_date(data):
    """
    In dimension and indicator, merge begin_date and end_date to a date field.
    """
    if not data:
        return []

    for index in (1, 2):
        values = data[index].values()[0]
        values = values['values']
        merge_date_field(values)

    return data

def merge_date_field(values):
    names = [item['name']['value'] for item in values]
    date_num = 0
    for name in ('begin_date', 'end_date'):
        if name in names:
            value = values[names.index(name)]
            date_num = date_num + 1
            if date_num == 1:
                value['name']['value'] = 'date'
                value['cname']['value'] ='时间'
            elif date_num == 2:
                values.remove(value) 
    
def get_default_body(column_names):
    """
    if view is not provided, use default column information.
    """

    structure = deepcopy(VIEW_BODY_STRUCTURE)

    for item in structure:
        values = []
        key = item.keys()[0]
        values = get_default_item(key, column_names)
        item[key]['values'] = values

    return structure

def get_default_item(key, column_names):

    values = []
    for name, cname in column_names:
        value = deepcopy(DEFAULT_COLUMN_VALUE.get(key))
        value = SortJsonDict(value)
        value['name']['value'] = name
        value['cname']['value'] = cname
        values.append(value)
    return values

def format_table(res,view,u_dimension, sum_data=True):
    """
    do some formatting job according to the view setting, e.g intcomma, floatformat and align.
    if sum is true, add a sum row to the bottom of result.
    """
    if not res:
        return ''
    res = [list(line) for line in res]
    headers = view.get_headers()
    new_headers = headers[:]
    if sum_data:
        sum_row = []
        columns = zip(*res)
        for i, column in enumerate(columns):
            if headers[i].has_key("count_sum"):
                if headers[i]['count_sum']['value']:
                    column = int(sum_data[headers[i]['name']['value']]) #将求和字段与求和的值做一个字典 放最后1行
                    sum_row.append(column)
                else:
                    sum_row.append('-')
            else:
                sum_row.append('-')
        sum_row[0]=''
        res.append(sum_row)
    date_field = filter(lambda x: x['name']['value'] in DATE_FORMAT_FIELD, new_headers)
    if len(date_field) == 2:
        new_headers.remove(date_field[0])
        
    if len(date_field):
        date_field[-1]['cname']['value'] = u'时间'
    time_name = view.get_body()['time_type']['name']
    for j, line in enumerate(res):
        date_field = []
        for i, header in enumerate(headers):
            if header['name']['value'] in DATE_FORMAT_FIELD:
                date_field.append(i)
            # do formating job, such as floatformat, intcomma and align.
            int_flag = header.get('initcomma', {}).get('value')
            decimal = int(header.get('decimal', {}).get('value', 0))
            indicators = False
            try:
                if decimal:
                    line[i] = floatformat(line[i], decimal)
                    indicators = True
                elif int_flag:
                    line[i] = intcomma(line[i])
                    indicators = True
            except:
                line[i] = line[i]               
            align = header.get('align', {}).get('value')
            style = ALIGN_VALUE.get(align, '')
            if line[i]==None:
                line[i]=""
            line[i] = {'value': line[i], 'style':style ,'indicators':indicators}          
        if len(date_field) == 2:           
            index1 = date_field[0]
            index2 = date_field[1]
            date2 = line[index1]
            date1 = line.pop(index2)
            if time_name != 'day':
                #if last line is sum, no need to display time.
                if j != len(res) -1:
                    if headers[index1]['name']['value'] == 'end_date':
                        # because a value is removed, index should move forward 1 step.
                        line[index2 - 1]['value'] = "%s~%s" % (date1['value'], date2['value'])
                    else:
                        line[index2 - 1]['value'] = "%s~%s" % (date2['value'], date1['value'])
    #apply align setting to headers
    for i, col in enumerate(res[0]):
        style = col.get('style')
        if style:
            new_headers[i]['style'] = style
    res.insert(0, new_headers)
    return res

def list2dict(body):
    """
    convert view body to a dict.
    """
    new_body = {}
    for item in body:
        new_body.update(item)

    return new_body

class SortJsonDict(SortedDict):
    """
    subclass django's SortedDict, sort keys using DEFAULT_LAYOUT_ORDER.
    """

    def __init__(self, data=None):
        super(SortJsonDict, self).__init__(data)
        self._sort_keyorder()

    def __setitem__(self, key, value):
        super(SortedDict, self).__setitem__(key, value)
        if key not in self.keyOrder:
            self.keyOrder.append(key)
            self._sort_keyorder()
        
    def _sort_keyorder(self):
        # sort keyOrder according to layout order.
        self.keyOrder = sorted(self.keyOrder, key=lambda x: x in DEFAULT_LAYOUT_ORDER and DEFAULT_LAYOUT_ORDER.index(x) or -1)
        
def get_default_demension(view_id):
    """
    must selected by default
    """
    view = View.objects.get(pk=view_id)
    body = simplejson.loads(view.body) 
    default_dim = [] 
    try:
        for i in body[1]['dimension']['values']:
            if i['default_dim']['value']:
                default_dim.append(i['name']['value'])
    except:
        pass
    return default_dim

def get_relation_query(view):
    '''
    有关联关系的条件，用于JS中判断
    '''
    body = simplejson.loads(view.body) 
    link_list = [] 
    try:
        for i in body[0]['query']['values']:
            v=i['link']['value'].split("|")
            if len(v)==3:
                link_list.append(i['name']['value']+"|"+i['link']['value'])
    except:
        pass
    return link_list

    
def get_main_dimension(view_id):
    """
    默认打勾的维度
    """
    main_dim = []
    view = View.objects.get(pk=view_id)
    body = simplejson.loads(view.body)
    try:
        main_dim = [i['name']['value'] for i in body[1]['dimension']['values'] if i['main_dim']['value']]
#        for i in body[1]['dimension']['values']:
#            if i['main_dim']['value']:
#                main_dim.append(i['name']['value'])
    except:
        main = []
    return main_dim 
   
def get_user_dimension(user_id, view_id):
    """
    if user defined dimension does not exist, return None.
    """
    main_dim = get_main_dimension(view_id)
    #main_dim.append("provname")    #以后要改的
    default_dim = get_default_demension(view_id)
    try:
        u_d = UserDimension.objects.get(user__id=user_id, view__id=view_id)
        if u_d.dimension:
            u_d = u_d.dimension.split(",")
            u_d = default_dim + u_d
        else:
            u_d= default_dim
    except:
        u_d = default_dim + main_dim
    u_d=sort_u(u_d)
    u_d = ",".join(u_d)
    return u_d

def get_dimension(view_dimension, user_id, view_id):
    """
    first look up user defined dimension, if not found, use default dimension from View.
    """
    
    u_d = get_user_dimension(user_id, view_id)

#    if u_d is None:
#        u_d = ",".join([item['name']['value'] for item in view_dimension])

    return u_d

def bind_dimension_options(view_dimension, user_id, view_id):
    """
    modify dimension in place, if user defined dimension exists, mark them by setting checked flag in view dimension, otherwise mark all dimension to checked. also merge begin_date and end_date to a date field.
    """
    u_d = get_user_dimension(user_id, view_id)
    all_d_name = [d['name']['value'] for d in view_dimension]
    if u_d is None:
        for d in view_dimension:
            d['checked'] = True
    else:
        u_d = u_d.split(",")
        for d in u_d:
            if d in all_d_name:
                index = all_d_name.index(d)
                view_dimension[index]['checked'] = True
    merge_date_field(view_dimension)

    return True

def country_session(u_d):
    '''
    省市都不选，读取全国报表
    '''
    if (u"cityname" not in u_d) and (u"provname" not in u_d):
        return True
    return False

def query_session(query):
    '''
    查看条件中是否包含省市
    '''
    if ("cityname" in query) or ("provname" in query):
        return True
    return False

def sort_headers(header):
    """
    Report to show the column to sort
    """
    list_tmp = []
    result = []
    for i in header:
        list_tmp.append(i['sort']['value'])
    list_tmp = [x for x in list_tmp if x not in locals()['_[1]']]    #去重复
    list_tmp = map(lambda x:int(x),list_tmp)
    list_tmp.sort()
    for x in list_tmp:
        for y in header:
            if int(y['sort']['value']) == x:
                result.append(y)
                continue
    return result

   
class ViewObj(object):
    """
    parse a View instance and its json body.
    """
    def __init__(self, view, request):
        self.obj = {}
        self.request = request
        self.obj['view_id'] = view.id
        self.obj['time_type'] = TIME_NAME_MAPPING.get(str(view.time_type))
        self.obj['dataset'] = view.dataset
        self.obj['prov_type']= view.prov_type
        self.obj['country_type']= view.country_type
        self.headers = []

        try:
            body = simplejson.loads(view.body) 
            self.obj.update(list2dict(body))
        except:
            pass
    def get_query(self):
        query = [q['name']['value'] for q in self.get_values("query")]
        return query
    def get_values(self, key):
        return self.obj.get(key, {}).get('values', [])
    def get_headers(self):
        """
        return header of search results.
        """
        if self.headers:
            return self.headers
        default_d = self.get_values('dimension')
        d = self.get_dimension()
        d = d.split(",")
        default_d_name = [dimension['name']['value'] for dimension in default_d]
        diff_d = set(default_d_name).difference(set(d))

        headers = self.get_values('indicator')[:]
        for i in headers[:]:
            if i['name']['value'] in diff_d:
                headers.remove(i)
        try:
            headers = sort_headers(headers)
        except:
            pass
        self.headers = headers
        return headers

    def get_dimension(self):
        default_d = self.get_values('dimension')
        d = get_dimension(default_d, self.request.user.id, self.obj['view_id'])
        return d

    def get_body(self):
        return self.obj

class SQLGenerator(object):
    """
    Generate sql from http request, query is a http request obj or a dict
    containing queries, view is a view obj.
    """
    def __init__(self, query, view, u_d,request,graph=None):
        self.d_prov=view.obj['prov_type']
        self.d_coun=view.obj['country_type']
        self.body = view.get_body()
        self.query = query.copy()
        self.u_d=u_d
        self.request = request
        self.use_prov=False
        self.graph=graph
        dimension = view.get_values('dimension')
        self.group = get_dimension(dimension, request.user.id, self.body['view_id'])
        indicator = view.get_headers()
        self.indicator,self.sum_indicator,self.sum_column = [],[],[]
        for item in indicator:
            value = item['name']['value']
            if item['initcomma']['value']:
                self.indicator.append("sum(%s)" % value)
                self.sum_indicator.append("sum(%s)" % value)
                self.sum_column.append(value)
            else:
                self.indicator.append("%s" % value)
        session=self.request.session.get('area', [])
        self.indicator = ",".join(self.indicator)
        self.sum_indicator = ",".join(self.sum_indicator)
        self.tb = self.body['dataset'].name   ## 数据源表名称
        if "cityname" not in self.u_d:
            self.use_prov=True
            self.tb=self.tb.replace("_city_",self.d_prov) 
        if country_session(self.u_d):
            if len(session)>=HIGHEST_AUTHORITY:
                self.tb=self.tb.replace(self.d_prov,self.d_coun)

    def get_query_sql(self):
        """
        generate where sql
        """
        sql = " where "
        if not self.query:
            sql = ""
        else:
            sql_list = []
            # process datetime query
            begin_date = self.query.get('begin_date')
            if begin_date:
                if '~' in begin_date:
                    begin_date = begin_date.split('~')[0].strip()
                elif len(begin_date)==7:
                    begin_date = "%s-01"%begin_date
                sql_list.append("begin_date>='%s'" % begin_date)
                self.query.pop('begin_date')      
            end_date = self.query.get('end_date')
            if end_date:
                if '~' in end_date:
                    end_date = end_date.split('~')[-1].strip()
                elif len(end_date)==7:
                    end_date = "%s-31"%end_date
                sql_list.append("end_date<='%s'" % end_date)
                self.query.pop('end_date')
            if country_session(self.u_d):
                if self.query.has_key("provname"):
                    self.query.pop("provname")
                if self.query.has_key("cityname"):
                    self.query.pop("cityname")
            else:
                provname = self.query.get('provname')
                #if provname is not provided, use default provname
                if not provname:
                    area = self.request.session.get('area', [])
                    area = map(lambda x:prov_dict[x],area)
                    area = ["'%s'" % a for a in area]
                    if len(area) == 1:
                        sql_list.append("province=%s" % area[0])
                    else:
                        area = ",".join(area)
                        sql_list.append("province in (%s)" % area)
            for key, value in self.query.items():
                value = value.strip().split(',')
                if key=="provname" and value[0]:
                    province = map(lambda x:prov_dict[x],value) 
                    if len(province) == 1 :
                        sql_list.append("province=%s" % province[0])
                    elif len(province) > 1:
                        province = ["'%s'" % i for i in province]
                        province = ",".join(province)
                        sql_list.append("province in (%s)" % province)  
                elif key=="cityname" and value[0]:
                    city = map(lambda x:city_dict[x],value) 
                    if len(city)==1:
                        sql_list.append("city=%s" % city[0])
                    elif len(city) > 1:
                        city = ["'%s'" % i for i in city]
                        city = ",".join(city)
                        sql_list.append("city in (%s)" % city)
                elif value[-1] == "__query_input":
                    value.pop(-1)
                    value = map(lambda x:"%s like '%%%s%%'"%(key,x),value)
                    sql_tmp = " or ".join(value)
                    sql_list.append("(%s)"%sql_tmp)
                else:
                    if len(value) == 1 and value[0]:
                        sql_list.append("%s = '%s'" % (key, value[0]))
                    elif len(value) > 1:
                        value = ["'%s'" % i for i in value]
                        value = ",".join(value)
                        sql_list.append("%s in (%s)" % (key, value))
            if len(sql_list)>0:
                sql += " and ".join(sql_list)
            else:return ""
        return sql
    
    def get_group_sql(self):
        """
        generate group sql
        """
        sql = " group by"
        if self.group:
            if self.graph:
                gp = [i for i in self.group.split(",") if i in self.graph]
                gp = ",".join(gp)
                sql = "%s %s"%(sql,gp) if gp else "%s null"%(sql)
            else:
                sql = "%s %s" % (sql, self.group)
        else:
            sql = "%s null" %(sql)
        return sql
    
    def sort_dimension(self):
        '''
        use in  order by
        '''
        dimension = [i['name']['value'] for i in self.body['dimension']['values']]
        user_dim = self.group.split(",")
        result = [i for i in dimension if i in user_dim]
        return ",".join(result)
        
    def get_order_sql(self):
        '''
        order by
        '''
        sql = " order by begin_date"
        g = self.sort_dimension()
        g = g.replace("begin_date","")
        g = g.replace("end_date","")
        order = [i for i in g.split(",") if len(i)>0]
        order = ",".join(order)
        if order:
            sql = "%s,%s" % (sql, order)
            return sql
        return sql
        
    def get_sql(self):
        sql = "select %s from %s"
        query_sql = self.get_query_sql()
        group_sql = self.get_group_sql()
        order_sql = self.get_order_sql()
        sql = sql % (self.indicator, self.tb)
        sql = "%s%s%s%s" %(sql, query_sql, group_sql,order_sql)
        sql = re.sub(r",+",",",sql)
        syslog.openlog("dana_report", syslog.LOG_PID)
        syslog.syslog(syslog.LOG_INFO, "sql: %s" % sql.encode("utf-8"))
        return sql
    def get_sum(self):
        sql = "select %s from %s"
        query_sql = self.get_query_sql()
        sql = sql % (self.sum_indicator, self.tb)
        sql = "%s%s" %(sql, query_sql)
        sql = re.sub(r",+",",",sql)
        return sql
        
class MyPaginator(object):
    '''
    翻页，不计算共多少页，只判断是否还有下一页
    原因：数据量大计算总条数太费时
    has_next(),has_prev() 是否有上一页/下一页
    has_paginator() 是否需要分页功能
    '''
    def __init__(self,count,page,mount_perpage):
        self.count_num = int(count)  #本次请求数据的条数
        self.page_num = int(page)
        self.next_page_num = page + 1
        self.prev_page_num = page - 1
        self.mount_perpage = int(mount_perpage)
    def has_next(self):
        next = True if self.count_num > self.mount_perpage else False
        return next
    def has_prev(self):
        prev = True if self.prev_page_num > 0 else False
        return prev
    def has_paginator(self):
        next = self.has_next()
        if not next and self.page_num == 1:
            return False
        return True
        


def format_date(date_str):
    date_str = str(date_str)
    component = date_str.split("-")

    try:
        format_str = "%s/%s" % (int(component[1]), int(component[2]))
    except:
        format_str = ''
        
    return format_str


def get_perminssion(request,data):
    """
    To determine whether the user has the highest authority
    """
    session=request.session.get('area', [])
    provlist=data['provname'].split(",")
    prov_perminssion=len(provlist)
    if prov_perminssion>=HIGHEST_AUTHORITY:
        return True
    return False 
    
def multiple_array(array):
    multilist = zip(array[::4],array[1::4],array[2::4],array[3::4])
    length = len(array)
    other = length%4 
    if other != 0:
        multilist.append(array[-other:])
    return multilist
    
def showtable_500(t,container_id,view_obj):
    '''
    show table error 500 page
    '''
    tips="查询过程可能出了一点问题，建议您<a href='#' onClick='document.location.reload()'><font color='blue'>刷新</font></a>后再尝试"
    html = t.render(Context({'res':1,
                            'tips':tips,
                            'u_session':False,
                            'container_id':container_id,
                            'table_name': view_obj.get_body()['dataset'].cname
                            }))
    json_text = simplejson.dumps({'container':container_id,'content':html})
    return json_text
    
    
class Mythread(threading.Thread):
    def __init__(self, args=(), kwargs={}):
        self.args, self.kwargs = args, kwargs
        super(Mythread, self).__init__(args=args, kwargs=kwargs)
    
    def run(self):
        self.v,self.time = self.worker(*self.args, **self.kwargs)

    def worker(self, sql):
    	try: 
    	    start = datetime.datetime.now()
            res = execute_sql(sql)
            end = datetime.datetime.now()
            run_time = end - start
            return (res, run_time)
    	except:
    	    return None,None
    	    
def tolog(request,log,log_id):
    syslog_body= "%s|%s|%s|%s\n"%(log_id,
                                  datetime.datetime.now().strftime("%Y%m%d %H:%M:%S"),
                                  request.user,
                                  log)
    syslog.openlog("danaweb", syslog.LOG_PID, syslog.LOG_LOCAL2)
    syslog.syslog(syslog_body)
    print "log is written"
