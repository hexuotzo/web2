# -*- coding: utf-8 -*-
from django.contrib import admin
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
from danaweb.models import View, DataSet, DataSetColumn, UserDimension, UserAction, FIELD_INSQL
from danaweb.utils import get_patch_connection, show_view_options, COLUMN_OPTION_MAPPING, merge_date

class ViewAdmin(admin.ModelAdmin):
    """
    fieldsets = fieldsets = (
    (None, {
        'fields': (('cname', 'view_type', 'dataset'), 'body')
    }),
)
    """
    list_filter = ('view_type','time_type')
    list_display = ("cname","time_type",'dataset')
    search_fields = ['cname', 'time_type']
    class Media:
        js = ("/site_media/js/jquery-1.2.6.pack.js",
            "/site_media/js/hack.js",
            "/site_media/js/json2.js",
            )

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):

        opts = self.model._meta
        app_label = opts.app_label
        ordered_objects = opts.get_ordered_objects()
        context.update({
            'add': add,
            'change': change,
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request, obj),
            'has_delete_permission': self.has_delete_permission(request, obj),
            'has_file_field': True, # FIXME - this should check if form or formsets have a FileField,
            'has_absolute_url': hasattr(self.model, 'get_absolute_url'),
            'ordered_objects': ordered_objects,
            'form_url': mark_safe(form_url),
            'opts': opts,
            'content_type_id': ContentType.objects.get_for_model(self.model).id,
            'save_as': self.save_as,
            'save_on_top': self.save_on_top,
            'root_path': self.admin_site.root_path,
        })
        
        #Hack modeladmin's render function
        if change:
            errors = context.get('errors')
            view_id = context.get('object_id')
            view = View.objects.get(pk=view_id)

            if errors:
                adminForm = context.get('adminform')
                options = show_view_options(view.dataset.id, None, adminForm.form.data['body'])
            else:
                options = show_view_options(view.dataset.id, view_id)
                options = merge_date(options)
            context.update({'options': options,
                            'option_mapping': COLUMN_OPTION_MAPPING
                            })

        return render_to_response(self.change_form_template or [
            "admin/%s/%s/change_form.html" % (app_label, opts.object_name.lower()),
            "admin/%s/change_form.html" % app_label,
            "admin/change_form.html"
        ], context, context_instance=template.RequestContext(request))

admin.site.register(View, ViewAdmin)

class DataSetColumnInline(admin.StackedInline):
    fieldsets = (
        (None, {
            'fields': (('column_name', 'column_cname', 'column_type'),)
        }),
    )
    model = DataSetColumn
    extra = 60
    max_num = 60
    #template = 'admin--ss/danaweb/dataset/inline.html'


class DataSetView(admin.ModelAdmin):
    inlines = [DataSetColumnInline]
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
                
                table_sql = "CREATE TABLE `%s` ( `id` INT( 20 ) NOT NULL AUTO_INCREMENT , " % new_object.name
                for i in new_object.datasetcolumn_set.all():
                    table_sql += " `%s` %s , " % (i.column_name, FIELD_INSQL[i.column_type])
                table_sql = table_sql + "	PRIMARY KEY ( `id` ) " + " ) ENGINE = MYISAM ; "  
                try:             
                    connection, cursor = get_patch_connection()
                    cursor.execute(table_sql)
                    cursor.close()
                    connection.close()
                except:
                    pass
                t = DataSet.objects.get(id=new_object.id)
                t.sql_sentence = table_sql
                t.save()
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
                connection, cursor = get_patch_connection()
                cursor.execute(drop_sql)
                cursor.close()
                connection.close()
            except:
                pass
            
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


admin.site.register(DataSet, DataSetView)

class UserActionAdmin(admin.ModelAdmin):
    search_fields = ['name','action','data']
    list_filter = ('action','time')
    list_display = ("name","action",'data','time')
admin.site.register(UserAction, UserActionAdmin)


class GroupAdmin(admin.ModelAdmin):
    search_fields = ['name']
    formfield_overrides = { ManyToManyField: { 'widget': admin.widgets.FilteredSelectMultiple(verbose_name='', is_stacked=False) }
                            }

    def formfield_for_dbfield(self, db_field, **kwargs):
        if isinstance( db_field, ManyToManyField ):
            kwargs['widget'] = admin.widgets.FilteredSelectMultiple(verbose_name='', is_stacked=False)
        if isinstance( db_field, TextField ):
            return forms.CharField(widget=forms.Textarea(attrs={'cols': 60, 'rows':3, 'class': 'docx'}),label='描述')

        return super(GroupAdmin, self).formfield_for_dbfield(db_field,**kwargs) 

admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)

from django.contrib import auth
class UserAdmin(auth.admin.UserAdmin):
    list_display = ('username','email','first_name','is_staff')
    list_filter = ('is_staff','is_superuser','groups')
    search_fields = ['username','first_name']
admin.site.unregister(User)
admin.site.register(User,UserAdmin)

class UserDimensionAdmin(admin.ModelAdmin):
    pass

admin.site.register(UserDimension, UserDimensionAdmin)
