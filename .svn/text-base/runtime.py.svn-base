from datetime import datetime
import os
import time

from django.conf import settings
from django.db import connection
from django.template import Template, Context

class TimeMiddleware(object):
    def process_request(self, request):
        request.META['page_render_start'] = time.time()
        return None

    def process_response(self, request, response):
        t = Template(''' {{ stat }} ''')
        stat_fmt = 'Total: %.2f, Python: %.2f, DB: %.2f, Queries: %d'
        delta = datetime.now() - datetime.fromtimestamp(request.META.get('page_render_start'))
        total = delta.seconds + delta.microseconds / 1000000.0
        db = 0
        for query in connection.queries:
            db += float(query['time']) * 1000
        stat = stat_fmt % (total, total - db, db, len(connection.queries))
        print stat
        return response
