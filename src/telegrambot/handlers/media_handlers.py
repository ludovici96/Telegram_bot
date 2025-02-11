import os
import re
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
from ..config.settings import ALLOWED_CHAT_ID
from ..services.downloader_service import DownloaderService

logger = logging.getLogger(__name__)
downloader = DownloaderService()

def register_media_handlers(app: Client):
    @app.on_message(filters.text & filters.chat(ALLOWED_CHAT_ID))
    async def handle_downloads(client, message):
        # Move URL check before any other processing
        urls = re.findall(r'(https?://\S+)', message.text)
        if not urls:
            return
            
        # Log for debugging
        logger.debug(f"Found URLs in message: {urls}")
        
        for url in urls:
            try:
                # Check for YouTube URLs first
                if downloader.is_youtube_url(url):
                    await client.send_message(
                        chat_id=ALLOWED_CHAT_ID,
                        text="No one is gonna watch that 🤷‍♂️",
                        reply_to_message_id=message.id
                    )
                    continue

                logger.debug(f"Processing URL: {url}")
                media_group = []
                description = ""
                
                # Try video download
                video_files, video_desc = downloader.download_video(url)
                if isinstance(video_files, list):  # Changed to handle multiple videos
                    for video_file in video_files:
                        media_group.append(InputMediaVideo(video_file))
                    description = video_desc
                elif video_desc and ("live video stream" in video_desc or "too large" in video_desc):
                    await client.send_message(
                        chat_id=ALLOWED_CHAT_ID,
                        text=f"⚠️ {video_desc}",
                        reply_to_message_id=message.id
                    )
                    continue

                # Try image download
                if downloader.is_supported(url):
                    image_files, image_desc = downloader.download_images(url)
                    if image_files:
                        for file in image_files:
                            media_group.append(InputMediaPhoto(file))
                        if not description and image_desc:
                            description = image_desc

                # Process media if we have any
                if media_group:
                    try:
                        # Add caption to the first media item
                        if description:
                            media_group[0].caption = description
                        
                        # Send as media group if there are multiple items
                        if len(media_group) > 1:
                            await client.send_media_group(
                                chat_id=ALLOWED_CHAT_ID,
                                media=media_group,
                                reply_to_message_id=message.id
                            )
                        # Send single media if only one item
                        else:
                            single_media = media_group[0]
                            if isinstance(single_media, InputMediaVideo):
                                await client.send_video(
                                    chat_id=ALLOWED_CHAT_ID,
                                    video=single_media.media,
                                    caption=single_media.caption,
                                    reply_to_message_id=message.id
                                )
                            elif isinstance(single_media, InputMediaPhoto):
                                await client.send_photo(
                                    chat_id=ALLOWED_CHAT_ID,
                                    photo=single_media.media,
                                    caption=single_media.caption,
                                    reply_to_message_id=message.id
                                )
                    except Exception as e:
                        logger.error(f"Error sending media: {e}")
                        continue
                    finally:
                        # Clean up downloaded files
                        downloader.purge_folder(downloader.YT_DLP_FOLDER)
                        downloader.purge_folder(downloader.DOWNLOAD_FOLDER)
                    continue

                # If no media found, only try downloading text for tiwtter
                if 'twitter.com' in url or 'x.com' in url:
                    content = downloader.download_tweet_text(url)
                    if content:
                        await client.send_message(
                            chat_id=ALLOWED_CHAT_ID,
                            text=content,  # Remove the f"🐥✍️\n{content}" as emoji is now added in the service
                            reply_to_message_id=message.id
                        )
                        downloader.purge_folder(downloader.DOWNLOAD_FOLDER)
            except Exception as e:
                logger.error(f"Error processing URL {url}: {e}")
                continue