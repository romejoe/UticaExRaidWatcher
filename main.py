import datetime
from pytz import timezone
import discord
import asyncio
import re


import gpxpy
import gpxpy.gpx
from shapely.geometry import Polygon, Point

with open('Utica.gpx', 'r') as gpx_file:
    gpx = gpxpy.parse(gpx_file)

exraid_locations = []
for trk in gpx.tracks:
    seg = trk.segments[0]
    poly_points = []
    for point in seg.points:
        poly_points.append((point.latitude, point.longitude))
    exraid_locations.append(Polygon(poly_points))

client = discord.Client()

message_type_re = re.compile("")
lat_re = re.compile('#(-?[0-9]+\.[0-9]+)')
lon_re = re.compile(',(-?[0-9]+\.[0-9]+)')


def parse_message(msg):
    info = {'timestamp': timezone("US/Eastern").localize(msg.timestamp)}

    embeds = msg.embeds[0]
    info['latitude'] = float(lat_re.findall(embeds['url'])[0])
    info['longitude'] = float(lon_re.findall(embeds['url'])[0])
    info['level'] = re.findall('Level ([0-5])', embeds['title'])[0]

    desc_parts = embeds['description'].split('\n')

    info['Gym'] = desc_parts[0].replace("**", "")
    #re.findall("'([a-zA-Z0-9 '.]+)'", desc_parts[0])[0]
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

def isExRaidPossible(info):
    p = Point(info['latitude'], info['longitude'])
    return any(x.contains(p) for x in exraid_locations)


async def forward_info(info):
    target_channel = client.get_channel("419537554191286294")
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
        embed.add_field(name="Moves", value="Fast Move: " + info['fast move'] + "\nCharged Move: " + info['charge move'], inline=True)
        embed.add_field(name="Map",
                        value="https://www.google.com/maps/@" + lat + "," + lon + ",16z",
                        inline=True)
        em = embed
        #em = discord.Embed(title="Raid has started!", type='rich')
    tmp = await client.send_message(target_channel, "", embed=em)
    print(tmp)


async def handle_message(message):
    if message.author.name != 'GymHuntrBot' or len(message.embeds) == 0:
        return
    info = parse_message(message)
    if isExRaidPossible(info):
        print("Exraid thingy")
        print(info)
        await forward_info(info)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    print("here")

    target_channel = client.get_channel("419537554191286294")
    client.send_message(target_channel, "Bot Activated")

    channel = client.get_channel("334867495846412288")

    async for message in client.logs_from(channel, limit=10):
        await handle_message(message)

    channel2 = client.get_channel("339208908331548673")

    async for message in client.logs_from(channel2, limit=10):
        await handle_message(message)


channels_to_watch = ["utica-legendary-raids", "utica-raids"]


@client.event
async def on_message(message):
    if (message.server.name != 'Pokemon Go Raids 315'):
        return
    if (message.channel.name not in channels_to_watch):
        return

    print(message)
    # if message.content.startswith('!test'):
    #    counter = 0
    #    tmp = await client.send_message(message.channel, 'Calculating messages...')
    #    async for log in client.logs_from(message.channel, limit=100):
    #        if log.author == message.author:
    #            counter += 1


#
#    await client.edit_message(tmp, 'You have {} messages.'.format(counter))
# elif message.content.startswith('!sleep'):
#    await asyncio.sleep(5)
#    await client.send_message(message.channel, 'Done sleeping')

#client.run()