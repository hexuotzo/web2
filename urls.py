from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^web2/', include('web2.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/(.*)', admin.site.root),
    (r'^$', 'web2.views.index'),
    (r'^login/$', 'web2.views.login'),
    (r'^logout/$', 'web2.views.logout'),
    (r'^area/$', 'web2.views.area'),
    (r'^admin/', include(admin.site.urls)),
    url(r'^draw_graph/$', 'web2.views.draw_graph', name='draw_graph'),
    url(r'^down_excel/$', 'web2.views.down_excel', name='down_excel'),
    url(r'^show_table/$', 'web2.views.show_table', name='show_table'),
    url(r'^get_view_option/$', 'web2.views.show_option', name='show_option'),
    url(r'^show_view/$', 'web2.views.show_view', name='show_view'),
    url(r'^change_dimension/$', 'web2.views.change_dimension', name='change_dimension'),
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'media', 'show_indexes':True})
)
