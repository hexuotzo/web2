# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import *

TIME_CHOICES = (('0','日报'),('1', '周报'),('2', '月报'))

TIME_NAME_MAPPING = {'0': {'name': 'day', 'cname': '日报'}, 
            '1': {'name': 'week','cname': '周报'}, 
            '2': {'name': 'month', 'cname': '月报'}}
            
LOCATION_MAPPING = {'0': 'city',
                    '1': 'province',
                    '2': 'country'
                    }
                    
VIEW_TYPE = (('0', 'KPI报表'),
             ('1', '生活播报报表'),
             ('2', '搜索报表'),
             ('3', '商旅报表'),
            )

FIELD_TYPE = (('0','VarChar'),
              ('1', 'Int'),
              ('2', 'DATE'),
             )

D_TYPE = (('0','非维度'),
          ('1', '可选维度'),
          ('2', '默认维度'),  
         )


FIELD_INSQL = {}
FIELD_INSQL['0'] = " VARCHAR( 255 ) NOT NULL "
FIELD_INSQL['1'] = " INT( 20 ) NOT NULL "
FIELD_INSQL['2'] = " DATE NOT NULL "

DATASET_PROVINCE=(('_city_','市表数据源'),
                  ('_province_','省表数据源'),
                  ('_country_','国表数据源'),
                 )
DATASET_COUNTRY=(('_city_','市表数据源'),
                 ('_province_','省表数据源'),
                 ('_country_','国表数据源'),
                )


class DataSet(models.Model):
    name = models.CharField('英文名', max_length=50)
    cname = models.CharField('中文名', max_length=50)
    sql_sentence = models.TextField('sql语句', default='', blank=True)
    
    def __unicode__(self):
        return self.cname

class View(models.Model):
    """
    body is a string serializing with a json object.
    eg:
[{'query': {'cname': '\xe6\x9d\xa1\xe4\xbb\xb6', 'values': [{'cname': '', 'type': '0', 'name': u'province'}, {'cname': '', 'type': '0', 'name': u'city'}, {'cname': '', 'type': '0', 'name': u'provname'}, {'cname': '', 'type': '0', 'name': u'cityname'}, {'cname': '', 'type': '0', 'name': u'kpiqueryn'}, {'cname': '', 'type': '0', 'name': u'kpiinfoqn'}, {'cname': '', 'type': '0', 'name': u'kpiflyqn'}, {'cname': '', 'type': '0', 'name': u'kpihotelqn'}, {'cname': '', 'type': '0', 'name': u'begin_date'}, {'cname': '', 'type': '0', 'name': u'end_date'}]}}, {'dimension': {'cname': '\xe7#\xbb\xb4\xe5\xba\xa6', 'values': [{'cname': '', 'name': u'province'}, {'cname': '', 'name': u'city'}, {'cname': '', 'name': u'provname'}, {'cname': '', 'name': u'cityname'}, {'cname': '', 'name': u'kpiqueryn'}, {'cname': '', 'name': u'kpiinfoqn'}, {'cname': '', 'name': u'kpiflyqn'}, {'cname': '', 'name': u'kpihotelqn'}, {'cname': '', 'name': u'begin_date'}, {'cname': '', 'name': u'end_date'}]}}, {'indicator': {'cname': '\xe6\x8c\x87\xe6\xa0\x87', 'values': [{'initcomma': True, 'cname': '', 'align': '0', 'decimal': 0, 'name': u'province'}, {'initcomma': True, 'cname': '', 'align': '0', 'decimal': 0, 'name': u'city'}, {'initcomma': True, 'cname': '', 'align': '0', 'decimal': 0, 'name': u'provname'}, {'initcomma': True, 'cname': '', 'align': '0', 'decimal': 0, 'name': u'cityname'}, {'initcomma': True, 'cname': '', 'align': '0', 'decimal': 0, 'name': u'kpiqueryn'}, {'initcomma': True, 'cname': '', 'align': '0', 'decimal': 0, 'name': u'kpiinfoqn'}, {'initcomma': True, 'cname': '', 'align': '0', 'decimal': 0, 'name': u'kpiflyqn'}, {'initcomma': True, 'cname': '', 'align': '0', 'decimal': 0, 'name': u'kpihotelqn'}, {'initcomma': True, 'cname': '', 'align': '0', 'decimal': 0, 'name': u'begin_date'}, {'initcomma': True, 'cname': '', 'align': '0', 'decimal': 0, 'name': u'end_date'}]}}]
    """    
    cname = models.CharField('中文名', max_length=100)
    dataset = models.ForeignKey(DataSet, help_text='数据集')
    view_type = models.CharField('视图类型', choices=VIEW_TYPE, max_length=1)
    time_type = models.CharField('时间类型', choices=TIME_CHOICES, max_length=1)
    prov_type = models.CharField('省维度数据源',choices=DATASET_PROVINCE,max_length=20)
    country_type = models.CharField('国维度数据源',choices=DATASET_COUNTRY,max_length=20)
    count_sum = models.BooleanField('计算合计')
    body = models.TextField()

    def __unicode__(self):
        return '%s %s' % (self.cname, self.get_time_type_display())

class DataSetColumn(models.Model):
    dataset = models.ForeignKey(DataSet)
    column_name = models.CharField('字段名', max_length=50)
    column_cname = models.CharField('中文名', max_length=50)
    #column_type = models.CharField('字段类型', max_length=50)
    column_type = models.CharField('类型', choices=FIELD_TYPE, max_length=1)

    class Meta:
        ordering = ('id',)

    def __unicode__(self):
        return self.column_cname

class Area(models.Model):
    pname = models.CharField('省名称', max_length = 30)
    cname = models.CharField('市名称', max_length = 30)
    pid = models.IntegerField('省id', default='0')
    cid = models.IntegerField('市id', default='0')
    parentid = models.IntegerField('父id', default='0')

    def __unicode__(self):
        return self.pname

class City(models.Model):
    pname = models.CharField('省名称', max_length = 30)
    cname = models.CharField('市名称', max_length = 30)
    pid = models.IntegerField('省id', default='0')
    cid = models.IntegerField('市id', default='0')
    parent = models.ForeignKey(Area)

    def __unicode__(self):
        return self.cname

class ProfileGroupBase(type):
    def __new__(cls, name, bases, attrs):
        module = attrs.pop('__module__')
        parents = [b for b in bases if isinstance(b, ProfileGroupBase)]
        if parents:
            fields = []
            for obj_name, obj in attrs.items():
                if isinstance(obj, models.Field): fields.append(obj_name)
                Group.add_to_class(obj_name, obj)
        return super(ProfileGroupBase, cls).__new__(cls, name, bases, attrs)

class ProfileGroup(object):
    __metaclass__ = ProfileGroupBase

class AreaView(ProfileGroup):
    area = models.ManyToManyField(Area)
    view = models.ManyToManyField(View)

class Describe(ProfileGroup):
    desc = models.TextField('描述', max_length = 200)

class UserDimension(models.Model):
    user = models.ForeignKey(User)
    view = models.ForeignKey(View)
    dimension = models.CharField(max_length=200,null=False)

    def __unicode__(self):
        return "%s - %s" %(self.user.username, self.view.cname)
