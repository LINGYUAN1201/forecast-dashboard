import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from dotenv import load_dotenv
load_dotenv()  # 自动加载 .env 文件中的环境变量

class FileEncryptor:
    def __init__(self, password, salt=b'saltysalt'):
        """
        初始化加密器，通过密码和盐派生 32 字节密钥（AES-256）
        :param password: 加密密码（字符串）
        :param salt: 盐值，默认 b'saltysalt'
        """
        self.password = password.encode('utf-8')
        self.salt = salt
        self.key = self.derive_key()
    
    def derive_key(self):
        """使用 scrypt 算法派生密钥"""
        kdf = Scrypt(
            salt=self.salt,
            length=32,
            n=2**14,
            r=8,
            p=1,
            backend=default_backend()
        )
        return kdf.derive(self.password)
    
    def encrypt_file(self, input_file, output_file):
        """
        加密文件
        :param input_file: 待加密文件路径
        :param output_file: 加密后保存文件路径
        加密格式：前 16 字节为随机 IV，后续为密文
        """
        with open(input_file, 'rb') as f:
            plaintext = f.read()
        
        # 生成随机 IV（16 字节）
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # 对数据进行 PKCS7 填充
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(plaintext) + padder.finalize()
        
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # 将 IV 与密文写入输出文件
        with open(output_file, 'wb') as f:
            f.write(iv + ciphertext)
    
    def decrypt_file(self, input_file, output_file):
        """
        解密文件
        :param input_file: 加密文件路径（前 16 字节为 IV）
        :param output_file: 解密后保存文件路径
        """
        with open(input_file, 'rb') as f:
            data = f.read()
        
        iv = data[:16]
        ciphertext = data[16:]
        
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
        
        with open(output_file, 'wb') as f:
            f.write(plaintext)

def check_integrity(original_file, decrypted_file):
    """
    测试函数：检查解密后的文件内容是否与原始文件一致
    仅用于本地测试，不应将原始文件上传至生产环境
    """
    with open(original_file, 'rb') as f:
        original_data = f.read()
    with open(decrypted_file, 'rb') as f:
        decrypted_data = f.read()
    if original_data == decrypted_data:
        print("数据校验通过：解密后的数据与原始数据一致。")
    else:
        print("数据校验失败：解密后的数据与原始数据不一致！")

# 以下为测试代码，仅用于本地验证加密/解密完整性
if __name__ == "__main__":
    # 注意：本地测试时，请确保存在 data/forecast_results.pkl（原始数据文件）
    password = os.environ.get("ENCRYPTION_PASSWORD", "default_password")
    encryptor = FileEncryptor(password)
    
    original_file = "data/forecast_results.pkl"         # 本地原始数据（仅用于测试）
    encrypted_file = "data/encrypted_forecast_results.pkl"  # 加密后的文件
    decrypted_file = "data/decrypted_forecast_results.pkl"  # 临时解密文件
    
    # 生成加密文件
    encryptor.encrypt_file(original_file, encrypted_file)
    print(f"文件已加密，保存为：{encrypted_file}")
    
    # 解密生成临时文件
    encryptor.decrypt_file(encrypted_file, decrypted_file)
    print(f"文件已解密，保存为：{decrypted_file}")
    
    # 检查解密后的数据与原始数据是否一致
    check_integrity(original_file, decrypted_file)
