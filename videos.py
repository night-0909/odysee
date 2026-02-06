# -*- encoding: utf-8 -*-

from datetime import datetime
import dateutil.parser
import os, sys, threading
import requests, json
from zoneinfo import ZoneInfo

# Add return value from thread functionnality, see solutions : https://stackoverflow.com/questions/6893968/how-to-get-the-return-value-from-a-thread
class ThreadWithReturnValue(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}):
        threading.Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None 

    def run(self):
        try:
            if self._target:
                self._return = self._target(*self._args, **self._kwargs)
        finally:
            del self._target, self._args, self._kwargs

class Program():
    def __init__(self, idchannel, handlechannel, getThumbnail, tz, dateFormats):
        self.idchannel = idchannel
        self.handlechannel = handlechannel
        self.getThumbnail = getThumbnail
        self.tzinfo = ZoneInfo(tz)
        self.dateFormats = dateFormats
        
        self.initLoggingFile()
        self.initResultFile()
            
    def initLoggingFile(self):
        loggingfilename = "videosstats_" + self.idchannel
        self.loggingfile = open(loggingfilename + ".log", "a", encoding="utf-8")
    
    def initResultFile(self):
        dateNow = self.getDateNow()
        resultfilename = "videosstats_" + self.idchannel + "_" + dateNow['dateFileString'] +  ".txt"
        self.resultfile = open(resultfilename, "w", encoding="utf-8")
    
    def getDateNow(self):
        timestamp_now = datetime.now().timestamp()
        date = datetime.fromtimestamp(timestamp_now, self.tzinfo)
        dateString = date.strftime(self.dateFormats['dateString'])
        dateDBString = date.strftime(self.dateFormats['dateDBString'])
        dateFileString = date.strftime(self.dateFormats['dateFileString'])
        
        dateNow = {"dateString": dateString, "dateDBString": dateDBString, "dateFileString": dateFileString}
        
        return dateNow

    def writelog(self, message):
        dateNow = self.getDateNow()
        self.loggingfile.write(dateNow["dateString"] + " : " + message + "\n")
        # Write in real time
        self.loggingfile.flush()
            
    def writeresult(self, message):
        self.resultfile.write(message)
        # Write in real time
        #self.resultfile.flush()

    def initChannel(self):
        # Get handle from idchannel
        channelInfosURL = 'https://api.na-backend.odysee.com/api/v1/proxy?m=claim_search'
        headers = {"Content-Type": "application/json-rpc", "Origin": "https://odysee.com", "Referer": "https://odysee.com"}
        data = {
            "jsonrpc": "2.0",
            "method": "claim_search",
            "params": {
                "page_size": 999, # automatically set to 50 in response
                "page": 1,
                "no_totals": False,
                "claim_ids": [self.idchannel]
            }
        }
        print(channelInfosURL)
        try:
            response = requests.post(channelInfosURL, json=data, headers=headers)
            if response.status_code == 200:
                channelInfosResponse = response.text
                channel_json = json.loads(channelInfosResponse)       

                result = channel_json.get('result')
                items = result.get('items')
                if len(items) == 0:
                    print(f"[×] channel={self.idchannel} Impossible to find idchannel on Odysee API")
                    self.writelog(f"[×] channel={self.idchannel} Impossible to find idchannel on Odysee API")
                    self.exitProgram()
                else:
                    item = items[0]
                    canonical_url = item.get('canonical_url')
                    self.handlechannel = canonical_url.replace('lbry://@', '').replace('#', ':')
            else:
                print(f"[×] channel={self.idchannel} Response of channelInfosURL {channelInfosURL} isn't OK : {response.status_code} {response.text}")
                self.writelog(f"[×] channel={self.idchannel} Response of channelInfosURL {channelInfosURL} isn't OK : {response.status_code} {response.text}")
                self.exitProgram()
        except Exception as e:
            print(f"[×] channel={self.idchannel} Error channelInfosURL {channelInfosURL} : {e}")
            self.writelog(f"[×] channel={self.idchannel} Error channelInfosURL {channelInfosURL} : {e}")
            self.exitProgram()
            
        self.urlchannel = 'https://www.odysee.com/@' + self.handlechannel

    # Used when errors/exceptions occured and when we want to exit right now
    def exitProgram(self):
        self.writelog("Execution had errors")
        self.writelog("Ending program")
        self.clean()
        #sys.exit(1)
        os._exit(1)
    
    # Used at the end of program without errors/exceptions and when errors/exception occured
    def clean(self):
        try:
            # Close Files
            self.loggingfile.close()
            self.resultfile.close()
        except Exception as e:
            print("Error cleaning up : " + str(e))

    def getViewCount(self, auth_token, claim_id):
        viewCount = None
        
        viewcountURL = 'https://api.odysee.com/file/view_count'
        headers = {"Origin": "https://odysee.com", "Referer": "https://odysee.com"}
        data = {"auth_token": auth_token, "claim_id": claim_id}
        try:
            response = requests.post(viewcountURL, data=data, headers=headers)
            if response.status_code == 200:
                viewcountResponse = response.text
                viewcount_json = json.loads(viewcountResponse)

                if viewcount_json["success"]:
                    viewCount = viewcount_json["data"][0]
                else:
                    print(f"[×] claim_id={claim_id} Error getting view_count viewcountURL={viewcountURL} data={data} : {viewcount_json['error']}")
                    self.writelog(f"[×] claim_id={claim_id} Error getting view_count viewcountURL={viewcountURL} data={data} : {viewcount_json['error']}")
                    self.exitProgram()                    
            else:
                print(f"[×] claim_id={claim_id} Response of viewcountURL {viewcountURL} isn't OK : {response.status_code} {response.text}")
                self.writelog(f"[×] claim_id={claim_id} Response of viewcountURL {viewcountURL} isn't OK : {response.status_code} {response.text}")
                self.exitProgram()
                
        except Exception as e:
            print(f"[×] claim_id={claim_id} Error viewcountURL {viewcountURL} : {e}")
            self.writelog(f"[×] claim_id={claim_id} Error viewcountURL {viewcountURL} : {e}")
            self.exitProgram()
            
        return viewCount

    def getReactions(self, auth_token, claim_id):
        reactions = {"likeCount": None, "dislikeCount": None}
        
        reactionsURL = 'https://api.odysee.com/reaction/list'
        headers = {"Origin": "https://odysee.com", "Referer": "https://odysee.com"}
        data = {"auth_token": auth_token, "claim_ids": claim_id}
        try:
            response = requests.post(reactionsURL, data=data, headers=headers)
            if response.status_code == 200:
                reactionsResponse = response.text
                reactions_json = json.loads(reactionsResponse)

                if reactions_json["success"]:
                    reactions['likeCount'] = reactions_json["data"]["others_reactions"][claim_id]["like"]
                    reactions['dislikeCount'] = reactions_json["data"]["others_reactions"][claim_id]["dislike"]
                else:
                    print(f"[×] claim_id={claim_id} Error getting reaction/list reactionsURL={reactionsURL} data={data} : {reactions_json['error']}")
                    self.writelog(f"[×] claim_id={claim_id} Error getting view_count reactionsURL={reactionsURL} data={data} : {reactions_json['error']}")
                    self.exitProgram()                                        
            else:
                print(f"[×] claim_id={claim_id} Response of reactionsURL {reactionsURL} isn't OK : {response.status_code} {response.text}")
                self.writelog(f"[×] claim_id={claim_id} Response of reactionsURL {reactionsURL} isn't OK : {response.status_code} {response.text}")
                self.exitProgram()
        except Exception as e:
            print(f"[×] claim_id={claim_id} Error reactionsURL {reactionsURL} : {e}")
            self.writelog(f"[×] claim_id={claim_id} Error reactionsURL {reactionsURL} : {e}")
            self.exitProgram()

        return reactions

    def getCommentsCount(self, claim_id):
        commentCount = None
        
        commentsURL = 'https://comments.odysee.tv/api/v2?m=comment.List'
        headers = {"Content-Type": "application/json", "Origin": "https://odysee.com", "Referer": "https://odysee.com"}
        data = {
              "jsonrpc": "2.0",
              "id": 1,
              "method": "comment.List",
              "params": {
                "page": 1,
                "claim_id": claim_id,
                "page_size": 1,
                "top_level": False,
                "sort_by": 0
              }
        }
        try:
            response = requests.post(commentsURL, json=data, headers=headers)
            if response.status_code == 200:
                commentsResponse = response.text
                comments_json = json.loads(commentsResponse)
            
                if 'error' not in comments_json:
                    result = comments_json.get('result')
                    commentCount = result.get("total_items")
                else:
                    print(f"[×] claim_id={claim_id} Error getting comment.List commentsURL={commentsURL} data={data} : {comments_json['error']['message']}")
                    self.writelog(f"[×] claim_id={claim_id} Error getting comment.List commentsURL={commentsURL} data={data} : {comments_json['error']['message']}")
                    self.exitProgram()                                        
            else:
                print(f"[×] claim_id={claim_id} Response of commentsURL {commentsURL} isn't OK : {response.status_code} {response.text}")
                self.writelog(f"[×] claim_id={claim_id} Response of commentsURL {commentsURL} isn't OK : {response.status_code} {response.text}")
                self.exitProgram()                
        except Exception as e:           
            print(f"[×] claim_id={claim_id} Error commentsURL {commentsURL} : {e}")
            self.writelog(f"[×] claim_id={claim_id} Error commentsURL {commentsURL} : {e}")
            self.exitProgram()

        return commentCount
    
    def main(self):
        print("Starting program")
        self.writelog("Starting program")
        self.initChannel()

        self.writeresult("Channel " + self.urlchannel + " id : " + self.idchannel)
        self.writeresult("\n\n")
        
        # Get auth_token
        auth_token = None
        auth_tokenURL = 'https://api.odysee.com/user/new'
        headers = {"Content-Type": "application/json-rpc", "Origin": "https://odysee.com", "Referer": "https://odysee.com"}
        try:
            response = requests.post(auth_tokenURL, headers=headers)
            if response.status_code == 200:
                auth_tokenResponse = response.text
                auth_token_json = json.loads(auth_tokenResponse)
                if auth_token_json["success"]:
                    auth_token = auth_token_json["data"]["auth_token"]
                else:
                    print(f"[×] Error getting auth_token auth_tokenURL={auth_tokenURL} data={data} : {auth_token_json['error']}")
                    self.writelog(f"[×] Error getting auth_token auth_tokenURL={auth_tokenURL} data={data} : {auth_token_json['error']}")
                    self.exitProgram()
            else:
                print(f"[×] claim_id={claim_id} Response of auth_tokenURL {auth_tokenURL} isn't OK : {response.status_code} {response.text}")
                self.writelog(f"[×] claim_id={claim_id} Response of auth_tokenURL {auth_tokenURL} isn't OK : {response.status_code} {response.text}")
                self.exitProgram()                
        except Exception as e:           
            print(f"[×] Error auth_tokenURL {auth_tokenURL} : {e}")
            self.writelog(f"[×] Error auth_tokenURL {auth_tokenURL} : {e}")
            self.exitProgram()

        # Get all ressources of Content tab of Odysee channel
        claimsURL = 'https://api.na-backend.odysee.com/api/v1/proxy?m=claim_search'
        headers = {"Content-Type": "application/json-rpc", "Origin": "https://odysee.com", "Referer": "https://odysee.com"}
        dataClaimsURL = {
            "jsonrpc": "2.0",
            "method": "claim_search",
            "params": {
                "page_size": 999, # automatically set to 50 in response
                "page": 1,
                "no_totals": False,
                "order_by": [
                    "release_time"
                ],
                "channel_ids": [
                    self.idchannel
                ]
            }
        }
        print(claimsURL)
        
        page = 1
        hasMorePages = True
        while hasMorePages is True:
            dataClaimsURL['params']['page'] = page       
            try:
                response = requests.post(claimsURL, json=dataClaimsURL, headers=headers)
                if response.status_code == 200:
                    claimsResponse = response.text
                    claims_json = json.loads(claimsResponse)
                    if 'error' in claims_json:
                        print(f"[×] Error getting claims claimsURL={claimsURL} data={dataClaimsURL} : {claims_json['error']['message']}")
                        self.writelog(f"[×] Error getting claims claimsURL={claimsURL} data={dataClaimsURL} : {claims_json['error']['message']}")
                        self.exitProgram()
                else:                   
                    print(f"[×] Response of claimsURL {claimsURL} isn't OK : {response.status_code} {response.text}")
                    self.writelog(f"[×] Response of claimsURL {claimsURL} isn't OK : {response.status_code} {response.text}")
                    self.exitProgram()
            except Exception as e:
                print(f"[×] Error claimsURL {claimsURL} : {e}")
                self.writelog(f"[×] Error claimsURL {claimsURL} : {e}")
                self.exitProgram()
                
            result = claims_json.get('result')
            items = result.get('items')
            total_pages = result.get('total_pages')

            for item in items:
                url = item.get('canonical_url').replace('lbry://@', 'https://odysee.com/@').replace('#', ':')
                claim_id = item.get('claim_id')
                print(url)
                self.writeresult(url)
                self.writeresult("\n")

                if "release_time" not in item:
                    release_time = item.get("timestamp")
                else:
                    release_time = item.get("release_time")

                dateVideo_text = datetime.fromtimestamp(int(release_time), self.tzinfo).strftime(self.dateFormats['dateString'])

                claim_type = item.get('value_type')
                reposted_claim = item.get('reposted_claim')
                if claim_type == 'repost':
                    value = reposted_claim.get('value')
                    claim_id_additionnalreq = reposted_claim.get('claim_id')
                    title = value.get('title')
                    description = value.get('description')
                    duration = value.get('video').get('duration')
                else:
                    value = item.get('value')
                    claim_id_additionnalreq = claim_id
                    title = value.get('title')
                    description = value.get('description')
                    duration = value.get('video').get('duration')
                
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                seconds = (duration % 3600) % 60
                if hours > 0:
                    durationString = '{:02d}H{:02d}M{:02d}S'.format(hours, minutes, seconds)
                elif minutes > 0:
                    durationString = '{:02d}M{:02d}S'.format(minutes, seconds)
                else:
                    durationString = '{:02d}S'.format(seconds)
                
                # If auth_token couldn't be retrieved, we don't get viewCount and like/dislikeCount
                threads = []
                if auth_token is not None:
                    # View count
                    threadGetViewCount = ThreadWithReturnValue(target=self.getViewCount, kwargs={"auth_token": auth_token, "claim_id": claim_id_additionnalreq})
                    threadGetViewCount.start()
                    threads.append(threadGetViewCount)

                    # Like/dislike count
                    threadGetReactions = ThreadWithReturnValue(target=self.getReactions, kwargs={"auth_token": auth_token, "claim_id": claim_id_additionnalreq})
                    threadGetReactions.start()
                    threads.append(threadGetReactions)
                                                           
                # Comment count
                threadGetCommentsCount = ThreadWithReturnValue(target=self.getCommentsCount, kwargs={"claim_id": claim_id_additionnalreq})
                threadGetCommentsCount.start()
                threads.append(threadGetCommentsCount)

                # Wait for threads to finish and store their returned value
                for thread in threads:
                    thread.join()

                if auth_token is not None:
                    viewCount = threadGetViewCount._return
                    reactions = threadGetReactions._return
                commentCount = threadGetCommentsCount._return                    

                print("Date : " + dateVideo_text)
                self.writeresult("Date : " + dateVideo_text)

                if self.getThumbnail is True:
                    thumbnail_url = value.get('thumbnail').get('url')
                    try:
                        response = requests.get(thumbnail_url, stream = True)
                        if response.status_code == 200:
                            thumbnailInfosResponse = response.content
                            filethumbnail = claim_id + "_thumbnail_" + datetime.fromtimestamp(datetime.now().timestamp(), self.tzinfo).strftime(self.dateFormats['dateFileString']) + ".webp"
                            fthumbnail = open(filethumbnail, "wb")
                            fthumbnail.write(thumbnailInfosResponse)
                            fthumbnail.close()
                        else:
                            print(f"[×] claim_id={claim_id_additionnalreq} Response of thumbnail_url {thumbnail_url} isn't OK : {response.status_code} {response.text}")
                            self.writelog(f"[×] claim_id={claim_id_additionnalreq} Response of thumbnail_url {thumbnail_url} isn't OK : {response.status_code} {response.text}")
                            self.exitProgram()
                    except Exception as e:
                        print(f"[×] Erreur thumbnail : {e}")
                        print(f"[×] claim_id={claim_id_additionnalreq} Error thumbnail_url {thumbnail_url} : {e}")
                        self.writelog(f"[×] claim_id={claim_id_additionnalreq} Error thumbnail_url {thumbnail_url} : {e}")
                        self.exitProgram()                        

                self.writeresult("\n")
                print("Id : " + str(claim_id))
                self.writeresult("Id : " + str(claim_id))
                self.writeresult("\n")
                print("Title : " + str(title))
                self.writeresult("Title : " + str(title))
                self.writeresult("\n")
                print("Duration : " + str(durationString))
                self.writeresult("Duration : " + str(durationString))
                self.writeresult("\n")
                print("Description : " + str(description))
                self.writeresult("Description : " + str(description))
                self.writeresult("\n")
                print("Views : " + str(viewCount))
                self.writeresult("Views : " + str(viewCount))
                self.writeresult("\n")
                print("Likes : " + str(reactions['likeCount']))
                self.writeresult("Likes : " + str(reactions['likeCount']))
                self.writeresult("\n")
                print("Dislikes : " + str(reactions['dislikeCount']))
                self.writeresult("Dislikes : " + str(reactions['dislikeCount']))
                self.writeresult("\n")
                print("Comments : " + str(commentCount))
                self.writeresult("Comments : " + str(commentCount))
                self.writeresult("\n")

                if claim_type == 'repost':
                    self.writeresult("\nOriginal content :\n")
                    self.writeresult("URL : " + reposted_claim.get('canonical_url').replace('lbry://@', 'https://odysee.com/@').replace('#', ':'))
                    self.writeresult("\n")
                    self.writeresult("Id : " + reposted_claim.get('claim_id'))
                    self.writeresult("\n")
                    self.writeresult("Date original content : " + datetime.fromtimestamp(int(reposted_claim.get('timestamp')), self.tzinfo).strftime(self.dateFormats['dateString']))
                    self.writeresult("\n")
                    self.writeresult("Author : " + reposted_claim.get('signing_channel').get('canonical_url').replace('lbry://@', 'https://odysee.com/@').replace('#', ':') +
                    " (" + reposted_claim.get('signing_channel').get('claim_id') + ")")
                    self.writeresult("\n")

                self.writeresult("\n")
                
            page = page + 1
            if page > total_pages:
                hasMorePages = False

        print("Execution was OK")
        self.writelog("Execution was OK")
        print("Ending program")
        self.writelog("Ending program")
        self.clean()

if __name__ == "__main__":
    # Odysee
    handlechannel = '' # What's come after https://odysee.com/@
    idchannel = '' # idchannel is "Claim ID" value on About page of channel
    getThumbnail = False

    # Format
    tz = "Europe/Paris"
    dateFormats = {"dateString": "%d/%m/%Y %H:%M:%S", "dateDBString": "%Y-%m-%d %H:%M:%S", "dateFileString": "%d%m%Y%H%M%S"}
    
    # Launch
    program = Program(idchannel, handlechannel, getThumbnail, tz, dateFormats)
    program.main()

