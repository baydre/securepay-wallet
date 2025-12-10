from fastapi import APIRouter, Request, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
import json
import models
from dependencies import get_db
from services.paystack import PaystackService

router = APIRouter(prefix="/webhook", tags=["Webhooks"])


@router.post("/paystack")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: Optional[str] = Header(None)
):
    """
    Handle Paystack webhook events
    
    This endpoint processes payment confirmations and credits user wallets.
    It implements idempotency to prevent double-crediting.
    """
    # Get raw request body
    body = await request.body()
    
    # Verify webhook signature
    if not x_paystack_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing signature"
        )
    
    if not PaystackService.verify_webhook_signature(body, x_paystack_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    # Parse the webhook payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    event = payload.get("event")
    data = payload.get("data", {})
    
    # We only care about successful charges
    if event != "charge.success":
        return {"status": "ignored", "message": f"Event '{event}' not processed"}
    
    # Extract transaction details
    reference = data.get("reference")
    amount_in_kobo = data.get("amount")
    paystack_status = data.get("status")
    
    if not reference or not amount_in_kobo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields"
        )
    
    # Convert amount from kobo to naira
    amount = amount_in_kobo / 100
    
    # Get database session
    from database import SessionLocal
    db = SessionLocal()
    
    try:
        # Find the transaction
        transaction = db.query(models.Transaction).filter(
            models.Transaction.reference == reference
        ).first()
        
        if not transaction:
            # Transaction not found in our system
            return {
                "status": "ignored",
                "message": "Transaction not found in system"
            }
        
        # Idempotency check: If already processed, don't process again
        if transaction.status == "success":
            return {
                "status": "already_processed",
                "message": "Transaction already credited"
            }
        
        # Verify the amount matches
        if abs(transaction.amount - amount) > 0.01:  # Allow small floating point differences
            transaction.status = "failed"
            transaction.meta_data = {
                "error": "Amount mismatch",
                "expected": transaction.amount,
                "received": amount
            }
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount mismatch"
            )
        
        # Get the wallet
        wallet = db.query(models.Wallet).filter(
            models.Wallet.id == transaction.wallet_id
        ).first()
        
        if not wallet:
            transaction.status = "failed"
            transaction.meta_data = {"error": "Wallet not found"}
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        # Credit the wallet
        wallet.balance += amount
        
        # Update transaction status
        transaction.status = "success"
        transaction.meta_data = {
            "paystack_status": paystack_status,
            "processed_at": data.get("paid_at"),
            "customer": data.get("customer", {})
        }
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Wallet credited successfully",
            "reference": reference,
            "amount": amount
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )
    finally:
        db.close()
