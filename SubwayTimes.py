from google.transit import gtfs_realtime_pb2
import requests
import time #imports module for Epoch/GMT time conversion
from flask import Flask, render_template
from protobuf_to_dict import protobuf_to_dict

app = Flask(__name__)

@app.route('/')
def hello():
   #Requests subway status data feed from City of New York MTA API     
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get('https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm', 
        headers={"x-api-key": '---INSERT KEY HERE---'}, allow_redirects=True)
    feed.ParseFromString(response.content)

    #The MTA data feed uses the General Transit Feed Specification (GTFS) which
    #is based upon Google's "protocol buffer" data format. While possible to
    #manipulate this data natively in python, it is far easier to use the
    #"gtfs-realtime-bindings" library which can be found on pypi
    subwayFeed = protobuf_to_dict(feed) #subwayFeed is a dictionary
    realtimeData = subwayFeed['entity'] #trainData is a list

    #Because the data feed includes multiple arrival times for a given station
    #a global list needs to be created to collect the various times
    collectedTimes = []

    #This function takes a converted MTA data feed and a specific station ID and
    #loops through various nested dictionaries and lists to (1) filter out active
    #trains, (2) search for the given station ID, and (3) append the arrival time
    #of any instance of the station ID to the collectedTimes list
    def stationLookup(trainData, station):
        for trains in trainData: # trains are dictionaries
            if trains.get('trip_update', False) != False:
                uniqueTrainSchedule = trains['trip_update'] #train_schedule is a dictionary with trip and stop_time_update
                try:
                    arrivalTimes = uniqueTrainSchedule['stop_time_update'] #arrival_times is a list of arrivals
                    for scheduledArrivals in arrivalTimes: #arrivals are dictionaries with time data and stop_ids
                        if scheduledArrivals.get('stop_id', False) == station:
                            timeData = scheduledArrivals['arrival']
                            uniqueTime = timeData['time']
                            if uniqueTime != None:
                                collectedTimes.append(uniqueTime)
                except KeyError:
                    pass
                    
    #Run the above function for the station ID for Broadway-Lafayette
    stationLookup(realtimeData, 'B06S')

    #Sort the collected times list in chronological order (the times from the data
    #feed are in Epoch time format)
    collectedTimes.sort()
    print(len(collectedTimes)) #At night the Roosevelt Island trains dont run so we only have one train, 
    #need to add error checking to see if we have that many trains

    #Grab the current time so that you can find out the minutes to arrival
    currentTime = int(time.time())

    #Check to make sure that there are enough trains to fill in the template
    if(len(collectedTimes) == 0):
        nextTrain = "N/A"
        secondTrain = "N/A"
        thirdTrain = "N/A"

    elif(len(collectedTimes) == 1):
        nearestArrival = collectedTimes[0]
        secondTrain = "N/A"
        thirdTrain = "N/A"

        nextTrain = int(((nearestArrival - currentTime) / 60))
    elif(len(collectedTimes) <= 2):
        nearestArrival = collectedTimes[0]
        secondTime = collectedTimes[1]
        thirdTrain = "N/A"

        nextTrain = int(((nearestArrival - currentTime) / 60))
        secondTrain = int(((secondTime - currentTime) / 60))
    elif(len(collectedTimes) >= 3):
        nearestArrival = collectedTimes[0]
        secondTime = collectedTimes[1]
        thirdTime = collectedTimes[2]

        nextTrain = int(((nearestArrival - currentTime) / 60))
        secondTrain = int(((secondTime - currentTime) / 60))
        thirdTrain = int(((thirdTime - currentTime) / 60))

    if(nextTrain == 0):
        #Train is currently in the station, so this train is not useful 
        #so we shift everything up a spot and grab the next time
        nextTrain = secondTrain
        secondTrain = thirdTrain
        thirdTrain = int(((collectedTimes[3] - currentTime) / 60))
    
    if(nextTrain == 1):
        minute = "minute"
    else:
        minute = "minutes"

    templateData = {
        'title' : 'Trains',
        'nextTrain': nextTrain,
        'secondTrain': secondTrain,
        'thirdTrain': thirdTrain,
        'minute': minute
    }
    return render_template('index.html', **templateData)
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=1500)