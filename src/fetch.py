"""
获取数据, http://bbs.hupu.com/9039396-n.html
"""

import concurrent.futures as cf
import lxml.html as html
import re

from lxml import etree
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor

import requests


class DataCollector():

    def __init__(self):
        self.base_url = 'http://bbs.hupu.com/9039396.html'
        self.page_list = ()
        self.vs = ('拜仁VS阿森纳', '马竞VS米兰', '巴萨VS曼城', '巴黎VS勒沃库森')
        self.vs_pattern = re.compile(r'({0}.*?\d).*({1}.*?\d).*({2}.*?\d).*({3}.*?\d)'.format(*self.vs))

    def get_page_amount(self):
        r = requests.get(self.base_url)
        div_class_page = html.fromstring(r.text).cssselect(".page")[0]
        h = HTMLParser()
        div_text = h.unescape(etree.tostring(div_class_page).decode('utf-8'))
        last_match = re.findall(r'>(\d+)<', div_text)[-1]
        if last_match:
            page_amount = last_match.strip('<>')
            print("page amount is " + page_amount)
            page_amount = int(page_amount)
            self.page_list = tuple(self.base_url.rstrip(".html")+'-%d.html' % i for i in range(2, page_amount+1))
            self.page_list = (self.base_url,) + self.page_list
            return page_amount
        else:
            print("get_page_amount wrong!")

    def get_userlist_onepage(self, page_url):
        """从一个页面获取用户列表, ((user1, link1), (user2, line2)..) """
        r = requests.get(page_url)
        a_class_u = html.fromstring(r.text).cssselect(".u")
        if page_url == self.base_url:
            # first page, strip first two(LZ)
            user_list = tuple((a.text, a.attrib['href']) for a in a_class_u[2:])
        else:
            user_list = tuple((a.text, a.attrib['href']) for a in a_class_u)
        return user_list

    def get_userprediction_onepage(self, page_url):
        """获取一个页面的预测结果"""
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
            result = re.search(self.vs_pattern, prediction)
            if result:
                prediction_list_onepage.append(tuple(i[-1] for i in result.groups()))
            else:
                prediction_list_onepage.append(None)
                print("get prediction error! pageurl: {0} {1}".format(page_url, prediction_text.index(prediction)))
        return prediction_list_onepage

    def get_userinfo_onepage(self, page_url):
        """获取一个页面的用户个人信息"""
        user_list = self.get_userlist_onepage(page_url)



if __name__ == "__main__":
    test = DataCollector()
    test.get_page_amount()
    test.get_userlist_onepage(test.base_url)
