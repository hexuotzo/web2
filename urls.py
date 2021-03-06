from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    # Example:
    # (r'^danaweb/', include('danaweb.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/(.*)', admin.site.root),
    (r'^$', 'danaweb.views.index'),
    (r'^login/$', 'danaweb.views.login'),
    (r'^logout/$', 'danaweb.views.logout'),
    (r'^area/$', 'danaweb.views.area'),
    (r'^query/$','danaweb.views.query'),
    (r'^val/$','danaweb.views.val'),
    (r'^url_save/$','danaweb.views.url_save'),
    (r'^help/(?P<name>\w+)/', 'danaweb.views.get_help'),
    (r'^help/','danaweb.views.help'),
    (r'^change_pwd/$','danaweb.views.change_pwd'),
    (r'^is_login/$','danaweb.views.is_login'),
    (r'^view_search/$','danaweb.views.view_search'),
    (r'^quickly_time/$','danaweb.views.quickly_time'),
    (r'^user_fav/$','danaweb.views.user_fav'),
    (r'^admin/', include(admin.site.urls)), #django1.1   
    (r'^what_we_eat_at_noon','danaweb.eat.lunch'),
    #(r'^admin/(.*)', admin.site.root),  #django 1.0
    url(r'^draw_graph/$', 'danaweb.views.draw_graph', name='draw_graph'),
    url(r'^down_excel/$', 'danaweb.views.down_excel', name='down_excel'),
    url(r'^show_table/$', 'danaweb.views.show_table', name='show_table'),
    url(r'^get_view_option/$', 'danaweb.views.show_option', name='show_option'),
    url(r'^show_view/$', 'danaweb.views.show_view', name='show_view'),
    url(r'^change_dimension/$', 'danaweb.views.change_dimension', name='change_dimension'),
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'media','show_indexes':True}),
    
    #dict manage
    (r'^temp/','danaweb.manage.views.temp'),
    (r'^v/(?P<tid>.*)','danaweb.manage.views.show_tables'),
    #(r'^test/','danaweb.manage.views.show_all_tables_by_department'),
    (r'^dt/(?P<vid>.*)','danaweb.manage.views.show_dicttables'),
    (r'^ajax_showdict/','danaweb.manage.views.ajax_showdict'),
    #danadict
    (r'^makepid/','danaweb.danadict.views.make_pid'),
    
)
