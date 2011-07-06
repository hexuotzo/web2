# -*- coding: utf-8 -*-
from django.db import models
from django.contrib import admin    
from django.contrib.auth.models import *

# Create your models here.

class PidName(models.Model):
    pid = models.CharField('pid',max_length=50)
    pname = models.CharField('推广名称',max_length=50)
    prov_name = models.CharField('省名称',max_length=50)
    prov_id = models.CharField('省id',max_length=50)
    promo_type = models.CharField('推广类型',max_length=50)
    product_coop = models.CharField('产品合作',max_length=50)
    promo_method = models.CharField('推广渠道',max_length=50)
    pid_type = models.CharField("PID类型",max_length=50,default="推广")
    create_time = models.DateTimeField('创建时间',auto_now=False, auto_now_add=True)
    change_time = models.DateTimeField('修改时间',auto_now=True, auto_now_add=False)
    last_user = models.CharField('修改人', default='',max_length=50,blank=True)
    class Meta:
        verbose_name = "PID字典"
        verbose_name_plural = "PID字典管理"
        def __unicode__(self):
            return self.pname
