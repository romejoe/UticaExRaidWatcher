import datetime
import json
import re

import discord
from dateutil import tz

import gpxpy.gpx
from shapely.geometry import Polygon, Point

UticaExRaidEligible_channel_id = "423577070610808852"

from_zone = tz.gettz('UTC')
to_zone = tz.gettz('America/New_York')

have_notified_set = []

message_type_re = re.compile("")
lat_re = re.compile('#(-?[0-9]+\.[0-9]+)')
lon_re = re.compile(',(-?[0-9]+\.[0-9]+)')

exraid_locations = []


with open('Utica.gpx', 'r') as gpx_file:
    gpx = gpxpy.parse(gpx_file)


for trk in gpx.tracks:
    seg = trk.segments[0]
    poly_points = []
    for point in seg.points:
        poly_points.append((point.latitude, point.longitude))
    exraid_locations.append(Polygon(poly_points))

client = discord.Client()


def parse_message(msg):
    # info = {'timestamp': timezone("US/Eastern").localize(msg.timestamp)}
    info = {'timestamp': msg.timestamp.replace(tzinfo=from_zone).astimezone(to_zone)}

    embeds = msg.embeds[0]
    info['latitude'] = float(lat_re.findall(embeds['url'])[0])
    info['longitude'] = float(lon_re.findall(embeds['url'])[0])
    info['level'] = re.findall('Level ([0-5])', embeds['title'])[0]

    desc_parts = embeds['description'].split('\n')

    info['Gym'] = desc_parts[0].replace("**", "")
    # re.findall("'([a-zA-Z0-9 '.]+)'", desc_parts[0])[0]
    if 'is starting soon' in embeds['title']:
        info['type'] = 'egg'
        time_parts = list(map(lambda x: float(x), re.findall('([0-9]+)', desc_parts[1])))
        info['start time'] = info['timestamp'] + datetime.timedelta(hours=time_parts[0], minutes=time_parts[1],
                                                                    seconds=time_parts[2])
    else:
        info['type'] = 'raid'
        info['mon'] = desc_parts[1]
        info['cp'] = re.findall('\*\*CP:\*\* ([0-9]+)', desc_parts[2])[0]
        info['fast move'] = re.findall('\*\* ([a-zA-Z ]+) /', desc_parts[2])[0]
        info['charge move'] = re.findall('/ ([a-zA-Z ]+)', desc_parts[2])[0]
        time_parts = list(map(lambda x: float(x), re.findall('([0-9]+)', desc_parts[3])))
        info['end time'] = info['timestamp'] + datetime.timedelta(hours=time_parts[0], minutes=time_parts[1],
                                                                  seconds=time_parts[2])

    return info


def make_string(info):
    tmp = {}
    for key, v in info.items():
        tmp[key] = str(v)
    return json.dumps(tmp)


def have_notified(info):
    s = make_string(info)
    if s in have_notified_set:
        return True
    have_notified_set.append(s)
    while len(have_notified_set) > 100:
        have_notified_set.pop()

    return False


def isExRaidPossible(info):
    p = Point(info['latitude'], info['longitude'])
    return any(x.contains(p) for x in exraid_locations)


def isStillRelevant(info):
    now = datetime.datetime.utcnow().replace(tzinfo=from_zone).astimezone(to_zone)
    if info['type'] == 'egg' and info['start time'] > now:
        return True
    elif info['type'] == 'raid' and info['end time'] > now:
        return True
    else:
        return False


async def forward_info(info):
    target_channel = client.get_channel(UticaExRaidEligible_channel_id)
    em = None
    if info['type'] == 'egg':
        lat = str(info["latitude"])
        lon = str(info["longitude"])
        embed = discord.Embed(title="Raid is incoming!",
                              url="https://gymhuntr.com/#" + lat + "," + lon)
        embed.add_field(name="Level", value=info["level"], inline=True)
        embed.add_field(name="Start Time",
                        value=datetime.datetime.strftime(info['start time'], '%I:%M:%S %p'),
                        inline=True)
        embed.add_field(name="Gym", value=info['Gym'], inline=True)
        embed.add_field(name="Map",
                        value="https://www.google.com/maps/@" + lat + "," + lon + ",16z",
                        inline=True)
        em = embed

    else:
        lat = str(info["latitude"])
        lon = str(info["longitude"])
        embed = discord.Embed(title="Raid has started!",
                              url="https://gymhuntr.com/#" + lat + "," + lon)
        embed.add_field(name="Pokemon", value=info["mon"], inline=True)
        embed.add_field(name="End Time",
                        value=datetime.datetime.strftime(info['end time'], '%I:%M:%S %p'),
                        inline=True)
        embed.add_field(name="Gym", value=info['Gym'], inline=True)
        embed.add_field(name="CP", value=info['cp'], inline=True)
        embed.add_field(name="Moves",
                        value="Fast Move: " + info['fast move'] + "\nCharged Move: " + info['charge move'], inline=True)
        embed.add_field(name="Map",
                        value="https://www.google.com/maps/@" + lat + "," + lon + ",16z",
                        inline=True)
        em = embed
        # em = discord.Embed(title="Raid has started!", type='rich')
    await client.send_message(target_channel, "", embed=em)


async def handle_message(message):
    if message.author.name != 'GymHuntrBot' or len(message.embeds) == 0:
        return
    info = parse_message(message)
    if isExRaidPossible(info) and isStillRelevant(info) and not have_notified(info):
        print("Exraid thingy")
        print(info)
        await forward_info(info)


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    target_channel = client.get_channel(UticaExRaidEligible_channel_id)
    await client.send_message(target_channel, "Bot Activated")

    channel = client.get_channel("334867495846412288")

    async for message in client.logs_from(channel, limit=100):
        await handle_message(message)

    channel2 = client.get_channel("339208908331548673")

    async for message in client.logs_from(channel2, limit=100):
        await handle_message(message)


#channels_to_watch = ["utica-legendary-raids", "utica-raids"]
channels_to_watch = ["utica-raids"]


@client.event
async def on_message(message):
    if message.server.name != 'Pokemon Go Raids 315':
        return
    if message.channel.name not in channels_to_watch:
        return

    await handle_message(message)

client.run("NDIzMjY1NDAwOTg2NTMzODk4.DYsXdg.SmV3WWlrEJuUgb8fg6csREbGI0E")
