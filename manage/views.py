# Create your views here.
#!/usr/bin/env python
# encoding: utf-8
"""
views.py

Created by tanxin on 2009-09-28.
Copyright (c) 2010 mactanxin. All rights reserved.
"""
from django.core.paginator import Paginator,InvalidPage,EmptyPage
from django.template.loader import render_to_string
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render_to_response
from django.core.paginator import Paginator,InvalidPage,EmptyPage
from django.contrib.auth.decorators import login_required #login auth import 
from django.contrib import auth
from django.contrib.auth.models import * 
from django.contrib.auth import logout
from danaweb.manage.models import * 
from utils import *
from danadict import sync_dict
# from danaweb.manage.settings import *
import time,MySQLdb

def hello(request):
    return render_to_response("hello.htm",locals())   

@login_required
def index(request):
    if not request.user.is_authenticated():
        return HttpResponseRedict('/login/')
    b=TableName.objects.order_by('-id')
    return render_to_response("template_base.html",locals())

def logout(request): 
    auth.logout(request)
    return HttpResponseRedirect('/') 

# @login_required
def show_tables(request,tid): 
    b=DepartmentName.objects.order_by('-id')
    dict_list_body =  TableName.objects.filter(buss_type=tid) 
    return render_to_response("dict_logs.html",locals())   

def show_dicttables(request,vid):
    b=DepartmentName.objects.order_by('-id')
    conn = MySQLdb.connect(host = settings.DATABASE_HOST, 
                            user = settings.DATABASE_USER,
                            passwd = settings.DATABASE_PASSWORD,
                            db = settings.DATABASE_NAME,
                            charset="utf8")
    #conn.set_character_set('utf8')
    cursor = conn.cursor()
    base_str = "manage_"
    final_str = base_str + vid
    n = cursor.execute("select * from %s" %final_str)
    rslt = cursor.fetchall()
    return render_to_response("dicttables.html",locals())  
    

def show_all_tables_by_department(request):
    b = TableName.objects.all()

    return render_to_response("template_base.html",locals())
                
    



        
#    
def ajax_showdict(request):
    try:
        return _ajax_showdict(request) 
       
    except:
        import traceback
        print "error"
        traceback.print_exc()
        
def _ajax_showdict(request): 
    if request.method == 'POST':
        vid = request.POST.get('dt_id')
        conn = MySQLdb.connect(host = settings.DATABASE_HOST, 
                            user = settings.DATABASE_USER,
                            passwd = settings.DATABASE_PASSWORD,
                            db = settings.DATABASE_NAME,
                            charset="utf8")
        cursor = conn.cursor()
        base_str = "manage_"
        final_str = base_str + vid
        tb_object = TableName.objects.get(name=vid)
        order_list = tb_object.fields_list
        print "order_list:",order_list
        t2 = TableFields.objects.filter(table_name=tb_object)
        for k in t2:
            print k
        tss = "select %s from %s ORDER BY %s" %(order_list,final_str,order_list)
        
        n = cursor.execute("select %s from %s ORDER BY %s" %(order_list,final_str,order_list))
        rslt = cursor.fetchall()
        return HttpResponse(render_to_string('ajax_temp.html', {'rslt':rslt,'t2':t2}))  
        
def temp(request):
    b=TableName.objects.order_by('-id')
    return render_to_response("base.html",locals())             
