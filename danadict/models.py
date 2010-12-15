# -*- coding: utf-8 -*-   
# I highly recommended using this way to create model instead of using dynamic models

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
    class Meta:
        verbose_name = "PID字典"
        def __unicode__(self):
            return self.pname
