#!/usr/bin/env python
# -*- coding: utf-8 -*-

import app

import mock
from tornado.escape import to_unicode
from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.httpclient import HTTPError


class AppTest(AsyncHTTPTestCase):
    def setUp(self):
        super(AppTest, self).setUp()
        # print("setup")

    def get_app(self):
        return app.application

    @gen_test(timeout=10)
    def test_homehandler(self):
        response = yield self.http_client.fetch(self.get_url('/'))
        self.assertIn("Podcast Home", to_unicode(response.body))

    @gen_test(timeout=10)
    def test_homehandler_admin(self):
        m = mock.MagicMock()
        m.get_session.return_value = 'test_cookie'
        self.get_app().sessions = m
        response = yield self.http_client.fetch(self.get_url('/'))
        self.assertIn("Log Out", to_unicode(response.body))

    @gen_test(timeout=10)
    def test_podcastindexhandler(self):
        response = yield self.http_client.fetch(self.get_url('/podcast'))
        self.assertIn("Everyone&#39;s Podcast", to_unicode(response.body))

    @gen_test(timeout=10)
    def test_podcastindexhandler_admin(self):
        m1 = mock.MagicMock()
        m1.return_value = 'admin'
        app.BaseHandler.get_current_user = m1
        m2 = mock.MagicMock()
        m2.get_session.return_value = 'test_cookie'
        self.get_app().sessions = m2
        response = yield self.http_client.fetch(self.get_url('/podcast'))
        self.assertIn("Logged in as admin", to_unicode(response.body))

    @gen_test
    def test_404(self):
        with self.assertRaises(HTTPError) as cm:
            yield self.http_client.fetch(self.get_url('/nonexistent'))
        self.assertEqual(cm.exception.code, 404)

    def tearDown(self):
        # print("teardown")
        super(AppTest, self).tearDown()
