import { Box, Button, Container, Grid, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { ValidatorCard, NetworkGraph, RiskDashboard } from '../../components';
import { useEigenData } from '../../hooks';

export const Explorer = () => {
  const navigate = useNavigate();
  const { validators, loading, error } = useEigenData();
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');

  const handleValidatorClick = (address: string) => {
    navigate(`/validator/${address}`);
  };

  if (loading) return <CircularProgress />;
  if (error) return <Typography color="error">{error.message}</Typography>;

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 4 }}>
        <Typography variant="h4">EigenLayer Explorer</Typography>
        <Box>
          <Button 
            variant={viewMode === 'cards' ? 'contained' : 'outlined'}
            onClick={() => setViewMode('cards')}
            sx={{ mr: 2 }}
          >
            Cards View
          </Button>
          <Button
            variant={viewMode === 'table' ? 'contained' : 'outlined'}
            onClick={() => setViewMode('table')}
          >
            Table View
          </Button>
        </Box>
      </Box>

      <Grid container spacing={4}>
        <Grid item xs={12} md={8}>
          <NetworkGraph 
            validators={validators} 
            onNodeClick={handleValidatorClick}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <RiskDashboard compact />
        </Grid>

        <Grid item xs={12}>
          {viewMode === 'cards' ? (
            <Grid container spacing={3}>
              {validators.map((validator) => (
                <Grid item xs={12} sm={6} md={4} key={validator.address}>
                  <ValidatorCard 
                    validator={validator}
                    onClick={handleValidatorClick}
                  />
                </Grid>
              ))}
            </Grid>
          ) : (
            <ValidatorTable 
              validators={validators}
              onRowClick={handleValidatorClick}
            />
          )}
        </Grid>
      </Grid>
    </Container>
  );
};
