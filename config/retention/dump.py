import csv, json
import time, os
import gzip
import shutil
import pandas
import schedule
from elasticsearch import Elasticsearch, exceptions
USERNAME = os.getenv('USERNAME', "")
PASSWORD = os.getenv('PASSWORD', "")
DUMP_TIME = os.getenv('DUMP_TIME', "01:30")
print("start")

def job():
    name = None
    # create a timestamp using the time() method
    start_time = time.time()
    # concatenate a string for the client's host paramater
    host = "http://" + USERNAME + ":" + PASSWORD + "@elasticsearch:9200"
    # declare an instance of the Elasticsearch library
    client = Elasticsearch(host)
    docs = pandas.DataFrame()
    try:
        # use the JSON library's dump() method for indentation
        info = json.dumps(client.info(), indent=4)
        # pass client object to info() method
        print ("Elasticsearch client info():", info)
    except exceptions.ConnectionError as err:
        # print ConnectionError for Elasticsearch
        print ("\nElasticsearch info() ERROR:", err)
        print ("\nThe client host:", host, "is invalid or cluster is not running")
        # change the client's value to 'None' if ConnectionError
        client = None
    # valid client instance for Elasticsearch
    if client != None:
        # get all of the indices on the Elasticsearch cluster
        all_indices = client.indices.get_alias("*")
        # keep track of the number of the documents returned
        doc_count = 0
        # iterate over the list of Elasticsearch indices
        for num, index in enumerate(all_indices):
            a = client.ilm.explain_lifecycle(index)
            if("beat-7.12.0-" in index and a["indices"][index]["action"] == "complete"):
                # declare a filter query dict object
                match_all = {
                    "size": 1000, #zmazat potom
                    "query": {
                        "match_all": {}
                    }
                }
                # make a search() request to get all docs in the index
                resp = client.search(
                    index = index,
                    body = match_all,
                    scroll = '20s' # length of time to keep search context
                )
                # keep track of pass scroll _id
                old_scroll_id = resp['_scroll_id']
                name = "/usr/src/ret/data/" + index + ".json.gz"
                # use a 'while' iterator to loop over document 'hits'
                with gzip.open(name, 'wt', encoding="ascii") as fp:
                    fp.write("[")
                    while len(resp['hits']['hits']):   
                        # make a request using the Scroll API
                        resp = client.scroll(
                            scroll_id = old_scroll_id,
                            scroll = '2s' # length of time to keep search context
                        )
                        # check if there's a new scroll ID
                        if old_scroll_id != resp['_scroll_id']: 
                            print ("NEW SCROLL ID:", resp['_scroll_id'])
                        # keep track of pass scroll _id
                        old_scroll_id = resp['_scroll_id'] 
                        fp.write(',\n'.join(json.dumps(doc) for doc in resp['hits']['hits']))
                        fp.write(',')
                        doc_count += 1
                        #print ("DOC COUNT:", doc_count)
                last_line = None
                l = None
                with gzip.open(name, 'rb+') as fp:
                    last_line = fp.readlines()[-1]
                    l = str(last_line)
                    l = l.replace(",,","]")
                fin = gzip.open(name, "r")
                name_out = name[:-8]+"-dump.json.gz"
                fout = gzip.open(name_out, "wb")
                for line in fin:
                    fout.write(line.replace(last_line, eval(l)))
                fin.close()
                fout.close()
                os.remove(name)  
                client.indices.delete(index) #delete dumped index
        # print the total time and document count at the end
    print ("DONE\nTOTAL TIME:", time.time() - start_time, "seconds.")

schedule.every().day.at(DUMP_TIME).do(job)
while True:
    schedule.run_pending()
    time.sleep(1)
