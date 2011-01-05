# -*- coding : utf-8 -*-
"""
admin.py

Created by uc0079 on 2009-04-28.
Copyright (c) 2009 mactanxin. All rights reserved.
"""
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
from danaweb.manage.models import *
from danaweb.utils import * 
from danaweb.urls import *
from danaweb.danadict import sync_dict 
import MySQLdb

class TableFieldsView(admin.StackedInline):    
    fieldsets = (
        (None, {
            'fields': (('name', 'cname', 'column_type',),)
        }),
    )
    model = TableFields
    extra = 30
    max_num = 30  

class TableNameView(admin.ModelAdmin):
    inlines = [TableFieldsView]
    list_display = ['cname','name']
    search_fields = ['cname','name']  
    
    def add_view(self, request, form_url='', extra_context=None):
        "The 'add' admin view for this model."
        model = self.model
        opts = model._meta

        if not self.has_add_permission(request):
            raise PermissionDenied

        ModelForm = self.get_form(request)
        formsets = []
        if request.method == 'POST':
            form = ModelForm(request.POST, request.FILES)
            if form.is_valid():                   
                form_validated = True
                new_object = self.save_form(request, form, change=False)
                #print "new_object",new_object.datasetcolumn_set.all(): 
            else:
                form_validated = False
                new_object = self.model()
            for FormSet in self.get_formsets(request):
                formset = FormSet(data=request.POST, files=request.FILES,
                                  instance=new_object,
                                  save_as_new=request.POST.has_key("_saveasnew"))
                formsets.append(formset)

            if all_valid(formsets) and form_validated:
                self.save_model(request, new_object, form, change=False)
                form.save_m2m()
                for formset in formsets:
                    self.save_formset(request, form, formset, change=False)
                
                self.log_addition(request, new_object)
                # print new_object.tablefields_set().all()
                
                table_sql = "CREATE TABLE `%s` ( `id` INT( 20 ) NOT NULL AUTO_INCREMENT, " % new_object.name               
                tfield = []
                for i in new_object.tablefields_set.all().order_by("id"):
                    table_sql += " `%s` %s , " % (i.name, FIELD_INSQL[i.column_type])
                    tfield.append(i.name)
                table_sql = table_sql + "	PRIMARY KEY ( `id` ) " + " ) ENGINE = MYISAM ; "
                # try:             
                # connection, cursor = get_patch_connection()
                # cursor.execute(table_sql)
                # cursor.close()
                # connection.close() 
                # except:
                    # pass
                try:    
                    t = TableName.objects.get(id=new_object.id)
                    t.sql_sentence = table_sql  
                    t.fields_list = ",".join(tfield)
                    t.save()   
                    sync_dict.get_model_class(new_object.cname)
                    sync_dict.syncdb() 
                    cls = sync_dict.get_model_class(new_object.cname)
                    admin.site.register(cls)
                    t.name = "danadict_%s" % t.name
                    t.save()
                except:
                    raise Http404
                return self.response_add(request, new_object)
        else:
            # Prepare the dict of initial data from the request.
            # We have to special-case M2Ms as a list of comma-separated PKs.
            initial = dict(request.GET.items())
            for k in initial:
                try:
                    f = opts.get_field(k)
                except models.FieldDoesNotExist:
                    continue
                if isinstance(f, models.ManyToManyField):
                    initial[k] = initial[k].split(",")
            form = ModelForm(initial=initial)
            for FormSet in self.get_formsets(request):
                formset = FormSet(instance=self.model())
                formsets.append(formset)

        adminForm = helpers.AdminForm(form, list(self.get_fieldsets(request)), self.prepopulated_fields)

        media = self.media + adminForm.media

        inline_admin_formsets = []
        for inline, formset in zip(self.inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request))
            inline_admin_formset = helpers.InlineAdminFormSet(inline, formset, fieldsets)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media

        context = {
            'title': _('Add %s') % force_unicode(opts.verbose_name),
            'adminform': adminForm,
            'is_popup': request.REQUEST.has_key('_popup'),
            'show_delete': False,
            'media': mark_safe(media),
            'inline_admin_formsets': inline_admin_formsets,
            'errors': helpers.AdminErrorList(form, formsets),
            'root_path': self.admin_site.root_path,
            'app_label': opts.app_label,
        }
        context.update(extra_context or {})
        return self.render_change_form(request, context, add=True)
    add_view = transaction.commit_on_success(add_view)

    
    def change_view(self, request, object_id, extra_context=None): 
        "The 'change' admin view for this model."
        model = self.model
        opts = model._meta
    
        obj = self.model._default_manager.get(pk=object_id)
    
        if not self.has_change_permission(request, obj):
            raise PermissionDenied
    
        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})
    
        if request.method == 'POST' and request.POST.has_key("_saveasnew"):
            return self.add_view(request, form_url='../add/')
    
        ModelForm = self.get_form(request, obj)
        formsets = []
        if request.method == 'POST':
            form = ModelForm(request.POST, request.FILES, instance=obj)
            if form.is_valid():
                form_validated = True
                new_object = self.save_form(request, form, change=True)
            else:
                form_validated = False
                new_object = obj
            prefixes = {}
            for FormSet in self.get_formsets(request, new_object):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(request.POST, request.FILES,
                                  instance=new_object, prefix=prefix)
                formsets.append(formset)
    
            if all_valid(formsets) and form_validated:
                self.save_model(request, new_object, form, change=True)
                form.save_m2m()
                for formset in formsets:
                    self.save_formset(request, form, formset, change=True)
    
                change_message = self.construct_change_message(request, form, formsets)
                self.log_change(request, new_object, change_message)
                table_sql = "CREATE TABLE `%s` ( `id` INT( 20 ) NOT NULL AUTO_INCREMENT , " % new_object.name.replace("manage","dict")
#                tfield = []
#                for i in new_object.tablefields_set.all():
#                    table_sql += " `%s` %s , " % (i.name, FIELD_INSQL[i.column_type])
#                    tfield.append(i.name)
#                table_sql = table_sql + " PRIMARY KEY ( `id` ) " + " ) ENGINE = MYISAM ; "  
#                t = TableName.objects.get(id=new_object.id)
#                t.sql_sentence = table_sql
#                #t.fields_list = ",".join(tfield)
#                t.save()      
#                sync_dict.get_model_class(new_object.cname)
#                sync_dict.syncdb()
                return self.response_change(request, new_object)
    
        else:
            form = ModelForm(instance=obj)
            prefixes = {}
            for FormSet in self.get_formsets(request, obj):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(instance=obj, prefix=prefix)
                formsets.append(formset)
    
        adminForm = helpers.AdminForm(form, self.get_fieldsets(request, obj), self.prepopulated_fields)
        media = self.media + adminForm.media
    
        inline_admin_formsets = []
        for inline, formset in zip(self.inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request, obj))
            inline_admin_formset = helpers.InlineAdminFormSet(inline, formset, fieldsets)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media
    
        context = {
            'title': _('Change %s') % force_unicode(opts.verbose_name),
            'adminform': adminForm,
            'object_id': object_id,
            'original': obj,
            'is_popup': request.REQUEST.has_key('_popup'),
            'media': mark_safe(media),
            'inline_admin_formsets': inline_admin_formsets,
            'errors': helpers.AdminErrorList(form, formsets),
            'root_path': self.admin_site.root_path,
            'app_label': opts.app_label,
        }
        context.update(extra_context or {})
        return self.render_change_form(request, context, change=True, obj=obj)
    change_view = transaction.commit_on_success(change_view)  
    
    def delete_view(self, request, object_id, extra_context=None):
        "The 'delete' admin view for this model."
        opts = self.model._meta
        app_label = opts.app_label
    
        try:
            obj = self.model._default_manager.get(pk=object_id)
        except self.model.DoesNotExist:
            # Don't raise Http404 just yet, because we haven't checked
            # permissions yet. We don't want an unauthenticated user to be able
            # to determine whether a given object exists.
            obj = None
    
        if not self.has_delete_permission(request, obj):
            raise PermissionDenied
    
        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})
    
        # Populate deleted_objects, a data structure of all related objects that
        # will also be deleted.
        deleted_objects = [mark_safe(u'%s: <a href="../../%s/">%s</a>' % (escape(force_unicode(capfirst(opts.verbose_name))), quote(object_id), escape(obj))), []]
        perms_needed = set()
        get_deleted_objects(deleted_objects, perms_needed, request.user, obj, opts, 1, self.admin_site)
    
        if request.POST: # The user has already confirmed the deletion.
            if perms_needed:
                raise PermissionDenied
            obj_display = force_unicode(obj)
            obj.delete()
            drop_sql = "DROP TABLE IF EXISTS `%s`;" % obj.name
            try:
                conn = MySQLdb.connect(host = settings.DATABASE_HOST, 
                            user = settings.DATABASE_USER,
                            passwd = settings.DATABASE_PASSWORD,
                            db = settings.DATABASE_NAME,
                            charset="utf8")
                cursor = conn.cursor()
                cursor.execute(drop_sql)  
            except:
                import traceback
                print "error"
                traceback.print_exc()             
            sync_dict.get_model_class(new_object.cname)
            sync_dict.syncdb() 
            cls = sync_dict.get_model_class(new_object.cname)
            admin.site.unregister(cls)
            
            # try:
            #     connection, cursor = get_patch_connection()
            #     cursor.execute(drop_sql)
            #     cursor.close()
            #     connection.close()
            # except:
            #     pass  
            
            self.log_deletion(request, obj, obj_display)
            self.message_user(request, _('The %(name)s "%(obj)s" was deleted successfully.') % {'name': force_unicode(opts.verbose_name), 'obj': force_unicode(obj_display)})
            
            if not self.has_change_permission(request, None):
                return HttpResponseRedirect("../../../../")
            return HttpResponseRedirect("../../")
    
        context = {
            "title": _("Are you sure?"),
            "object_name": force_unicode(opts.verbose_name),
            "object": obj,
            "deleted_objects": deleted_objects,
            "perms_lacking": perms_needed,
            "opts": opts,
            "root_path": self.admin_site.root_path,
            "app_label": app_label,
        }
        context.update(extra_context or {})
        return render_to_response(self.delete_confirmation_template or [
            "admin/%s/%s/delete_confirmation.html" % (app_label, opts.object_name.lower()),
            "admin/%s/delete_confirmation.html" % app_label,
            "admin/delete_confirmation.html"
        ], context, context_instance=template.RequestContext(request))
    
admin.site.register(TableName,TableNameView)
admin.site.register(DepartmentName) 

#for t in TableName.objects.all():
#    cls = sync_dict.get_model_class(t.cname)                
#    print t.fields_list
#    k = sync_dict.build_admin_view_class(t.name,t.fields_list)
#    admin.site.register(cls,k)

