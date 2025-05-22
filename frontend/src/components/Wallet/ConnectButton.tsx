import Web3Modal from 'web3modal';
import { ethers } from 'ethers';

export const ConnectButton = () => {
  const [account, setAccount] = useState<string>('');

  const connectWallet = async () => {
    const web3Modal = new Web3Modal({ cacheProvider: true });
    const instance = await web3Modal.connect();
    const provider = new ethers.providers.Web3Provider(instance);
    const signer = provider.getSigner();
    setAccount(await signer.getAddress());
  };

  return (
    <Button variant="contained" onClick={connectWallet}>
      {account ? shortenAddress(account) : 'Connect Wallet'}
    </Button>
  );
};
