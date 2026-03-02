from sqlite3 import IntegrityError
from DBmodels.CommentModel import PageComment
from dotenv import load_dotenv
import os
import httpx
from datetime import datetime
from sqlalchemy.orm import Session

load_dotenv() 

#load environment variables
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET_KEY = os.getenv("FACEBOOK_APP_SECRET_KEY")
FACEBOOK_URL = os.getenv("FACEBOOK_URL")

async def exchange_facebook_token(short_lived_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        url = f"{FACEBOOK_URL}/oauth/access_token"
        params = {
           "grant_type": "fb_exchange_token",
           "client_id": FACEBOOK_APP_ID,
           "client_secret": FACEBOOK_APP_SECRET_KEY,
           "fb_exchange_token": short_lived_token
}
        response = await client.get(url, params=params)
        return response
    
async def fb_page_list(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        url = f"{FACEBOOK_URL}/me/accounts"
        params = {
            "access_token": access_token,
            "fields": "id,name,tasks,access_token"
        }
        response = await client.get(url, params=params)
        return response
    
async def post_page_list(page_id: str, page_access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        url = f"{FACEBOOK_URL}/{page_id}/posts?access_token={page_access_token}"
        params = {
            "access_token": page_access_token,
            "fields": "id,message,story,full_picture,permalink_url,created_time"
        }
        response = await client.get(url, params=params)
        return response
    
async def get_post_comments(post_id: str, page_access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        url = f"{FACEBOOK_URL}/{post_id}/comments"
        params = {
            "access_token": page_access_token,
            "fields": "id,message,from,created_time"
        }
        response = await client.get(url, params=params)
        return response
    
async def get_page_token(page_id: str, user_access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        url = f"{FACEBOOK_URL}/{page_id}"
        params = {
            "access_token": user_access_token,
            "fields": "access_token"
        }
        response = await client.get(url, params=params)
        return response

async def get_profile (page_id: str, page_access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        url = f"{FACEBOOK_URL}/{page_id}"
        params = {
            "access_token": page_access_token,
            "fields": "picture.width(200).height(200),id,name,about,category,fan_count"
        }
        response = await client.get(url, params=params)
        return response
    

        #######################################################################

async def get_all_comments(page_id: str, page_access_token: str) -> list[dict]:
    all_comments = []

    async with httpx.AsyncClient() as client:
        feed_url = f"{FACEBOOK_URL}/{page_id}/feed"
        feed_params = {
            "access_token": page_access_token,
            "fields": "comments.limit(100){id,message,created_time}",
            "limit": 100
        }

        while feed_url:
            response = await client.get(feed_url, params=feed_params)
            data = response.json()

            for post in data.get("data", []):
                if "comments" in post:
                    comment_block = post["comments"]

                    # Extract structured data for this batch
                    for c in comment_block.get("data", []):
                        all_comments.append({
                            "comment_id": c.get("id"),
                            "message": c.get("message"),
                            "created_time": c.get("created_time")
                        })

                    # Handle pagination for comments on this post
                    next_comments_url = comment_block.get("paging", {}).get("next")
                    while next_comments_url:
                        c_res = await client.get(next_comments_url)
                        c_data = c_res.json()
                        for c in c_data.get("data", []):
                            all_comments.append({
                                "comment_id": c.get("id"),
                                "message": c.get("message"),
                                "created_time": c.get("created_time")
                            })
                        next_comments_url = c_data.get("paging", {}).get("next")

            # Move to the next page of posts
            feed_url = data.get("paging", {}).get("next")
            feed_params = {}

    return all_comments