import asyncio
import os
import nextcord
import aiohttp
import sqlite3
import aiosqlite
from nextcord.ext import commands, tasks
from datetime import datetime, timedelta
import re

# Import config, save_config, and logger from the main bot file
from bot import config, save_config, logger, send_webhook_message

class YouTubeNotifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_new_videos.start()

    def cog_unload(self):
        self.check_new_videos.cancel()

    @nextcord.slash_command(name="add_channel", description="Add a YouTube channel to the watch list")
    async def add_channel(self, interaction: nextcord.Interaction, channel_identifier: str):
        await interaction.response.defer()
        if interaction.user.id not in (1107002211306852443, 399668151475765258):
            await interaction.followup.send("Lass gut sein, du idiot.", ephemeral=True)
            return
        channel_id = await self.get_channel_id(channel_identifier)
        if not channel_id:
            await interaction.followup.send("Invalid channel identifier. Please provide a valid channel ID or handle.")
            return

        if channel_id not in config['youtube_channels']:
            config['youtube_channels'].append(channel_id)
            save_config(config)
            await interaction.followup.send(f"YouTube channel {channel_id} added to the watch list.")
            logger.info(f"Added YouTube channel {channel_id} to watch list")
        else:
            await interaction.followup.send("This channel is already in the watch list.")

    @nextcord.slash_command(name="remove_channel", description="Remove a YouTube channel from the watch list")
    async def remove_channel(self, interaction: nextcord.Interaction, channel_identifier: str):
        await interaction.response.defer()
        if interaction.user.id not in (1107002211306852443, 399668151475765258):
            await interaction.followup.send("Lass gut sein, du idiot.", ephemeral=True)
            return
        channel_id = await self.get_channel_id(channel_identifier)
        if not channel_id:
            await interaction.followup.send("Invalid channel identifier. Please provide a valid channel ID or handle.")
            return

        if channel_id in config['youtube_channels']:
            config['youtube_channels'].remove(channel_id)
            save_config(config)
            await interaction.followup.send(f"YouTube channel {channel_id} removed from the watch list.")
            logger.info(f"Removed YouTube channel {channel_id} from watch list")
            
            # Delete channel handle and ID from the database
            await self.delete_channel_handle(channel_id)
            
        else:
            await interaction.followup.send("This channel is not in the watch list.")
            
    async def delete_channel_handle(self, channel_id):
        try:
            async with aiosqlite.connect('youtube_notifier.db') as conn:
                await conn.execute("DELETE FROM channel_handles WHERE channel_id = ?", (channel_id,))
                await conn.commit()
                logger.info(f"Succesfully deleted channel handle for channel {channel_id}")
        except aiosqlite.Error as e:
            logger.error(f"Database error: {e}")

    @nextcord.slash_command(name="set_notification_channel", description="Set the Discord channel for notifications")
    async def set_notification_channel(self, interaction: nextcord.Interaction, channel: nextcord.TextChannel):
        await interaction.response.defer()
        if interaction.user.id not in (1107002211306852443, 399668151475765258):
            await interaction.followup.send("Lass gut sein, du idiot.", ephemeral=True)
            return
        config['notification_channel_id'] = channel.id
        save_config(config)
        await interaction.followup.send(f"Notification channel set to {channel.mention}")
        logger.info(f"Set notification channel to {channel.id}")

    @nextcord.slash_command(name="list_channels", description="List all YouTube channels in the watch list")
    async def list_channels(self, interaction: nextcord.Interaction):
        if interaction.user.id not in (1107002211306852443, 399668151475765258):
            await interaction.response.send_message("Lass gut sein, du idiot.", ephemeral=True)
            return
        await interaction.response.defer()
        if config['youtube_channels']:
            channels = []
            for channel_id in config['youtube_channels']:
                channel_handle = await self.get_channel_handle(channel_id)
                if channel_handle:
                    channels.append(channel_handle)
                else:
                    channels.append(channel_id)
            channels_text = "\n".join(channels)
            await interaction.followup.send(f"Watched YouTube channels:\n{channels_text}")
        else:
            await interaction.followup.send("No YouTube channels are currently being watched.")

    async def get_channel_handle(self, channel_id):
        try:
            async with aiosqlite.connect('youtube_notifier.db') as conn:
                async with conn.execute("SELECT * FROM channel_handles WHERE channel_id = ?", (channel_id,)) as cursor:
                    result = await cursor.fetchone()
        except aiosqlite.Error as e:
            logger.error(f"Database error: {e}")
            return None

        if result:
            return result[1]
        else:
            channel_handle = await self.fetch_channel_handle(channel_id)
            if channel_handle:
                await self.add_channel_handle(channel_id, channel_handle)
                return channel_handle
            else:
                return None

    async def fetch_channel_handle(self, channel_id):
        logger.info(f"Fetching channel handle for channel {channel_id}")
        url = f"https://yt.lemnoslife.com/noKey/channels?part=snippet&id={channel_id}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch channel handle: {response.status}")
                        return None
                    data = await response.json()
                    if 'items' in data and data['items']:
                        return data['items'][0]['snippet']['title']
                    else:
                        return None
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request error: {e}")
            send_webhook_message(f"Failed to fetch channel handle for channel {channel_id}\n{str(e)}")
            return None

    async def add_channel_handle(self, channel_id, channel_handle):
        try:
            async with aiosqlite.connect('youtube_notifier.db') as conn:
                await conn.execute("INSERT INTO channel_handles (channel_id, channel_handle) VALUES (?, ?)", (channel_id, channel_handle))
                await conn.commit()
        except aiosqlite.Error as e:
            logger.error(f"Database error: {e}")

    async def get_channel_id(self, identifier):
        if re.match(r'^UC[\w-]{22}$', identifier):
            return identifier
        elif re.match(r'^@[\w-]+$', identifier):
            channel_handle = identifier.lstrip('@')
            url = f"https://yt.lemnoslife.com/noKey/search?part=snippet&type=channel&q={channel_handle}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                    if 'items' in data and data['items']:
                        return data['items'][0]['snippet']['channelId']
        return None

    async def fetch_latest_video(self, identifier):
        channel_id = await self.get_channel_id(identifier)
        if not channel_id:
            return None, None, None, None

        url = f"https://yt.lemnoslife.com/noKey/search?&channelId={channel_id}&part=snippet,id&order=date&maxResults=1"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 403:
                    logger.error("The request cannot be completed because you have exceeded your quota.")
                    send_webhook_message(f"YouTube API quota exceeded\n{response.text}")
                    return None, None, None, None

                data = await response.json()
                if 'items' in data and data['items']:
                    video = data['items'][0]
                    video_id = video['id']['videoId']
                    title = video['snippet']['title']
                    published_at = datetime.fromisoformat(video['snippet']['publishedAt'].replace('Z', '+00:00'))
                    
                    # Fetch video details to get the duration
                    video_details_url = f"https://yt.lemnoslife.com/noKey/videos?part=contentDetails&id={video_id}"
                    async with session.get(video_details_url) as details_response:
                        details_data = await details_response.json()
                        if 'items' in details_data and details_data['items']:
                            duration = details_data['items'][0]['contentDetails']['duration']
                            duration_seconds = self.parse_duration(duration)
                            logger.info(f"Fetched latest video: {title} from {channel_id} with duration {duration_seconds} seconds")
                            return video_id, title, published_at, duration_seconds

        logger.warning(f"No latest video found for channel {channel_id}")
        return None, None, None, None

    def parse_duration(self, duration):
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds

    def is_video_posted(self, video_id):
        conn = sqlite3.connect('youtube_notifier.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posted_videos WHERE video_id = ?", (video_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def add_posted_video(self, video_id, channel_id):
        conn = sqlite3.connect('youtube_notifier.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO posted_videos (video_id, channel_id, posted_at) VALUES (?, ?, ?)",
                       (video_id, channel_id, datetime.now()))
        conn.commit()
        conn.close()

    @tasks.loop(minutes=15)
    async def check_new_videos(self):
        logger.info("Checking for new videos")
        if not config['notification_channel_id']:
            logger.warning("Notification channel not set")
            return
    
        channel = self.bot.get_channel(config['notification_channel_id'])
        logger.info(f"Notification channel: {channel}")
        if not channel:
            logger.error(f"Could not find channel with ID {config['notification_channel_id']}")
            return

        logger.info("Checking videos for all channels")
        for youtube_channel_id in config['youtube_channels']:
            try:
                logger.info(f"Checking videos for channel {youtube_channel_id}")
                video_id, title, published_at, duration_seconds = await self.fetch_latest_video(youtube_channel_id)
                if video_id and published_at > datetime.now(published_at.tzinfo) - timedelta(minutes=15):
                    if duration_seconds > 61:
                        logger.info(f"New video found from {youtube_channel_id} - {title}")
                        if not self.is_video_posted(video_id):
                            logger.info(f"New video not in database: {title} from {youtube_channel_id}")
                            await channel.send(f"https://www.youtube.com/watch?v={video_id}")
                            await send_webhook_message(f"New video notified: {title} from {youtube_channel_id}  -  https://www.youtube.com/watch?v={video_id}")
                            self.add_posted_video(video_id, youtube_channel_id)
                            logger.info(f"New video notified: {title} from {youtube_channel_id}")
                        else:
                            logger.info(f"New video already in database: {title} from {youtube_channel_id}")
                    else:
                        logger.info(f"Ignored short video from {youtube_channel_id} - {title}")
                await asyncio.sleep(2)  # Add a delay to avoid rate-limiting
            except Exception as e:
                logger.error(f"Error checking videos for channel {youtube_channel_id}: {str(e)}")
            
        logger.info("Finished checking for new videos. Waiting for next check.")
    
    @check_new_videos.before_loop
    async def before_check_new_videos(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(YouTubeNotifier(bot))