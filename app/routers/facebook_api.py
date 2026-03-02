from DBmodels.CommentModel import PageComment
from fastapi import APIRouter, Query, Depends, HTTPException
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from services import facebook_services, openai_services
import os
import httpx
from core.database import DATABASE_URL, Base, get_db,engine, AsyncSession
from datetime import datetime

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


# {'type': 'missing', 'loc': ('response', 'id'), 'msg': 'Field required', 'input': {'post_comments': []}}
# {'type': 'missing', 'loc': ('response', 'permalink_url'), 'msg': 'Field required', 'input': {'post_comments': []}}
#{'type': 'missing', 'loc': ('response', 'created_time'), 'msg': 'Field required', 'input': {'post_comments': []}}



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

@router.get("/get-all-page-comments", summary="Get all comments from a Facebook page")
async def get_all_page_comments(page_id: str = Query(..., description="Facebook Page ID"), db: AsyncSession = Depends(get_db)):

    page_access_token = await facebook_services.get_page_token(page_id, os.getenv("USER_ACCESS_TOKEN"))
    profile = await facebook_services.get_profile(page_id, page_access_token.json().get("access_token",None))
    response = await facebook_services.get_all_comments(page_id, page_access_token.json().get("access_token",None))
    comment_sentiments = await  openai_services.get_comment_sentiments(response)
    suggestions = await openai_services.get_suggestion(response)
    topper_comments = await openai_services.get_topper(response)

    for comment in response:
        db_comment = PageComment(
            comment_id=comment["comment_id"],
            message=comment["message"],
            created_time=datetime.strptime(comment["created_time"], "%Y-%m-%dT%H:%M:%S%z")
        )
        db.add(db_comment)
    await db.commit()


    return {
        "comments": response, 
        "facebook": profile.json(), 
        "follower": profile.json().get("fan_count", None),
        "url": profile.json()["picture"]["data"]["url"],
        "comment_sentiments": comment_sentiments,
        "suggestions": suggestions,
        "topper_comments": topper_comments
        }     



   