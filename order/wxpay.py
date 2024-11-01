from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging
from wechatpayv3 import WechatPayService, WechatPayConfig  # 假设有相关的微信支付库
from datetime import datetime

logging.basicConfig(level=logging.INFO)

class WechatPayServiceImpl:
    def __init__(self, config):
        self.config = config

    def call_wechat_pay(self, order):
        openid = order['openid']
        out_trade_no = self.get_business_no('TRADE')
        description = order['description']
        total = order['total']

        try:
            request_data = {
                'total': total,
                'app_id': self.config.app_id,
                'merchant_id': self.config.merchant_id,
                'description': description,
                'out_trade_no': out_trade_no,
                'openid': openid
            }
            response = WechatPayService.prepay_with_request_payment(request_data)
            logging.info(f"Order placed successfully, outTradeNo: {out_trade_no}")
            return {
                'appId': response['appId'],
                'timeStamp': response['timeStamp'],
                'nonceStr': response['nonceStr'],
                'package': response['packageVal'],
                'signType': response['signType'],
                'paySign': response['paySign']
            }
        except Exception as e:
            logging.error(f"Error creating payment order: {e}")
            return {'error': str(e)}

    def resolve_notify(self, request_body, headers):
        try:
            notification_data = self.get_request_param(headers, request_body)
            transaction = WechatPayService.parse_notification(notification_data)
            logging.debug(f"Transaction: {transaction}")
            # 处理交易结果...
        except Exception as e:
            logging.error(f"Error processing payment notification: {e}")

    def refund(self, out_trade_no):
        try:
            refund_response = self.create_refund(out_trade_no)
            logging.debug(f"Refund response: {refund_response}")
            return refund_response
        except Exception as e:
            logging.error(f"Error processing refund: {e}")
            return {'error': str(e)}

    def create_refund(self, out_trade_no):
        transaction = self.query_order_by_out_trade_no(out_trade_no)
        total = transaction['amount']['payer_total']

        refund_request = {
            'out_refund_no': self.get_business_no('REFUND'),
            'amount': {
                'currency': 'CNY',
                'refund': total,
                'total': total
            },
            'out_trade_no': out_trade_no,
            'notify_url': 'https://your-notify-url.com/refund/notify'
        }
        return WechatPayService.create_refund(refund_request)

    def get_business_no(self, business_type):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"{business_type}_{timestamp[:32]}"

    def query_order_by_out_trade_no(self, out_trade_no):
        return WechatPayService.query_order(out_trade_no)

    def get_request_param(self, headers, request_body):
        logging.info(f"Received WeChat payment callback: {request_body}")
        return {
            'signature': headers.get('Wechatpay-Signature'),
            'nonce': headers.get('Wechatpay-Nonce'),
            'timestamp': headers.get('Wechatpay-Timestamp'),
            'serial_no': headers.get('Wechatpay-Serial'),
            'signature_type': headers.get('Wechatpay-Signature-Type'),
            'body': request_body
        }

config = WechatPayConfig()  # Initialize your config
wechat_pay_service = WechatPayServiceImpl(config)

class WechatPayView(APIView):
    def post(self, request):
        order = request.data
        response_data = wechat_pay_service.call_wechat_pay(order)
        return Response(response_data, status=status.HTTP_200_OK)

class WechatNotifyView(APIView):
    def post(self, request):
        wechat_pay_service.resolve_notify(request.body, request.headers)
        return Response({'status': 'success'}, status=status.HTTP_200_OK)

class RefundView(APIView):
    def post(self, request):
        out_trade_no = request.data.get('out_trade_no')
        response_data = wechat_pay_service.refund(out_trade_no)
        return Response(response_data, status=status.HTTP_200_OK)