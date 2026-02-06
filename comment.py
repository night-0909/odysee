# -*- encoding: utf-8 -*-

from datetime import datetime
import dateutil.parser
import sys, threading
import requests, json
from autoindent import Indent
from zoneinfo import ZoneInfo

# Note : autoindent package is https://github.com/ANoneTypeOn/autoindent/blob/master/autoindent.py // but change small things

class Program():
    def __init__(self, idchannel, handlechannel, tz, dateFormats):
        self.idchannel = idchannel
        self.handlechannel = handlechannel
        self.tzinfo = ZoneInfo(tz)
        self.dateFormats = dateFormats
        
        self.initLoggingFile()
        self.initResultFile()
            
    def initLoggingFile(self):
        loggingfilename = "comments_" + self.idchannel
        self.loggingfile = open(loggingfilename + ".log", "a", encoding="utf-8")
    
    def initResultFile(self):
        dateNow = self.getDateNow()
        resultfilename = "comments_" + self.idchannel + "_" + dateNow['dateFileString'] +  ".txt"
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
        sys.exit(1)
    
    # Used at the end of program without errors/exceptions and when errors/exception occured
    def clean(self):
        try:
            # Close Files
            self.loggingfile.close()
            self.resultfile.close()
        except Exception as e:
            print("Error cleaning up : " + str(e))
            
    def getComments(self, claim_id, page):
        comments = None
        
        commentsURL = 'https://comments.odysee.tv/api/v2?m=comment.List'
        headers = {"Content-Type": "application/json", "Origin": "https://odysee.com", "Referer": "https://odysee.com"}
        data = {
              "jsonrpc": "2.0",
              "id": 1,
              "method": "comment.List",
              "params": {
                "page": page,
                "claim_id": claim_id,
                "page_size": 999, # automatically set to 600 in response
                "top_level": False,
                "sort_by": 0
              }
        }
        print(commentsURL)
        print(data)
        try:
            response = requests.post(commentsURL, json=data, headers=headers)
            if response.status_code == 200:
                commentsResponse = response.text
                comments_json = json.loads(commentsResponse)
                result = comments_json.get('result')
                if 'error' in comments_json:
                    print(f"[×] claim_id={claim_id} Error getting comment.List commentsURL={commentsURL} data={data} : {comments_json['error']['message']}")
                    self.writelog(f"[×] claim_id={claim_id} Error getting comment.List commentsURL={commentsURL} data={data} : {comments_json['error']['message']}")
                else:
                    # Sometimes 'items' key is missing in result
                    comments = result
            else:
                print(f"[×] claim_id={claim_id} Response of commentsURL {commentsURL} isn't OK : {response.status_code} {response.text}")
                self.writelog(f"[×] claim_id={claim_id} Response of commentsURL {commentsURL} isn't OK : {response.status_code} {response.text}")
        except Exception as e:
            print(f"[×] claim_id={claim_id} Error commentsURL {commentsURL} : {e}")
            self.writelog(f"[×] claim_id={claim_id} Error commentsURL {commentsURL} : {e}")

        return comments  

    # Add a new key for each comment on the list for sub replies
    def augment_replies(self, base_comments):
        augmented_comments = []
        
        for base in base_comments:
            base["sub_replies"] = []
            augmented_comments.append(base)
            
        return augmented_comments

    # Find the replies belonging to base_comments
    def find_replies(self, all_replies, base_comments):
        lvl_comment = []
        
        for rep in all_replies:
            for base in base_comments:
                if rep["parent_id"] == base["comment_id"]:
                    # Each reply may have more sub-replies.
                    # We allocate the space for them.
                    rep["sub_replies"] = []
                    lvl_comment.append(rep)

        return lvl_comment

    # Arrange raw comments list to a list of comments with their replies
    def arrange_comments(self, comments):
        root_comments = []
        all_replies = []
        channel_ids = []
        channel_infos = {}
        
        for comment in comments:
            if "parent_id" in comment:
                all_replies.append(comment)
            else:
                root_comments.append(comment)

            if comment['channel_id'] not in channel_ids:
                channel_ids.append(comment['channel_id'])
        
        # Search channel_title for each channel that comments
        # Can be optimized if I make only one call to claim_search at the end of all comments
        if len(comments) > 0:
            pageChannels = 1
            hasMorePagesChannels = True
            while hasMorePagesChannels is True :
                channelInfosURL = 'https://api.na-backend.odysee.com/api/v1/proxy?m=claim_search'
                headers = {"Content-Type": "application/json-rpc", "Origin": "https://odysee.com", "Referer": "https://odysee.com"}
                data = {
                    "jsonrpc": "2.0",
                    "method": "claim_search",
                    "params": {
                        "page_size": 999, # automatically set to 50 in response
                        "page": pageChannels,
                        "no_totals": False,
                        "claim_ids": channel_ids
                    }
                }
                print(channelInfosURL)
                try:
                    response = requests.post(channelInfosURL, json=data, headers=headers)
                    if response.status_code == 200:
                        channelInfosResponse = response.text
                        channel_json = json.loads(channelInfosResponse)
                    else:
                        print(f"[×] channel_ids={channel_ids} Response of channelInfosURL {channelInfosURL} isn't OK : {response.status_code} {response.text}")
                        self.writelog(f"[×] channel_ids={channel_ids} Response of channelInfosURL {channelInfosURL} isn't OK : {response.status_code} {response.text}")
                        self.exitProgram()                
                except Exception as e:
                    print(f"[×] channel_ids={channel_ids} Error channelInfosURL {channelInfosURL} : {e}")
                    self.writelog(f"[×] channel_ids={channel_ids} Error channelInfosURL {channelInfosURL} : {e}")
                    self.exitProgram()

                if 'error' in channel_json:
                    print(f"[×] channel_ids={channel_ids} Error getting claim_search channelInfosURL={channelInfosURL} data={data} : {channel_json['error']['message']}")
                    self.writelog(f"[×] channel_ids={channel_ids} Error getting claim_search channelInfosURL={channelInfosURL} data={data} : {channel_json['error']['message']}")
                    self.exitProgram()                                        
                
                result = channel_json.get('result')
                items = result.get('items')
                for item in items:
                    channel_infos[item['claim_id']] = item.get('value').get('title')                        
                                                        
                total_pagesChannels = result['total_pages']
                pageChannels = pageChannels + 1

                if pageChannels > total_pagesChannels:
                    hasMorePagesChannels = False

            # Add channel_title to each comment
            # Sometimes channel_id isn't found in claim_search call (eg. comment appears in comment.List but not on Odysee, and channel_id don't exist anymore)
            for comment in comments:
                comment['channel_title'] = channel_infos.get(comment['channel_id'], comment['channel_name'])

        n_comms = len(comments)
        n_base = len(root_comments)
        n_replies = len(all_replies)

        n = 1
        lvl_comments = {n: self.augment_replies(root_comments)}

        while True:
            replies_sub = self.find_replies(all_replies, lvl_comments[n])
            n_lvl = len(replies_sub)

            if n_lvl:
                n += 1
                lvl_comments[n] = replies_sub
            else:
                break

        indices = list(range(2, len(lvl_comments) + 1))
        indices.reverse()

        for n in indices:
            for rep in lvl_comments[n]:
                for base in lvl_comments[n-1]:
                    if rep["parent_id"] == base["comment_id"]:
                        base["sub_replies"].append(rep)

        return {"root_comments": root_comments,
                "replies": all_replies,
                "levels": lvl_comments}

    def writeComments(self, comments, indent=0):
        for num, comment in enumerate(comments, start=1):
            ch_id = comment.get("channel_id")
            # If a title hasn't been set by channel owner, title is missing so we take channel_name
            ch_name = comment.get("channel_title") if comment.get("channel_title") is not None else comment.get("channel_name")
            comm = comment["comment"]
            release_time = comment.get("timestamp")
            date_text = datetime.fromtimestamp(int(release_time), self.tzinfo).strftime(self.dateFormats['dateString'])

            line = date_text + " " + ch_name + " " + "(" + ch_id + ") : " + comm
            indent_line = Indent()
            indent_line.add(line, indent)
            self.writeresult(str(indent_line))
            self.writeresult('\n')

            if ("replies" in comment
                    and "sub_replies" in comment
                    and comment["sub_replies"]):
                self.writeComments(comment["sub_replies"], indent=indent+4)

    def main(self):
        print("Starting program")
        self.writelog("Starting program")
        self.initChannel()

        self.writeresult("Channel " + self.urlchannel + " id : " + self.idchannel)
        self.writeresult("\n\n")
        
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

        pageClaims = 1
        hasMorePagesClaims = True
        while hasMorePagesClaims is True:
            dataClaimsURL['params']['page'] = pageClaims
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
            total_pagesClaims = result.get('total_pages')

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
                    duration = value.get('video').get('duration')
                else:
                    value = item.get('value')
                    claim_id_additionnalreq = claim_id
                    title = value.get('title')
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

                print("Date : " + dateVideo_text)
                self.writeresult("Date : " + dateVideo_text)
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

                # Get all comments, copied from https://github.com/belikor/lbrytools/comment_list.py functions with small edits
                pageComments = 1
                total_pagesComments = 1
                hasMorePagesComments = True

                while hasMorePagesComments is True:
                    commentsRequest = self.getComments(claim_id_additionnalreq, pageComments)
                    if commentsRequest is None:
                        self.exitProgram()

                    # Sometimes 'items' key isn't present
                    comments = commentsRequest.get('items', [])

                    comments = self.arrange_comments(comments)
                    self.writeComments(comments['root_comments'])
                    total_pagesComments = commentsRequest['total_pages']                       

                    pageComments = pageComments + 1
                    if pageComments > total_pagesComments:
                        hasMorePagesComments = False

                self.writeresult("\n")                
                
            pageClaims = pageClaims + 1
            if pageClaims > total_pagesClaims:
                hasMorePagesClaims = False

        print("Execution was OK")
        self.writelog("Execution was OK")
        print("Ending program")
        self.writelog("Ending program")
        self.clean()

if __name__ == "__main__":
    # Odysee
    handlechannel = '' # What's come after https://odysee.com/@
    idchannel = '' # idchannel is "Claim ID" value on About page of channel

    # Format
    tz = "Europe/Paris"
    dateFormats = {"dateString": "%d/%m/%Y %H:%M:%S", "dateDBString": "%Y-%m-%d %H:%M:%S", "dateFileString": "%d%m%Y%H%M%S"}
    
    # Launch
    program = Program(idchannel, handlechannel, tz, dateFormats)
    program.main()

