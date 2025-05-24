import { Card, Chip, Stack, Typography } from '@mui/material';
import { RiskGauge } from './RiskGauge';

type Validator = {
  address: string;
  staked: number;
  risks: {
    total: number;
    slashing: number;
    liquidity: number;
  };
};

export const ValidatorList = ({ validators }: { validators: Validator[] }) => (
  <Stack spacing={2}>
    {validators.map((v) => (
      <Card key={v.address} sx={{ p: 2 }}>
        <Stack direction="row" alignItems="center" spacing={3}>
          <Box>
            <Typography variant="subtitle1" fontFamily="monospace">
              {v.address.slice(0, 6)}...{v.address.slice(-4)}
            </Typography>
            <Chip label={`${v.staked} ETH`} size="small" />
          </Box>
          <Box flexGrow={1}>
            <RiskGauge value={v.risks.total} width={150} height={100} />
          </Box>
          <Box>
            <Typography color="text.secondary">
              Slashing: {(v.risks.slashing * 100).toFixed(1)}%
            </Typography>
          </Box>
        </Stack>
      </Card>
    ))}
  </Stack>
);
