from cryptography.fernet import Fernet
import time


# 二维码时效（s）
QR_VALID_PERIOD = 20  


class QRVerif:

    @staticmethod
    def load_secret_key():
        import base64
        with open('secret_key.pem', 'r') as pem_file:
            pem_data = pem_file.readlines()
        encoded_key = ''.join(pem_data[1:-1]) 
        key = base64.b64decode(encoded_key.encode())
        return Fernet(key)

    @staticmethod
    def encrypt_info(order_id: str) -> str:
        timestamp = int(time.time()).__str__()
        code = f"{timestamp},{order_id}"
        cipher_suite = QRVerif.load_secret_key()
        encode_info = cipher_suite.encrypt(code.encode())
        return encode_info.decode()

    @staticmethod
    def decrypt_info(encrypted_order_id: str) -> str:
        cipher_suite = QRVerif.load_secret_key()

        try:
            decode_info = cipher_suite.decrypt(encrypted_order_id.encode()).decode()
            timestamp, order_id = decode_info.split(',')
            cur_time = int(time.time()).__str__()
            return timestamp, order_id, cur_time
        except Exception as e:
            print(f"解密失败: {e}")
            raise
        
    @staticmethod
    def gen_QR_code(order_id: str) -> str:
        pass
        
