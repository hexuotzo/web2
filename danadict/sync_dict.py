#encoding: utf-8
import new
from django.db import models
from django.core.management.commands.syncdb import Command
from django.contrib import admin   
from danaweb.manage.models import TableName, TableFields, FIELD_TYPE
                           
def clean_cache():
    from django.db.models.loading import AppCache
    cache = AppCache()
    from django.utils.datastructures import SortedDict
    cache.app_store = SortedDict()
    cache.app_models = SortedDict()
    cache.app_errors = {}
    cache.handled = {}
    cache.loaded = False

def get_definition_from_db(cname):
    tn = TableName.objects.get(cname=cname)
    fs = TableFields.objects.filter(table_name=tn).order_by("id")
    return str(tn.name), dict([ (f.name, [f.cname, f.column_type]) for f in fs ])

def build_model_class(cname, name, fields):
    def u(self):
        return unicode(cname)
    class Meta:
        verbose_name = cname
        verbose_name_plural = "%s%s"%(cname,u"管理")
    fs = {'__unicode__': u,
          'Meta': Meta,
          }
    for n,t in fields.items():
        cn_name = t[0]
        t = dict(FIELD_TYPE)[t[1]]
        if t == 'VarChar':
            f = models.CharField(cn_name, max_length = 255, blank = True)
        elif t == 'Int':
            f = models.IntegerField()
        elif t == 'DATE':
            f = models.DateTimeField()
        else:
            assert False
        fs[n] = f
    #default field
    fs['create_time'] = models.DateTimeField(u'创建时间',auto_now=False, auto_now_add=True)
    fs['change_time'] = models.DateTimeField(u'修改时间',auto_now=True, auto_now_add=False)
    fs['last_user'] = models.CharField(u'修改人', default='',max_length=50,blank=True)
    cls = new.classobj(name, (models.Model,), fs)
    return cls


cache = {}
def get_model_class(cname):
    if cname not in cache:
        name, fields = get_definition_from_db(cname)
        cache[cname] = build_model_class(cname, name.replace("danadict_",""), fields)
    return cache[cname]

def syncdb():
    Command().execute()

def build_admin_view_class(name,data):
    class_name = str("%s_view" %name)
    property_list = {}
    default_field = ['create_time','change_time','last_user']
    property_list["list_display"] = data.split(",") + default_field
    property_list["search_fields"] = data.split(",")
    property_list["list_filter"] = default_field
    admin_view_class = new.classobj(class_name, (admin.ModelAdmin,), property_list)
    return admin_view_class

#from django wiki's dynamic model page : http://code.djangoproject.com/wiki/DynamicModels    
# not in use
def create_model_class(name, fields=None, app_label='', module='', options=None, admin_opts=None):
    '''
    Create dynamic model
    '''
    class Meta:
        pass
    if app_label:
        setattr(Meta,'app_label',app_label)
    if options is not None:
        for key,value in options.iteritems():
            setattr(Meta, key, value)
    attrs = {'__module__':module,'Meta':Meta}
    if fields:
        attrs.update(fields)
        
    model = type(name, (models.Model,), attrs)
    
    if admin_opts is not None:
        class Admin(admin.ModelAdmin):
            def save_model(self, request, obj, form, change):
                obj.last_user = request.user.username
                bj.save()
        for key, value in admin_opts:
            setattr(Admin, key, value)
        admin.site.register(model, Admin)
        
    return model                
