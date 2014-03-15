import pymongo
import fetch
import conf

test = fetch.DataCollector()


def storedata():
    test.fetch_all()
    fetched_data = test.fetched_info
    print("fetch finish")
    client = pymongo.MongoClient()
    db = client.db1
    collection = db['hupu_prediction_%d' % conf.page_id]
    print("start writing to db")
    collection.insert(fetched_data)  # bulk insert
    print("store success")


def readdata():
    client = pymongo.MongoClient()
    db = client.db1
    collection = db['hupu_prediction_%d' % conf.page_id]
    for data in collection.find():
        print(data)

    print(collection.count())


if __name__ == '__main__':
    #storedata()
    readdata()

