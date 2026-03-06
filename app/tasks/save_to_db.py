import asyncio
from core.database_celery_sync import SessionLocal
from celery.utils.log import get_task_logger
from celery_app import celery_app
from sqlalchemy import select, desc
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
import os
from DBmodels.CommentModel import PageComment
from services import facebook_services, openai_services 

logger = get_task_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def long_task(self, page_id: str):
    db = SessionLocal()
    try:
        asyncio.run(_process(page_id, db))
        logger.info(f"Task completed for page_id: {page_id}")

    except Exception as e:
        db.rollback()
        raise self.retry(exc=e, countdown=5)

    finally:
        db.close()
    
async def _process(page_id: str, db):       
        page_access_token = await facebook_services.get_page_token(page_id, os.getenv("USER_ACCESS_TOKEN"))
        profile = await facebook_services.get_profile(page_id, page_access_token.json().get("access_token",None))
        response = await facebook_services.get_all_comments(page_id, page_access_token.json().get("access_token",None))

        """ DO NOT REMOVE!"""
        #comment_sentiments = await  openai_services.get_comment_sentiments(response)
        #suggestions = await openai_services.get_suggestion(response)
        #topper_comments = await openai_services.get_topper(response)

        print("Success Checkpoint 1")
        ###Database
        latest_comment_stmt = select(PageComment).order_by(desc(PageComment.created_time)).limit(1)
        print("Success Checkpoint latest comment stmt")
        result = db.execute(latest_comment_stmt)
        print("Success Checkpoint latest comment result")
        latest_comment = result.scalar_one_or_none()
        print("Success Checkpoint latest comment result scalar")

        print("Success Checkpoint 2")


        #Get Post_Comments

        # Test with Bulk Insert for better performance use Python Lists to temporarily store the comments and then insert them into the database in one go. This can significantly reduce the number of database transactions and improve performance.
        # Time <= logic for each comment and insert into DB
        # Web Socket Notification to say that background task is completed.
        #Background Task


        #Bulk Insert Logic to List
        formatted_comments = [
            {
                "comment_id": c["comment_id"],
                "message": c["message"],
                "created_time": datetime.strptime(
                c["created_time"], "%Y-%m-%dT%H:%M:%S%z"
                ).replace(tzinfo=None)
            }
            for c in response
        ]

        print("Success Checkpoint 3")

        #Get lahat ng data sa formatted_comments, isa-isahin tas cocompare sa latest_comment.created time if greater than ang value overwrite new list tas palitan nung bago
        latest_time = latest_comment.created_time.replace(tzinfo=None) if latest_comment else None
        formatted_comments = [
            c for c in formatted_comments
            if (latest_time is None) or (c["created_time"] > latest_time)
        ]

            
        #For testing purpose only!!! REMOVE MO PAGKATAPOS
        #Pangcheck if nag update ba yung Lists, print out lahat ng mga bagong shit, dapat walang lumang shit
        print("Success Checkpoint 4")
        print(f"this is the comments to be pushed: {formatted_comments}")
        #pangcheck ko lang if tama yung latest comment
        
        if latest_comment is not None:
            print(f"this is the latest comment: {latest_comment.message}")
        else:
            print("there is no latest comment yet / Database table is empty")
        if formatted_comments:
            stmt = insert(PageComment).values(formatted_comments) 
            stmt = stmt.on_conflict_do_nothing(index_elements=['comment_id'])
            db.execute(stmt)
            db.commit()
        
        logger.info("Task completed successfully")

