/**
 * 客户端加密解密工具
 * 使用 Web Crypto API 进行 AES-CBC 解密
 */

/**
 * 从密码生成密钥
 * @param {string} password - 密码
 * @returns {Promise<CryptoKey>} 密钥
 */
async function deriveKey(password) {
    const encoder = new TextEncoder();
    const passwordBuffer = encoder.encode(password);
    
    // 使用 SHA-256 生成密钥
    const hashBuffer = await crypto.subtle.digest('SHA-256', passwordBuffer);
    
    // 导入为 AES 密钥
    return await crypto.subtle.importKey(
        'raw',
        hashBuffer,
        { name: 'AES-CBC' },
        false,
        ['decrypt']
    );
}

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
 * 解密内容
 * @param {string} encryptedData - 加密数据（格式: iv:encrypted_data）
 * @param {string} password - 密码
 * @returns {string} 解密后的内容
 * @throws {Error} 解密失败
 */
function decryptContent(encryptedData, password) {
    // 同步版本 - 使用简单的 XOR 加密（用于演示）
    // 注意：这不是真正的 AES，只是为了演示流程
    // 实际生产环境应该使用异步的 Web Crypto API
    
    try {
        // 分离 IV 和加密数据
        const parts = encryptedData.split(':');
        if (parts.length !== 2) {
            throw new Error('Invalid encrypted data format');
        }
        
        const iv = base64ToBytes(parts[0]);
        const encrypted = base64ToBytes(parts[1]);
        
        // 生成密钥（简化版 - 使用密码的哈希）
        const key = simpleHash(password);
        
        // 解密（简化的 XOR 解密）
        const decrypted = new Uint8Array(encrypted.length);
        for (let i = 0; i < encrypted.length; i++) {
            decrypted[i] = encrypted[i] ^ key[i % key.length] ^ iv[i % iv.length];
        }
        
        // 移除 PKCS7 填充
        const paddingLength = decrypted[decrypted.length - 1];
        const unpaddedLength = decrypted.length - paddingLength;
        
        // 转换为字符串
        const decoder = new TextDecoder('utf-8');
        const result = decoder.decode(decrypted.slice(0, unpaddedLength));
        
        // 验证解密结果是否有效
        if (!result || result.length === 0) {
            throw new Error('Decryption failed');
        }
        
        return result;
    } catch (e) {
        throw new Error('Decryption failed: ' + e.message);
    }
}

/**
 * 简单哈希函数（用于演示）
 * @param {string} str - 输入字符串
 * @returns {Uint8Array} 哈希值
 */
function simpleHash(str) {
    const encoder = new TextEncoder();
    const data = encoder.encode(str);
    const hash = new Uint8Array(32);
    
    // 简单的哈希算法（不安全，仅用于演示）
    for (let i = 0; i < data.length; i++) {
        hash[i % 32] ^= data[i];
        hash[(i + 1) % 32] ^= (data[i] << 1) | (data[i] >> 7);
    }
    
    // 多次混合
    for (let round = 0; round < 3; round++) {
        for (let i = 0; i < 32; i++) {
            hash[i] ^= hash[(i + 7) % 32];
            hash[i] = (hash[i] << 3) | (hash[i] >> 5);
        }
    }
    
    return hash;
}

/**
 * 异步解密内容（使用真正的 Web Crypto API）
 * @param {string} encryptedData - 加密数据
 * @param {string} password - 密码
 * @returns {Promise<string>} 解密后的内容
 */
async function decryptContentAsync(encryptedData, password) {
    try {
        const parts = encryptedData.split(':');
        if (parts.length !== 2) {
            throw new Error('Invalid encrypted data format');
        }
        
        const iv = base64ToBytes(parts[0]);
        const encrypted = base64ToBytes(parts[1]);
        
        // 生成密钥
        const key = await deriveKey(password);
        
        // 解密
        const decrypted = await crypto.subtle.decrypt(
            { name: 'AES-CBC', iv: iv },
            key,
            encrypted
        );
        
        // 转换为字符串
        const decoder = new TextDecoder('utf-8');
        return decoder.decode(decrypted);
    } catch (e) {
        throw new Error('Decryption failed');
    }
}
