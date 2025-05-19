#pragma once
#include <string>
#include <vector>
#include <cstdint>

namespace Ethereum {

struct Transaction {
    uint64_t nonce;
    uint64_t gas_price;
    uint64_t gas_limit;
    std::string to;
    uint64_t value;
    std::string data;
    uint64_t chain_id; // Для EIP-155
};

struct SignedTransaction {
    std::string raw_hex;
    std::string tx_hash;
};

class TransactionBuilder {
public:
    SignedTransaction sign(const Transaction& tx, const std::string& priv_key_hex);
    
private:
    std::vector<uint8_t> serialize(const Transaction& tx, bool include_signature = false);
    std::vector<uint8_t> keccak256(const std::vector<uint8_t>& data);
};

} // namespace Ethereum
