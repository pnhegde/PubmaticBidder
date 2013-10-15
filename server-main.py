import sys
import random
import time  
import hashlib
import re
import json
import datetime
import base64
import os
import thread
import socket
import csv
import operator
import tornado.ioloop
import tornado.web
import tornado.httpclient
import tornado.options
import pygeoip

from pyDes import *
from urlparse import urlparse
from tornado.web import asynchronous
from collections import defaultdict
from tornado.options import define, options

#Address of the forecasting server
UDP_IP = "46.137.241.79"
UDP_PORT = 5006

class MainHandler(tornado.web.RequestHandler):
    def get(self):
	global campaignData
	global bidCountIndex     
	global gi4
        start = time.time()
        
        adHeight= self.get_argument('adHeight', True)
        requestId= self.get_argument('requestId', True)        
        adWidth=self.get_argument('adWidth',True)
        ip=self.get_argument('ip',True)
        pageurl=self.get_argument('pageurl',True)
        
        print pageurl
        
        bid = False
        bidCpm = 0
        code = ""
        
	domain = re.sub('www.',r'',str(pageurl.netloc))
	country = gi4.country_code_by_addr(ip).lower()

	try:
	  ronCampaigns = campaignData['display:roe']
	except KeyError:
	  ronCampaigns = list()
	try:
	  black = campaignData['display:roe:black:'+domain]
	except KeyError:
	  black = list()

	ronCampaigns = list(set(ronCampaigns) - set(black))			

	try:
	  whiteCampaigns = campaignData['display:white:'+domain]
	except KeyError:
	  whiteCampaigns = list()

	campaigns = list(set(ronCampaigns+whiteCampaigns))

	try:
	  geoCampaigns = campaignData['display:geo:'+country]
	except KeyError:
	  geoCampaigns = list()
	  
	campaigns = list(set(geoCampaigns) & set(campaigns))

	size=str(adWidth)+"x"+str(adHeight)
	try:
	  sizeCampaigns = campaignData['display:size:'+size]
	except KeyError:
	  sizeCampaigns = list()
	  
	campaigns = list(set(sizeCampaigns) & set(campaigns))

	if(len(campaigns)>0):
	  camplist=[]
	  for camp in campaigns:
	      l = [camp, campaignData["display:campaign:"+str(camp)+":bid"],campaignData["display:campaign:"+str(camp)+":pacing"]]
	      camplist.append(l)
	      
	  camplist.sort(key=operator.itemgetter(1), reverse=True) # sorts the list in place decending by bids
	  
	  finalCampaign=0
	  for camp in camplist:
	      r=random.randrange(1,100)
	      if r<camp[2]:
		  finalCampaign=camp[0]
		  finalBid=camp[1]
		  break
		  
	  if finalCampaign>0:
	      bid = True
	      banners = campaignData['display:campaign:'+str(finalCampaign)+':'+str(adWidth)+'x'+str(adHeight)]
	      randomBannerId = random.choice(banners)
	      landingPageURL = campaignData['display:campaign:'+str(finalCampaign)+':url']
	      buyerId=campaignData['display:campaign:'+str(finalCampaign)+':advertiserId']
	      bidCpm = finalBid
	      info = base64.b64encode(json.dumps({'e':'pubmatic','d':domain,'bid':randomBannerId,'cid':finalCampaign, 'b':finalBid,"country":country}))
	      info = info.replace("+","-").replace("/","_").replace("=","")
	      code="http://rtbidder.impulse01.com/serve?info='+info+'&p={PUBMATIC_SECOND_PRICE}&r={RANDOM}&red="

        if bid == False :
	    self.write("id="+str(random.randRange(1000000,9999999)))
	    self.write("bid="+bidCpm)
	else:
	    self.write("id="+str(random.randRange(1000000,9999999)))
	    self.write("bid="+bidCpm)
	    self.write("buyer="+buyerId)
	    self.write("creativeId="+randomBannerId)
	    self.write("creativeHTMLURL="+code)
	    self.write("landingPageURL="+landingPageURL)
	    self.write("landingPageTLD="+re.sub('www.',r'',str(landingPageURL.netloc)))	    
	    self.write("requestId="+requestId)
	
        timeTaken = time.time() - start

def autovivify(levels=1, final=dict):
    return (defaultdict(final) if levels < 2 else defaultdict(lambda: autovivify(levels - 1, final)))

	
#---------------------Refresh Campaign Index------------------------------------------------
def refreshCache():
    global campaignData
    http_client = tornado.httpclient.HTTPClient()
    try:
	response = http_client.fetch("http://terminal.impulse01.com:5003/index?channel=1")
	invertedIndex=json.loads(response.body)
    except:
        invertedIndex=dict()
    campaignData=invertedIndex
    print options.name+" Refreshed campaign inverted index from http://terminal.impulse01.com:5003/index?channel=1"
#-----------------------------------------------------------------------------------------------



#----------------------Initialize the Tornado Server --------------------------------
define("port", default=8888, help="run on the given port", type=int)
define("name", default="noname", help="name of the server")
define("refreshCache", default=10000, help="millisecond interval between cache refresh", type=int)
#sredisClient = tornadoredis.Client('cookie-tokyo.impulse01.com')
#redisClient.connect()
application = tornado.web.Application([(r".*", MainHandler),])
gi4 = pygeoip.GeoIP('/home/GeoLiteCity.dat', pygeoip.MEMORY_CACHE)
#-----------------------------------------------------------------------------------------------


#---------------------Construct Campaign Index------------------------------------------------
campaignData=dict()
http_client = tornado.httpclient.HTTPClient()
try:
    response = http_client.fetch("http://terminal.impulse01.com:5003/index?channel=1")
    invertedIndex=json.loads(response.body)
except:
    invertedIndex=dict()
campaignData=invertedIndex
print options.name+" Loaded campaign inverted index from http://terminal.impulse01.com:5003/index?channel=1"

#-----------------------------------------------------------------------------------------------

bidCountIndex = autovivify(6, int)

if __name__ == "__main__":
    tornado.options.parse_command_line()
    application.listen(options.port)
    tornado.ioloop.PeriodicCallback(refreshCache, options.refreshCache).start()
    tornado.ioloop.IOLoop.instance().start()     