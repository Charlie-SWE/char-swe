import http.client
import json

# get schedule to get game dates so that we can get game info and such later
conn = http.client.HTTPConnection("ncaa-api.henrygd.me") # can be subbed out for a self-hosted version later but idk how to do that !

# also of note - /schedule/ api endpoint seems to just 404, and is listed as kinda broken on the page itself so. probably not great
conn.request("GET", "/schedule-alt/soccer-women/d1/2025") 
# schedule-alt api endpoint only goes back to 2023? also error 422s before 2000 . so  
# still an amount of data to look at in here but maybe less than I was under the impression we could get.
# still not sure if this is the NCAA api that was brought up earlier or if there's another better one

response = conn.getresponse()
print(response.status, response.reason)
if response.status != 200:
    print("(insert error handling for non OK cases here)")
    #debug show whatever's there
    schedule = json.loads(response.read().decode())
    print(schedule)
else:
    schedule = json.loads(response.read().decode())
    # print(schedule)
    if schedule["data"]["schedules"] != None:
        print(str(len(schedule["data"]["schedules"]["games"])) + " scheduled games found.")
        for x in schedule["data"]["schedules"]["games"]:
            print(x["contestDate"]) 
            # thought process is "if you have the days a bunch of games happen on, 
            # you can probably go in and recursively grab from each of those too."
            # that said at the moment i dont know how best to go about this
            
            # unsure of how much we can properly get out of this data without just brute forcing a bunch of things annoyingly


conn.close()
