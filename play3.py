#!/usr/bin/python3
"""A play local music files example
To use the script:
 * Make sure soco is installed
 * Drop this script into a folder that, besides python files, contains
nothing but music files
 * Choose which player to use and run the script at the command line as such:
play_local_files.py "Living Room"
NOTE: The script has been changed from the earlier version, where the
settings were written directly into the file. They now have to be
given at the command line instead. But, it should only be necessary to
supply the zone name. The local machine IP should be autodetected.
"""



import os
import sys
import time
import socket
import signal
import RPi.GPIO as GPIO
from threading import Thread

from urllib.parse import quote
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from soco.discovery import scan_network_get_by_name, discover

song_selection_started = False
number_being_selected = False
letter_index = 0
number_index = 0
time_of_last_negative_pulse = time.time()
time_of_last_positive_pulse = time.time()
gap_since_last_pulse = 0
number_letter_gap = 0.200
minimum_pulse_width = 0.03
maximum_pulse_width = 0.07


class HttpServer(Thread):
    """A simple HTTP Server in its own thread"""

    def __init__(self, port):
        super().__init__()
        self.daemon = True
        handler = SimpleHTTPRequestHandler
        self.httpd = TCPServer(("", port), handler)

    def run(self):
        """Start the server"""
        print("Start HTTP server")
        self.httpd.serve_forever()

    def stop(self):
        """Stop the server"""
        print("Stop HTTP server")
        self.httpd.socket.close()



def process_signal(channel):

    global song_selection_started
    global number_being_selected
    global letter_index
    global number_index
    global time_of_last_negative_pulse
    global time_of_last_positive_pulse
    global gap_since_last_pulse
    global number_letter_gap


    pulse_width = 0
#    time.sleep (0.001)
    time_now = time.time()

    if GPIO.input(channel):
        time_of_last_positive_pulse =  time_now        
        pulse_width = time_of_last_positive_pulse - time_of_last_negative_pulse
 #       print ("Pulse Width: " + str(pulse_width))

        if pulse_width < minimum_pulse_width or pulse_width > maximum_pulse_width: # ignore the pulse
            return (0) 

        if song_selection_started == False:
            print ("Starting Song. Delay: " +str(time_now - time_of_last_negative_pulse))
            gap_since_last_pulse = 0
            song_selection_started = True
            number_being_selected = True
            return (0)


        if gap_since_last_pulse > number_letter_gap:  
            number_being_selected = False
#            print ("switching.  Number: " +str(number_index))
    
        if number_being_selected == True:
            number_index +=1
            print("gap: " + str(gap_since_last_pulse) + "width: " + str(pulse_width) + "number: " + str(number_index))
        else:
            print("gap: " + str(gap_since_last_pulse) + "width: " + str(pulse_width) + "letter: " + str(letter_index))
            letter_index +=1
 #           print("letter: " + str(letter_index))

    else: # its a falling edge

        gap_since_last_pulse =  time_now - time_of_last_negative_pulse
        time_of_last_negative_pulse = time_now





def button_press(channel):
    if not GPIO.input(channel):
        print("shutdown requested")
        GPIO.cleanup()
        from subprocess import call
        call("sudo shutdown -h now", shell = True)





def play_selection(machine_ip, port, zone):

    global letter_index
    global number_index

    """play selection"""

    letters = ("X","V","U","T","S","R","Q","P","N","M","L","K","J","H","G","F","E","D","C","B","A")
    numbers = ("9","8","7","6","5","4","3","2","1")

    # urlencode all the path parts (but not the /'s)

    if number_index <= 9 and number_index >0 and letter_index < 21 and letter_index >0:
        random_file = letters[letter_index]+numbers[number_index]+".mp3"
        print("\nPlaying file:", random_file)
        netpath = "http://{}:{}/{}".format(machine_ip, port, random_file)


    #    number_in_queue = zone.play_uri("http://icecast.radiofrance.fr/fip-midfi.mp3")
    #  play radio - then if song selected - stop radio and play song
    # if song playing then add next song to queue
    #     # play_from_queue indexes are 0-based

        if zone.is_playing_radio:
            zone.stop()

        player_status = zone.get_current_transport_info()['current_transport_state']

        if player_status == "PLAYING":
            number_in_queue = zone.add_uri_to_queue(netpath)
        else:
            zone.clear_queue() 
            number_in_queue = zone.add_uri_to_queue(netpath)
            zone.play_from_queue(0)

        # reset the indexes here

    else:
        print("something wrong - trying to play letter index:" + str(letter_index) + " number index:" + str (number_index))

    letter_index = 0
    number_index = 0





def detect_ip_address():
    """Return the local ip-address"""
    # Rather hackish way to get the local ip-address, recipy from
    # https://stackoverflow.com/a/166589
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_address = s.getsockname()[0]
    s.close()
    return ip_address


def parse_args():
    """Parse the command line arguments"""
    import argparse

    description = "Play local files with Sonos by running a local web server"
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("zone", help="The name of the zone to play from")
    parser.add_argument(
        "--port", default=8000, help="The local machine port to run the webser on"
    )
    parser.add_argument(
        "--ip",
        default=detect_ip_address(),
        help="The local IP address of this machine. By "
        "default it will attempt to autodetect it.",
    )

    return parser.parse_args()


def main():

    button_pin = 22
    signal_pin = 4


    global song_selection_started
    global number_being_selected
    global letter_index
    global number_index
    global time_of_last_negative_pulse

    GPIO.setmode(GPIO.BCM)
 
    GPIO.setup(button_pin, GPIO.IN)
    GPIO.setup(signal_pin, GPIO.IN)

    GPIO.add_event_detect(signal_pin, GPIO.BOTH, callback=process_signal, bouncetime=20)
    GPIO.add_event_detect(button_pin, GPIO.FALLING, callback=button_press, bouncetime=300)

	
    # Settings
    args = parse_args()
    print(
        " Will use the following settings:\n"
        " Zone: {args.zone}\n"
        " IP of this machine: {args.ip}\n"
        " Use port: {args.port}".format(args=args)
    )

    # Get the zone
    print("Zone requested: {}".format(args.zone))  
    zoneFound = False

    while (zoneFound == False):
        zone = scan_network_get_by_name(args.zone, multi_household=True, max_threads=256, scan_timeout=5)
        if zone is not None:
            zoneFound = True
        else:
            zone_names = [zone_.player_name for zone_ in discover()]
            print("No Sonos player named '{}'. Player names are {}".format(args.zone, zone_names))
            time.sleep(3)

    # Check if a zone by the given name was found
    if zone is None:
        sys.exit(1)

    # Check whether the zone is a coordinator (stand alone zone or
    # master of a group)
    if not zone.is_coordinator:
        print(
            "The zone '{}' is not a group master, and therefore cannot "
            "play music. Please use '{}' in stead".format(
                args.zone, zone.group.coordinator.player_name
            )
        )
        sys.exit(2)

    # Setup and start the http server
    server = HttpServer(args.port)
    server.start()

    # When the http server is setup you can really add your files in
    # any way that is desired. The source code for
    # add_random_file_from_present_folder is just an example, but it may be
    # helpful in figuring out how to format the urls


    try:
        while True:
            delay_since_last_selection = time.time() - time_of_last_negative_pulse

            if song_selection_started == True and delay_since_last_selection > 3:
                # play selection
                play_selection(args.ip, args.port, zone)
                #reset pulse counting logic
                number_being_selected = False
                song_selection_started = False

            # Remember the http server runs in its own daemonized thread, so it is
            # necessary to keep the main thread alive. So sleep for 3 years.

    except KeyboardInterrupt:
        GPIO.cleanup()
        server.stop()


main()


