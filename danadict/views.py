# -*- coding: utf-8 -*-   
"""
views.py

Created by tanxin on 2010-12-09.
Copyright (c) 2010 mactanxin. All rights reserved.
"""

from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render_to_response
from django.core.paginator import Paginator,InvalidPage,EmptyPage
from django.template import Context, loader, RequestContext
from danaweb.danadict.models import PidName
from danaweb.danadict import BeautifulSoup
from danaweb.danadict.BeautifulSoup import *
import re
from urllib2 import build_opener
from danaweb import dict

def make_pid(request): 
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/admin/')
    if "danadict.add_pidname" not in request.user.get_all_permissions(): #有权限增加PID的人，有权限浏览此页
        return HttpResponse("您没有浏览此页的权限")
    p_type = dict.promo_type
    p_coop = dict.product_coop
    p_method = dict.promo_method
    if request.method == "POST":
        #省名称信息
        prov_info = request.POST.getlist('provname')
        #推广类型
        promo_type = request.POST.get('promo_type')
        #推广渠道
        promo_method = request.POST.get('promo_method')
        #推广名称
        promo_name = request.POST.get('promo_name')
        #产品合作
        product_coop = request.POST.get('product_coop')
        #原始链接
        lu = request.POST.get('lu')
        if not lu or not promo_name:
            error_msg = "字段不能为空"
            return render_to_response('pid_maker.html',locals(), context_instance=RequestContext(request))  
        if not prov_info:
            error_msg = "省份选择不能为空"
            return render_to_response('pid_maker.html',locals(), context_instance=RequestContext(request))  
        #数量
        try:
            promo_qty = int(request.POST.get('promo_qty'))
        except:
            error_msg = "请填写数字[推广数量]"    
            return render_to_response('pid_maker.html',locals(), context_instance=RequestContext(request))
        
        
        pid_surl_dict = {}
            
        opener = build_opener()
        
        for i in range(promo_qty):
            #detail_promo_name = "%s%s" %(promo_name,i)
            detail_promo_name = promo_name
            for j in prov_info:
                try:
                    max_id_counter = PidName.objects.order_by('-id')[0].id
                except:
                    max_id_counter = 1
                prov_name = j.split(',')[1]
                prov_id = j.split(',')[0]
                pid = "%s%s%06d%s" %(promo_type,product_coop,max_id_counter,prov_id)
                long_url = "http://uss.intra.umessage.com.cn:8180/UrlChangeService/urlGet.do?lu=%s&pid=%s" %(lu,pid)
                whole_url = "%s&pid=%s"%(lu,pid)
                #turn into short url
                #step1 get full xml request from page
                page = opener.open(long_url).read()
                #step2 For  processing XML
                soup = BeautifulSoup(page)
                #step3 get value
                short_url = soup.shorturl.string
                pid_surl_dict[pid]=short_url,whole_url,prov_name,promo_name
                
                PidName(pid ='%s' %pid,
                        pname ='%s' %detail_promo_name,
                        prov_name ='%s' %prov_name,
                        prov_id ='%s' %prov_id,
                        promo_type ='%s' %promo_type,
                        product_coop ='%s' %product_coop,
                        promo_method ='%s' %promo_method,
                        last_user = request.user.username).save()
                
        return render_to_response("finish.html",locals(), context_instance=RequestContext(request))
    return render_to_response("pid_maker.html",locals(), context_instance=RequestContext(request))
