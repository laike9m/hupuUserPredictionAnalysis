"""
可能的指标：
    正确场次(hit) - 正确1,错误0
    分差(gap) - d((1,1,1,1), (1,3,3,3)) = 0 + 2 + 2 + 2 = 6

document示例 {
    '_id': ObjectId('532319cdfb6dec0dd429b9f4'),
    'name': 'pastacyndi',
    'info': {
        'laliga主队': '皇家马德里',
        'premierleague主队': '切尔西',
        'ligue1主队': '里昂',
        'seriea主队': '那不勒斯',
        'bundesliga主队': '拜仁慕尼黑'
        'level': 15,
        'interest': ['切尔西', '皇家马德里'],
    },
    'prediction': ['3', '3', '1', '3']
}

(1) 计算评价指标,写入document
(2) 计算关注联赛,写入document
(3) 评价等级关联度
(4) 评价联赛关注关联度
"""
from collections import OrderedDict

import pymongo

import conf
from clubdata import club

RESULTS = conf.RESULTS[conf.page_id]
LEAGUE = ('laliga', 'premierleague', 'ligue1', 'bundesliga', 'seriea')
LEAGUE2 = tuple((x, y) for x in LEAGUE for y in LEAGUE[LEAGUE.index(x) + 1:])


class DataAnalysis():
    def __init__(self):
        self.client = pymongo.MongoClient()
        self.db = self.client.db1
        self.collection = self.db['hupu_prediction_%d' % conf.page_id]

    def readdata(self):
        for doc in self.collection.find():
            print(doc)

    def evaluate_correctness(self):
        for doc in self.collection.find():
            hit = sum(1 for x, y in zip(doc['prediction'], RESULTS) if int(x) == y)
            gap = sum(abs(int(x) - int(y)) for x, y in zip(doc['prediction'], RESULTS))
            self.collection.update({'_id': doc['_id']}, {'$set': {'hit': hit, 'gap': gap}})

    def find_loi(self):
        """loi = league of interest"""
        for doc in self.collection.find():
            loi_affiliation = [l for l in LEAGUE if l + '主队' in doc['info']]
            try:
                loi_interest = [club[clubname] for clubname in doc['info']['interest'] if clubname in club]
            except KeyError:
                loi_interest = []  # no 'interest' field
            loi = list(set(loi_interest + loi_affiliation))
            self.collection.update({'_id': doc['_id']}, {'$set': {'loi': loi}})

    def calc_level_correlation(self):
        """计算等级关联,粒度10level,0-9,10-19,20-29,30-39,40+"""
        self.stats_level = [OrderedDict({'hit': 0, 'gap': 0, 'amount': 0}) for _ in range(5)]
        for doc in self.collection.find():
            temp = int(doc['info']['level']) // 10
            index = temp if temp < 5 else 4
            self.stats_level[index]['hit'] += int(doc['hit'])
            self.stats_level[index]['gap'] += int(doc['gap'])
            self.stats_level[index]['amount'] += 1
        from pprint import pprint
        for d in self.stats_level:
            d['avg_hit'] = round(d['hit'] / d['amount'], 3)
            d['avg_gap'] = round(d['gap'] / d['amount'], 3)
        with open('../data/level_correlation_%d.txt' % conf.page_id, 'wt') as f:
            pprint(self.stats_level, f)

    def calc_loi_correlation(self):
        from pprint import pprint
        self.collection.ensure_index('loi')  # this is a multikey index

        self.stats_loi1 = {k: OrderedDict({'hit': 0, 'gap': 0, 'amount': 0}) for k in ('null',) + LEAGUE}
        for league in LEAGUE:
            for doc in self.collection.find({'loi': league}):
                self.stats_loi1[league]['hit'] += int(doc['hit'])
                self.stats_loi1[league]['gap'] += int(doc['gap'])
                self.stats_loi1[league]['amount'] += 1
        for doc in self.collection.find({'loi': []}):  # people without loi
            self.stats_loi1['null']['hit'] += int(doc['hit'])
            self.stats_loi1['null']['gap'] += int(doc['gap'])
            self.stats_loi1['null']['amount'] += 1
        for v in self.stats_loi1.values():
            v['avg_hit'] = round(v['hit'] / v['amount'], 3)
            v['avg_gap'] = round(v['gap'] / v['amount'], 3)

        self.stats_loi2 = {k: OrderedDict({'hit': 0, 'gap': 0, 'amount': 0}) for k in LEAGUE2}
        for league2 in LEAGUE2:
            for doc in self.collection.find({'$and': [{'loi': league2[0]}, {'loi': league2[1]}]}):
                try:
                    self.stats_loi2[league2]['hit'] += int(doc['hit'])
                    self.stats_loi2[league2]['gap'] += int(doc['gap'])
                    self.stats_loi2[league2]['amount'] += 1
                except KeyError:
                    pass
        for v in self.stats_loi2.values():
            v['avg_hit'] = round(v['hit'] / v['amount'], 3)
            v['avg_gap'] = round(v['gap'] / v['amount'], 3)

        with open('../data/loi_correlation_%d.txt' % conf.page_id, 'wt') as f:
            pprint(self.stats_loi1, f)
            pprint(self.stats_loi2, f)

    def write_to_excel(self):
        import xlwt
        book = xlwt.Workbook()
        sheet1 = book.add_sheet('Sheet 1', cell_overwrite_ok=True)
        sheet2 = book.add_sheet('Sheet 2', cell_overwrite_ok=True)
        row10, row20 = sheet1.row(0), sheet2.row(0)
        # write head
        for i, key in enumerate(self.stats_level[0], 1):
            row10.write(i, key)
            row20.write(i, key)
        row10.write(0, "等级")
        row20.write(0, "关注联赛")

        # write sheet 1: level correlation stats
        for row, element in enumerate(self.stats_level, 1):
            sheet1.write(row, 0, str(10 * row - 10) + '~' + str(10 * row -1))
            for col, value in enumerate(element.values(), 1):
                sheet1.write(row, col, value)

        # write sheet 2: loi correlation stats
        from itertools import chain
        for row, (loi, element) in enumerate(chain(self.stats_loi1.items(), self.stats_loi2.items()), 1):
            sheet2.write(row, 0, str(loi))
            for col, value in enumerate(element.values(), 1):
                sheet2.write(row, col, value)

        book.save('../data/analysis_result_%d.xls' % conf.page_id)


if __name__ == '__main__':
    analyzer = DataAnalysis()
    #analyzer.evaluate_correctness()
    #analyzer.find_loi()
    #analyzer.readdata()
    analyzer.calc_level_correlation()
    analyzer.calc_loi_correlation()
    analyzer.write_to_excel()
