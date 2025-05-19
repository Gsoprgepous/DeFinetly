#include "transaction_builder.hpp"
#include <secp256k1.h>
#include <secp256k1_ecdsa.h>
#include <secp256k1_recovery.h>
#include "utils/hex.hpp"
#include <array>
#include <stdexcept>

namespace Ethereum {

using ByteArray = std::vector<uint8_t>;

// Конвертация hex-ключа в байты
ByteArray hex_to_bytes(const std::string& hex) {
    if (hex.size() % 2 != 0) throw std::invalid_argument("Invalid hex length");
    ByteArray bytes;
    for (size_t i = 0; i < hex.size(); i += 2) {
        bytes.push_back(static_cast<uint8_t>(std::stoi(hex.substr(i, 2), nullptr, 16)));
    }
    return bytes;
}

// Keccak-256 хеширование (реализация через OpenSSL)
ByteArray TransactionBuilder::keccak256(const ByteArray& data) {
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    const EVP_MD* md = EVP_keccak256();
    ByteArray hash(EVP_MD_size(md), 0);
    
    EVP_DigestInit_ex(ctx, md, nullptr);
    EVP_DigestUpdate(ctx, data.data(), data.size());
    EVP_DigestFinal_ex(ctx, hash.data(), nullptr);
    EVP_MD_CTX_free(ctx);
    
    return hash;
}

// RLP-сериализация (упрощенная версия)
ByteArray TransactionBuilder::serialize(const Transaction& tx, bool include_signature) {
    ByteArray result;
    
    auto encode_rlp = [](auto val) -> ByteArray {
        // ... реализация RLP-кодирования
    };
    
    // Сериализация полей транзакции
    auto nonce_enc = encode_rlp(tx.nonce);
    auto gas_price_enc = encode_rlp(tx.gas_price);
    auto gas_limit_enc = encode_rlp(tx.gas_limit);
    auto to_enc = encode_rlp(hex_to_bytes(tx.to));
    auto value_enc = encode_rlp(tx.value);
    auto data_enc = encode_rlp(hex_to_bytes(tx.data));
    
    // Конкатенация всех полей
    result.insert(result.end(), nonce_enc.begin(), nonce_enc.end());
    result.insert(result.end(), gas_price_enc.begin(), gas_price_enc.end());
    // ... остальные поля
    
    if (include_signature) {
        result.push_back(0x01); // EIP-155 signature flag
        result.push_back(static_cast<uint8_t>(tx.chain_id));
    }
    
    return result;
}

SignedTransaction TransactionBuilder::sign(const Transaction& tx, const std::string& priv_key_hex) {
    // 1. Подготовка контекста secp256k1
    secp256k1_context* ctx = secp256k1_context_create(SECP256K1_CONTEXT_SIGN);
    if (!ctx) throw std::runtime_error("Failed to create secp256k1 context");
    
    // 2. Загрузка приватного ключа
    ByteArray priv_key = hex_to_bytes(priv_key_hex);
    if (priv_key.size() != 32) throw std::invalid_argument("Invalid private key length");
    
    // 3. Сериализация и хеширование транзакции
    ByteArray tx_serialized = serialize(tx, true);
    ByteArray tx_hash = keccak256(tx_serialized);
    
    // 4. Создание подписи ECDSA
    secp256k1_ecdsa_signature sig;
    if (!secp256k1_ecdsa_sign(ctx, &sig, tx_hash.data(), priv_key.data(), nullptr, nullptr)) {
        secp256k1_context_destroy(ctx);
        throw std::runtime_error("Failed to sign transaction");
    }
    
    // 5. Сериализация подписи (65 байт)
    ByteArray signature(65, 0);
    secp256k1_ecdsa_signature_serialize_compact(ctx, signature.data(), &sig);
    
    // 6. Добавление recovery_id (v)
    signature[64] += 27; // Ethereum-style recovery id
    
    // 7. Формирование raw-транзакции
    ByteArray raw_tx = serialize(tx);
    raw_tx.insert(raw_tx.end(), signature.begin(), signature.end());
    
    // 8. Очистка ресурсов
    secp256k1_context_destroy(ctx);
    
    return SignedTransaction{
        .raw_hex = bytes_to_hex(raw_tx),
        .tx_hash = bytes_to_hex(keccak256(raw_tx))
    };
}

} // namespace Ethereum
