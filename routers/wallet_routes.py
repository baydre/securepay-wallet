from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import secrets
import string
from datetime import datetime
import models
from schemas import (
    DepositRequest, DepositResponse, BalanceResponse,
    TransferRequest, TransferResponse, TransactionResponse,
    WalletResponse
)
from dependencies import get_db, get_current_user, get_current_user_or_service, require_permission
from services.paystack import PaystackService

router = APIRouter(prefix="/wallet", tags=["Wallet"])


def generate_transaction_reference() -> str:
    """Generate a unique transaction reference"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_string = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    return f"TXN-{timestamp}-{random_string}"


@router.get("/", response_model=WalletResponse)
async def get_wallet(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's wallet information
    """
    wallet = db.query(models.Wallet).filter(
        models.Wallet.user_id == current_user.id
    ).first()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    return wallet


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    current_user: models.User = Depends(get_current_user_or_service),
    db: Session = Depends(get_db)
):
    """
    Get wallet balance
    
    Supports both JWT and API key authentication (with 'read' permission)
    """
    wallet = db.query(models.Wallet).filter(
        models.Wallet.user_id == current_user.id
    ).first()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    return BalanceResponse(
        wallet_number=wallet.wallet_number,
        balance=wallet.balance
    )


@router.post("/deposit", response_model=DepositResponse)
async def deposit_funds(
    deposit_data: DepositRequest,
    current_user: models.User = Depends(get_current_user_or_service),
    db: Session = Depends(get_db)
):
    """
    Initialize a deposit using Paystack payment gateway
    
    **Process:**
    1. Creates a pending transaction in the database
    2. Initializes Paystack payment session
    3. Returns authorization URL for payment
    
    **To Complete Deposit:**
    1. Open the `authorization_url` in a browser
    2. Use Paystack test card: `4084084084084081`
    3. CVV: `408`, PIN: `0000`, OTP: `123456`
    4. Webhook automatically credits wallet on success
    
    **Check Status:**
    - Use `GET /wallet/deposit/{reference}/status` to check payment status
    - View pending deposits: `GET /wallet/transactions/pending`
    
    **Authentication:**
    - Supports both JWT tokens and API keys (requires 'deposit' permission)
    
    Supports both JWT and API key authentication (with 'deposit' permission)
    """
    wallet = db.query(models.Wallet).filter(
        models.Wallet.user_id == current_user.id
    ).first()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    # Generate unique transaction reference
    reference = generate_transaction_reference()
    
    # Create pending transaction record
    transaction = models.Transaction(
        wallet_id=wallet.id,
        type="deposit",
        amount=deposit_data.amount,
        status="pending",
        reference=reference,
        description="Wallet deposit via Paystack"
    )
    
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    
    # Initialize Paystack transaction
    try:
        paystack = PaystackService()
        paystack_response = paystack.initialize_transaction(
            email=current_user.email,
            amount=deposit_data.amount,
            reference=reference
        )
        
        return DepositResponse(
            authorization_url=paystack_response["authorization_url"],
            reference=reference,
            amount=deposit_data.amount
        )
    
    except Exception as e:
        # Update transaction status to failed
        transaction.status = "failed"
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize payment: {str(e)}"
        )


@router.get("/deposit/{reference}/status", response_model=None)
async def check_deposit_status(
    reference: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Check the status of a deposit transaction in real-time
    
    **Description:**
    Queries Paystack API to get the current payment status and compares with local database status.
    Can be used as a callback URL for Paystack payments (shows HTML page).
    
    **Returns:**
    - HTML page if accessed via browser (from Paystack redirect)
    - JSON if accessed via API (with Accept: application/json header)
    
    **JSON Response:**
    - `reference`: Transaction reference number
    - `status`: Current status from Paystack (pending/success/failed)
    - `amount`: Transaction amount
    - `paid_at`: Payment completion timestamp (if paid)
    - `local_status`: Status in local database
    
    **Note:** If Paystack shows 'success' but local shows 'pending', the webhook may be delayed.
    Wait a moment or contact support if it persists.
    
    This endpoint queries Paystack but does NOT credit the wallet.
    Wallet crediting happens via webhook only.
    """
    # Find the transaction
    transaction = db.query(models.Transaction).filter(
        models.Transaction.reference == reference
    ).first()
    
    if not transaction:
        # If coming from browser (Paystack redirect), show HTML error
        if "text/html" in request.headers.get("accept", ""):
            return HTMLResponse(content="""
                <!DOCTYPE html>
                <html>
                <head><title>Transaction Not Found</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>❌ Transaction Not Found</h1>
                    <p>The transaction reference could not be found in our system.</p>
                    <a href="/docs">View API Docs</a>
                </body>
                </html>
            """, status_code=404)
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # If coming from browser (Paystack redirect), return HTML page
    if "text/html" in request.headers.get("accept", ""):
        return FileResponse("static/payment-success.html")
    
    # For API requests, return JSON with transaction status
    # Query Paystack for the latest status
    try:
        paystack = PaystackService()
        paystack_data = paystack.verify_transaction(reference)
        
        return {
            "reference": reference,
            "status": paystack_data["status"],
            "amount": paystack_data["amount"] / 100,  # Convert from kobo
            "paid_at": paystack_data.get("paid_at"),
            "local_status": transaction.status,
            "type": transaction.type,
            "created_at": transaction.created_at.isoformat()
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify transaction: {str(e)}"
        )


@router.post("/transfer", response_model=TransferResponse)
async def transfer_funds(
    transfer_data: TransferRequest,
    current_user: models.User = Depends(get_current_user_or_service),
    db: Session = Depends(get_db)
):
    """
    Transfer funds to another wallet
    
    Supports both JWT and API key authentication (with 'transfer' permission)
    """
    # Get sender's wallet
    sender_wallet = db.query(models.Wallet).filter(
        models.Wallet.user_id == current_user.id
    ).first()
    
    if not sender_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sender wallet not found"
        )
    
    # Check if sender has sufficient balance
    if sender_wallet.balance < transfer_data.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance"
        )
    
    # Get recipient's wallet
    recipient_wallet = db.query(models.Wallet).filter(
        models.Wallet.wallet_number == transfer_data.recipient_wallet_number
    ).first()
    
    if not recipient_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient wallet not found"
        )
    
    # Prevent self-transfer
    if sender_wallet.id == recipient_wallet.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transfer to your own wallet"
        )
    
    # Generate transaction reference
    reference = generate_transaction_reference()
    
    try:
        # Perform atomic transfer
        # Debit sender
        sender_wallet.balance -= transfer_data.amount
        
        # Create debit transaction
        debit_transaction = models.Transaction(
            wallet_id=sender_wallet.id,
            type="transfer_out",
            amount=transfer_data.amount,
            status="success",
            reference=f"{reference}-OUT",
            description=transfer_data.description or "Transfer to another wallet",
            recipient_wallet_number=recipient_wallet.wallet_number
        )
        
        # Credit recipient
        recipient_wallet.balance += transfer_data.amount
        
        # Create credit transaction
        credit_transaction = models.Transaction(
            wallet_id=recipient_wallet.id,
            type="transfer_in",
            amount=transfer_data.amount,
            status="success",
            reference=f"{reference}-IN",
            description=transfer_data.description or "Transfer from another wallet",
            sender_wallet_number=sender_wallet.wallet_number
        )
        
        db.add(debit_transaction)
        db.add(credit_transaction)
        db.commit()
        
        return TransferResponse(
            reference=reference,
            amount=transfer_data.amount,
            recipient_wallet_number=recipient_wallet.wallet_number,
            status="success"
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transfer failed: {str(e)}"
        )


@router.get("/transactions")
async def get_transactions(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    type: Optional[str] = None,
    current_user: models.User = Depends(get_current_user_or_service),
    db: Session = Depends(get_db)
):
    """
    Get transaction history with optional filters
    
    **Query Parameters:**
    - **limit**: Maximum number of transactions to return (default: 50)
    - **offset**: Number of transactions to skip for pagination (default: 0)
    - **status**: Filter by transaction status - `pending`, `success`, or `failed`
    - **type**: Filter by transaction type - `deposit`, `withdrawal`, or `transfer`
    
    **Authentication:**
    - Supports both JWT tokens and API keys (requires 'read' permission)
    
    **Example Usage:**
    - Get all transactions: `GET /wallet/transactions`
    - Get pending only: `GET /wallet/transactions?status=pending`
    - Get successful deposits: `GET /wallet/transactions?status=success&type=deposit`
    """
    wallet = db.query(models.Wallet).filter(
        models.Wallet.user_id == current_user.id
    ).first()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    query = db.query(models.Transaction).filter(
        models.Transaction.wallet_id == wallet.id
    )
    
    # Apply filters
    if status:
        if status not in ["pending", "success", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status. Must be: pending, success, or failed"
            )
        query = query.filter(models.Transaction.status == status)
    
    if type:
        if type not in ["deposit", "withdrawal", "transfer"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid type. Must be: deposit, withdrawal, or transfer"
            )
        query = query.filter(models.Transaction.type == type)
    
    transactions = query.order_by(
        models.Transaction.created_at.desc()
    ).limit(limit).offset(offset).all()
    
    return {"transactions": transactions}


@router.get("/transactions/pending")
async def get_pending_transactions(
    current_user: models.User = Depends(get_current_user_or_service),
    db: Session = Depends(get_db)
):
    """
    Get all pending transactions
    
    **Description:**
    Returns all transactions with status='pending'. These are typically:
    - Paystack deposits awaiting payment completion
    - Transfers awaiting confirmation
    
    **To Complete Pending Deposits:**
    1. Use the transaction reference to get payment URL: `GET /wallet/deposit/{reference}/status`
    2. Complete payment via Paystack checkout
    3. Webhook will automatically update status to 'success' and credit wallet
    
    **Authentication:**
    - Supports both JWT tokens and API keys (requires 'read' permission)
    """
    wallet = db.query(models.Wallet).filter(
        models.Wallet.user_id == current_user.id
    ).first()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    transactions = db.query(models.Transaction).filter(
        models.Transaction.wallet_id == wallet.id,
        models.Transaction.status == "pending"
    ).order_by(
        models.Transaction.created_at.desc()
    ).all()
    
    return {"transactions": transactions}


@router.get("/transactions/completed")
async def get_completed_transactions(
    current_user: models.User = Depends(get_current_user_or_service),
    db: Session = Depends(get_db)
):
    """
    Get all completed (successful) transactions
    
    **Description:**
    Returns all transactions with status='success'. These transactions have been:
    - Confirmed and funds credited/debited
    - Reflected in wallet balance
    
    **Authentication:**
    - Supports both JWT tokens and API keys (requires 'read' permission)
    """
    wallet = db.query(models.Wallet).filter(
        models.Wallet.user_id == current_user.id
    ).first()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    transactions = db.query(models.Transaction).filter(
        models.Transaction.wallet_id == wallet.id,
        models.Transaction.status == "success"
    ).order_by(
        models.Transaction.created_at.desc()
    ).all()
    
    return {"transactions": transactions}


@router.get("/transactions/summary")
async def get_transactions_summary(
    current_user: models.User = Depends(get_current_user_or_service),
    db: Session = Depends(get_db)
):
    """
    Get transaction summary and statistics
    
    **Returns:**
    - Total number of transactions by status
    - Total amount by transaction type
    - Pending amount awaiting completion
    - Current wallet balance
    
    **Authentication:**
    - Supports both JWT tokens and API keys (requires 'read' permission)
    """
    wallet = db.query(models.Wallet).filter(
        models.Wallet.user_id == current_user.id
    ).first()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    transactions = db.query(models.Transaction).filter(
        models.Transaction.wallet_id == wallet.id
    ).all()
    
    # Calculate summary
    pending_txs = [t for t in transactions if t.status == "pending"]
    success_txs = [t for t in transactions if t.status == "success"]
    failed_txs = [t for t in transactions if t.status == "failed"]
    
    summary = {
        "wallet_number": wallet.wallet_number,
        "current_balance": wallet.balance,
        "total_transactions": len(transactions),
        "by_status": {
            "pending": {
                "count": len(pending_txs),
                "total_amount": sum(t.amount for t in pending_txs)
            },
            "success": {
                "count": len(success_txs),
                "total_amount": sum(t.amount for t in success_txs)
            },
            "failed": {
                "count": len(failed_txs),
                "total_amount": sum(t.amount for t in failed_txs)
            }
        },
        "by_type": {
            "deposits": sum(t.amount for t in transactions if t.type == "deposit" and t.status == "success"),
            "withdrawals": sum(t.amount for t in transactions if t.type == "withdrawal" and t.status == "success"),
            "transfers_out": sum(t.amount for t in transactions if t.type == "transfer" and t.status == "success" and t.sender_wallet_number),
            "transfers_in": sum(t.amount for t in transactions if t.type == "transfer" and t.status == "success" and t.recipient_wallet_number)
        },
        "pending_amount": sum(t.amount for t in pending_txs),
        "total_success_amount": sum(t.amount for t in success_txs if t.type == "deposit")
    }
    
    return summary


@router.delete("/transactions/pending/clear")
async def clear_old_pending_transactions(
    days_old: int = 1,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clear old pending transactions that were never completed
    
    **Description:**
    Cancels pending transactions older than the specified number of days.
    This is useful for cleaning up abandoned Paystack payment sessions.
    
    **Query Parameters:**
    - `days_old`: Minimum age in days for transactions to clear (default: 1)
      - Minimum: 1 day (safety measure)
      - Transactions older than this will be marked as 'failed'
    
    **Safety Features:**
    - Only affects transactions with status='pending'
    - Does not affect completed or failed transactions
    - Does not modify wallet balance (pending transactions aren't credited)
    - Minimum 1 day old to prevent accidental cancellation of active payments
    
    **Use Cases:**
    - Clean up abandoned payment sessions
    - Remove clutter from transaction history
    - Prepare for fresh testing
    
    **Returns:**
    - Number of transactions cleared
    - Total amount of cleared transactions
    - List of cleared transaction references
    
    **Authentication:**
    - Requires JWT token (user must own the wallet)
    
    **Example:**
    ```
    DELETE /wallet/transactions/pending/clear?days_old=1
    ```
    """
    wallet = db.query(models.Wallet).filter(
        models.Wallet.user_id == current_user.id
    ).first()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    # Validate days_old parameter
    if days_old < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="days_old must be at least 1 to prevent accidental deletion of active payments"
        )
    
    # Calculate cutoff date
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    
    # Find old pending transactions
    old_pending = db.query(models.Transaction).filter(
        models.Transaction.wallet_id == wallet.id,
        models.Transaction.status == "pending",
        models.Transaction.created_at < cutoff_date
    ).all()
    
    if not old_pending:
        return {
            "message": f"No pending transactions older than {days_old} day(s) found",
            "cleared_count": 0,
            "cleared_amount": 0,
            "cleared_references": []
        }
    
    # Mark as failed with explanation
    cleared_refs = []
    cleared_amount = 0
    
    for transaction in old_pending:
        transaction.status = "failed"
        transaction.description += f" (Cleared: abandoned after {days_old}+ days)"
        cleared_refs.append(transaction.reference)
        cleared_amount += transaction.amount
    
    db.commit()
    
    return {
        "message": f"Successfully cleared {len(old_pending)} old pending transaction(s)",
        "cleared_count": len(old_pending),
        "cleared_amount": cleared_amount,
        "cleared_references": cleared_refs,
        "days_old_threshold": days_old
    }


@router.delete("/transactions/{reference}/cancel")
async def cancel_pending_transaction(
    reference: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a specific pending transaction
    
    **Description:**
    Cancels a single pending transaction by marking it as 'failed'.
    This is useful when you no longer want to complete a specific payment.
    
    **Path Parameters:**
    - `reference`: Transaction reference (e.g., TXN-20251210081957-KBODC6JN)
    
    **Safety Features:**
    - Only affects transactions with status='pending'
    - Cannot cancel completed or already failed transactions
    - Does not affect wallet balance
    - User must own the transaction
    
    **Returns:**
    - Transaction details
    - Confirmation message
    
    **Authentication:**
    - Requires JWT token (user must own the transaction)
    
    **Example:**
    ```
    DELETE /wallet/transactions/TXN-20251210081957-KBODC6JN/cancel
    ```
    """
    wallet = db.query(models.Wallet).filter(
        models.Wallet.user_id == current_user.id
    ).first()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    # Find the transaction
    transaction = db.query(models.Transaction).filter(
        models.Transaction.reference == reference,
        models.Transaction.wallet_id == wallet.id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with reference '{reference}' not found"
        )
    
    # Check if already completed or failed
    if transaction.status == "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a completed transaction. This transaction has already been processed."
        )
    
    if transaction.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction is already cancelled/failed"
        )
    
    # Cancel the transaction
    transaction.status = "failed"
    transaction.description += " (Cancelled by user)"
    db.commit()
    db.refresh(transaction)
    
    return {
        "message": "Transaction cancelled successfully",
        "reference": transaction.reference,
        "amount": transaction.amount,
        "type": transaction.type,
        "previous_status": "pending",
        "current_status": "failed",
        "created_at": transaction.created_at
    }


@router.delete("/transactions/pending/clear-all")
async def clear_all_pending_transactions(
    confirm: bool = False,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clear ALL pending transactions (requires confirmation)
    
    **⚠️ WARNING: This clears ALL pending transactions regardless of age!**
    
    **Description:**
    Cancels all pending transactions for your wallet. Use this with caution
    as it will clear active payment sessions that might still be in progress.
    
    **Query Parameters:**
    - `confirm`: Must be `true` to execute (safety measure)
      - Prevents accidental execution
      - Default: false
    
    **Safety Features:**
    - Requires explicit confirmation via `confirm=true` parameter
    - Only affects transactions with status='pending'
    - Does not affect wallet balance
    - Cannot be undone
    
    **Use Cases:**
    - Complete cleanup before fresh testing
    - Remove all abandoned payments at once
    - Start with a clean slate
    
    **Returns:**
    - Number of transactions cleared
    - Total amount of cleared transactions
    - List of cleared transaction references
    
    **Authentication:**
    - Requires JWT token (user must own the wallet)
    
    **Example:**
    ```
    DELETE /wallet/transactions/pending/clear-all?confirm=true
    ```
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must set confirm=true to clear all pending transactions. This action cannot be undone."
        )
    
    wallet = db.query(models.Wallet).filter(
        models.Wallet.user_id == current_user.id
    ).first()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    # Find all pending transactions
    pending_txns = db.query(models.Transaction).filter(
        models.Transaction.wallet_id == wallet.id,
        models.Transaction.status == "pending"
    ).all()
    
    if not pending_txns:
        return {
            "message": "No pending transactions to clear",
            "cleared_count": 0,
            "cleared_amount": 0,
            "cleared_references": []
        }
    
    # Mark all as failed
    cleared_refs = []
    cleared_amount = 0
    
    for transaction in pending_txns:
        transaction.status = "failed"
        transaction.description += " (Bulk cleared by user)"
        cleared_refs.append(transaction.reference)
        cleared_amount += transaction.amount
    
    db.commit()
    
    return {
        "message": f"Successfully cleared all {len(pending_txns)} pending transaction(s)",
        "cleared_count": len(pending_txns),
        "cleared_amount": cleared_amount,
        "cleared_references": cleared_refs
    }
