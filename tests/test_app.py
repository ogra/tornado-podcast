#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
import app
 
from tornado.escape import to_unicode
from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.httpclient import HTTPError
 
 
class AppTest(AsyncHTTPTestCase):
    def setUp(self):
        super(AppTest, self).setUp()
        print("setup")
 
    def get_app(self):
        return app.application
 
    @gen_test(timeout=10)
    def test_homehandler(self):
        response = yield self.http_client.fetch(self.get_url('/'))
        self.assertIn("Podcast Home", to_unicode(response.body))
 
    @gen_test
    def test_404(self):
        with self.assertRaises(HTTPError) as cm:
            yield self.http_client.fetch(self.get_url('/nonexistent'))
        self.assertEqual(cm.exception.code, 404)
 
    def tearDown(self):
        print("teardown")
        super(AppTest, self).tearDown()
