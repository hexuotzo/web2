# -*- coding: utf-8 -*-
import syslog
from copy import deepcopy
import MySQLdb
from django.conf import settings
from django.utils import simplejson
from django.template.defaultfilters import floatformat
from django.template.loader import render_to_string
from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils.datastructures import SortedDict
from django.shortcuts import render_to_response
from web2.models import TIME_NAME_MAPPING, View, DataSet, UserDimension, City

#import logging
#LOG_FILENAME = '/tmp/log.out'
#logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG,)

VIEW_BODY_STRUCTURE = [{'query': {'cname': '条件'}}, 
                       {'dimension': {'cname': '维度'}},
                       {'indicator': {'cname': '指标'}}]


DEFAULT_LAYOUT_ORDER = ['name', 'cname', 'type', 'align', 'initcomma', 'decimal', 'checked']


DEFAULT_COLUMN_VALUE = {'query': 
                        {'name': {'value': '', 'cname': '字段名'},
                         'cname': {'cname': '中文名', 'value': ''},
                         'type': {'cname': '类型', 'value':'0'},
                         'checked': False,
                         },
                        'indicator': 
                        {'name': {'value': '', 'cname': '字段名'},
                         'cname': {'cname': '中文名', 'value': ''},
                         'initcomma':{'cname': '千分位', 'value': True},
                         'align': {'cname': '对齐', 'value': '0'},
                         'decimal': {'cname': '小数位', 'value':0},
                         'checked': False,
                         },
                        'dimension': 
                        {'name': {'value': '', 'cname': '字段名'},
                         'cname': {'cname': '中文名', 'value': ''},
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
                         'initcomma': True,
                        }
#维度写死了-------
NON_NUMBER_FIELD = ['begin_date', 'end_date', 'provname', 'cityname', 'province', 'city']
DATE_FORMAT_FIELD = ['begin_date', 'end_date']
#－－－－－－
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
                            db = settings.PATCH_DATABASE)
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

def get_range(body, name, request):
    """
    calculate given column's value range
    """
    table = body['table']
    time_type = body['time_type']['name']
    
    # special cases for weekly and monthly date.
    if name in ('begin_date', 'end_date') and time_type in ('week', 'month'):
        return get_date_range(table, name)

    if name == 'provname':
        areas = request.session.get('area', [])
        return areas

    if name == 'cityname':
        provnames = request.session.get('area', [])
        citys = City.objects.filter(pname__in=provnames)
        return citys

    sql = "select distinct(%s) from %s order by %s desc" % (name, table, name)

    try:
        connection, cursor = get_patch_connection()
        cursor.execute(sql)
        res = [line[0] for line in cursor.fetchall()]
    except:
        return None
        
    connection.close()
    cursor.close() 
       
    return res


def get_date_range(table, name):
    connection, cursor = get_patch_connection()
    sql = "select distinct(begin_date), end_date from %s order by begin_date desc" % table
    cursor.execute(sql)
    res = ["%s ~ %s" % line for line in cursor.fetchall()]
    return res


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
                value['cname']['value'] = u'时间'
            elif date_num == 2:
                values.remove(value) 
    
def divide_date(data):
    """
    divide date to begin_date and end_date. 
    """
    pass

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

def format_table(res,view,view_id, sum_data=True):
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
        area=[]
        view_getobjects=View.objects.get(id=view_id)
        body = simplejson.loads(view_getobjects.body)
        body = body[1]["dimension"]["values"]
        for j in body:
            area.append(j["name"]["value"])
        for i, column in enumerate(columns):
            if headers[i]['name']['value'] in area:
                sum_row.append('')
            else:
                column = list(column)
                column = map(lambda num:int(num),column)
                sum_row.append(sum(column))
        sum_row[0] = '合计'
        res.append(sum_row)
    headers_flag = 0
    line_flag = 0
    date_field = filter(lambda x: x['name']['value'] in DATE_FORMAT_FIELD, new_headers)
    if len(date_field) == 2:
        new_headers.remove(date_field[0])
        
    if len(date_field):
        date_field[-1]['cname']['value'] = u'时间'
    bd = ed = ""
    temp = {}
    date_flag = 0
    time_name = view.get_body()['time_type']['name']
    for j, line in enumerate(res):
        date_field = []
        for i, header in enumerate(headers):

            if header['name']['value'] in DATE_FORMAT_FIELD:
                date_field.append(i)

            # do formating job, such as floatformat, intcomma and align.
            int_flag = header.get('initcomma', {}).get('value')
            decimal = int(header.get('decimal', {}).get('value', 0))

            if decimal:
                line[i] = floatformat(line[i], decimal)
            if int_flag:
                line[i] = intcomma(line[i])
            
            align = header.get('align', {}).get('value')
            style = ALIGN_VALUE.get(align, '')
            line[i] = {'value': line[i], 'style':style}
            
        if len(date_field) == 2:
            index1 = date_field[0]
            index2 = date_field[1]
            date2 = line[index2]
            date1 = line.pop(index1)
            
            if time_name != 'day':
                #last line is sum, no need to display time.
                if j != len(res) -1:
                    if headers[index1]['name']['value'] == 'begin_date':
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

def get_user_dimension(user_id, view_id):
    """
    if user defined dimension does not exist, return None.
    """
    try:
        u_d = UserDimension.objects.get(user__id=user_id, view__id=view_id)
        u_d = u_d.dimension
    except:
        u_d = None
        
    return u_d

def get_dimension(view_dimension, user_id, view_id):
    """
    first look up user defined dimension, if not found, use default dimension from View.
    """
    
    u_d = get_user_dimension(user_id, view_id)

    if u_d is None:
        u_d = ",".join([item['name']['value'] for item in view_dimension])

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
        self.headers = []

        try:
            body = simplejson.loads(view.body)            
            self.obj.update(list2dict(body))
        except:
            pass

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
    def __init__(self, query, view, request):
        self.body = view.get_body()
        self.query = query
        self.request = request

        dimension = view.get_values('dimension')
        self.group = get_dimension(dimension, request.user.id, self.body['view_id'])

        indicator = view.get_headers()
        self.indicator = []

        for item in indicator:
            value = item['name']['value']
            if item['initcomma']['value'] or int(item['decimal']['value']):
                self.indicator.append("sum(%s)" % value)
            else:
                self.indicator.append("%s" % value)

        self.indicator = ",".join(self.indicator)
        self.tb = self.body['dataset'].name

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
                sql_list.append("begin_date>='%s'" % begin_date)
                self.query.pop('begin_date')
                
            end_date = self.query.get('end_date')
            if end_date:
                if '~' in end_date:
                    end_date = end_date.split('~')[-1].strip()
                sql_list.append("end_date<='%s'" % end_date)
                self.query.pop('end_date')

            provname = self.query.get('provname')
            
            #if provname is not provided, use default provname
            if not provname:
                area = self.request.session.get('area', [])
                area = ["'%s'" % a for a in area]
                if len(area) == 1:
                    sql_list.append("provname=%s" % area[0])
                else:
                    area = ",".join(area)
                    sql_list.append("provname in (%s)" % area)
                
                
            for key, value in self.query.items():
                value = value.strip().split(',')

                if len(value) == 1 and value[0]:
                    sql_list.append("%s = '%s'" % (key, value[0]))
                elif len(value) > 1:
                    value = ["'%s'" % i for i in value]
                    value = ",".join(value)
                    sql_list.append("%s in (%s)" % (key, value))
            sql += " and ".join(sql_list)
        
        return sql
    
    def get_group_sql(self):
        """
        generate group sql
        """
        sql = " group by"
        if self.group:
            sql = "%s %s" % (sql, self.group)
        else:
            sql = ""

        return sql
    
    def get_sql(self):
        sql = "select %s from %s"
        sql = sql % (self.indicator, self.tb)
        query_sql = self.get_query_sql()
        group_sql = self.get_group_sql()
        sql = "%s%s%s" %(sql, query_sql, group_sql)
        
        syslog.openlog("dana_report", syslog.LOG_PID)
        syslog.syslog(syslog.LOG_INFO, "sql: %s" % sql.encode("utf-8"))
        
        return sql

def format_date(date_str):
    component = date_str.split("-")

    try:
        format_str = "%s/%s" % (int(component[1]), int(component[2]))
    except:
        format_str = ''
        
    return format_str
