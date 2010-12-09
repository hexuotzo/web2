# -*- coding: utf-8 -*-   

# I am not responsible of this code. 
# They made me write it, against my will.

from django.db import models
from django.contrib import admin    
from django.contrib.auth.models import *

from danaweb.danadict.sync_dict import *


FIELD_TYPE = (
    ('0','VarChar'),
    ('1', 'Int'),
    ('2', 'DATE'),
)
 

FIELD_INSQL = {}
FIELD_INSQL['0'] = " VARCHAR( 255 ) NOT NULL "
FIELD_INSQL['1'] = " INT( 20 ) NOT NULL "
FIELD_INSQL['2'] = " DATE NOT NULL "


class DepartmentName(models.Model):
    cname = models.CharField('中文名',max_length=50)
    class Meta:
        verbose_name = "*部门"
        verbose_name_plural = "*部门管理"
    def __unicode__(self):
        return self.cname

class TableName(models.Model):
    name = models.CharField('英文表名称',max_length=50,unique=True)
    cname = models.CharField('中文表名称',max_length=50)        
    buss_type = models.ForeignKey(DepartmentName)
    sql_sentence = models.TextField('sql语句', default='', blank=True)
    fields_list = models.CharField('具体字段',default='',blank=True,max_length=255)
    class Meta:
        ordering = ('id',)
        verbose_name = "*字典表"
        verbose_name_plural = "*字典表名称管理"
        def __unicode__(self):
            return self.cname

class TableFields(models.Model):
    table_name = models.ForeignKey(TableName) #foreignkey
    name = models.CharField('字段英文名',max_length=50)
    cname = models.CharField('字段中文名',max_length=50)
    column_type = models.CharField('字段类型',choices=FIELD_TYPE,max_length=1)
    class Meta:
        ordering = ('id',)
    def __unicode__(self):
        return self.cname 
