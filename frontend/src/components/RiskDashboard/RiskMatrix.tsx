import { Box, Typography } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';

type RiskItem = {
  id: string;
  validator: string;
  slashingRisk: number;
  liquidityRisk: number;
  concentrationRisk: number;
};

const columns: GridColDef[] = [
  { 
    field: 'validator', 
    headerName: 'Validator', 
    width: 150,
    renderCell: (params) => (
      <Box fontFamily="monospace">{params.value}</Box>
    )
  },
  { 
    field: 'slashingRisk', 
    headerName: 'Slashing', 
    width: 120,
    renderCell: (params) => (
      <Box 
        color={params.value > 0.7 ? '#f44336' : params.value > 0.3 ? '#ffa726' : '#66bb6a'}
      >
        {(params.value * 100).toFixed(1)}%
      </Box>
    )
  },
  // ...аналогичные колонки для других рисков
];

export const RiskMatrix = ({ data }: { data: RiskItem[] }) => (
  <Box sx={{ height: 400, width: '100%' }}>
    <DataGrid
      rows={data}
      columns={columns}
      pageSize={5}
      rowsPerPageOptions={[5]}
      disableSelectionOnClick
    />
  </Box>
);
