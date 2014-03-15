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
import pymongo

import conf
from clubdata import club

RESULTS = (1, 3, 3, 3)
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
        stats = [{'hit': 0, 'gap': 0, 'amount': 0} for _ in range(5)]
        for doc in self.collection.find():
            temp = int(doc['info']['level']) // 10
            index = temp if temp < 5 else 4
            stats[index]['hit'] += int(doc['hit'])
            stats[index]['gap'] += int(doc['gap'])
            stats[index]['amount'] += 1
        from pprint import pprint
        for d in stats:
            d['avg_hit'] = round(d['hit'] / d['amount'], 3)
            d['avg_gap'] = round(d['gap'] / d['amount'], 3)
        with open('../data/level_correlation_%d.txt' % conf.page_id, 'wt') as f:
            pprint(stats, f)

    def calc_loi_correlation(self):
        from pprint import pprint
        stats = {k: {'hit': 0, 'gap': 0, 'amount': 0} for k in ('null',) + LEAGUE}
        self.collection.ensure_index('loi')  # this is a multikey index
        for league in LEAGUE:
            for doc in self.collection.find({'loi': league}):
                stats[league]['hit'] += int(doc['hit'])
                stats[league]['gap'] += int(doc['gap'])
                stats[league]['amount'] += 1
        for doc in self.collection.find({'loi': []}):  # people without loi
            stats['null']['hit'] += int(doc['hit'])
            stats['null']['gap'] += int(doc['gap'])
            stats['null']['amount'] += 1
        for v in stats.values():
            v['avg_hit'] = round(v['hit'] / v['amount'], 3)
            v['avg_gap'] = round(v['gap'] / v['amount'], 3)

        stats2 = {k: {'hit': 0, 'gap': 0, 'amount': 0} for k in LEAGUE2}
        for league2 in LEAGUE2:
            for doc in self.collection.find({'$and': [{'loi': league2[0]}, {'loi': league2[1]}]}):
                try:
                    stats2[league2]['hit'] += int(doc['hit'])
                    stats2[league2]['gap'] += int(doc['gap'])
                    stats2[league2]['amount'] += 1
                except KeyError:
                    pass
        for v in stats2.values():
            v['avg_hit'] = round(v['hit'] / v['amount'], 3)
            v['avg_gap'] = round(v['gap'] / v['amount'], 3)

        with open('../data/loi_correlation_%d.txt' % conf.page_id, 'wt') as f:
            pprint(stats, f)
            pprint(stats2, f)


if __name__ == '__main__':
    analyzer = DataAnalysis()
    #analyzer.evaluate_correctness()
    #analyzer.find_loi()
    #analyzer.readdata()
    analyzer.calc_level_correlation()
    analyzer.calc_loi_correlation()
