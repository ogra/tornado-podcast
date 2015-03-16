import tornado.ioloop
import tornado.options
import tornado.web
import uuid
import logging
import os
import os.path
import pytz
import imghdr
from PIL import Image
import markdown

from auth import MongoAuthentication
from bson.json_util import dumps
from session import MongoSessions
from tornado.web import HTTPError, RequestHandler
from blog import MongoBlog
from imageutil import ImageUtil
from audioutil import AudioUtil
from feedgen.feed import FeedGenerator


__UPLOADS__ = "uploads/"
__THUMBNAILS__ = "thumbnails/"
__THUMBNAIL_MAX_PIXEL__ = 120

__PODCAST_TITLE__ = "Ogura's Podcast"
__PODCAST_LINK__ = 'http://localhost:8888/podcast'
__PODCAST_DESCRIPTION__ = "Toshiyuki Ogura's podcast"
__PODCAST_ITUNES_CATEGORY__ = ('Technology', 'Podcasting')
__PODCAST_ITUNES_AUTHOR__ = 'Toshiyuki Ogura'
__SITE_ROOT__ = 'http://localhost:8888/'


def convert_to_jst(datetime_obj):
    jst = pytz.timezone('Asia/Tokyo')
    if datetime_obj.tzinfo == None:
        datetime_obj = datetime_obj.replace(tzinfo=pytz.timezone('UTC'))
    return datetime_obj.astimezone(jst)


def file_exists(file_name):
    path_to_file = __UPLOADS__ + file_name
    if os.path.exists(path_to_file):
        return True
    else:
        return False


class Application(tornado.web.Application):
    def __init__(self, handlers, **settings):
        tornado.web.Application.__init__(self, handlers, **settings)
        self.sessions = MongoSessions("mutiny", "sessions", timeout=30)
        self.auth = MongoAuthentication("mutiny", "authentication")
        if self.auth._coll.count() == 0:
            self.auth.register("admin", "admin", ['admin'])
        self.blog = MongoBlog("blog", "entries")
        self.imageutil = ImageUtil(__THUMBNAILS__)
        self.audioutil = AudioUtil(__UPLOADS__)


class SessionMixin:
    def prepare(self):
        id = self.get_cookie('id')
        logging.debug(id)
        self.session = self.application.sessions.get_session(id)
        logging.debug(self.session)

    def begin_session(self, username, password):
        if not self.application.auth.log_in(username, password):
            return False

        data = {'username': username}
        id = self.application.sessions.new_session(data).hex
        self.session = self.application.sessions.get_session(id)
        self.set_cookie('id', id, httponly=True)
        return True

    def end_session(self):
        id = self.get_cookie('id')
        self.application.sessions.clear_session(id)
        if self.session is not None:
            username = self.session['data']['username']
            self.application.auth.log_out(username)
        self.session = None
        self.clear_cookie('id')


class BaseHandler(RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("username")


class UserLoginHandler(SessionMixin, BaseHandler):
    def get(self):
        self.render('login2.html')

    def post(self):
        username = self.get_argument('username', None)
        password = self.get_argument('password', None)
        next_page = self.get_argument('next', None)

        res = self.begin_session(username, password)
        if not res:
            self.render('login_failed.html')
        self.set_secure_cookie("username", self.get_argument("username"), httponly=True)
        if next_page:
            self.redirect(next_page)
        else:
            self.redirect('/')


class UserRegisterHandler(SessionMixin, BaseHandler):
    def get(self):
        self.render('register.html')

    def post(self):
        username = self.get_argument('username', None)
        password = self.get_argument('password', None)

        res = self.application.auth.register(username, password)
        if not res:
            self.render('register_failed.html')

        res = self.begin_session(username, password)
        if not res:
            self.render('login_failed.html')

        self.redirect('/')


class UserLogoutHandler(SessionMixin, BaseHandler):
    def get(self):
        self.post()

    def post(self):
        if (self.get_argument("logout", None)):
            self.clear_cookie("username")
            self.end_session()
            self.redirect("/")


class HomeHandler(SessionMixin, BaseHandler):
    @tornado.web.authenticated
    def get(self):
        if self.session is None:
            urls = '<a href="/register">Register</a> | <a href="/login">Log In</a>'
        else:
            urls = '<a href="/logout?logout=1">Log Out</a>'
        self.render('home.html', urls=urls, data=dumps(self.session, indent=2))


class PodcastIndexHandler(SessionMixin, BaseHandler):
    def get(self):
        entries = self.application.blog.get_index()
        self.render('podcast_index.html', entries=entries, user=self.current_user, session=self.session, convert_to_jst=convert_to_jst, podcast_title=__PODCAST_TITLE__)


class NewEntryHandler(SessionMixin, BaseHandler):
    @tornado.web.authenticated
    def get(self):
        if self.session is None:
            self.redirect('/login?next=%2Fnew')
        else:
            images = self.application.imageutil.get_index()
            audios = self.application.audioutil.get_index()
            self.render('new_entry.html', user=self.current_user, session=self.session, images=images, audios=audios, uploadpath=__UPLOADS__, thumbnailpath=__THUMBNAILS__)

    @tornado.web.authenticated
    def post(self):
        if self.session is None:
            self.redirect('/login?next=%2Fnew')
        else:
            title = self.get_argument("title", None)
            body = self.get_argument("body", None)
            image_filename = self.get_argument("image", None)
            audio_filename = self.get_argument("audio", None)
            self.application.blog.create_entry(title, body, image_filename, audio_filename)
            self.redirect('/podcast')


class DeleteEntryHandler(SessionMixin, BaseHandler):
    @tornado.web.authenticated
    def post(self):
        if self.session is None:
            self.redirect('/login?next=%2Fdelete')
        else:
            entry_id = self.get_argument("entry_id", None)
            self.application.blog.delete_entry(entry_id)
            self.redirect('/podcast')


class DeleteAllEntriesHandler(SessionMixin, BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render('deleteall.html', user=self.current_user, session=self.session)

    @tornado.web.authenticated
    def post(self):
        if self.session is None:
            self.redirect('/login?next=%2Fdeleteall')
        else:
            param = self.get_argument("deleteall", None)
            if param == 'true':
                self.application.blog.delete_all_entries()
                self.redirect('/podcast')


class UpdateEntryHandler(SessionMixin, BaseHandler):
    @tornado.web.authenticated
    def get(self):
        if self.session is None:
            self.redirect('/login?next=%2Fpodcast')
        else:
            entry_id = self.get_argument("entry_id", None)
            entry = self.application.blog.get_entry(entry_id)
            if entry:
                images = self.application.imageutil.get_index()
                audios = self.application.audioutil.get_index()
                self.render('update_entry.html',
                            entry=entry,
                            images=images,
                            audios=audios,
                            uploadpath=__UPLOADS__,
                            thumbnailpath=__THUMBNAILS__)
            else:
                self.render('404.html')

    @tornado.web.authenticated
    def post(self):
        if self.session is None:
            self.redirect('/login?next=%2Fpodcast')
        else:
            entry_id = self.get_argument("entry_id", None)
            title = self.get_argument("title", None)
            body = self.get_argument("body", None)
            tmp_image_filename = self.get_argument("image", None)
            image_filename = None
            if not tmp_image_filename in ['None', '']:
                image_filename = tmp_image_filename
            tmp_audio_filename = self.get_argument("audio", None)
            audio_filename = None
            if not tmp_audio_filename in ['None', '']:
                audio_filename = tmp_audio_filename
            self.application.blog.update_entry(entry_id, title, body, image_filename, audio_filename)
            self.redirect('/entry/' + entry_id)


class ShowEntryHandler(SessionMixin, BaseHandler):
    def get(self, entry_id):
        entry = self.application.blog.get_entry(entry_id)
        if entry:
            self.render('entry.html', entry=entry, user=self.current_user, session=self.session, convert_to_jst=convert_to_jst, markdown=markdown.Markdown(), file_exists=file_exists)
        else:
            self.render('404.html')


class UploadFormHandler(SessionMixin, BaseHandler):
    @tornado.web.authenticated
    def get(self):
        if self.session is None:
            self.redirect('/login?next=%2Fuploadform')
        else:
            self.render("fileuploadform.html")
 
 
class UploadHandler(SessionMixin, BaseHandler):
    def initialize(self):
        self.filename_count = 0

    def get_unique_filename(self, path, filename):
        basename = os.path.splitext(filename)[0]
        extension = os.path.splitext(filename)[1]
        if not os.path.isfile(path + filename):
            return filename
        else:
            self.filename_count += 1
            return self.get_unique_filename(path, basename + '-' + str(self.filename_count) + extension)

    def get_thumbnail_size(self, img):
        width, height = img.size
        if width > height:
            new_width = __THUMBNAIL_MAX_PIXEL__
            new_height = int(height * float(new_width) / float(width))
        if width <= height:
            new_height = __THUMBNAIL_MAX_PIXEL__
            new_width = int(width * float(new_height) / float(height))
        return (new_width, new_height)

    @tornado.web.authenticated
    def post(self):
        if self.session is None:
            self.redirect('/login')
        else:
            image_cname = None
            audio_cname = None
            if 'filearg1' in self.request.files:
                image_file_info = self.request.files['filearg1'][0]
                image_file_name = image_file_info['filename']
                image_cname = self.get_unique_filename(__UPLOADS__, image_file_name)
                image_fh = open(__UPLOADS__ + image_cname, 'wb')
                image_fh.write(image_file_info['body'])
                image_fh.close()
                if imghdr.what(__UPLOADS__ + image_cname) in ['gif', 'jpeg', 'png']:
                    img = Image.open(__UPLOADS__ + image_cname, 'r')
                    img.thumbnail(self.get_thumbnail_size(img))
                    img.save(__THUMBNAILS__ + image_cname)
                    img.close()
                    if not 'filearg2' in self.request.files:
                        images = self.application.imageutil.get_index()
                        audios = self.application.audioutil.get_index()
                        self.render('upload_complete.html', image_filename=image_cname, audio_filename=audio_cname, uploads=__UPLOADS__, images=images, audios=audios, thumbnailpath=__THUMBNAILS__, uploadpath=__UPLOADS__)
                else:
                    os.remove(__UPLOADS__ + image_cname)
                    self.write('Invalid file type. Only gif, jpeg and png are allowed.')
            if 'filearg2' in self.request.files:
                audio_file_info = self.request.files['filearg2'][0]
                audio_file_name = audio_file_info['filename']
                audio_cname = self.get_unique_filename(__UPLOADS__, audio_file_name)
                audio_fh = open(__UPLOADS__ + audio_cname, 'wb')
                audio_fh.write(audio_file_info['body'])
                audio_fh.close()
                if audio_file_info['content_type'] == 'audio/mp3':
                    images = self.application.imageutil.get_index()
                    audios = self.application.audioutil.get_index()
                    self.render('upload_complete.html', image_filename=image_cname, audio_filename=audio_cname, uploads=__UPLOADS__, images=images, audios=audios, thumbnailpath=__THUMBNAILS__, uploadpath=__UPLOADS__)
                else:
                    os.remove(__UPLOADS__ + audio_cname)
                    self.write('Invalid file type. Only gif, jpeg and png are allowed.')
            if not 'filearg1' in self.request.files and not 'filearg2' in self.request.files:
                self.write('Nothing uploaded.')


class ImageIndexHandler(SessionMixin, BaseHandler):
    def get(self):
        images = self.application.imageutil.get_index()
        user = self.current_user
        self.render('image_index.html', images=images, user=user, thumbnailpath=__THUMBNAILS__)


class AudioIndexHandler(SessionMixin, BaseHandler):
    def get(self):
        audios = self.application.audioutil.get_index()
        user = self.current_user
        self.render('audio_index.html', audios=audios, user=user, uploadpath=__UPLOADS__)


class RssHandler(SessionMixin, BaseHandler):
    def get(self):
        fg = FeedGenerator()
        fg.title(__PODCAST_TITLE__)
        fg.link(href=__PODCAST_LINK__)
        fg.description(__PODCAST_DESCRIPTION__)
        fg.load_extension('podcast')
        fg.podcast.itunes_category(*__PODCAST_ITUNES_CATEGORY__)
        fg.podcast.itunes_author(__PODCAST_ITUNES_AUTHOR__)

        entries = self.application.blog.get_index()
        for entry in entries:
            fe = fg.add_entry()
            fe.title(entry['title'])
            fe.description(entry['body'])
            fe.pubdate(convert_to_jst(entry['ts']))
            fe.link(href=__SITE_ROOT__ + 'entry/' + entry['entry_id'])
            fe.guid(__SITE_ROOT__ + 'entry/' + entry['entry_id'])
            if 'audio' in entry:
                if not entry['audio'] is None:
                    path_to_audiofile = __UPLOADS__ + entry['audio']
                    if os.path.exists(path_to_audiofile):
                        length = os.path.getsize(path_to_audiofile)
                        fe.enclosure(__SITE_ROOT__ + path_to_audiofile, str(length), 'audio/mpeg')
        self.set_header('Content-Type', 'application/rss+xml; charset=UTF-8')
        self.write(fg.rss_str(pretty=True))


class NotFoundHandler(SessionMixin, BaseHandler):
    def get(self, invalid_url_part):
        self.render('404.html')

if __name__ == "__main__":
    tornado.options.parse_command_line()
    settings = {
        "template_path": os.path.join(os.path.dirname(__file__), "templates"),
        "cookie_secret": "bZJc2sWbQLKos6GkHn/VB9oXwQt8S0R0kRvJ5/xJ89E=",
        "xsrf_cookies": True,
        "login_url": "/login",
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "debug": True
    }
    application = Application([
        (r"/", HomeHandler),
        (r"/logout", UserLogoutHandler),
        (r"/login", UserLoginHandler),
        (r"/register", UserRegisterHandler),
        (r"/podcast/?", PodcastIndexHandler),
        (r"/new", NewEntryHandler),
        (r"/delete", DeleteEntryHandler),
        (r"/deleteall", DeleteAllEntriesHandler),
        (r"/update", UpdateEntryHandler),
        (r"/entry/([0-9a-f]+)", ShowEntryHandler),
        (r"/uploadform", UploadFormHandler),
        (r"/upload", UploadHandler),
        (r"/uploads/(.*)", tornado.web.StaticFileHandler, {"path": "uploads"}),
        (r"/thumbnails/(.*)", tornado.web.StaticFileHandler, {"path": "thumbnails"}),
        (r"/images/?", ImageIndexHandler),
        (r"/audios/?", AudioIndexHandler),
        (r"/rss/?", RssHandler),
        (r"/(.*)", NotFoundHandler)
    ], **settings)
    application.sessions.clear_all_sessions()
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
