import secrets
import string
import sys

DEFAULT_KEY_LEN = 32

# 生成一个高强度 API key
def generate_key(length=DEFAULT_KEY_LEN):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

if __name__ == "__main__":
    count = 1
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print("用法: python gen_api_keys.py [数量]")
            sys.exit(1)
    keys = [generate_key() for _ in range(count)]
    print("API_KEYS=" + ','.join(keys))
