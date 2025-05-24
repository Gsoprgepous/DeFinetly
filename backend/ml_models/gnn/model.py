import torch
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, global_mean_pool
from torch_geometric.data import Data

class ValidatorGNN(torch.nn.Module):
    def __init__(self, num_features=8, hidden_dim=64, num_classes=3):
        super().__init__()
        self.conv1 = GCNConv(num_features, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim)
        self.classifier = torch.nn.Linear(hidden_dim, num_classes)
        
    def forward(self, data: Data):
        # data.x: [num_nodes, num_features]
        # data.edge_index: [2, num_edges]
        
        x = self.conv1(data.x, data.edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=0.5, training=self.training)
        x = self.conv2(x, data.edge_index)
        
        # Градуированный пулинг
        x = global_mean_pool(x, data.batch)
        return self.classifier(x)

    def predict_risk(self, graph_data: dict) -> dict:
        """Интерфейс для предсказания"""
        self.eval()
        with torch.no_grad():
            data = self._preprocess(graph_data)
            out = self.forward(data)
            probs = F.softmax(out, dim=1)
            
        return {
            "low_risk": probs[0][0].item(),
            "medium_risk": probs[0][1].item(),
            "high_risk": probs[0][2].item()
        }

    def _preprocess(self, raw_data: dict) -> Data:
        edge_index = torch.tensor(raw_data["connections"], dtype=torch.long)
        node_features = torch.tensor(raw_data["node_features"], dtype=torch.float)
        return Data(x=node_features, edge_index=edge_index.t().contiguous())
