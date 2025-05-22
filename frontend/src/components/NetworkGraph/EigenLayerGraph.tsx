import CytoscapeComponent from 'react-cytoscapejs';

const elements = [
  { data: { id: 'eigen', label: 'EigenLayer' } },
  { data: { id: 'validator1', label: 'Validator A' } },
  { data: { source: 'validator1', target: 'eigen', label: '32 ETH' } }
];

export const EigenLayerGraph = () => (
  <CytoscapeComponent
    elements={elements}
    style={{ width: '100%', height: '500px' }}
    stylesheet={[{
      selector: 'node',
      style: {
        'label': 'data(label)',
        'background-color': '#6200EE'
      }
    }]}
  />
);
