"""
获取数据, http://bbs.hupu.com/9039396-n.html
注意:页面编码实际上是gbk, 但是headcharset里面写的是gb2312, 导致繁体字符无法正确解码！！
"""

import lxml.html as html
import re

from lxml import etree
from html.parser import HTMLParser
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

import requests
from clubdata import club, clubname_alias


class DataCollector():

    def __init__(self):
        self.base_url = 'http://bbs.hupu.com/9039396.html'
        self.page_url_list = ()
        self.vs = ('拜仁VS阿森[纳|娜]', '马[竞|竟]VS米兰', '巴萨VS曼城', '巴黎VS勒沃库森')
        self.vs_pattern = re.compile(r'({0}.*?\d).*({1}.*?\d).*({2}.*?\d).*({3}.*?\d)'\
                                     .format(*self.vs), flags=re.DOTALL | re.IGNORECASE)
        self.vs_pattern2 = re.compile(r'\d{4}')  # 1331
        self.level_pattern = re.compile(r'<span class="f666">论坛等级：</span>(\d+)')
        self.page_amount = self.get_page_amount()
        self.fetched_info = []  # final return value

    @staticmethod
    def httpget(url):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; \
                WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.107 Safari/537.36",
            "Referer": "http://bbs.hupu.com/9039396.html",
        }
        r = requests.get(url, headers=headers)
        r.encoding = 'gbk'
        return r

    def get_page_amount(self):
        r = self.httpget(self.base_url)
        div_class_page = html.fromstring(r.text).cssselect(".page")[0]
        h = HTMLParser()
        div_text = h.unescape(etree.tostring(div_class_page).decode('utf-8'))
        last_match = re.findall(r'>(\d+)<', div_text)[-1]
        if last_match:
            page_amount = last_match.strip('<>')
            print("page amount is " + page_amount)
            page_amount = int(page_amount)
            self.page_url_list = tuple(self.base_url.rstrip(".html") + '-%d.html' %\
                                       ii for ii in range(2, page_amount + 1))
            self.page_url_list = (self.base_url,) + self.page_url_list
            return page_amount
        else:
            print("get_page_amount wrong!")

    def get_userlist_onepage(self, page_url):
        """从一个页面获取用户列表
            format: ((user1, link1), (user2, line2)..)
        """
        r = self.httpget(page_url)
        r.encoding = 'gbk'
        a_class_u = html.fromstring(r.text).cssselect("div.left>a.u")
        if page_url == self.base_url:
            # first page, strip first two(LZ)
            user_list = [a.text for a in a_class_u[1:]]
            user_link_list = [a.attrib['href'] for a in a_class_u[1:]]
        else:
            user_list = [a.text for a in a_class_u]
            user_link_list = [a.attrib['href'] for a in a_class_u]
        from collections import Counter
        # 同一个人多次预测, 这里只针对在同一页的情形. 把重复出现的+index使不重复, 否则userinfo长度比prediction短
        users_duplicate = (x for x, y in Counter(user_list).items() if y > 1)
        for user in users_duplicate:
            indices = [i for i, x in enumerate(user_list) if x == user]
            for index in indices[1:]:
                user_list[index] += str(index)
        assert len(user_list) == len(user_link_list), "get_userlist error!"
        return tuple(zip(user_list, user_link_list))

    def get_userinfo_onepage(self, page_url):
        """获取一个页面的用户个人信息
            主队
            (1) span itemprop='affiliation'>a text 主队
            等级
            (2) <span class="f666">论坛等级：</span>"14  "
            兴趣
            (3) div.brief m5px text 的兴趣：-> split+strip
            (4) span#j_hobby_m text split+strip
            return userinfo_onepage{username:userinfo, ...}
        """
        user_list = self.get_userlist_onepage(page_url)
        userinfo_onepage = OrderedDict()

        def get_userinfo(userinfo_link):  # 不定义成类的函数好不好?
            userinfo = {'level': 0}
            r = self.httpget(userinfo_link)
            userinfo_page = html.fromstring(r.text)
            # 主队
            affiliation_list = userinfo_page.cssselect("span[itemprop='affiliation']>a")

            for affiliation in affiliation_list:
                clubname = affiliation.text
                if clubname in clubname_alias:
                    clubname = clubname_alias[clubname]  # 队名转换
                if clubname in club:
                    userinfo[club[clubname] + '主队'] = clubname
                    #print(club[clubname]+'主队: '+clubname)
            # 等级
            try:
                level = int(re.search(self.level_pattern, r.text).group(1))
                userinfo['level'] = level
                #print("level: %d" % level)
            except AttributeError:
                print("get level wrong!")
            # 兴趣
            if userinfo_page.cssselect("div.m5px"):
                interests_part1 = userinfo_page.cssselect("div.m5px")[0].text
                interests_part2 = userinfo_page.cssselect("span#j_hobby_m")
                interests_part2 = interests_part2[0].text if interests_part2 else ''
                interests = interests_part1 + interests_part2
                interests = interests[interests.index('：') + 1:].split()
                userinfo['interest'] = interests
                #print(interests)
            return userinfo

        for user in user_list:
            username, userlink = user
            #print(username)
            userinfo = get_userinfo(userlink)
            userinfo_onepage[username] = userinfo
        return userinfo_onepage

    def get_userprediction_onepage(self, page_url):
        """获取一个页面的预测结果
            format: [(3,0,1,1),(3,3,3,3),...]
        """
        prediction_list_onepage = []
        r = requests.get(page_url)
        a_class_case = html.fromstring(r.text).cssselect("table.case>tr>td")

        def get_text(element):
            h = HTMLParser()
            div_text = h.unescape(etree.tostring(element).decode('utf-8'))
            return div_text

        if page_url == self.base_url:
            prediction_text = tuple(get_text(a) for a in a_class_case[1:])  # first page, strip first one(LZ)
        else:
            prediction_text = tuple(get_text(a) for a in a_class_case)

        for prediction in prediction_text:
            results = re.search(self.vs_pattern, prediction)
            if results:
                prediction_list_onepage.append(tuple(vs_result[-1] for vs_result in results.groups()))
            else:
                results = re.search(self.vs_pattern2, prediction)
                if results:
                    prediction_list_onepage.append(tuple(results.group()))
                else:
                    prediction_list_onepage.append(None)
                    print("get prediction error! pageurl: {0} {1}".format(page_url, prediction_text.index(prediction)))
        return prediction_list_onepage

    def fetch_onepage(self, page_url):
        userinfo_onepage = self.get_userinfo_onepage(page_url)
        prediction_list_onepage = self.get_userprediction_onepage(page_url)
        assert len(userinfo_onepage) == len(prediction_list_onepage), \
            "length not equal, pageurl: {0}".format(page_url)
        print("page %d fetch success" % self.page_url_list.index(page_url))
        for (username, userinfo), userprediction in zip(userinfo_onepage.items(), prediction_list_onepage):
            if userprediction:
                self.fetched_info.append({'name': username, 'info': userinfo, 'prediction': userprediction})

    def fetch_all(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            for page_url in self.page_url_list:
                executor.submit(self.fetch_onepage, page_url,)


if __name__ == "__main__":
    test = DataCollector()
    test.fetch_all()
    #test.fetch_onepage(test.base_url)
    with open("fetched_info.txt", 'wt', encoding='utf-8') as f:
        for info_item in test.fetched_info:
            f.write(str(info_item) + '\n')