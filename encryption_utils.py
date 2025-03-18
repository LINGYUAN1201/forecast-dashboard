import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

class FileEncryptor:
    def __init__(self, password, salt=b'saltysalt'):
        """
        初始化加密器，通过密码和盐派生 32 字节密钥（AES-256）
        :param password: 加密密码（字符串）
        :param salt: 盐值，默认 b'saltysalt'（可根据需要更改）
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
        # 读取原始文件内容
        with open(input_file, 'rb') as f:
            plaintext = f.read()
        
        # 生成随机 IV（16 字节）
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # 对数据进行 PKCS7 填充
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(plaintext) + padder.finalize()
        
        # 加密数据
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
        
        # 前 16 字节为 IV，其余为密文
        iv = data[:16]
        ciphertext = data[16:]
        
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        # 去除 PKCS7 填充
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
        
        with open(output_file, 'wb') as f:
            f.write(plaintext)

# 以下为测试代码，可直接运行本文件进行加密/解密测试
if __name__ == "__main__":
    password = "your_password_here"  # 请将此处修改为您的实际密码
    encryptor = FileEncryptor(password)
    
    input_file = "data/forecast_results.pkl"
    encrypted_file = "data/encrypted_forecast_results.pkl"
    decrypted_file = "data/decrypted_forecast_results.pkl"
    
    # 加密文件
    encryptor.encrypt_file(input_file, encrypted_file)
    print(f"文件已加密，保存为：{encrypted_file}")
    
    # 解密文件
    encryptor.decrypt_file(encrypted_file, decrypted_file)
    print(f"文件已解密，保存为：{decrypted_file}")
