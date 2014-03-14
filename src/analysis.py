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
from clubdata import club

RESULTS = (1, 3, 3, 3)
LEAGUE = ('laliga', 'premierleague', 'ligue1', 'bundesliga', 'seriea')


class DataAnalysis():
    def __init__(self):
        self.client = pymongo.MongoClient()
        self.db = self.client.db1
        self.collection = self.db['hupu_prediction_9039396']

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


if __name__ == '__main__':
    analyzer = DataAnalysis()
    analyzer.evaluate_correctness()
    analyzer.find_loi()
    analyzer.readdata()
