import { useEffect, useState } from 'react';
import { ethers } from 'ethers';
import EigenABI from '../../../abis/EigenLayer.json';

type RiskData = {
  validators: Validator[];
  loading: boolean;
  error?: string;
};

export const useRiskData = (provider: ethers.providers.Web3Provider | null) => {
  const [data, setData] = useState<RiskData>({ 
    validators: [], 
    loading: true 
  });

  useEffect(() => {
    const fetchData = async () => {
      if (!provider) return;
      
      try {
        const contract = new ethers.Contract(
          import.meta.env.VITE_EIGEN_ADDRESS,
          EigenABI,
          provider
        );
        
        const validators = await contract.getValidatorsWithRisk();
        setData({
          validators: parseValidatorData(validators),
          loading: false
        });
      } catch (err) {
        setData({
          validators: [],
          loading: false,
          error: err instanceof Error ? err.message : 'Unknown error'
        });
      }
    };

    fetchData();
  }, [provider]);

  return data;
};

// Парсинг данных из контракта
const parseValidatorData = (raw: any[]): Validator[] => {
  return raw.map(v => ({
    address: v.validator,
    staked: parseFloat(ethers.utils.formatEther(v.staked)),
    risks: {
      total: v.riskScore / 100,
      slashing: v.slashingRisk / 100,
      liquidity: v.liquidityRisk / 100
    }
  }));
};
