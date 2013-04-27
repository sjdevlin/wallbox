# -*- coding: utf-8 -*-

# Copyright (C) 2013 Stephen Devlin

import RPi.GPIO as GPIO
import time
import sys, httplib

#contants and literals
SELECTION_LETTERS=("A","B","C","D","E","F","G","H","J","K","L","M","N","P","Q","R","S","T","U","V")
WALLBOX=13

#>>>these constants can be changed to fit the characteristics of your wallbox
MAXMIMUM_GAP=3
MINIMUM_PULSE_GAP_WIDTH=0.004
LETTER_NUMBER_GAP=0.12

#>>> you will need to change the directory name in the SOAP message to correspond
#>>> with the location of your jukebox music files

SOAP_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Body>
<ns1:AddURIToQueue xmlns:ns1="urn:schemas-upnp-org:service:AVTransport:1">
              <InstanceID>0</InstanceID>
              <EnqueuedURI>x-file-cifs://Rainbow-Media/QRecordings/jukebox/%s.mp3</EnqueuedURI>
              <EnqueuedURIMetaData></EnqueuedURIMetaData>
              <DesiredFirstTrackNumberEnqueued>0</DesiredFirstTrackNumberEnqueued>
              <EnqueueAsNext>1</EnqueueAsNext>
        </ns1:AddURIToQueue>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>
"""

#set up IO port for input

GPIO.setmode(GPIO.BOARD)
GPIO.setup(WALLBOX, GPIO.IN)


#this function tests if a pulse or gap is wide enough to be registered
#this is needed for two reasons. 1) Sometimes the wallbox will generate an errant pulse
#which will cause errors if interpretted as a proper contact pulse 2) because of the
#way that I have tapped the wallbox pulses, there will be short gaps inside each pulse
#that need to be ignored

def state_has_changed(starting_state):
    starting_time = time.time()
    elapsed_time = 0

    for i in range (200):
        if GPIO.input(WALLBOX) != starting_state: 
            elapsed_time = time.time() - starting_time
#            print ("check time recorded: %.3f" %elapsed_time)
            return False
    return True
        
#this function is called as soon as the main loop determines that a train of pulses
#has started.  It begins by counting the number pulses, then when it encounters a larger
#gap, it starts incrementing the letters.  If your wallbox uses the opposite order
#you will need to change this.  Also the final calculation of the track may need to be changed
#as some boxes have additional pulses at either the start or the end of the train
#once it encounters a gap over a pre-determined maxmimum we know that the rotator arm
#has stopped and we calculate the track 

def calculate_track():

    state = True
    count_of_number_pulses = 1 #since we are in the first pulse
    count_of_letter_pulses = 0
    length_of_last_gap = 0
    first_train = True
    time_of_last_gap = time.time()

    while length_of_last_gap < MAXMIMUM_GAP:
        if GPIO.input(WALLBOX) != state: 
            
            if state_has_changed(not state): # state has changed but check it is not anomaly
                state = not state # I use this rather than the GPIO value just in case GPIO has changed - unlikely but possible
                if state: #indicates we're in a new pulse
                    length_of_last_gap = time.time() - time_of_last_gap 
                    print ("Pulse.  Last gap: %.3f" %length_of_last_gap)

                    if length_of_last_gap > LETTER_NUMBER_GAP: # indicates we're into the second train of pulses
                        first_train = False

                    if first_train:
                        count_of_number_pulses += 1
                    else:
                        count_of_letter_pulses +=1
                else: #indicates we're in a new gap
                    time_of_last_gap = time.time()
        else:
            length_of_last_gap = time.time() - time_of_last_gap #update gap length and continue to poll

    track = SELECTION_LETTERS[count_of_letter_pulses-1] + str((count_of_number_pulses-1))
    print ("+++ TRACK FOUND +++ Track Selection: ", track)
    return   track


#this function constructs and sends the header

def play_song(track):
    
        SoapMessage = SOAP_TEMPLATE%(track)
        webservice = httplib.HTTP("192.168.1.70:1400")
        webservice.putrequest("POST", "/MediaRenderer/AVTransport/Control")
        webservice.putheader("Host", "192.168.1.70:1400")
        webservice.putheader("User-Agent", "Python post")
        webservice.putheader("Content-type", "text/xml; charset=\"UTF-8\"")
        webservice.putheader("Content-length", "%d" % len(SoapMessage))
        webservice.putheader("SOAPAction", "urn:schemas-upnp-org:service:AVTransport:1#AddURIToQueue")
        webservice.endheaders()
        webservice.send(SoapMessage)


#this is the main loop.  We poll the GPIO port until there is a pulse.
#sometimes there can be random pulses, or a spike when the rotor arm starts to move 
#so before trying to decode the pulse train I check that
#the pulse is long enough to indicate a contact on the selector arm

while True:
    if GPIO.input(WALLBOX):
        if state_has_changed(True):
            track = calculate_track()
            play_song(track)
        else:
            print ("--> Pulse ignored")

      


