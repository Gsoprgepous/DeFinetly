import { useParams } from 'react-router-dom';
import { 
  Box, 
  Breadcrumbs, 
  Card, 
  Chip, 
  Container, 
  Link, 
  Skeleton, 
  Tab, 
  Tabs, 
  Typography 
} from '@mui/material';
import { 
  RiskGauge,
  StakingHistoryChart,
  SlashingEventsTable
} from '../../components';
import { useValidatorQuery } from '../../hooks';

export const Validator = () => {
  const { address } = useParams();
  const { data, isLoading, error } = useValidatorQuery(address!);
  const [tabValue, setTabValue] = useState(0);

  if (isLoading) return <ValidatorSkeleton />;
  if (error) return <Typography color="error">{error.message}</Typography>;

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Breadcrumbs sx={{ mb: 3 }}>
        <Link href="/explorer" underline="hover">
          Explorers
        </Link>
        <Typography color="text.primary">
          {data?.address.slice(0, 8)}...{data?.address.slice(-6)}
        </Typography>
      </Breadcrumbs>

      <Grid container spacing={4}>
        {/* Основная информация */}
        <Grid item xs={12} md={4}>
          <Card sx={{ p: 3, height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <Typography variant="h5" sx={{ mr: 2 }}>
                Validator Details
              </Typography>
              <Chip 
                label={data?.status} 
                color={
                  data?.status === 'active' ? 'success' : 
                  data?.status === 'slashed' ? 'error' : 'warning'
                }
              />
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography variant="body2" color="text.secondary">
                Address
              </Typography>
              <Typography fontFamily="monospace">
                {data?.address}
              </Typography>
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography variant="body2" color="text.secondary">
                Total Staked
              </Typography>
              <Typography variant="h6">
                {data?.totalStaked} ETH
              </Typography>
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography variant="body2" color="text.secondary">
                Overall Risk
              </Typography>
              <RiskGauge value={data?.riskScore || 0} width={200} height={120} />
            </Box>
          </Card>
        </Grid>

        {/* Графики и таблицы */}
        <Grid item xs={12} md={8}>
          <Card sx={{ p: 2 }}>
            <Tabs 
              value={tabValue}
              onChange={(_, newValue) => setTabValue(newValue)}
              sx={{ mb: 3 }}
            >
              <Tab label="Staking History" />
              <Tab label="Slashing Events" />
              <Tab label="Restaked Assets" />
            </Tabs>

            {tabValue === 0 && <StakingHistoryChart data={data?.history || []} />}
            {tabValue === 1 && <SlashingEventsTable events={data?.slashingEvents || []} />}
            {tabValue === 2 && <RestakedAssetsList assets={data?.restakedAssets || []} />}
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
};

const ValidatorSkeleton = () => (
  <Container maxWidth="lg" sx={{ py: 4 }}>
    <Skeleton width={300} height={40} sx={{ mb: 3 }} />
    <Grid container spacing={4}>
      <Grid item xs={12} md={4}>
        <Card sx={{ p: 3, height: '100%' }}>
          <Skeleton width="60%" height={40} sx={{ mb: 3 }} />
          {[...Array(4)].map((_, i) => (
            <Box key={i} sx={{ mb: 3 }}>
              <Skeleton width="30%" height={24} />
              <Skeleton width="80%" height={32} />
            </Box>
          ))}
        </Card>
      </Grid>
      <Grid item xs={12} md={8}>
        <Card sx={{ p: 2, height: 400 }}>
          <Skeleton width="100%" height={400} />
        </Card>
      </Grid>
    </Grid>
  </Container>
);
