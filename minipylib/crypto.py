# -*- coding: utf-8 -*-
"""
minipylib.crypto

Cryptographic and encoding/decoding functions.

Copyright (c) 2011-2012 Kevin Chan <kefin@makedostudio.com>

* created: 2012-06-25 Kevin Chan <kefin@makedostudio.com>
* updated: 2012-06-25 kchan
"""

import os
import hashlib
import base64
import hmac
import string
from random import choice

try:
    import cPickle as pickle
except ImportError:
    import pickle

from Crypto.Cipher import AES




### AES encryption/decryption

# def encryption_test(data):
#     """
#     encrypt/decrypt test
#     """
#     secret = 'abc'
#
#     cipher = Cipher(secret)
#     ciphertext = cipher.encrypt(data)
#
#     print "# password: %s" % secret
#     print "# iv: %s" % base64.b64encode(cipher.iv)
#     print "# digest: %s" % base64.b64encode(cipher.digest)
#     print "# encrypted:"
#     print base64.b64encode(ciphertext)
#
#     cipher = Cipher(secret)
#     plaintext = cipher.decrypt(ciphertext)
#
#     print "# iv: %s" % base64.b64encode(cipher.iv)
#     print "# digest: %s" % base64.b64encode(cipher.digest)
#     print "# decrypted:"
#     print plaintext


class CipherError(Exception):
    pass

class Cipher(object):
    """
    Encryption/decryption cipher object using AES (from PyCrypto).
    * i.e., requires PyCrypto
    
    Reference links:

    * PyCrypto
      http://www.pycrypto.org/
      https://www.dlitz.net/software/pycrypto/

    * Eli Bendersky's website > AES encryption of files in Python with PyCrypto
      http://bit.ly/KXmxJM

    """
    iv_size = AES.block_size
    mode = AES.MODE_CFB
    digest_mod = hashlib.sha256
    digest_size = 32

    def __init__(self, secret):
        """
        :param secret: secret password
        """
        self.set_secret(secret)
        self.key = self.gen_key(secret)
        self.iv = None
        self.digest = None

    def set_secret(self, secret):
        """
        Set secret password.
        """
        self.secret = secret

    @classmethod
    def gen_key(cls, secret):
        """
        Generate a fix-length key from secret password.
        * default is 32 byte key (from sha256)
        """
        if not secret:
            raise CipherError("Empty encryption key")
        h = hashlib.sha256()
        h.update(secret)
        return h.digest()

    def make_digest(self, *args):
        """
        Return a message digest for arguments.
        """
        h = self.digest_mod()
        for arg in args:
            h.update(arg)
        return h.digest()

    def encrypt(self, plaintext):
        """
        Encrypt plaintext.
        """
        if not self.key:
            raise CipherError("Empty encryption key")
        self.iv = os.urandom(self.iv_size)
        cryptobj = AES.new(self.key, mode=self.mode, IV=self.iv)
        encrypted = self.iv + cryptobj.encrypt(plaintext)
        self.digest = self.make_digest(encrypted)
        return self.digest + encrypted

    def decrypt(self, data):
        """
        Decrypt ciphertext.
        """
        if not self.key:
            raise CipherError("Empty encryption key")
        self.digest = data[:self.digest_size]
        header = self.digest_size + self.iv_size
        self.iv = data[self.digest_size:header]
        ciphertext = data[header:]
        cryptobj = AES.new(self.key, mode=self.mode, IV=self.iv)
        decrypted = cryptobj.decrypt(ciphertext)
        if self.make_digest(data[self.digest_size:]) != self.digest:
            raise CipherError("Data signatures do not match!")
        return decrypted


### functions to encode/decode using AES Cipher object (above)

### example encode/decode function
#
# def encoder(data, secret, mode):
#     """
#     encrypt or decrypt data.
#
#     :param data: data to be encoded/decoded
#     :param secret: secret password
#     :param mode: 'e' (encode) or 'd' (decode)
#     :returns: encoded/decoded data
#     """
#     if mode == 'd':
#         plaintext = decode_data(data, secret, b64_encoding=True)
#         print plaintext
#     else:
#         ciphertext = encode_data(data, secret, b64_encoding=True)
#         print ciphertext


def encode_data(data, secret_key, pickle_data=False, b64_encoding=False):
    """
    Encode data using encryption, pickle and base64.b64encode.

    :param data: data to encrypt (set pickle_data to True if Python data structure).
    :param pickle_data: True or False; set to True to enable pickling.
    :param b64_encoding: True or False; set to True to base64 encode result.
    :returns: string
    """
    if pickle_data:
        data = pickle.dumps(data)
    encoded = Cipher(secret_key).encrypt(data)
    if b64_encoding:
        encoded = base64.b64encode(encoded)
    return encoded


def decode_data(encrypted, secret_key, pickle_data=False, b64_encoding=False):
    """
    Decode data encrypted and encoded by encode_data above.

    :param encrypted: encoded string to be decoded.
    :param pickle_data: True or False; set to True if encrypted data is  pickled.
    :param b64_encoding: True or False; set to True if ciphertext is base64 encoded.
    :returns: data structure.
    """
    if b64_encoding:
        encrypted = base64.b64decode(encrypted)
    decoded = Cipher(secret_key).decrypt(encrypted)
    if pickle_data:
        decoded = pickle.loads(decoded)
    return decoded


### hash functions

DefaultHash = hashlib.sha256
DefaultHashAlgorithms = {
    'md5': hashlib.md5,
    'sha1': hashlib.sha1,
    'sha224': hashlib.sha224,
    'sha256': hashlib.sha256,
    'sha384': hashlib.sha384,
    'sha512': hashlib.sha512
}

def file_digest(path, block_size=2**10, hashfunc=None, algorithm=None):
    """
    Calculate hash for file (default algorithm is hashlib.sha256).

    :param path: file system path for file
    :param hashfunc: algorithm to use (from hashlib)
    :param algorithm: alternative method of specifying hash algorithm (as string)
    :returns: hash in hex
    """
    if hashfunc is None:
        if algorithm is None:
            hashfunc = DefaultHash
        else:
            hashfunc = DefaultHashAlgorithms.get(algorithm, DefaultHash);
    h = hashfunc()
    f = open(path)
    while True:
        data = f.read(block_size)
        if not data:
            break
        h.update(data)
    f.close()
    return h.hexdigest()


def md5_for_file(path, block_size=2**10):
    """
    Calculate md5 checksum for file.

    :param path: file system path for file
    :returns: md5 hash in hex
    """
    return file_digest(path, block_size=block_size, hashfunc=hashlib.md5)



### make hmac digest

def make_digest(secret_key, *args, **kwargs):
    """
    Return a hmac digest for arguments.

    :param secret_key: secret password to use for creating hash digest
    :param digestmod: keyword argument for digest module (default: DefaultHash)
    :param hexdigest: if True, return hexdigest format, else regular binary
    :returns: string (in hexdigest format)
    """
    digestmod = kwargs.get('digestmod', DefaultHash)
    h = hmac.new(secret_key, digestmod=digestmod)
    for arg in args:
        h.update(arg)
    if kwargs.get('hexdigest') is True:
        return h.hexdigest()
    return h.digest()



### secret key generation

### old version (begin)
# DEFAULT_SECRET_KEY_SIZE = 50
#
# def gen_secret_key(keysize=DEFAULT_SECRET_KEY_SIZE, use_punctuation=False):
#     """
#     Generate secret key for encryption.
#
#     :param keysize: number of characters in key (default is 50)
#     :param use_punctuation: include punctuation characters (default: alphanumeric)
#     :returns: string
#     """
#     ch = string.letters + string.digits
#     if use_punctuation:
#         ch += string.punctuation
#     return ''.join([choice(ch) for i in range(keysize)])
### old version (end)


### secret key generation

DEFAULT_KEY_SIZE = 50
SECRET_KEY_CHAR_SET = "anp"
DEFAULT_KEY_CHAR_SET = "an"

def gen_secret_key(keysize=DEFAULT_KEY_SIZE,
                   charset=DEFAULT_KEY_CHAR_SET,
                   use_punctuation=False):
    """
    Generate secret key for encryption.
    * caller should specify character set to use:
    a: alphabets
    n: numerals
    p: punctuations

    :param keysize: number of characters in key (default is 50)
    :param charset: characters to use in key (a, n and/or p)
    :param use_punctuation: legacy option for compatibility with old function
    :returns: string
    """
    try:
        keysize = int(keysize)
    except TypeError:
        keysize = DEFAULT_SECRET_KEY_SIZE
    if use_punctuation:
        charset += 'p'
    ch = ''
    for c in charset:
        if c is 'a':
            ch += string.letters
        elif c is 'n':
            ch += string.digits
        elif c is 'p':
            ch += string.punctuation
    return ''.join([choice(ch) for i in range(keysize)])
