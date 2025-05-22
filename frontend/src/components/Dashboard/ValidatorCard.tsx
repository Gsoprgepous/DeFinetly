import { RiskBadge } from './RiskBadge';

type ValidatorProps = {
  address: string;
  staked: number;
  risk: number;
};

export const ValidatorCard = ({ address, staked, risk }: ValidatorProps) => (
  <Card sx={{ p: 2 }}>
    <Typography variant="h6">{shortenAddress(address)}</Typography>
    <Box display="flex" alignItems="center" mt={1}>
      <Chip label={`${staked} ETH`} />
      <RiskBadge value={risk} sx={{ ml: 2 }} />
    </Box>
    <Button size="small" sx={{ mt: 2 }}>View Details</Button>
  </Card>
);
