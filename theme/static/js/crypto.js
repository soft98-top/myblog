/**
 * 客户端加密解密工具
 * 使用 Web Crypto API 进行 AES-GCM 解密
 */

// Encryption constants - must match Python constants
const PBKDF2_ITERATIONS = 100000;
const KEY_SIZE = 256;  // bits
const SALT_SIZE = 16;  // bytes
const NONCE_SIZE = 12;  // bytes

/**
 * Base64 解码
 * @param {string} base64 - Base64 字符串
 * @returns {Uint8Array} 字节数组
 */
function base64ToBytes(base64) {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes;
}

/**
 * 从密码派生加密密钥（使用 PBKDF2）
 * @param {string} password - 用户密码
 * @param {Uint8Array} salt - 盐值（从加密数据中提取）
 * @returns {Promise<CryptoKey>} 256-bit AES 密钥
 */
async function deriveKey(password, salt) {
    const encoder = new TextEncoder();
    const passwordBuffer = encoder.encode(password);
    
    // 导入密码作为密钥材料
    const passwordKey = await crypto.subtle.importKey(
        'raw',
        passwordBuffer,
        'PBKDF2',
        false,
        ['deriveKey']
    );
    
    // 使用 PBKDF2 派生 AES 密钥
    return await crypto.subtle.deriveKey(
        {
            name: 'PBKDF2',
            salt: salt,
            iterations: PBKDF2_ITERATIONS,
            hash: 'SHA-256'
        },
        passwordKey,
        {
            name: 'AES-GCM',
            length: KEY_SIZE
        },
        false,
        ['decrypt']
    );
}

/**
 * 解密内容（使用 AES-GCM）
 * @param {string} encryptedData - 加密数据（格式: "salt:nonce:ciphertext"，Base64 编码）
 * @param {string} password - 用户密码
 * @returns {Promise<string>} 解密后的明文
 * @throws {Error} 如果密码错误或数据损坏
 */
async function decryptContent(encryptedData, password) {
    try {
        // 解析加密数据
        const parts = encryptedData.split(':');
        if (parts.length !== 3) {
            throw new Error('CORRUPTED_DATA');
        }
        
        const salt = base64ToBytes(parts[0]);
        const nonce = base64ToBytes(parts[1]);
        const ciphertext = base64ToBytes(parts[2]);
        
        // 验证大小
        if (salt.length !== SALT_SIZE || nonce.length !== NONCE_SIZE) {
            throw new Error('CORRUPTED_DATA');
        }
        
        // 派生密钥
        const key = await deriveKey(password, salt);
        
        // 使用 AES-GCM 解密
        // GCM 模式会自动验证认证标签
        // 如果密码错误，这里会抛出错误
        const decrypted = await crypto.subtle.decrypt(
            {
                name: 'AES-GCM',
                iv: nonce
            },
            key,
            ciphertext
        );
        
        // 解码 UTF-8
        const decoder = new TextDecoder('utf-8');
        return decoder.decode(decrypted);
        
    } catch (e) {
        // 区分密码错误和数据损坏
        if (e.message === 'CORRUPTED_DATA') {
            throw new Error('CORRUPTED_DATA');
        } else {
            // Web Crypto API 对认证失败抛出通用错误
            throw new Error('WRONG_PASSWORD');
        }
    }
}
