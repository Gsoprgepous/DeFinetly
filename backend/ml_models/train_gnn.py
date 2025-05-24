import torch
import torch.nn.functional as F
from torch_geometric.data import Data, DataLoader
from torch_geometric.nn import GATConv, global_max_pool
from torch.optim import AdamW
from torch.utils.tensorboard import SummaryWriter
import numpy as np
import os
from datetime import datetime
from model import ValidatorGNN  # Наша GNN модель из предыдущего шага

class GNNTrainer:
    def __init__(self, config):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = ValidatorGNN(
            num_features=config['num_features'],
            hidden_dim=config['hidden_dim'],
            num_classes=config['num_classes']
        ).to(self.device)
        self.optimizer = AdamW(
            self.model.parameters(),
            lr=config['lr'],
            weight_decay=config['weight_decay']
        )
        self.writer = SummaryWriter(log_dir=config['log_dir'])
        self.best_val_loss = float('inf')

    def train_epoch(self, loader):
        self.model.train()
        total_loss = 0
        
        for batch in loader:
            batch = batch.to(self.device)
            self.optimizer.zero_grad()
            out = self.model(batch)
            loss = F.cross_entropy(out, batch.y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()
            total_loss += loss.item()
            
        return total_loss / len(loader)

    def validate(self, loader):
        self.model.eval()
        total_loss = 0
        correct = 0
        
        with torch.no_grad():
            for batch in loader:
                batch = batch.to(self.device)
                out = self.model(batch)
                loss = F.cross_entropy(out, batch.y)
                total_loss += loss.item()
                pred = out.argmax(dim=1)
                correct += int((pred == batch.y).sum())
                
        return total_loss / len(loader), correct / len(loader.dataset)

    def save_checkpoint(self, epoch, is_best=False):
        state = {
            'epoch': epoch,
            'state_dict': self.model.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'config': self.config
        }
        
        torch.save(state, os.path.join(self.config['checkpoint_dir'], f'checkpoint_{epoch}.pt'))
        if is_best:
            torch.save(state, os.path.join(self.config['checkpoint_dir'], 'best_model.pt'))

    def train(self, train_dataset, val_dataset):
        train_loader = DataLoader(train_dataset, batch_size=self.config['batch_size'], shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=self.config['batch_size'])
        
        for epoch in range(1, self.config['epochs'] + 1):
            train_loss = self.train_epoch(train_loader)
            val_loss, val_acc = self.validate(val_loader)
            
            self.writer.add_scalar('Loss/train', train_loss, epoch)
            self.writer.add_scalar('Loss/val', val_loss, epoch)
            self.writer.add_scalar('Accuracy/val', val_acc, epoch)
            
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.save_checkpoint(epoch, is_best=True)
                
            print(f'Epoch: {epoch:03d}, '
                  f'Train Loss: {train_loss:.4f}, '
                  f'Val Loss: {val_loss:.4f}, '
                  f'Val Acc: {val_acc:.4f}')

        self.writer.close()

def prepare_datasets():
    """Генерация синтетических данных для примера"""
    train_data = []
    val_data = []
    
    # Пример: 100 тренировочных и 20 валидационных графов
    for i in range(100):
        num_nodes = np.random.randint(5, 15)
        edge_index = torch.tensor(
            np.random.choice(num_nodes, (2, num_nodes*2)), 
            dtype=torch.long
        )
        x = torch.randn((num_nodes, 8))  # 8 features per node
        y = torch.tensor(np.random.randint(0, 3), dtype=torch.long)
        train_data.append(Data(x=x, edge_index=edge_index, y=y))
        
    for i in range(20):
        num_nodes = np.random.randint(5, 15)
        edge_index = torch.tensor(
            np.random.choice(num_nodes, (2, num_nodes*2)), 
            dtype=torch.long
        )
        x = torch.randn((num_nodes, 8))
        y = torch.tensor(np.random.randint(0, 3), dtype=torch.long)
        val_data.append(Data(x=x, edge_index=edge_index, y=y))
        
    return train_data, val_data

if __name__ == "__main__":
    config = {
        'num_features': 8,
        'hidden_dim': 128,
        'num_classes': 3,
        'lr': 0.001,
        'weight_decay': 1e-5,
        'batch_size': 32,
        'epochs': 100,
        'log_dir': 'logs/gnn_' + datetime.now().strftime("%Y%m%d-%H%M%S"),
        'checkpoint_dir': 'checkpoints'
    }
    
    # Создание директорий
    os.makedirs(config['log_dir'], exist_ok=True)
    os.makedirs(config['checkpoint_dir'], exist_ok=True)
    
    # Подготовка данных
    train_data, val_data = prepare_datasets()
    
    # Обучение
    trainer = GNNTrainer(config)
    trainer.train(train_data, val_data)
