import os
import logging
from yookassa import Configuration, Payment
import uuid

logger = logging.getLogger(__name__)

class YooKassaPayment:
    def __init__(self):
        """Инициализация класса для работы с YooKassa"""
        self.shop_id = os.environ.get('YOOKASSA_SHOP_ID')
        self.secret_key = os.environ.get('YOOKASSA_SECRET_KEY')
        
        if not self.shop_id or not self.secret_key:
            logger.error("Missing YooKassa credentials!")
            raise ValueError("Missing YooKassa credentials!")
            
        # Настройка YooKassa
        Configuration.account_id = self.shop_id
        Configuration.secret_key = self.secret_key
        
    def create_payment(self, amount, description):
        """Создание платежа через YooKassa"""
        try:
            logger.info(f"Creating payment for amount: {amount} RUB")
            logger.info(f"Using shop_id: {self.shop_id}")
            
            payment = Payment.create({
                "amount": {
                    "value": str(amount),
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/norma_zhora_bot"
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "order_id": str(uuid.uuid4())
                }
            })
            
            if payment and payment.confirmation and payment.confirmation.confirmation_url:
                logger.info(f"Payment created successfully. Confirmation URL: {payment.confirmation.confirmation_url}")
                return payment
            else:
                logger.error("Payment created but confirmation URL is missing")
                return None
                
        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details available'}")
            return None 