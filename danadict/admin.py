# -*- coding : utf-8 -*-
from django.contrib import admin   
from django.contrib.auth.models import Group,User 
from django import forms, template
from django.db import models, transaction
from django.forms.formsets import all_valid
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.contrib.admin import helpers
from django.contrib.admin.util import quote, get_deleted_objects
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Group,User
from django.db.models import ManyToManyField, TextField
from danaweb.danadict import sync_dict
from danaweb.manage.models import *
from danaweb.danadict.models import PidName

for t in TableName.objects.all():
    cls = sync_dict.get_model_class(t.cname)                
    k = sync_dict.build_admin_view_class(t.name,t.fields_list)
    admin.site.register(cls,k)
    
    
class PidNameAdmin(admin.ModelAdmin):
    list_filter = ('prov_name','promo_type','product_coop','promo_method')
    list_display = ('pid','pname','prov_name','prov_id','promo_type','product_coop','promo_method')
    search_fields = ['pid','pname','prov_name','prov_id','promo_type','product_coop','promo_method']

admin.site.register(PidName,PidNameAdmin)
