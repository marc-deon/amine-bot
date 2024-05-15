import discord
from Message import Message

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

weekly_anime_id = 1221920619487039618
starlight_test_channel_id = 1043384233261006888
default_channel_id = weekly_anime_id

_messages = []
testing = False


async def send_message(msg, channel_id=default_channel_id):
    c = client.get_channel(channel_id)
    # Image embedding not implemented because mal link is enough
    await c.send(msg.message + "\n" + msg.link)
    await client.close()


@client.event
async def on_ready():
    if testing:
        await send_message(Message("I'm alive"), starlight_test_channel_id)
        return

    print(f"We have logged in as {client.user}")

    print(len(_messages), "message")
    for m in _messages:
        await send_message(m)

    await client.close()


def test(token):
    global testing
    testing = True
    client.run(token)


def begin(messages, token):
    global _messages
    _messages = messages
    client.run(token)
