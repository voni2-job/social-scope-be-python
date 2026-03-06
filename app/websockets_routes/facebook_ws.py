from datetime import datetime
from fastapi import APIRouter, WebSocket
import asyncio
from DBmodels.CommentModel import PageComment
from core.database_celery_sync import SessionLocal
from sqlalchemy import select, desc

router = APIRouter()

# Track notified comment IDs globally in this connection
connections = []

@router.websocket("/notifications")
async def websocket_notifications(ws: WebSocket, page_id: str = None, page_access_token: str = None):
    await ws.accept()
    print("CONNECTED")

    notified_comments = set()  # keeps track of already sent comment IDs

    try:
        while True:
            # create a fresh session each loop to avoid caching issues
            db = SessionLocal()

                
            latest_comment_stmt = select(PageComment).order_by(desc(PageComment.created_time)).limit(1)
            result = db.execute(latest_comment_stmt)
            latest_comment = result.scalars().all()

            new_message_sent = False

            # iterate oldest first
            for comment in reversed(latest_comment):
                if comment.comment_id not in notified_comments:
                    text = f"New message: {comment.message} | Posted at: {comment.created_time}"
                    await ws.send_text(text)
                    notified_comments.add(comment.comment_id)
                    new_message_sent = True

            if not new_message_sent:
                await ws.send_text(f"No new messages. Last checked at {datetime.utcnow().isoformat()}")

            db.close()
            await asyncio.sleep(5)

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        print("Connection closed")
        await ws.close()