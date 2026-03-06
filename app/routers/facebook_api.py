import asyncio
from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert
from DBmodels.CommentModel import PageComment
from fastapi import APIRouter, Query, Depends, HTTPException, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from services import facebook_services, openai_services
import os
import httpx
from core.database import DATABASE_URL, Base, get_db,engine, AsyncSession
from datetime import datetime
from tasks.save_to_db import long_task


load_dotenv() 
router = APIRouter()

async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)



#load environment variables
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET_KEY = os.getenv("FACEBOOK_APP_SECRET_KEY")
FACEBOOK_URL = os.getenv("FACEBOOK_URL")

class FacebookTokenResponse(BaseModel):
    access_token: str
    token_type: str

class FacebookPageDetails(BaseModel):
    id: str
    name: str
    tasks: list[str]
    access_token: str

class FacebookPageListResponse(BaseModel):
    fb_pages: list[FacebookPageDetails]


class FacebookPagePostDetails(BaseModel):
    id: str
    message: str | None = None
    story: str | None = None
    full_picture: str | None = None
    permalink_url: str
    created_time: str


class FacebookPagePostListResponse(BaseModel):
    page_posts: list[FacebookPagePostDetails]

class FacebookCommentDetails(BaseModel):
    id: str
    message: str
    from_user: dict = Field(alias="from")
    created_time: str

## THE DB MODEL ##
class FacebookCommentDatabase(BaseModel):
    comment_id: str
    message: str
    created_time: str
  

class FacebookCommentListResponse(BaseModel):
    post_comments: list[FacebookCommentDetails]


@router.get("/exchange-token", response_model=FacebookTokenResponse, summary="Exchange short-lived Facebook token for long-lived token",)
async def get_token(shortLivedToken: str = Query(..., description="Short-lived token")):
    response = await facebook_services.exchange_facebook_token(shortLivedToken)
    return response.json()
    
@router.get("/get-fb-page", summary="Get the list of page the user have accessed to", response_model=FacebookPageListResponse)
async def get_fb_page(access_token: str = Query(..., description="User access token")):
    response = await facebook_services.fb_page_list(access_token)
    return {"fb_pages": response.json().get("data", [])}
    
@router.get("/get-page-posts", summary="Get posts from a Facebook page", response_model=FacebookPagePostListResponse)
async def get_page_posts(page_access_token: str = Query(..., description="Page access token"), page_id: str = Query(..., description="Facebook Page ID")):
    response = await facebook_services.post_page_list(page_id, page_access_token)
    return {"page_posts": response.json().get("data", [])}

@router.get("/get-post-comments", summary="Get Facebook post comments", response_model=FacebookCommentListResponse)
async def get_post_comments(post_id: str = Query(..., description="Facebook Post ID"), page_access_token: str = Query(..., description="Page access token")):
    response = await facebook_services.get_post_comments(post_id, page_access_token)
    return {"post_comments": response.json().get("data", [])}

@router.get("/get-all-page-comments")
async def get_all_page_comments(page_id: str):
    """
    Triggers background processing of Facebook comments.
    Returns immediately with Celery task_id.
    """
    task = long_task.delay(page_id)
    return {"message": "Processing started", "task_id": task.id}

#For testing purposes only, to check if the comments are being saved in the database and can be retrieved successfully. REMOVE PAGKATPOS
@router.get("/comments")
async def get_comments(limit: int = 100, db: AsyncSession = Depends(get_db)):
    stmt = select(PageComment).order_by(PageComment.created_time.desc()).limit(limit)
    result = await db.execute(stmt)
    comments = result.scalars().all()
    

    return {"count": len(comments), "comments": comments}


