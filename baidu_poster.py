#coding: utf-8
"""
Author: piglei2007@gmail.com
Version: 1.0
"""
import wx
import os
import urllib
import urllib2
import cookielib
import simplejson
import tempfile

class LoginError(Exception):
    """登录失败抛出异常"""
    pass

def text_wrapped_by(start, end, content):
    """get the text wrapped by start、end in content"""
    si = content.find(start)
    if si != -1:
        si += len(start)
        ei = content.find(end, si)
        if ei != -1:
            return content[si:ei]
    return None

class Shower(wx.App):

    result = ""

    def __init__(self, *args, **kwargs):
        image = kwargs.pop("image")

        wx.App.__init__(self, *args, **kwargs)

        self.frame = wx.Frame(None, wx.ID_ANY, "please input", size=(200, 90))
        self.frame.Show(True)
        self.panel = wx.Panel(self.frame, -1, size=(200, 90))

        # image
        jpg = wx.Image(image, wx.BITMAP_TYPE_JPEG).ConvertToBitmap()
        wx.StaticBitmap(self.panel, -1, jpg, (10, 10), (jpg.GetWidth(), jpg.GetHeight()))

        # text input
        self.t = wx.TextCtrl(self.panel, -1, "", (10, 55), size=(135, -1))
        self.t.Bind(wx.EVT_CHAR, self.OnInput)
        self.t.SetFocus()

        # button
        self.b = wx.Button(self.panel, 10, "OK", (150, 55))
        self.Bind(wx.EVT_BUTTON, self.OnClick, self.b)
        self.b.SetSize((40, 26))

    def _submit(self):
        value = self.t.GetValue()
        if len(value) == 4:
            self.result = value
            self.frame.Close()

    def OnClick(self, event):
        self._submit()

    def OnInput(self, event):
        if event.GetKeyCode() == 13:
            self._submit()
        event.Skip()

    def start(self):
        self.MainLoop()

class BaiduUser(object):

    COOKIE_PATH = "cookies"
        
    LOGIN_URL = "https://passport.baidu.com/?login"
    LOGIN_IMG_URL = "https://passport.baidu.com/?verifypic"
    POST_URL = "http://tieba.baidu.com/f/commit/post/add"
    THREAD_URL = "http://tieba.baidu.com/f/commit/thread/add"
    TBS_URL = "http://tieba.baidu.com/dc/common/tbs"
    VCODE_URL = "http://tieba.baidu.com/f/user/json_vcode?lm=%s&rs10=2&rs1=0&t=0.7"
    IMG_URL = "http://tieba.baidu.com/cgi-bin/genimg?%s"

    LOGIN_ERR_MSGS = {
        "1": "用户名格式错误，请重新输入",
        "2": "用户不存在",
        "3": "",
        "4": "登录密码错误，请重新输入",
        "5": "今日登录次数过多",
        "6": "验证码不匹配，请重新输入验证码",
        "7": "登录时发生未知错误，请重新输入",
        "8": "登录时发生未知错误，请重新输入",
        "16": "对不起，您现在无法登录",
        "51": '该手机号未通过验证',
        "52": '该手机已经绑定多个用户',
        "53": '手机号码格式不正确',
        "58": '手机号格式错误，请重新输入',
        "256": "",
        "257": "请输入验证码",
        "20": "此账号已登录人数过多",
        "default": "登录时发生未知错误，请重新输入"
    }
    POST_ERR_MSGS = {
        "38": "验证码超时，请重新输入",
        "40": "验证码输入错误，请您返回后重新输入",
        "703": "为了减少恶意灌水和广告帖，本吧被设置为仅本吧会员才能发贴",
        "704": "为了减少恶意灌水和广告帖，本吧被设置为仅本吧管理团队才能发贴，给您带来的不便深表歉意",
        "705": "本吧当前只能浏览，不能发贴！",
        "706": "抱歉，本贴暂时无法回复。",
        "900": "为抵御挖坟危害，本吧吧主已放出贴吧神兽--超级静止蛙，本贴暂时无法回复。"
    }

    def __init__(self, username, password):
        self.username = username
        self.password = password
        if not os.path.exists(self.COOKIE_PATH):
            os.makedirs(self.COOKIE_PATH)
        self.COOKIE_FILE = os.path.join(self.COOKIE_PATH, str(hash(self.username)))
        self.cj = cookielib.MozillaCookieJar(self.COOKIE_FILE)
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
        self.opener.addheaders = [
            ("User-agent", "Mozilla/5.0 (X11; U; FreeBSD i386; en-US; rv:1.9.1) Gecko/20090704 Firefox/3.5"),
            ("Accept", "*/*")
        ]

    def is_login(self):
        """通过访问TBS判断是否是登录状态"""
        content = self.opener.open(self.TBS_URL).read()
        content = simplejson.loads(content)
        return content["is_login"]
        
    def login(self, verify_code=""):
        """
        登录
        """
        print u"正在登录 %s ..." % self.username
        if os.path.exists(self.COOKIE_FILE):
            try:
                self.cj.load()
                print "发现上次登录的cookie，使用旧cookie."
                if self.is_login():
                    return
                print "cookie已失效，重新登录."
            except Exception, e:
                pass

        login_params = {
            'mem_pass': 'on',
            'username': self.username.encode("gbk"),
            'password': self.password,
            'verifycode': verify_code
        }
        result = self.opener.open(self.LOGIN_URL, urllib.urlencode(login_params))
        # 检查是否登录成功
        if "USERID" in [ x.name for x in self.cj ]:
            self.cj.save()
            return 

        content = result.read().decode("gbk", "ignore")
        body = text_wrapped_by('<body onload="sett_pwd_load()">', '</body>', content)
        err_code =  text_wrapped_by("get_err_str(", ",", body)
        # 如果是需要输入验证码
        if err_code == '257':
            print "需要输入验证码，重新登录中..."
            verify_code = self.open_img(self.LOGIN_IMG_URL)
            return self.login(verify_code=verify_code)
        
        err_msg = self.LOGIN_ERR_MSGS.get(err_code, self.LOGIN_ERR_MSGS["default"])
        raise LoginError(err_msg)

    def reply(self, url, content):
        """回复帖子"""
        print u"%s 正在发表回帖(%s)..." % (self.username, url)
        return self._post("post", url, content)

    def post(self, url, title, content):
        """发布帖子"""
        print u"%s 正在发表主帖(%s)..." % (self.username, url)
        return self._post("thread", url, title, content)

    def _post(self, ptype, *args):
        """
        发表回帖或主贴
        """
        if ptype == "thread":
            url, title, content = args
        else:
            url, content = args
        post_content = self.opener.open(url).read().decode("gbk", "ignore")
        tieba_name = self.get_tieba_name(post_content)
        if not tieba_name:
            return

        tieba_name = tieba_name.encode("utf-8")
        tbs = self.get_tbs(post_content)
        tid = self.get_tid(post_content)
        fid = self.get_fid(post_content)
        vcode_md5 = self.get_vcode(fid)

        # 获得验证码而且写入本地文件
        vcode = self.open_img(self.IMG_URL % vcode_md5)

        post_args = {
            "hasuploadpic": 0,
            "ie": "utf-8",
            "picsign": "",
            "rich_text": 1,
            "tfrom": 1,
            "quote_id": 0,
            "user_type": 0,
            "floor_num": "",
            "content": "%s<br>" % content,
            "kw": tieba_name, 
            "fid": fid,
            "tbs": tbs,
            "tid": tid,
            "vcode": vcode,
            "vcode_md5": vcode_md5,
        }
        if ptype == "thread":
            post_args.update(
                title=title,
                useSignName="on",
                floor_num=0
            )
        ret = self.opener.open(self.POST_URL if ptype == "post" else self.THREAD_URL, urllib.urlencode(post_args))
        ret = simplejson.loads(ret.read())
        ret_no = ret["no"]
        if ret_no == 0:
            print "发帖成功！(%s)..." % url
            return
        err_msg = self.POST_ERR_MSGS.get(str(ret_no))
        if err_msg:
            print err_msg
        else:
            print "发帖失败。(%s)..." % ret_no

        if ret_no in (38, 40):
            return self._post(ptype, *args)

    @staticmethod
    def get_tieba_name(content):
        ret = text_wrapped_by("<title>", u"吧_贴吧", content)
        if ret:
            return ret.split("_")[-1]
        return None

    @staticmethod
    def get_tbs(content):
        return text_wrapped_by('tbs:"', '"', content)

    @staticmethod
    def get_tid(content):
        ret = text_wrapped_by("tid:'", "'", content)
        return ret

    @staticmethod
    def get_fid(content):
        ret = text_wrapped_by("fid:'", "'", content)
        return ret

    def get_vcode(self, fid):
        content = self.opener.open(self.VCODE_URL % fid).read()
        content = simplejson.loads(content)
        return content['data']['vcodestr']

    def open_img(self, url):
        """
        获得验证码
        """
        img = self.opener.open(url)
        content = img.read()
        if not content:
            return ""

        f = tempfile.NamedTemporaryFile()
        f.write(content)
        f.flush()
        
        s = Shower(False, image=f.name)
        s.start()

        return s.result.encode("utf-8")

if __name__ == '__main__':
    username = u"用户名"
    password = "password"
    u = BaiduUser(username, password)
    u.login()
    # 发表主贴
    u.post("http://tieba.baidu.com/f?kw=asdfasdf", "this is a test(2)", "Hello, world.")
    # 发表回复
    u.reply("http://tieba.baidu.com/p/1150567896", "test")
