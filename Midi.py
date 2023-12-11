#!/usr/bin/env python3

from time import sleep
import pulsectl
from pygame import midi
import subprocess
import uinput
import yaml
import json
import gi
gi.require_version("Notify", "0.7")
from gi.repository import Notify
import paho.mqtt.client as mqttClient
from pydbus import SessionBus
import psutil


keyboard_emu = uinput.Device([uinput.KEY_PLAYPAUSE])


pulse = pulsectl.Pulse('python')
bus = SessionBus()

def get_default_sink():
    default_sink = []
    default_sink.append(pulse.get_sink_by_name(pulse.server_info().default_sink_name))
    return default_sink
def get_default_source():
    default_source = []
    default_source.append(pulse.get_source_by_name(pulse.server_info().default_source_name))
    return default_source
def volume_set(var1, var2):
    if var1 != []:    
        for i in var1:
            vol = i.volume
            vol.value_flat = var2/100
            pulse.volume_set(i, vol)
    else:
        print("Not Bound")
def pulse_mute(var1, var2):
    if var1 != []:
        for i in var1:
            if i.mute == 0:
                pulse.mute(i)
                midi_output.write_short(176, data1=var2, data2=127)
            else:
                pulse.mute(i, mute=False)
                midi_output.write_short(176, data1=var2, data2=0)
    else:
        print("Not Bound")
def bind_app(var1):
    #print(var1)
    app = []
    if var1.endswith('.exe') or var1.endswith('.'):
        if var1.endswith('.'):
            var1 = var1 = var1.replace(".", ".exe")
        for index, item in enumerate(pulse.sink_input_list()):
            if "application.name" in item.proplist and item.proplist['application.name'] == var1:
                app.append(item)
        if app == []:
            var1 = var1.replace(".exe", "")
            for index, item in enumerate(pulse.sink_input_list()):
                if "application.name" in item.proplist and item.proplist['application.name'] == var1:
                    app.append(item)
        
    else:
        for index, item in enumerate(pulse.sink_input_list()):
            if "application.name" in item.proplist:
                #print(item.proplist['application.name'])
                pass            
            if "application.process.binary" in item.proplist and item.proplist['application.process.binary'] == var1:
                app.append(item)

    return app
def get_focused():
    try: 
        remote_object = bus.get(
            "org.gnome.Shell", # Bus name
            "/org/gnome/Shell/Extensions/Windows" # Object path
        )
        #print(remote_object.List())
        for i in json.loads(remote_object.List()):
            if (i["focus"]):
                focused = bind_app(psutil.Process(int(i["pid"])).name())
            else:
                focused = []
        #focused = bind_app(psutil.Process(int(remote_object.FocusPID())).name())
    except:
        focused = []
    #print(focused)
    return focused
def on_connect(client, userdata, flags, rc):
 
    if rc == 0:
 
        #print("Connected to broker")
 
        global Connected                #Use global variable
        Connected = True                #Signal connection 
 
    else:
 
        print("Connection failed")
# intialization
midi.init()
config = yaml.safe_load(open("config.yaml", "r"))
apps = config["apps"]
default_sink = get_default_sink()
default_source = get_default_source()
app3 = bind_app(apps["app3"])
app4 = bind_app(apps["app4"])
app5 = bind_app(apps["app5"])
focused = get_focused()
count = 0
sink_index = 0

default_in = None
default_out = None
midi_devices = midi.get_count()
#print(midi_devices)
for i in range(0, midi_devices):
    if str(midi.get_device_info(i)) == config["midi"]["input"]:
        default_in = i
    if str(midi.get_device_info(i)) == config["midi"]["output"]:
        default_out = i
midi_input = midi.Input(device_id=default_in)
midi_output = midi.Output(device_id=default_out)

Connected = False   #global variable for the state of the connection
client = mqttClient.Client("Python")
client.on_connect = on_connect
client.connect(config["mqtt"]["address"], port=config["mqtt"]["port"])
client.loop_start()
while Connected != True:
    sleep(0.1)
    #print(Connected)

try: 
    while True:
        sleep(0.0001)
        count = count + 1 
        #print(count)
        if count == 10000:
            count = 0
            default_sink = get_default_sink()
            default_source = get_default_source()
            app3 = bind_app(apps["app3"])
            app4 = bind_app(apps["app4"])
            app5 = bind_app(apps["app5"])
            focused = get_focused()
            pulse_objects = (default_sink, default_source, app3, app4, app5)
            midi_locations = (48, 49, 50, 51, 52, 53, 54, 55)
            counter = 0
            while counter < len(pulse_objects):
                for i in pulse_objects[counter]:
                    if (str(i)) != "None":
                        if i.mute == 1:
                            midi_output.write_short(176, data1=midi_locations[counter], data2=127)
                        else:
                            midi_output.write_short(176, data1=midi_locations[counter], data2=0)
                counter += 1
        if midi_input.poll():
            #print(midi_input.read(num_events=1))
            lst_midi = midi_input.read(num_events=1)
            ch_midi = lst_midi[0][0][1]
            data_midi = lst_midi[0][0][2]
            ch_data = (ch_midi, data_midi)
            #print(ch_data)
            match ch_data:
                # column 1
                case 0, _:
                    volume_set(default_sink, data_midi)
                case 16, _:
                    client.publish("arch/midi/knobs/1", round(data_midi*100/127))
                case 32, 127:
                    volume_set(default_sink, 100)
                case 48, 127:
                    pulse_mute(default_sink, ch_midi)
                case 64, 127:
                    default_sink = get_default_sink()
                # column 2
                case 1, _:
                    volume_set(default_source, data_midi)                  
                case 33, 127: 
                    volume_set(default_source, 100)
                case 49, 127:
                    pulse_mute(default_source, ch_midi)
                case 65, 127:
                    default_source = get_default_source()
                # column 3
                case 2, _:
                    volume_set(app3, data_midi)
                case 34, 127:
                    volume_set(app3, 100)
                case 50, 127:
                    pulse_mute(app3, ch_midi)
                case 66, 127:
                    app3 = bind_app(apps["app3"])
                # column 4
                case 3, _:
                    volume_set(app4, data_midi)
                case 35, 127:
                    volume_set(app4, 100)
                case 51, 127:
                    pulse_mute(app4, ch_midi)
                case 67, 127:
                    app4 = bind_app(apps["app4"])
                # column 5
                case 4, _:
                    volume_set(app5, data_midi)
                case 36, 127:
                    volume_set(app5, 100)
                case 52, 127:
                    pulse_mute(app5, ch_midi)
                case 68, 127:
                    app5 = bind_app(apps["app5"])
                # column 6
                case 5, _:
                    volume_set(focused, data_midi)
                case 37, 127:
                    volume_set(focused, 100)
                case 53, 127:
                    pulse_mute(focused, ch_midi)
                case 69, 127:
                    focused = get_focused()
                # misc
                case 41, 127:
                    keyboard_emu.emit_click(uinput.KEY_PLAYPAUSE)
                    pass
                case 42, 127:
                    quit()
                case 46, 127:
                    default_sink = get_default_sink()
                    default_source = get_default_source()
                case 60, 127:
                    client.publish("arch/midi/button/get", "toggle")
                case 61, 127:
                    pulse.sink_default_set(config["outputs"]["speakers"])
                case 62, 127:
                    pulse.sink_default_set(config["outputs"]["headphones"])
except KeyboardInterrupt as err:
    print("Stopping...")
    client.disconnect()
    client.loop_stop()
    
# Notify.init("Python Midi Control")
# Notify.Notification.new("Midi Control", pulse.sink_list()[sink_index].description).show()
# Notify.uninit()